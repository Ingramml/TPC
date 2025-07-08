import os
import requests
from bs4 import BeautifulSoup
import zipfile
import glob
import multiprocessing
import shutil
import logging
from datetime import datetime

try:
    import patoolib
    PATOOLIB_AVAILABLE = True
except ImportError:
    PATOOLIB_AVAILABLE = False

# Configure logging
def setup_logging(base_path=None):
    """Set up logging configuration"""
    # Create date-based directory structure for logs
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    if base_path:
        # Extract the base volume path (e.g., '/Volumes/TPC' from '/Volumes/TPC/2025-07-07/downloads/file.zip')
        # Find the TPC part in the path
        path_parts = base_path.split('/')
        if 'TPC' in path_parts:
            tpc_index = path_parts.index('TPC')
            base_volume = '/'.join(path_parts[:tpc_index + 1])  # e.g., '/Volumes/TPC'
        else:
            base_volume = '/Volumes/TPC'  # fallback
        
        log_dir = os.path.join(base_volume, current_date, 'logs')
    else:
        # Fallback to local directory
        log_dir = os.path.join('TPC', current_date, 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join(log_dir, f'tpc_990_{timestamp}.log')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_filename}")
    logger.info(f"Working directory: {os.getcwd()}")
    return logger

# Initialize logger (will be updated in main with proper path)
logger = None

def download_file(url, destination):
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
        response.raise_for_status()  # Raise an exception for bad status codes
        
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

def download_zip_files(url, file_location):
    logger.info(f"Starting to download ZIP files from URL: {url}")
    logger.info(f"Download location: {file_location}")
    try:
        logger.info(f"Fetching webpage content from {url}")
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        os.makedirs(file_location, exist_ok=True)
        logger.info(f"Created download directory: {file_location}")

        # Use find_all instead of findAll
        tables = soup.find_all(class_="link-label label-file label-file-zip")
        logger.info(f"Found {len(tables)} ZIP file links on the webpage")

        for i, link in enumerate(tables, 1):
            # Check if the parent has an 'href' attribute
            parent = link.parent
            if parent and parent.has_attr('href'):
                link_url = parent['href']
                if not link_url.startswith('http'):
                    # Handle relative URLs
                    link_url = requests.compat.urljoin(url, link_url)
                logger.info(f"Processing ZIP file {i}/{len(tables)}: {link_url}")
                download_file(link_url, file_location)
            else:
                logger.warning(f"Skipping link {i} - no valid href attribute found")
                
        logger.info("Completed downloading all ZIP files")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error occurred while fetching ZIP links from {url}: {e}")
        print(f"Network error occurred while fetching ZIP links: {e}")
    except Exception as e:
        logger.error(f"Unexpected error occurred while fetching ZIP links from {url}: {e}")
        print(f"An error occurred while fetching ZIP links: {e}")

def extract_zip(zip_file, unzip_location):
    logger.info(f"Starting extraction of ZIP file: {zip_file}")
    logger.info(f"Extraction destination: {unzip_location}")
    try:
        # Check if the ZIP file exists
        if not os.path.exists(zip_file):
            logger.error(f"ZIP file does not exist: {zip_file}")
            print(f"Error: '{zip_file}' does not exist.")
            return False

        # Check if the destination directory already exists
        if os.path.exists(unzip_location):
            logger.info(f"Directory already exists, skipping extraction: {unzip_location}")
            print(f"Files from '{zip_file}' have already been unzipped.")
        else:
            logger.info(f"Creating directory and extracting files: {unzip_location}")
            os.makedirs(unzip_location, exist_ok=True)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(unzip_location)
                logger.info(f"Successfully extracted {zip_file} to {unzip_location}")
                print(f"Files from '{zip_file}' unzipped successfully to {unzip_location} .")

        return True

    except zipfile.BadZipFile as e:
        logger.error(f"Invalid ZIP file: {zip_file} - {e}")
        print(f"Error: '{zip_file}' is not a valid ZIP file.")
    except zipfile.LargeZipFile as e:
        logger.error(f"ZIP file too large: {zip_file} - {e}")
        print(f"Error: '{zip_file}' is too large to be unzipped.")
    except Exception as e:
        logger.error(f"Error during ZIP extraction: {zip_file} - {e}")
        print(f"An error occurred while processing '{zip_file}': {e}")

        # Indicate that shutil.unpack_archive is being tried
        logger.info(f"Attempting alternative extraction method with shutil for: {zip_file}")
        print(f"Attempting to extract using shutil.unpack_archive")

        try:
            shutil.unpack_archive(zip_file, unzip_location)
            logger.info(f"Successfully extracted {zip_file} using shutil.unpack_archive")
            print(f"Files from '{zip_file}' extracted successfully to {unzip_location}.")
        except shutil.ReadError as e:
            logger.error(f"shutil.unpack_archive failed for {zip_file}: {e}")
            print(f"An error occurred while extracting '{zip_file}' with shutil.unpack_archive: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during shutil extraction of {zip_file}: {e}")
            print(f"An unexpected error occurred during extraction: {e} Shulti cannot exract {zip_file}")

        # Attempt to remove the directory if it was created
        if os.path.exists(unzip_location):
            try:
                os.rmdir(unzip_location)
                logger.info(f"Cleaned up directory after failed extraction: {unzip_location}")
                print(f"Removed directory '{unzip_location}'")
            except Exception as e:
                logger.error(f"Failed to clean up directory {unzip_location}: {e}")
                print(f"Failed to remove directory '{unzip_location}': {e}")

    return False
   
    #Add Shulti to try and unzip files that were unzipped by unzip package

