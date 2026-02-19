import subdirectory_concat_gpt
import TPC_990_Boardmembers
import TPC_grants
import TPC_990
import income_expense
import os
import datetime
import logging
from folder_check import folder_check
from logging_setup import setup_main_logging

#TODO
# - Add error handling for folder creation
# - Add error handling for file operations
# - General Error or General error needs to be forced Null and traced by to each file



def main(file_download_directory=None, xml_unzip_directory=None):

    if file_download_directory is None:
        raise ValueError("file_download_directory cannot be None")
    if xml_unzip_directory is None:
        raise ValueError("xml_unzip_directory cannot be None")


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

    logger, run_id = setup_main_logging(file_download_directory)
    logging.info("=== Run started ===")

    try:
        # TODO: Re-enable download and extraction steps when ready
        # TPC_990.download_zip_files(url, file_location)
        # TPC_990.extract_and_move_xml_files(file_location, xml_location, file_location)

        logging.info(f"Processing BoardMembers and saving to {target_location}")
        TPC_990_Boardmembers.irs_boardmember(xml_location, target_location)

        logging.info(f"Processing Income and Expenses and saving to {target_location}")
        income_expense.irs_expense_income(xml_location, target_location)

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

if __name__ == '__main__':
    file_location = '/Volumes/TPC'
    xml_location = '/Volumes/TPC/xmlfiles'
    main(file_location, xml_location)
