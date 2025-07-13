# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.


import income_expense
import subdirectory_concat_gpt
import TPC_990_Boardmembers
import TPC_grants
import TPC_990
import os
import datetime
import uuid
import logging
import multiprocessing 
from folder_check import folder_check
import datetime
import income_expense_fixed




def main(file_download_directory=None, xml_unzip_directory=None):
    start=datetime.datetime.now()
    today=datetime.date.today()
    #Folder Creation
    folder_check(file_download_directory)
    folder_check(xml_unzip_directory)
    working_directory = os.path.join(file_download_directory,today.strftime("%Y-%m-%d"))
    folder_check(working_directory)
    print(f"Folders created at {file_download_directory} and {xml_unzip_directory}")

    file_location = os.path.join(file_download_directory, today.strftime("%Y-%m-%d"), 'downloads')
    folder_check(file_location)

    log_location = os.path.join(file_download_directory, today.strftime("%Y-%m-%d"), 'logs')
    folder_check(log_location)

    xml_location = os.path.join(xml_unzip_directory, today.strftime("%Y-%m-%d"), 'xml')
    folder_check(xml_location)
    
    # Create target directory for CSV files
    target_location = os.path.join(xml_unzip_directory, today.strftime("%Y-%m-%d"), 'csv')
    folder_check(target_location)
    
    error_location = os.path.join(xml_unzip_directory, today.strftime("%Y-%m-%d"), 'errors')
    folder_check(error_location)

    # Generate a unique run ID using timestamp and UUID
    run_id = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    log_file = f'{log_location}/tpc_run_{run_id}.log'
    os.makedirs(os.path.dirname(log_file), exist_ok=True)  # Ensure logs folder exists

       # Create separate handlers with different levels
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)  # Log everything to file
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)  # Only errors to console
    
    # Set up logging with both handlers
    logging.basicConfig(
        level=logging.INFO,  # Overall level
        format=f'%(asctime)s [RUN_ID: {run_id}] %(levelname)s: %(message)s',
        handlers=[file_handler, console_handler]
    )
    logging.info("=== Run started ===")

    try:
        """
        # Initialize TPC_990 logger first
        TPC_990.logger = TPC_990.setup_logging(log_location)
        
        logging.info(f"Downloading ZIP files to {file_location}")
        TPC_990.download_zip_files('https://www.irs.gov/charities-non-profits/form-990-series-downloads', file_location)
        
        logging.info("Extracting and moving XML files")
        TPC_990.extract_and_move_xml_files(file_location, xml_location, file_location)
        """
        logging.info(f"Processing BoardMembers and saving to {target_location}")
        TPC_990_Boardmembers.irs_boardmember(xml_location, target_location)

        logging.info(f"Processing Income and Expenses and saving to {target_location}")
        #income_expense.irs_expense_income(xml_location, target_location)
        income_expense_fixed.irs_expense_income(xml_location, target_location)

        logging.info(f"Processing Grants and saving to {target_location}")
        TPC_grants.irs_grants(xml_location, target_location)

        for prefix in ['income_expenses_', 'profile_', 'grants_', 'boardmembers_']:
            logging.info(f"Concatenating CSVs with prefix '{prefix}' in {target_location}")
            subdirectory_concat_gpt.folder_csv_concat(target_location, prefix, num_processes=4)
            logging.info(f"Processing folder for prefix '{prefix}'")
            subdirectory_concat_gpt.process_folder((target_location, prefix))

        endtime = datetime.datetime.now()
        elapsed_time = endtime - start
        print(f"Total processing time: {elapsed_time}")
        logging.info(f"Total processing time: {elapsed_time}")
        logging.info("=== Run completed successfully ===")
        
    except Exception as e:
        logging.exception(f"An error occurred during processing: {e}")
        logging.info("=== Run failed ===")
#         # Send notification to VS Code
   

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    file_location = '/Volumes/TPC'
    xml_location = '/Volumes/TPC/xmlsamples'
    main(file_location, xml_location)