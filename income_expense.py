import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
import json
import logging

# Import custom modules
from logging_setup import get_standard_logger
from error_handler import move_error_file, setup_error_logging
from xml_helpers import safe_find_element, get_element_text


def process_single_file(file_path: str, target_location: str, logger: logging.Logger) -> tuple[dict, dict]:
    """
    Process a single XML file and extract data.
    
    Args:
        file_path: Path to the XML file
        target_location: Directory to save output files
        logger: Logger instance
        
    Returns:
        Tuple of (profile_dict, income_expense_dict)
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Use safe element finding
        GrantorEIN_check = root[0].find('./*{http://www.irs.gov/efile}EIN')
        begindate_check = safe_find_element(
            root[0], 
            './{http://www.irs.gov/efile}TaxPeriodBeginDate',
            './{http://www.irs.gov/efile}TaxPeriodBeginDt'
        )
        
        begindate = get_element_text(begindate_check)
        year = begindate[0:4] if len(begindate) >= 4 else ''

        if GrantorEIN_check is None:
            error_reason = "No EIN found in XML file"
            logger.warning(f"{error_reason}: {os.path.basename(file_path)}")
            move_error_file(file_path, error_reason=error_reason, logger=logger)
            return {}, {}

        GrantorEIN = GrantorEIN_check.text

        # Create folder based on beginning year
        if year:
            folder = os.path.join(target_location, year)
            os.makedirs(folder, exist_ok=True)

        filecheck_income = os.path.join(target_location, year, f'income_expenses_{GrantorEIN}.csv')
        filecheck_Profile = os.path.join(target_location, year, f'profile_{GrantorEIN}.csv')

        Filer = root[0].find('./{http://www.irs.gov/efile}Filer')
        if Filer is None:
            error_reason = "No Filer element found in XML"
            logger.warning(f"{error_reason}: {os.path.basename(file_path)}")
            move_error_file(file_path, error_reason=error_reason, logger=logger)
            return {}, {}

        # Business name checks with safe element finding
        businessname_check_ln1 = safe_find_element(
            Filer,
            './*{http://www.irs.gov/efile}BusinessNameLine1',
            './*{http://www.irs.gov/efile}BusinessNameLine1Txt'
        )
        businessname_ln1 = get_element_text(businessname_check_ln1).upper()

        businessname_check_ln2 = safe_find_element(
            Filer,
            './*{http://www.irs.gov/efile}BusinessNameLine2',
            './*{http://www.irs.gov/efile}BusinessNameLine2Txt'
        )
        businessname_ln2 = get_element_text(businessname_check_ln2).upper()

        # Return type check
        return_check1 = safe_find_element(
            root[0],
            './{http://www.irs.gov/efile}ReturnType',
            './{http://www.irs.gov/efile}ReturnTypeCd'
        )
        returnType = get_element_text(return_check1)

        # Revenue and expenses with safe checking
        total_revenue_check = safe_find_element(
            root[1],
            './*{http://www.irs.gov/efile}TotalRevenueAmt',
            './*{http://www.irs.gov/efile}CYTotalRevenueAmt'
        )
        
        total_expenses_check = safe_find_element(
            root[1],
            './*{http://www.irs.gov/efile}TotalExpensesAmt',
            './*{http://www.irs.gov/efile}CYTotalExpensesAmt'
        )

        # Process based on return type
        if returnType == '990PF':
            pf_AnalysisOfRevenueAndExpenses_check = root[1].find('.//*{http://www.irs.gov/efile}AnalysisOfRevenueAndExpenses')
            if pf_AnalysisOfRevenueAndExpenses_check is not None:
                pf_TotalRevAndExpnssAmt_check = root[1].find('.//*{http://www.irs.gov/efile}TotalRevAndExpnssAmt')
                pf_TotalExpensesRevAndExpnssAmt = root[1].find('.//{http://www.irs.gov/efile}TotalExpensesRevAndExpnssAmt')
                Revenue = get_element_text(pf_TotalRevAndExpnssAmt_check)
                Expense = get_element_text(pf_TotalExpensesRevAndExpnssAmt)
            else:
                Revenue = None
                Expense = None
        elif returnType == '990EZ':
            Revenue = get_element_text(total_revenue_check) if total_revenue_check is not None else None
            Expense = get_element_text(total_expenses_check) if total_expenses_check is not None else None
        elif returnType == '990':
            Revenue = get_element_text(total_revenue_check) if total_revenue_check is not None else None
            Expense = get_element_text(total_expenses_check) if total_expenses_check is not None else None
        else:
            Revenue = None
            Expense = None

        # Address information with safe checking
        address_element_check = safe_find_element(
            root[0],
            '.*/*{http://www.irs.gov/efile}AddressLine1Txt',
            '.*/*{http://www.irs.gov/efile}AddressLine1'
        )
        address_element_line1 = get_element_text(address_element_check)

        address_element_line2_check = safe_find_element(
            root[0],
            '.*/*{http://www.irs.gov/efile}AddressLine2Txt',
            '.*/*{http://www.irs.gov/efile}AddressLine2'
        )
        address_element_line2 = get_element_text(address_element_line2_check)

        address_element_city_check = safe_find_element(
            root[0],
            '.*/*{http://www.irs.gov/efile}CityNm',
            '.*/*{http://www.irs.gov/efile}City'
        )
        address_element_city = get_element_text(address_element_city_check)

        address_element_state_check = safe_find_element(
            root[0],
            '.*/*{http://www.irs.gov/efile}StateAbbreviationCd',
            '.*/*{http://www.irs.gov/efile}State'
        )
        address_element_state = get_element_text(address_element_state_check)

        address_element_zip_check = safe_find_element(
            root[0],
            '.*/*{http://www.irs.gov/efile}ZIPCd',
            '.*/*{http://www.irs.gov/efile}ZIPCode'
        )
        address_element_zip = get_element_text(address_element_zip_check)

        # Website
        website_element_check = safe_find_element(
            root[1],
            './*{http://www.irs.gov/efile}WebsiteAddressTxt',
            './*{http://www.irs.gov/efile}WebSite'
        )
        website_element = get_element_text(website_element_check).upper()

        # Total Assets
        if returnType == '990PF':
            Form990TotalAssetsGrpy_check = root[1].find('./*{http://www.irs.gov/efile}Form990PFBalanceSheetsGrp')
            if Form990TotalAssetsGrpy_check is not None:
                BOY_check = root[1].find('.//*{http://www.irs.gov/efile}TotalAssetsBOYAmt')
                EOY_check = root[1].find('.//*{http://www.irs.gov/efile}TotalAssetsEOYAmt')
                total_assets_boy = get_element_text(BOY_check) if BOY_check is not None else None
                total_assets_eoy = get_element_text(EOY_check) if EOY_check is not None else None
            else:
                total_assets_boy = None
                total_assets_eoy = None
        elif returnType == '990':
            # Multiple possible paths for 990 forms
            total_assets_boy_paths = [
                './*{http://www.irs.gov/efile}TotalAssetsBOY',
                './*{http://www.irs.gov/efile}TotalAssetsBOYAmt',
                './*{http://www.irs.gov/efile}Form990TotalAssetsGrp/{http://www.irs.gov/efile}BOYAmt',
                './*{http://www.irs.gov/efile}TotalAssetsGrp/{http://www.irs.gov/efile}BOYAmt'
            ]
            total_assets_eoy_paths = [
                './*{http://www.irs.gov/efile}TotalAssetsEOY',
                './*{http://www.irs.gov/efile}TotalAssetsEOYAmt',
                './*{http://www.irs.gov/efile}Form990TotalAssetsGrp/{http://www.irs.gov/efile}EOYAmt'
            ]
            
            total_assets_boy_element = None
            total_assets_eoy_element = None
            
            for path in total_assets_boy_paths:
                total_assets_boy_element = root[1].find(path)
                if total_assets_boy_element is not None:
                    break
                    
            for path in total_assets_eoy_paths:
                total_assets_eoy_element = root[1].find(path)
                if total_assets_eoy_element is not None:
                    break
            
            total_assets_boy = get_element_text(total_assets_boy_element) if total_assets_boy_element is not None else '990 error_1'
            total_assets_eoy = get_element_text(total_assets_eoy_element) if total_assets_eoy_element is not None else '990 error_1'
        
        elif returnType == '990EZ':
            assets_check = root[1].find('./*{http://www.irs.gov/efile}Form990TotalAssetsGrp')
            if assets_check is not None:
                BOY_check = root[1].find('.//*{http://www.irs.gov/efile}BOYAmt')
                EOY_check = root[1].find('.//*{http://www.irs.gov/efile}EOYAmt')
                total_assets_boy = get_element_text(BOY_check) if BOY_check is not None else '990EZ error_2'
                total_assets_eoy = get_element_text(EOY_check) if EOY_check is not None else '990EZ error_2'
            else:
                total_assets_boy = '990EZ error_2'
                total_assets_eoy = '990EZ error_2'
        else:
            total_assets_boy = 'General error'
            total_assets_eoy = 'General Error'

        # Status
        status_check3 = root[1].find('./*{http://www.irs.gov/efile}Organization501c3Ind')
        status_check4 = root[1].find('./*{http://www.irs.gov/efile}Organization501c3')
        status_check = root[1].find('./*{http://www.irs.gov/efile}Organization501cInd')
        status_check2 = root[1].find('./*{http://www.irs.gov/efile}Organization501c')

        if status_check3 is not None and status_check3.text == 'X':
            status = "501(c)3"
        elif status_check4 is not None and status_check4.text == 'X':
            status = "501(c)3"
        elif status_check is not None and hasattr(status_check, 'attrib') and 'organization501cTypeTx' in status_check.attrib:
            status = '501(c)' + str(status_check.attrib['organization501cTypeTx'])
        elif status_check2 is not None and hasattr(status_check2, 'attrib') and 'typeOf501cOrganization' in status_check2.attrib:
            status = '501(c)' + str(status_check2.attrib['typeOf501cOrganization'])
        else:
            status = ''

        # Mission
        mission_paths = [
            "./*{http://www.irs.gov/efile}ActivityOrMissionDesc",
            './*{http://www.irs.gov/efile}PrimaryExemptPurposeTxt',
            './*{http://www.irs.gov/efile}MissionDesc',
            './*{http://www.irs.gov/efile}ActivityOrMissionDescription'
        ]
        
        mission_element = None
        for path in mission_paths:
            mission_element = root[1].find(path)
            if mission_element is not None:
                break
        
        mission = get_element_text(mission_element)

        # Create dataframes and save files
        rows_income_expense = [[GrantorEIN, Revenue, Expense, total_assets_boy, total_assets_eoy, returnType, year]]
        df = pd.DataFrame(rows_income_expense, columns=["ein", "revenue", "expenses", "total_assets_boy", "total_assets_eoy", "return_type", "year"], dtype="object")

        rows2_profile = [[GrantorEIN, businessname_ln1.upper(), businessname_ln2.upper(), address_element_line1.upper(),
                          address_element_line2.upper(), address_element_city.upper(), address_element_state,
                          address_element_zip, website_element, mission.upper(), status, year]]
        df2 = pd.DataFrame(rows2_profile, columns=["ein", "org_name1", "org_name2", "address_1", "address_2", "city", "state", "zipcode", "website", "mission", "status", "year"], dtype="object")

        df.to_csv(filecheck_income, index=False)
        df2.to_csv(filecheck_Profile, index=False)

        # Store in dictionaries
        profile_dict = {
            "EIN": GrantorEIN,
            "Business_name": businessname_ln1.upper(),
            "Business_name2": businessname_ln2.upper(),
            "address": address_element_line1.upper(),
            "Address2": address_element_line2.upper(),
            "City": address_element_city.upper(),
            "State": address_element_state.upper(),
            "Zip": address_element_zip,
            "Website": website_element,
            "Mission": mission.upper(),
            "Status": status.upper() if status else None,
            "Year": year,
        }

        income_expense_dict = {
            "ein": GrantorEIN,
            "revenue": Revenue,
            "expenses": Expense,
            "total_assets_boy": total_assets_boy,
            "total_assets_eoy": total_assets_eoy,
            "return_type": returnType,
            "year": year
        }

        logger.debug(f"Successfully processed file: {os.path.basename(file_path)}")
        return profile_dict, income_expense_dict
        
    except ET.ParseError as e:
        error_reason = f"XML parsing failed: {str(e)}"
        logger.error(f"{error_reason}: {os.path.basename(file_path)}")
        move_error_file(file_path, error_reason=error_reason, logger=logger)
        return {}, {}
    except Exception as e:
        error_reason = f"Unexpected error during processing: {str(e)}"
        logger.error(f"{error_reason}: {os.path.basename(file_path)}")
        move_error_file(file_path, error_reason=error_reason, logger=logger)
        return {}, {}


def irs_expense_income(file_location: str, target_location: str) -> None:
    """
    Process IRS XML files to extract income and expense data.
    
    Args:
        file_location: Path to XML files or directory
        target_location: Path to save output files
    """
    # Set up logging using the logging_setup module
    logger = get_standard_logger('income_expense', target_location)
    logger.info(f"Starting processing: {file_location} -> {target_location}")
    
    # Determine file paths
    if os.path.isdir(file_location):
        file_path = os.path.join(file_location, '*/', '*.xml')
        files = glob.glob(file_path)
    else:
        files = [file_location]

    if not files:
        logger.warning(f"No XML files found in {file_location}")
        return

    logger.info(f"Found {len(files)} files to process")

    profile_empty_dict = {}
    income_expense_empty_dict = {}
    
    # Counters for tracking
    successful_files = 0
    error_files = 0

    for file_path in tqdm(files, desc="Processing files"):
        try:
            profile_dict, income_expense_dict = process_single_file(file_path, target_location, logger)
            
            if profile_dict is not None and income_expense_dict is not None:
                profile_empty_dict[file_path] = profile_dict
                income_expense_empty_dict[file_path] = income_expense_dict
                successful_files += 1
            else:
                error_files += 1
                
        except Exception as e:
            error_reason = f"Critical error processing file: {str(e)}"
            logger.error(f"{error_reason}: {os.path.basename(file_path)}")
            move_error_file(file_path, error_reason=error_reason, logger=logger)
            error_files += 1
            continue

    # Convert keys to strings and save JSON files
    profile_empty_dict = {str(k): v for k, v in profile_empty_dict.items()}
    income_expense_empty_dict = {str(k): v for k, v in income_expense_empty_dict.items()}

    try:
        with open(f"{target_location}/incomeexpense_profiles.json", 'w') as f:
            json.dump(profile_empty_dict, f, indent=2)
        with open(f"{target_location}/income_expense.json", 'w') as f:
            json.dump(income_expense_empty_dict, f, indent=2)
        
        logger.info("JSON files saved successfully")
    except Exception as e:
        logger.error(f"Failed to save JSON files: {str(e)}")

    logger.info(f"Processing completed - Success: {successful_files}, Errors: {error_files}, Total: {len(files)}")


if __name__ == "__main__":
    file_location = '/Volumes/TPC/2025-07-08/xml'
    target_location = '/Volumes/TPC/2025-07-08/csv'
    irs_expense_income(file_location, target_location)