def extract_and_move_xml_files_worker(zip_file, file_location, xml_location, base_path=None):
    # Function to handle the extraction and moving of XML files in a separate process
    # Initialize logger for this worker process
    worker_logger = setup_logging(base_path)
    worker_logger.info(f"Worker process starting for ZIP file: {zip_file}")
    files_moved = 0
    files_already_exist = 0
    try:
        # Create subfolder named after the ZIP file (without .zip extension)
        zip_basename = os.path.splitext(os.path.basename(zip_file))[0]
        unzip_location = os.path.join(file_location, zip_basename)
        worker_logger.info(f"Extraction will go to subfolder: {unzip_location}")
        
        # Check if the extraction folder already exists
        if os.path.exists(unzip_location):
            worker_logger.info(f"Extraction folder already exists: {unzip_location}")
            # Check for XML files in the existing folder and all subdirectories
            xml_files = glob.glob(os.path.join(unzip_location, '**', '*.xml'), recursive=True)
            worker_logger.info(f"Found {len(xml_files)} XML files in existing folder (searching recursively)")
        else:
            worker_logger.info(f"Extraction folder does not exist, extracting ZIP: {zip_file}")
            # Extract the ZIP file to the subfolder
            if PATOOLIB_AVAILABLE:
                try:
                    if extract_zip(zip_file, unzip_location):
                        worker_logger.info(f"Using patoolib for additional extraction: {zip_file}")
                        patoolib.extract_archive(zip_file, outdir=unzip_location)
                except NotImplementedError:
                    worker_logger.warning(f"patoolib is not implemented. Falling back to zipfile for '{zip_file}'.")
                    print(f"patoolib is not implemented. Falling back to zipfile for '{zip_file}'.")
                    extract_zip(zip_file, unzip_location)
            else:
                worker_logger.info(f"Using standard extraction method for: {zip_file}")
                extract_zip(zip_file, unzip_location)

            # After extraction, find XML files recursively in all subdirectories
            xml_files = glob.glob(os.path.join(unzip_location, '**', '*.xml'), recursive=True)
            worker_logger.info(f"Found {len(xml_files)} XML files after extraction (searching recursively)")
        
        # Process and move XML files to the final destination
        for xml_file in xml_files:
            file_name = os.path.basename(xml_file)
            subdirectory = file_name[:4]  # Use first 4 characters for year-based subdirectory
            new_xml_subdirectory = os.path.join(xml_location, subdirectory)
            os.makedirs(new_xml_subdirectory, exist_ok=True)
            new_xml_file_location = os.path.join(new_xml_subdirectory, file_name)

            if os.path.exists(new_xml_file_location):
                worker_logger.debug(f"File already exists in destination: {new_xml_file_location}")
                # Remove the source file since destination already exists
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

def extract_and_move_xml_files(file_location, xml_location, base_path=None):
    logger.info(f"Starting extraction and movement of XML files from {file_location} to {xml_location}")
    
    # Check if file_location is a single ZIP file or a directory
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

    # Using multiprocessing Pool to run the extraction tasks in parallel
    logger.info(f"Starting multiprocessing pool with {multiprocessing.cpu_count()} processes")
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.starmap(extract_and_move_xml_files_worker, [(zip_file, os.path.dirname(zip_file), xml_location, base_path) for zip_file in zip_files])

    files_moved = sum(result[0] for result in results)
    files_already_exist = sum(result[1] for result in results)
    logger.info(f"Extraction and movement completed: {files_moved} files moved, {files_already_exist} files already existed")
    print(f"{files_moved} files moved to {xml_location}.")
    print(f"{files_already_exist} files already existed in {xml_location}.")



if __name__ == "__main__":
    file_location = '/Volumes/TPC/2025-07-07/downloads/2021_TEOS_XML_01A.zip'  # Directory containing ZIP files
    xml_location = '/Volumes/TPC/2025-07-07/xml_files'  # Directory to store extracted XML files
    
    # Initialize logger with the file location for proper log directory
    logger = setup_logging(file_location)
    
    logger.info("Starting TPC 990 processing script")
    logger.info(f"Configuration - Download location: {file_location}")
    logger.info(f"Configuration - XML location: {xml_location}")
    
    # Download ZIP files (commented out)
    #logger.info("Starting ZIP file download process")
    #download_zip_files('https://www.irs.gov/charities-non-profits/form-990-series-downloads', file_location)
    
    # Extract and move XML files
    logger.info("Starting extraction and movement of XML files")
    extract_and_move_xml_files(file_location, xml_location, file_location)
    
    logger.info("TPC 990 processing script completed successfully")


