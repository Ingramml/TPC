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
from download_from_index import download_all


def main(file_download_directory=None):

    if file_download_directory is None:
        raise ValueError("file_download_directory cannot be None")

    start=datetime.datetime.now()
    today=datetime.date.today()
    #Folder Creation
    folder_check(file_download_directory)
    working_directory = os.path.join(file_download_directory, today.strftime("%Y-%m-%d"))
    folder_check(working_directory)

    file_location = os.path.join(working_directory, 'downloads')
    folder_check(file_location)

    log_location = os.path.join(working_directory, 'logs')
    folder_check(log_location)

    xml_location = os.path.join(working_directory, 'xmlfiles')
    folder_check(xml_location)

    target_location = os.path.join(working_directory, 'csv')
    folder_check(target_location)

    error_location = os.path.join(working_directory, 'errors')
    folder_check(error_location)

    print(f"Folders created under {working_directory}")

    logger, run_id = setup_main_logging(file_download_directory)
    logging.info("=== Run started ===")

    try:
        # Download index CSVs for all years, then download all zip files
        download_start = datetime.datetime.now()
        download_all(file_location)
        download_time = datetime.datetime.now() - download_start
        logging.info(f"Download time (index CSV): {download_time}")
        print(f"Download time (index CSV): {download_time}")

        extract_start = datetime.datetime.now()
        TPC_990.extract_and_move_xml_files(file_location, xml_location)
        extract_time = datetime.datetime.now() - extract_start
        logging.info(f"Extract time: {extract_time}")
        print(f"Extract time: {extract_time}")

        boardmember_start = datetime.datetime.now()
        logging.info(f"Processing BoardMembers and saving to {target_location}")
        TPC_990_Boardmembers.irs_boardmember(xml_location, target_location)
        boardmember_time = datetime.datetime.now() - boardmember_start
        logging.info(f"BoardMembers time: {boardmember_time}")
        print(f"BoardMembers time: {boardmember_time}")

        ie_start = datetime.datetime.now()
        logging.info(f"Processing Income and Expenses and saving to {target_location}")
        income_expense.irs_expense_income(xml_location, target_location)
        ie_time = datetime.datetime.now() - ie_start
        logging.info(f"Income/Expenses time: {ie_time}")
        print(f"Income/Expenses time: {ie_time}")

        grants_start = datetime.datetime.now()
        logging.info(f"Processing Grants and saving to {target_location}")
        TPC_grants.irs_grants(xml_location, target_location)
        grants_time = datetime.datetime.now() - grants_start
        logging.info(f"Grants time: {grants_time}")
        print(f"Grants time: {grants_time}")

        concat_start = datetime.datetime.now()
        for prefix in ['income_expenses_', 'profile_', 'grants_', 'boardmembers_']:
            logging.info(f"Concatenating CSVs with prefix '{prefix}' in {target_location}")
            subdirectory_concat_gpt.folder_csv_concat(target_location, prefix, num_processes=4)
            logging.info(f"Processing folder for prefix '{prefix}'")
            subdirectory_concat_gpt.process_folder((target_location, prefix))
        concat_time = datetime.datetime.now() - concat_start
        logging.info(f"Concatenation time: {concat_time}")
        print(f"Concatenation time: {concat_time}")

        endtime = datetime.datetime.now()
        elapsed_time = endtime - start

        print(f"\n{'='*50}")
        print(f"TIMING SUMMARY")
        print(f"{'='*50}")
        print(f"  Download (index CSV):  {download_time}")
        print(f"  Extract & move XML:    {extract_time}")
        print(f"  BoardMembers:          {boardmember_time}")
        print(f"  Income/Expenses:       {ie_time}")
        print(f"  Grants:                {grants_time}")
        print(f"  Concatenation:         {concat_time}")
        print(f"{'='*50}")
        print(f"  TOTAL:                 {elapsed_time}")
        print(f"{'='*50}")

        logging.info(f"Total processing time: {elapsed_time}")
        logging.info("=== Run completed successfully ===")

    except Exception as e:
        logging.exception(f"An error occurred during processing: {e}")
        logging.info("=== Run failed ===")

if __name__ == '__main__':
    main('/Volumes/TPC')
