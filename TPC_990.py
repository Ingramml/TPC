import os
import requests
from bs4 import BeautifulSoup
import zipfile
import glob
import multiprocessing
import shutil
import logging
from datetime import datetime
from urllib.parse import urljoin
from logging_setup import get_standard_logger

try:
    import patoolib
    PATOOLIB_AVAILABLE = True
except ImportError:
    PATOOLIB_AVAILABLE = False


def download_file(url, destination, logger):
    logger.info(f"Starting download of file from URL: {url}")
    try:
        file_name = os.path.basename(url)
        destination_path = os.path.join(destination, file_name)

        if os.path.exists(destination_path):
            logger.info(f"File '{file_name}' already exists at {destination_path}. Skipping download.")
            print(f"File '{file_name}' already exists. Skipping download.")
            return

        logger.info(f"Downloading file '{file_name}' to {destination_path}")
        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()

        with open(destination_path, 'wb') as file:
            file.write(response.content)

        logger.info(f"File '{file_name}' downloaded successfully to {destination_path}")
        print(f"File '{file_name}' downloaded successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error occurred while downloading {url}: {e}")
        print(f"Network error occurred while downloading {url}: {e}")
    except IOError as e:
        logger.error(f"File I/O error occurred while saving {url}: {e}")
        print(f"File I/O error occurred while saving {url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error occurred while downloading {url}: {e}")
        print(f"Error occurred while downloading {url}: {e}")


def download_zip_files(url, file_location, logger=None):
    if logger is None:
        logger = get_standard_logger('tpc_990', file_location)

    logger.info(f"Starting to download ZIP files from URL: {url}")
    logger.info(f"Download location: {file_location}")
    try:
        logger.info(f"Fetching webpage content from {url}")
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        os.makedirs(file_location, exist_ok=True)
        logger.info(f"Created download directory: {file_location}")

        tables = soup.find_all(class_="link-label label-file label-file-zip")
        logger.info(f"Found {len(tables)} ZIP file links on the webpage")

        for i, link in enumerate(tables, 1):
            parent = link.parent
            if parent and parent.has_attr('href'):
                link_url = str(parent['href'])
                if not link_url.startswith('http'):
                    link_url = urljoin(url, link_url)
                logger.info(f"Processing ZIP file {i}/{len(tables)}: {link_url}")
                download_file(link_url, file_location, logger)
            else:
                logger.warning(f"Skipping link {i} - no valid href attribute found")

        logger.info("Completed downloading all ZIP files")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error occurred while fetching ZIP links from {url}: {e}")
        print(f"Network error occurred while fetching ZIP links: {e}")
    except Exception as e:
        logger.error(f"Unexpected error occurred while fetching ZIP links from {url}: {e}")
        print(f"An error occurred while fetching ZIP links: {e}")


def extract_zip(zip_file, unzip_location, extract_logger):
    extract_logger.info(f"Starting extraction of ZIP file: {zip_file}")
    extract_logger.info(f"Extraction destination: {unzip_location}")

    try:
        if not os.path.exists(zip_file):
            extract_logger.error(f"ZIP file does not exist: {zip_file}")
            print(f"Error: '{zip_file}' does not exist.")
            return False

        os.makedirs(unzip_location, exist_ok=True)

        # Try standard zipfile first
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(unzip_location)
                extract_logger.info(f"Successfully extracted {zip_file} using zipfile")
                print(f"Files from '{zip_file}' unzipped successfully to {unzip_location}")
                return True
        except zipfile.BadZipFile:
            extract_logger.warning(f"Standard zipfile failed for {zip_file}, trying alternative methods")
        except Exception as e:
            extract_logger.warning(f"Standard zipfile failed for {zip_file}: {e}, trying alternative methods")

        # Try shutil.unpack_archive as fallback
        try:
            shutil.unpack_archive(zip_file, unzip_location)
            extract_logger.info(f"Successfully extracted {zip_file} using shutil.unpack_archive")
            print(f"Files from '{zip_file}' extracted successfully using shutil")
            return True
        except Exception as e:
            extract_logger.warning(f"shutil.unpack_archive failed for {zip_file}: {e}")

        # Try patoolib if available
        if PATOOLIB_AVAILABLE:
            try:
                patoolib.extract_archive(zip_file, outdir=unzip_location)
                extract_logger.info(f"Successfully extracted {zip_file} using patoolib")
                print(f"Files from '{zip_file}' extracted successfully using patoolib")
                return True
            except Exception as e:
                extract_logger.warning(f"patoolib failed for {zip_file}: {e}")

        extract_logger.error(f"All extraction methods failed for {zip_file}")
        print(f"Error: Could not extract '{zip_file}' using any available method")
        return False

    except Exception as e:
        extract_logger.error(f"Unexpected error during extraction of {zip_file}: {e}")
        print(f"Unexpected error occurred during extraction: {e}")
        return False


