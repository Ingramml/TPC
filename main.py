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
    
    xml_location = os.path.join(xml_unzip_directory, today.strftime("%Y-%m-%d"), 'xml')
    folder_check(xml_location)
    
    # Create target directory for CSV files
    target_location = os.path.join(xml_unzip_directory, today.strftime("%Y-%m-%d"), 'csv')
    folder_check(target_location)
    
    error_location = os.path.join(xml_unzip_directory, today.strftime("%Y-%m-%d"), 'errors')
    folder_check(error_location)

    # Generate a unique run ID using timestamp and UUID
    run_id = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    log_file = f'{working_directory}/logs/tpc_run_{run_id}.log'
    os.makedirs(os.path.dirname(log_file), exist_ok=True)  # Ensure logs folder exists

    # Log to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s [RUN_ID: {run_id}] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info("=== Run started ===")

    try:
        # Initialize TPC_990 logger first
        TPC_990.logger = TPC_990.setup_logging(file_location)
        
        logging.info(f"Downloading ZIP files to {file_location}")
        TPC_990.download_zip_files('https://www.irs.gov/charities-non-profits/form-990-series-downloads', file_location)
        
        logging.info("Extracting and moving XML files")
        TPC_990.extract_and_move_xml_files(file_location, xml_location, file_location)

        logging.info(f"Processing BoardMembers and saving to {target_location}")
        TPC_990_Boardmembers.irs_boardmember(xml_location, target_location)

        logging.info(f"Processing Income and Expenses and saving to {target_location}")
        #income_expense.irs_expense_income(xml_location, target_location)
        income_expense_fixed.irs_expense_income_fixed(xml_location, target_location)

        logging.info(f"Processing Grants and saving to {target_location}")
        TPC_grants.irs_grants(xml_location, target_location)

        for prefix in ['income_expenses_', 'profile_', 'grants_', 'boardmembers_']:
            logging.info(f"Concatenating CSVs with prefix '{prefix}' in {target_location}")
            subdirectory_concat_gpt.folder_csv_concat(target_location, prefix, num_processes=4)
            logging.info(f"Processing folder for prefix '{prefix}'")
            subdirectory_concat_gpt.process_folder((target_location, prefix))

        endtime = datetime.datetime.now()
        elapsed_time = endtime - start
        logging.info(f"Total processing time: {elapsed_time}")
        logging.info("=== Run completed successfully ===")
        
    except Exception as e:
        logging.exception(f"An error occurred during processing: {e}")
        logging.info("=== Run failed ===")

    TPC_990.download_zip_files('https://www.irs.gov/charities-non-profits/form-990-series-downloads', file_location)
    TPC_990.extract_and_move_xml_files(file_location, xml_location)
    #file_location = '/w/SSD/TPC/xml'
    #target_location = '/Volumes/SSD/TPC/csv'
    print(f"Processing BoardMembers and saving to {target_location}")
    TPC_990_Boardmembers.irs_boardmember(xml_location, target_location)
    print(f"Processing Income and Expenses and saving to {target_location}")
    income_expense.irs_expense_income(xml_location, target_location)
    print(f"Processing Grants and saving to {target_location}")
    TPC_grants.irs_grants(xml_location, target_location)
    #Political_contributions_2.political_contributions(file_location, target_location)
    subdirectory_concat_gpt.folder_csv_concat(target_location, 'income_expenses_', num_processes=4)
    subdirectory_concat_gpt.process_folder((target_location, 'income_expenses_'))
    subdirectory_concat_gpt.folder_csv_concat(target_location, 'profile_', num_processes=4)
    subdirectory_concat_gpt.process_folder((target_location, 'profile_'))
    subdirectory_concat_gpt.folder_csv_concat(target_location, 'grants_', num_processes=4)
    subdirectory_concat_gpt.process_folder((target_location, 'grants_'))
    subdirectory_concat_gpt.folder_csv_concat(target_location, 'boardmembers_', num_processes=4)
    subdirectory_concat_gpt.process_folder((target_location, 'boardmembers_'))
    endtime=datetime.datetime.now()
    elapsed_time = endtime - start
    print(f"Total processing time: {elapsed_time}")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    file_location = '/Volumes/TPC'
    xml_location = '/Volumes/TPC'
    main(file_location, xml_location)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/