import os
import gzip
import tarfile
import subprocess
import requests
from bs4 import BeautifulSoup
import zipfile
import glob
import multiprocessing
import shutil
from urllib.parse import urljoin
from logging_setup import get_standard_logger

try:
    import patoolib
    PATOOLIB_AVAILABLE = True
except ImportError:
    PATOOLIB_AVAILABLE = False


def download_file(url, destination, logger):
    from tqdm import tqdm as _tqdm
    file_name = os.path.basename(url)
    try:
        destination_path = os.path.join(destination, file_name)

        if os.path.exists(destination_path):
            return True

        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()

        with open(destination_path, 'wb') as file:
            file.write(response.content)

        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error occurred while downloading {url}: {e}")
        _tqdm.write(f"DOWNLOAD ERROR: {file_name} - {e}")
        return False
    except IOError as e:
        logger.error(f"File I/O error occurred while saving {url}: {e}")
        _tqdm.write(f"DOWNLOAD ERROR: {file_name} - {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error occurred while downloading {url}: {e}")
        _tqdm.write(f"DOWNLOAD ERROR: {file_name} - {e}")
        return False


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


def _redownload_zip(zip_file, extract_logger):
    """Re-download a corrupt zip file from the IRS server."""
    file_name = os.path.basename(zip_file)
    batch_id = os.path.splitext(file_name)[0].upper()
    year = batch_id[:4]
    url = f"https://apps.irs.gov/pub/epostcard/990/xml/{year}/{batch_id}.zip"

    extract_logger.info(f"Re-downloading corrupt file: {url}")
    try:
        os.remove(zip_file)
        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()
        with open(zip_file, 'wb') as f:
            f.write(response.content)
        extract_logger.info(f"Re-downloaded {file_name} ({len(response.content)} bytes)")
        return True
    except Exception as e:
        extract_logger.error(f"Re-download failed for {file_name}: {e}")
        return False


