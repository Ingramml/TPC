import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
from multiprocessing import Pool, cpu_count
import json
import logging
import shutil
from datetime import datetime

from logging_setup import get_standard_logger
from error_handler import move_error_file
from xml_helpers import safe_find_element, get_element_text


def process_single_file(file_path: str, target_location: str, logger: logging.Logger) -> tuple:
    """
    Process a single XML file to extract Section 527 political contribution data.

    Returns:
        tuple: (result_string, contributions_dict_or_None)
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Check return type — Schedule C (Part I-C, Line 5) only applies to 990 and 990EZ.
        # 990PF and 990T do not file Schedule C and never have Section527PoliticalOrgGrp.
        return_type_check = root[0].find('./{http://www.irs.gov/efile}ReturnTypeCd')
        if return_type_check is None:
            return_type_check = root[0].find('./{http://www.irs.gov/efile}ReturnType')
        return_type = return_type_check.text if return_type_check is not None else ''

        if return_type not in ('990', '990EZ'):
            return (f"Skipped {return_type} file {file_path}", None)

        # Get filer EIN
        GrantorEIN_check = root[0].find('./*{http://www.irs.gov/efile}EIN')
        if GrantorEIN_check is None:
            error_reason = "No EIN found in XML file"
            logger.warning(f"{error_reason}: {os.path.basename(file_path)}")
            move_error_file(file_path, error_reason=error_reason, logger=logger)
            return (f"Error: {error_reason} - {file_path}", None)

        filer_ein = GrantorEIN_check.text

        # Get tax year
        year_check = safe_find_element(
            root[0],
            './{http://www.irs.gov/efile}TaxYr',
            './{http://www.irs.gov/efile}TaxYear'
        )
        if year_check is None:
            begindate_check = safe_find_element(
                root[0],
                './{http://www.irs.gov/efile}TaxPeriodBeginDate',
                './{http://www.irs.gov/efile}TaxPeriodBeginDt'
            )
            begindate = get_element_text(begindate_check)
            year = begindate[0:4] if len(begindate) >= 4 else ''
        else:
            year = get_element_text(year_check)

        if not year:
            error_reason = "No valid year found in XML file"
            logger.warning(f"{error_reason}: {os.path.basename(file_path)}")
            move_error_file(file_path, error_reason=error_reason, logger=logger)
            return (f"Error: {error_reason} - {file_path}", None)

        # Create year folder
        folder = os.path.join(target_location, year)
        os.makedirs(folder, exist_ok=True)

        # Check if already processed
        filecheck = os.path.join(folder, f'political_contributions_{filer_ein}.csv')
        if os.path.isfile(filecheck):
            logger.debug(f"File already processed, skipping: {os.path.basename(file_path)}")
            return (f"Already processed {file_path}", None)

        # Look for Section 527 political organization groups
        donations = root[1].findall('.//{http://www.irs.gov/efile}Section527PoliticalOrgGrp')

        if not donations:
            return (f"No political contribution data found in {file_path}", None)

        rows = []
        contributions_dict = {}

        for recipient in donations:
            # Recipient EIN
            recipient_ein_check = recipient.find('.//{http://www.irs.gov/efile}EIN')
            recipient_ein = get_element_text(recipient_ein_check)

            # Business name line 1
            name1_check = safe_find_element(
                recipient,
                './/{http://www.irs.gov/efile}BusinessNameLine1Txt',
                './/{http://www.irs.gov/efile}BusinessNameLine1'
            )
            business_name1 = get_element_text(name1_check).upper()

            # Business name line 2
            name2_check = safe_find_element(
                recipient,
                './/{http://www.irs.gov/efile}BusinessNameLine2Txt',
                './/{http://www.irs.gov/efile}BusinessNameLine2'
            )
            business_name2 = get_element_text(name2_check).upper()

            # Combine names
            business_name = f"{business_name1} {business_name2}".strip()

            # Address line 1
            addr1_check = safe_find_element(
                recipient,
                './/{http://www.irs.gov/efile}AddressLine1Txt',
                './/{http://www.irs.gov/efile}AddressLine1'
            )
            address_line1 = get_element_text(addr1_check)

            # Address line 2
            addr2_check = safe_find_element(
                recipient,
                './/{http://www.irs.gov/efile}AddressLine2Txt',
                './/{http://www.irs.gov/efile}AddressLine2'
            )
            address_line2 = get_element_text(addr2_check)

            # City
            city_check = safe_find_element(
                recipient,
                './/{http://www.irs.gov/efile}CityNm',
                './/{http://www.irs.gov/efile}City'
            )
            city = get_element_text(city_check)

            # State
            state_check = safe_find_element(
                recipient,
                './/{http://www.irs.gov/efile}StateAbbreviationCd',
                './/{http://www.irs.gov/efile}State'
            )
            state = get_element_text(state_check)

            # Zip code
            zip_check = safe_find_element(
                recipient,
                './/{http://www.irs.gov/efile}ZIPCd',
                './/{http://www.irs.gov/efile}ZIPCode'
            )
            zipcode = get_element_text(zip_check)

            # Amount paid from internal funds
            paid_check = safe_find_element(
                recipient,
                './/{http://www.irs.gov/efile}PaidInternalFundsAmt',
                './/{http://www.irs.gov/efile}AmountPaidFromInternalFunds'
            )
            amount_paid = get_element_text(paid_check)

            # Contributions received and delivered
            contrib_check = safe_find_element(
                recipient,
                './/{http://www.irs.gov/efile}ContributionsRcvdDlvrAmt',
                './/{http://www.irs.gov/efile}ContributionsRcvdDeliveredAmt'
            )
            contributions_received = get_element_text(contrib_check)

            rows.append([
                filer_ein, business_name, address_line1, address_line2,
                city, state, zipcode, recipient_ein, amount_paid,
                contributions_received, year
            ])

        columns = [
            'filer_ein', 'recipient_name', 'address_line1', 'address_line2',
            'city', 'state', 'zipcode', 'recipient_ein', 'amount_paid',
            'contributions_received', 'year'
        ]

        df = pd.DataFrame(rows, columns=columns, dtype='object')
        df.to_csv(filecheck, index=False)

        contributions_dict = {
            'EIN': filer_ein,
            'Year': year,
            'Count': len(rows)
        }

        logger.debug(f"Successfully processed {len(rows)} political contributions: {os.path.basename(file_path)}")
        return (f"Processed {file_path}", contributions_dict)

    except ET.ParseError as e:
        error_reason = f"XML parsing failed: {str(e)}"
        logger.error(f"{error_reason}: {os.path.basename(file_path)}")
        move_error_file(file_path, error_reason=error_reason, logger=logger)
        return (f"XML Parse Error: {file_path}", None)
    except Exception as e:
        error_reason = f"Unexpected error during processing: {str(e)}"
        logger.error(f"{error_reason}: {os.path.basename(file_path)}")
        move_error_file(file_path, error_reason=error_reason, logger=logger)
        return (f"Error processing {file_path}: {e}", None)


def process_file_helper(args):
    """Helper function for multiprocessing."""
    file_path, target_location = args[0], args[1]
    logger = logging.getLogger('tpc.political.worker')
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return process_single_file(file_path, target_location, logger)


def irs_political_contributions(file_location: str, target_location: str, log_dir=None) -> None:
    """
    Process IRS XML files to extract Section 527 political contribution data.

    Args:
        file_location: Path to XML files or directory
        target_location: Path to save output files
        log_dir: Explicit log directory path (prevents midnight date drift)
    """
    logger = get_standard_logger('political_contributions', target_location, log_dir=log_dir)
    logger.info(f"Starting political contributions processing: {file_location} -> {target_location}")

    # Determine file paths
    files = []
    if os.path.isdir(file_location):
        logger.info(f"Scanning directory for XML files: {file_location}")
        for root_dir, dirs, files_in_dir in os.walk(file_location):
            for file in files_in_dir:
                if file.endswith('.xml'):
                    files.append(os.path.join(root_dir, file))
    elif os.path.isfile(file_location) and file_location.endswith('.xml'):
        files = [file_location]
    else:
        logger.error(f"No valid XML files found in {file_location}")
        return

    if not files:
        logger.warning(f"No XML files found in {file_location}")
        return

    logger.info(f"Found {len(files)} XML files to process")

    args = [(file, target_location) for file in files]

    try:
        with Pool(processes=cpu_count()) as pool:
            results = list(tqdm(pool.imap(process_file_helper, args), total=len(files), desc="Processing political contributions"))

        result_strings = [r[0] for r in results]
        all_contribution_data = {}
        for r in results:
            if r[1] is not None:
                all_contribution_data[r[1]['EIN']] = r[1]

        if all_contribution_data:
            json_path = os.path.join(target_location, "political_contributions_profiles.json")
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w') as f:
                json.dump(all_contribution_data, f, indent=2)
            logger.info(f"Saved {len(all_contribution_data)} political contribution profiles to {json_path}")

        successful = sum(1 for r in result_strings if r.startswith("Processed"))
        errors = sum(1 for r in result_strings if "Error" in r)
        already_processed = sum(1 for r in result_strings if "Already processed" in r)
        no_data = sum(1 for r in result_strings if "No political contribution data" in r)
        skipped = sum(1 for r in result_strings if r.startswith("Skipped"))

        logger.info(f"Political contributions processing completed:")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Already processed: {already_processed}")
        logger.info(f"  Skipped (non-990/990EZ): {skipped}")
        logger.info(f"  No political data: {no_data}")
        logger.info(f"  Errors: {errors}")
        logger.info(f"  Total files: {len(files)}")

        for r in result_strings:
            if "Error" in r:
                logger.warning(r)

    except Exception as e:
        logger.error(f"Critical error during multiprocessing: {str(e)}")
        raise


if __name__ == '__main__':
    file_location = '/Volumes/TPC/2025-07-08/xmlfiles'
    target_location = '/Volumes/TPC/2025-07-08/csv'
    irs_political_contributions(file_location, target_location)
