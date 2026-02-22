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

    logger, run_id = setup_main_logging(file_download_directory, console_output=False)
    logging.info("=== Run started ===")

    try:
        # Download index CSVs for all years, then download all zip files
        download_start = datetime.datetime.now()
        failed_downloads = download_all(file_location, log_dir=log_location) or []
        download_time = datetime.datetime.now() - download_start
        logging.info(f"Download time (index CSV): {download_time}")
        print(f"Download time (index CSV): {download_time}")

        extract_start = datetime.datetime.now()
        failed_extractions = TPC_990.extract_and_move_xml_files(file_location, xml_location, log_dir=log_location) or []
        extract_time = datetime.datetime.now() - extract_start
        logging.info(f"Extract time: {extract_time}")
        print(f"Extract time: {extract_time}")

        boardmember_start = datetime.datetime.now()
        logging.info(f"Processing BoardMembers and saving to {target_location}")
        TPC_990_Boardmembers.irs_boardmember(xml_location, target_location, log_dir=log_location)
        boardmember_time = datetime.datetime.now() - boardmember_start
        logging.info(f"BoardMembers time: {boardmember_time}")
        print(f"BoardMembers time: {boardmember_time}")

        ie_start = datetime.datetime.now()
        logging.info(f"Processing Income and Expenses and saving to {target_location}")
        income_expense.irs_expense_income(xml_location, target_location, log_dir=log_location)
        ie_time = datetime.datetime.now() - ie_start
        logging.info(f"Income/Expenses time: {ie_time}")
        print(f"Income/Expenses time: {ie_time}")

        grants_start = datetime.datetime.now()
        logging.info(f"Processing Grants and saving to {target_location}")
        TPC_grants.irs_grants(xml_location, target_location, log_dir=log_location)
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

        # Generate run report (.md)
        report_path = os.path.join(error_location, f"run_report_{today.strftime('%Y-%m-%d')}.md")
        has_errors = bool(failed_downloads or failed_extractions)

        md = []
        md.append(f"# Run Report - {today.strftime('%Y-%m-%d')}")
        md.append("")
        md.append(f"**Status:** {'ERRORS DETECTED' if has_errors else 'SUCCESS'}")
        md.append(f"**Total runtime:** {elapsed_time}")
        md.append("")

        md.append("## Timing")
        md.append("")
        md.append("| Stage | Duration |")
        md.append("|-------|----------|")
        md.append(f"| Download (index CSV) | {download_time} |")
        md.append(f"| Extract & move XML | {extract_time} |")
        md.append(f"| BoardMembers | {boardmember_time} |")
        md.append(f"| Income/Expenses | {ie_time} |")
        md.append(f"| Grants | {grants_time} |")
        md.append(f"| Concatenation | {concat_time} |")
        md.append(f"| **Total** | **{elapsed_time}** |")
        md.append("")

        if has_errors:
            md.append("## Errors")
            md.append("")
            md.append("> Data from the files listed below is **MISSING** from output CSVs.")
            md.append("")

            if failed_downloads:
                md.append(f"### Failed Downloads ({len(failed_downloads)})")
                md.append("")
                for f_name in failed_downloads:
                    md.append(f"- `{f_name}`")
                md.append("")

            if failed_extractions:
                md.append(f"### Failed Extractions ({len(failed_extractions)})")
                md.append("")
                for f_name in failed_extractions:
                    md.append(f"- `{f_name}`")
                md.append("")
        else:
            md.append("## Errors")
            md.append("")
            md.append("No errors - all files downloaded and extracted successfully.")
            md.append("")

        with open(report_path, 'w') as rf:
            rf.write('\n'.join(md))

        # Plain text version
        txt_path = os.path.join(error_location, f"run_report_{today.strftime('%Y-%m-%d')}.txt")
        txt = []
        txt.append(f"Run Report - {today.strftime('%Y-%m-%d')}")
        txt.append(f"{'='*50}")
        txt.append(f"Status:        {'ERRORS DETECTED' if has_errors else 'SUCCESS'}")
        txt.append(f"Total runtime: {elapsed_time}")
        txt.append("")
        txt.append("TIMING")
        txt.append(f"{'-'*50}")
        txt.append(f"  Download (index CSV):  {download_time}")
        txt.append(f"  Extract & move XML:    {extract_time}")
        txt.append(f"  BoardMembers:          {boardmember_time}")
        txt.append(f"  Income/Expenses:       {ie_time}")
        txt.append(f"  Grants:                {grants_time}")
        txt.append(f"  Concatenation:         {concat_time}")
        txt.append(f"  TOTAL:                 {elapsed_time}")
        txt.append("")

        if has_errors:
            txt.append("ERRORS")
            txt.append(f"{'-'*50}")
            txt.append("Data from the files listed below is MISSING from output CSVs.")
            txt.append("")

            if failed_downloads:
                txt.append(f"Failed Downloads ({len(failed_downloads)}):")
                for f_name in failed_downloads:
                    txt.append(f"  - {f_name}")
                txt.append("")

            if failed_extractions:
                txt.append(f"Failed Extractions ({len(failed_extractions)}):")
                for f_name in failed_extractions:
                    txt.append(f"  - {f_name}")
                txt.append("")
        else:
            txt.append("ERRORS")
            txt.append(f"{'-'*50}")
            txt.append("No errors - all files downloaded and extracted successfully.")
            txt.append("")

        with open(txt_path, 'w') as rf:
            rf.write('\n'.join(txt))

        # Console summary
        if has_errors:
            print(f"\n{'='*50}")
            print(f"ERRORS DETECTED - see reports in {error_location}")
            print(f"  Failed downloads:   {len(failed_downloads)}")
            print(f"  Failed extractions: {len(failed_extractions)}")
            print(f"{'='*50}")
            logging.error(f"Run reports saved to {error_location}")
        else:
            print(f"\nNo errors - all files downloaded and extracted successfully.")
            print(f"Reports saved to {error_location}")

        logging.info(f"Total processing time: {elapsed_time}")
        logging.info("=== Run completed successfully ===")

    except Exception as e:
        logging.exception(f"An error occurred during processing: {e}")
        logging.info("=== Run failed ===")

if __name__ == '__main__':
    main('/Volumes/TPC')