def _detect_file_type(file_path):
    """Read magic bytes to determine the actual file format."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
    except Exception:
        return "unknown"

    if header[:4] == b'PK\x03\x04':
        return "zip"
    if header[:2] == b'\x1f\x8b':
        return "gzip"
    if header[:5] == b'%PDF-':
        return "pdf"
    if header[:1] in (b'<', b'\xef'):  # UTF-8 BOM or raw '<'
        return "html_or_xml"
    if len(header) >= 6 and header[:6] == b'Rar!\x1a\x07':
        return "rar"
    if len(header) >= 6 and b'ustar' in header:
        return "tar"
    return "unknown"


def _extract_gzip(gz_file, unzip_location, extract_logger):
    """Extract a gzip-compressed file (plain gzip or .tar.gz)."""
    os.makedirs(unzip_location, exist_ok=True)

    # Try as tar.gz first
    try:
        with tarfile.open(gz_file, 'r:gz') as tar:
            tar.extractall(unzip_location)
            extract_logger.info(f"Successfully extracted {gz_file} as tar.gz")
            return True
    except tarfile.TarError:
        extract_logger.info(f"{gz_file} is not tar.gz, trying plain gzip")

    # Plain gzip — decompress to a single file
    try:
        out_name = os.path.basename(gz_file).replace('.zip', '.xml')
        out_path = os.path.join(unzip_location, out_name)
        with open(gz_file, 'rb') as raw_f:
            with gzip.GzipFile(fileobj=raw_f) as f_in, open(out_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        extract_logger.info(f"Successfully extracted {gz_file} as plain gzip -> {out_path}")
        return True
    except Exception as e:
        extract_logger.warning(f"Plain gzip extraction failed for {gz_file}: {e}")
        return False


def _extract_with_system_tool(file_path, unzip_location, extract_logger):
    """Try system unzip, then 7z as last-resort extraction."""
    os.makedirs(unzip_location, exist_ok=True)

    # Try system unzip
    try:
        result = subprocess.run(
            ['unzip', '-o', file_path, '-d', unzip_location],
            capture_output=True, text=True, timeout=1800
        )
        if result.returncode == 0:
            extract_logger.info(f"Successfully extracted {file_path} using system unzip")
            return True
        extract_logger.warning(f"System unzip failed (rc={result.returncode}): {result.stderr.strip()}")
    except FileNotFoundError:
        extract_logger.info("System unzip not available")
    except Exception as e:
        extract_logger.warning(f"System unzip error for {file_path}: {e}")

    # Try 7z / 7zz (Homebrew on macOS installs as 7zz)
    for cmd in ['7z', '7zz']:
        try:
            result = subprocess.run(
                [cmd, 'x', file_path, f'-o{unzip_location}', '-y'],
                capture_output=True, text=True, timeout=1800
            )
            if result.returncode == 0:
                extract_logger.info(f"Successfully extracted {file_path} using {cmd}")
                return True
            extract_logger.warning(f"{cmd} failed (rc={result.returncode}): {result.stderr.strip()}")
        except FileNotFoundError:
            continue
        except Exception as e:
            extract_logger.warning(f"{cmd} error for {file_path}: {e}")

    return False


def extract_zip(zip_file, unzip_location, extract_logger):
    from tqdm import tqdm as _tqdm
    extract_logger.info(f"Starting extraction of ZIP file: {zip_file}")
    extract_logger.info(f"Extraction destination: {unzip_location}")

    try:
        if not os.path.exists(zip_file):
            extract_logger.error(f"ZIP file does not exist: {zip_file}")
            return False

        # Validate zip file before attempting extraction
        if os.path.getsize(zip_file) == 0:
            extract_logger.warning(f"ZIP file is empty (0 bytes): {zip_file}")
            if not _redownload_zip(zip_file, extract_logger):
                _tqdm.write(f"EXTRACT ERROR: {os.path.basename(zip_file)} - empty file, re-download failed")
                return False

        # Detect actual file type via magic bytes
        file_type = _detect_file_type(zip_file)
        extract_logger.info(f"Detected file type for {os.path.basename(zip_file)}: {file_type}")

        if file_type == "html_or_xml":
            extract_logger.warning(f"{zip_file} is HTML/XML, not an archive — likely an error page from IRS server")
            _tqdm.write(f"EXTRACT WARNING: {os.path.basename(zip_file)} - file is HTML/XML, not a ZIP. Re-downloading...")
            if _redownload_zip(zip_file, extract_logger):
                file_type = _detect_file_type(zip_file)
                extract_logger.info(f"After re-download, detected file type: {file_type}")
                if file_type == "html_or_xml":
                    _tqdm.write(f"EXTRACT ERROR: {os.path.basename(zip_file)} - still HTML/XML after re-download")
                    return False
            else:
                return False

        os.makedirs(unzip_location, exist_ok=True)

        # If detected as gzip, try gzip/tar.gz extraction first
        if file_type == "gzip":
            extract_logger.info(f"File is gzip-compressed, trying gzip/tar.gz extraction")
            if _extract_gzip(zip_file, unzip_location, extract_logger):
                return True

        # Try standard zipfile
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(unzip_location)
                extract_logger.info(f"Successfully extracted {zip_file} using zipfile")
                return True
        except zipfile.BadZipFile:
            extract_logger.warning(f"Bad zip file: {zip_file} - attempting re-download")
            if _redownload_zip(zip_file, extract_logger):
                # Re-check file type after re-download
                new_type = _detect_file_type(zip_file)
                extract_logger.info(f"After re-download, detected file type: {new_type}")
                if new_type == "gzip":
                    if _extract_gzip(zip_file, unzip_location, extract_logger):
                        return True
                try:
                    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                        zip_ref.extractall(unzip_location)
                        extract_logger.info(f"Successfully extracted {zip_file} after re-download")
                        return True
                except Exception as e:
                    extract_logger.error(f"Extraction still failed after re-download: {e}")
        except Exception as e:
            extract_logger.warning(f"Standard zipfile failed for {zip_file}: {e}, trying alternative methods")

        # Try shutil.unpack_archive as fallback
        try:
            shutil.unpack_archive(zip_file, unzip_location)
            extract_logger.info(f"Successfully extracted {zip_file} using shutil.unpack_archive")
            return True
        except Exception as e:
            extract_logger.warning(f"shutil.unpack_archive failed for {zip_file}: {e}")

        # Try patoolib if available
        if PATOOLIB_AVAILABLE:
            try:
                patoolib.extract_archive(zip_file, outdir=unzip_location)
                extract_logger.info(f"Successfully extracted {zip_file} using patoolib")
                return True
            except Exception as e:
                extract_logger.warning(f"patoolib failed for {zip_file}: {e}")

        # Try system unzip / 7z as last resort
        if _extract_with_system_tool(zip_file, unzip_location, extract_logger):
            return True

        extract_logger.error(f"All extraction methods failed for {zip_file} (detected type: {file_type})")
        _tqdm.write(f"EXTRACT ERROR: {os.path.basename(zip_file)} - all methods failed (type: {file_type})")
        return False

    except Exception as e:
        extract_logger.error(f"Unexpected error during extraction of {zip_file}: {e}")
        _tqdm.write(f"EXTRACT ERROR: {os.path.basename(zip_file)} - {e}")
        return False


def extract_and_move_xml_files_worker(zip_file, file_location, xml_location, log_dir=None):
    worker_logger = get_standard_logger('tpc_990', file_location, log_dir=log_dir)
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
                return 0, 0, os.path.basename(zip_file)
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
        return files_moved, files_already_exist, None

    except Exception as e:
        worker_logger.error(f"Error occurred while processing '{zip_file}': {e}")
        return 0, 0, os.path.basename(zip_file)


def extract_and_move_xml_files(file_location, xml_location, logger=None, log_dir=None):
    if logger is None:
        logger = get_standard_logger('tpc_990', file_location, log_dir=log_dir)

    logger.info(f"Starting extraction and movement of XML files from {file_location} to {xml_location}")

    if os.path.isfile(file_location) and file_location.endswith('.zip'):
        logger.info(f"Single ZIP file detected: {file_location}")
        zip_files = [file_location]
    elif os.path.isdir(file_location):
        logger.info(f"Directory detected, scanning for ZIP files: {file_location}")
        zip_files = glob.glob(os.path.join(file_location, '*.zip'))
    else:
        logger.error(f"Invalid file_location: {file_location} - must be a ZIP file or directory containing ZIP files")
        return

    logger.info(f"Found {len(zip_files)} ZIP files to process")

    logger.info(f"Starting multiprocessing pool with {multiprocessing.cpu_count()} processes")
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.starmap(extract_and_move_xml_files_worker, [(zip_file, os.path.dirname(zip_file), xml_location, log_dir) for zip_file in zip_files])

    files_moved = sum(result[0] for result in results)
    files_already_exist = sum(result[1] for result in results)
    failed_extractions = [result[2] for result in results if result[2] is not None]
    logger.info(f"Extraction and movement completed: {files_moved} files moved, {files_already_exist} files already existed")
    if failed_extractions:
        logger.error(f"Failed to extract {len(failed_extractions)} files: {failed_extractions}")
    return failed_extractions
