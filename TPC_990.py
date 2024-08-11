import os
import requests
from bs4 import BeautifulSoup
import zipfile
import glob
import multiprocessing
import shutil

try:
    import patoolib
    PATOOLIB_AVAILABLE = True
except ImportError:
    PATOOLIB_AVAILABLE = False

def download_file(url, destination):
    try:
        file_name = os.path.basename(url)
        destination_path = os.path.join(destination, file_name)

        if os.path.exists(destination_path):
            print(f"File '{file_name}' already exists. Skipping download.")
            return

        response = requests.get(url, allow_redirects=True)
        with open(destination_path, 'wb') as file:
            file.write(response.content)

        print(f"File '{file_name}' downloaded successfully.")
    except Exception as e:
        print(f"Error occurred while downloading {url}: {e}")

def download_zip_files(url, file_location):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        os.makedirs(file_location, exist_ok=True)

        tables = soup.findAll(class_="link-label label-file label-file-zip")

        for link in tables:
            link_url = link.parent.contents[0].get('href')
            download_file(link_url, file_location)
    except Exception as e:
        print(f"An error occurred while fetching ZIP links: {e}")

def extract_zip(zip_file, unzip_location):
    try:
        # Check if the ZIP file exists
        if not os.path.exists(zip_file):
            print(f"Error: '{zip_file}' does not exist.")
            return False

        # Check if the destination directory already exists
        if os.path.exists(unzip_location):
            print(f"Files from '{zip_file}' have already been unzipped.")
        else:
            os.makedirs(unzip_location, exist_ok=True)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(unzip_location)
                print(f"Files from '{zip_file}' unzipped successfully to {unzip_location} .")

        return True

    except zipfile.BadZipFile as e:
        print(f"Error: '{zip_file}' is not a valid ZIP file.")
    except zipfile.LargeZipFile as e:
        print(f"Error: '{zip_file}' is too large to be unzipped.")
    except Exception as e:
        print(f"An error occurred while processing '{zip_file}': {e}")

        # Indicate that shutil.unpack_archive is being tried
        print(f"Attempting to extract using shutil.unpack_archive")

        try:
            shutil.unpack_archive(zip_file, unzip_location)
            print(f"Files from '{zip_file}' extracted successfully to {unzip_location}.")
        except shutil.ReadError as e:
            print(f"An error occurred while extracting '{zip_file}' with shutil.unpack_archive: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during extraction: {e} Shulti cannot exract {zip_file}")

        # Attempt to remove the directory if it was created
        if os.path.exists(unzip_location):
            try:
                os.rmdir(unzip_location)
                print(f"Removed directory '{unzip_location}'")
            except Exception as e:
                print(f"Failed to remove directory '{unzip_location}': {e}")

    return False
    """
        orginal method
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                if os.path.exists(unzip_location): # Fixed typo
                    print(f"Files from '{zip_file}' have already been unzipped.")
                else:
                    os.makedirs(unzip_location, exist_ok=True)
                    zip_ref.extractall(unzip_location)
                    print(f"Files from '{zip_file}' unzipped successfully to {unzip_location} .")
    
    
                return True
        except zipfile.BadZipFile as e:
            # Handle exceptions as before...
            print(f"Error: '{zip_file}' is not a valid ZIP file.")
        except zipfile.LargeZipFile as e:
            print(f"Error: '{zip_file}' is too large to be unzipped.")
        except Exception as e:
    
            print(f"Error occurred while processing '{zip_file}': {e}")
            import shutil
            try:
                shutil.unpack_archive(zip_file, unzip_location)
                print(f"Files from '{zip_file}' extracted successfully to {unzip_location}.")
            except shutil.ReadError as e:
                print(f"An error occurred while extracting '{zip_file}': {e}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
            print(f"Removing directory '{os.rmdir(unzip_location)}' ")
            os.rmdir(unzip_location)
    
        return False
"""
    #Add Shulti to try and unzip files that were unzipped by unzip package

def extract_and_move_xml_files_worker(zip_file, file_location, xml_location):
    # Function to handle the extraction and moving of XML files in a separate process
    files_moved = 0
    files_already_exist = 0
    try:
        unzip_location = os.path.join(file_location, os.path.splitext(os.path.basename(zip_file))[0])
        if os.path.exists(unzip_location):
            for xml_file in glob.glob(os.path.join(unzip_location, '*.xml')):
                file_name = os.path.basename(xml_file)
                subdirectory = file_name[:4]
                new_xml_subdirectory = os.path.join(xml_location, subdirectory)
                os.makedirs(new_xml_subdirectory, exist_ok=True)
                new_xml_file_location = os.path.join(new_xml_subdirectory, file_name)

                if os.path.exists(new_xml_file_location):
                    os.remove(xml_file)
                    files_already_exist += 1
                else:
                    os.rename(xml_file, new_xml_file_location)
                    files_moved += 1
        else:
            if PATOOLIB_AVAILABLE:
                try:
                    if extract_zip(zip_file, unzip_location):
                        patoolib.extract_archive(zip_file, outdir=unzip_location)
                except NotImplementedError:
                    print(f"patoolib is not implemented. Falling back to zipfile for '{zip_file}'.")
                    extract_zip(zip_file, unzip_location)
            else:
                extract_zip(zip_file, unzip_location)

            for xml_file in glob.glob(os.path.join(unzip_location, '*.xml')):
                file_name = os.path.basename(xml_file)
                subdirectory = file_name[:4]
                new_xml_subdirectory = os.path.join(xml_location, subdirectory)
                os.makedirs(new_xml_subdirectory, exist_ok=True)
                new_xml_file_location = os.path.join(new_xml_subdirectory, file_name)

                if os.path.exists(new_xml_file_location):
                    #os.remove(xml_file)
                    files_already_exist += 1
                else:
                    os.rename(xml_file, new_xml_file_location)
                    files_moved += 1

        return files_moved, files_already_exist

    except Exception as e:
        print(f"Error occurred while processing '{zip_file}': {e}")
        return 0, 0

def extract_and_move_xml_files(file_location, xml_location):
    zip_files = glob.glob(os.path.join(file_location, '*.zip'))

    # Using multiprocessing Pool to run the extraction tasks in parallel
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.starmap(extract_and_move_xml_files_worker, [(zip_file, file_location, xml_location) for zip_file in zip_files])

    files_moved = sum(result[0] for result in results)
    files_already_exist = sum(result[1] for result in results)
    print(f"{files_moved} files moved to {xml_location}.")
    print(f"{files_already_exist} files already existed in {xml_location}.")



if __name__ == "__main__":
    file_location = '/Volumes/TPC/downloads'
    xml_location = '/Volumes/TPC/xml'

    #download_zip_files('https://www.irs.gov/charities-non-profits/form-990-series-downloads', file_location)
    extract_and_move_xml_files(file_location, xml_location)