def extract_and_move_xml_files_worker(zip_file, file_location, xml_location, base_path=None):
    worker_logger = get_standard_logger('tpc_990', file_location)
    worker_logger.info(f"Worker process starting for ZIP file: {zip_file}")
    files_moved = 0
    files_already_exist = 0

    try:
        zip_basename = os.path.splitext(os.path.basename(zip_file))[0]
        unzip_location = os.path.join(file_location, zip_basename)
        worker_logger.info(f"Extraction will go to subfolder: {unzip_location}")

        existing_xml_files = []
        if os.path.exists(unzip_location):
            existing_xml_files = glob.glob(os.path.join(unzip_location, '**', '*.xml'), recursive=True)
            worker_logger.info(f"Found {len(existing_xml_files)} existing XML files in {unzip_location}")

        if not existing_xml_files:
            worker_logger.info(f"Extracting ZIP file: {zip_file}")
            if not extract_zip(zip_file, unzip_location, worker_logger):
                worker_logger.error(f"Failed to extract {zip_file}")
                return 0, 0
        else:
            worker_logger.info(f"Skipping extraction - XML files already exist in {unzip_location}")

        xml_files = glob.glob(os.path.join(unzip_location, '**', '*.xml'), recursive=True)
        worker_logger.info(f"Found {len(xml_files)} XML files to process")

        for xml_file in xml_files:
            file_name = os.path.basename(xml_file)
            subdirectory = file_name[:4]
            new_xml_subdirectory = os.path.join(xml_location, subdirectory)
            os.makedirs(new_xml_subdirectory, exist_ok=True)
            new_xml_file_location = os.path.join(new_xml_subdirectory, file_name)

            if os.path.exists(new_xml_file_location):
                worker_logger.debug(f"File already exists in destination: {new_xml_file_location}")
                os.remove(xml_file)
                files_already_exist += 1
            else:
                worker_logger.debug(f"Moving XML file from {xml_file} to {new_xml_file_location}")
                os.rename(xml_file, new_xml_file_location)
                files_moved += 1

        worker_logger.info(f"Worker completed for {zip_file}: {files_moved} moved, {files_already_exist} already existed")
        return files_moved, files_already_exist

    except Exception as e:
        worker_logger.error(f"Error occurred while processing '{zip_file}': {e}")
        print(f"Error occurred while processing '{zip_file}': {e}")
        return 0, 0


def extract_and_move_xml_files(file_location, xml_location, base_path=None, logger=None):
    if logger is None:
        logger = get_standard_logger('tpc_990', file_location)

    logger.info(f"Starting extraction and movement of XML files from {file_location} to {xml_location}")

    if os.path.isfile(file_location) and file_location.endswith('.zip'):
        logger.info(f"Single ZIP file detected: {file_location}")
        zip_files = [file_location]
    elif os.path.isdir(file_location):
        logger.info(f"Directory detected, scanning for ZIP files: {file_location}")
        zip_files = glob.glob(os.path.join(file_location, '*.zip'))
    else:
        logger.error(f"Invalid file_location: {file_location} - must be a ZIP file or directory containing ZIP files")
        print(f"Error: '{file_location}' is not a valid ZIP file or directory.")
        return

    logger.info(f"Found {len(zip_files)} ZIP files to process")

    logger.info(f"Starting multiprocessing pool with {multiprocessing.cpu_count()} processes")
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.starmap(extract_and_move_xml_files_worker, [(zip_file, os.path.dirname(zip_file), xml_location, base_path) for zip_file in zip_files])

    files_moved = sum(result[0] for result in results)
    files_already_exist = sum(result[1] for result in results)
    logger.info(f"Extraction and movement completed: {files_moved} files moved, {files_already_exist} files already existed")
    print(f"{files_moved} files moved to {xml_location}.")
    print(f"{files_already_exist} files already existed in {xml_location}.")
