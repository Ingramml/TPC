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
import fcntl  # For file locking

# Import custom modules
from logging_setup import get_standard_logger
from error_handler import move_error_file
from xml_helpers import safe_find_element, get_element_text


def safe_json_load(file_path: str, logger: logging.Logger) -> dict:
    """
    Safely load JSON file with error handling and backup recovery.
    
    Args:
        file_path: Path to JSON file
        logger: Logger instance
        
    Returns:
        dict: Loaded JSON data or empty dict if error
    """
    if not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {str(e)}")
        logger.error(f"Error at line {e.lineno}, column {e.colno}")
        
        # Backup corrupted file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{file_path}.corrupted_{timestamp}"
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Corrupted JSON backed up to: {backup_path}")
        except Exception as backup_error:
            logger.error(f"Failed to backup corrupted JSON: {str(backup_error)}")
        
        # Try to recover from backup files
        backup_pattern = f"{file_path}.backup_*"
        backup_files = glob.glob(backup_pattern)
        
        if backup_files:
            # Use most recent backup
            latest_backup = max(backup_files, key=os.path.getmtime)
            try:
                with open(latest_backup, 'r') as f:
                    data = json.load(f)
                logger.info(f"Recovered data from backup: {latest_backup}")
                return data
            except Exception as recovery_error:
                logger.error(f"Failed to recover from backup: {str(recovery_error)}")
        
        return {}
    except Exception as e:
        logger.error(f"Failed to load JSON from {file_path}: {str(e)}")
        return {}


def safe_json_save(data: dict, file_path: str, logger: logging.Logger) -> bool:
    """
    Safely save JSON file with atomic write and backup.
    
    Args:
        data: Data to save
        file_path: Path to save JSON file
        logger: Logger instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Create backup of existing file
        if os.path.exists(file_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{file_path}.backup_{timestamp}"
            try:
                shutil.copy2(file_path, backup_path)
            except Exception as backup_error:
                logger.warning(f"Failed to create backup: {str(backup_error)}")
        
        # Write to temporary file first (atomic write)
        temp_path = f"{file_path}.tmp_{os.getpid()}"
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Move temporary file to final location
        shutil.move(temp_path, file_path)
        logger.debug(f"Successfully saved JSON to: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {str(e)}")
        # Clean up temporary file if it exists
        temp_path = f"{file_path}.tmp_{os.getpid()}"
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False


def process_single_file(file_path: str, target_location: str, logger: logging.Logger) -> str:
    """
    Process a single XML file to extract grant data.
    
    Args:
        file_path: Path to the XML file
        target_location: Directory to save output files
        logger: Logger instance
        
    Returns:
        String indicating processing result
    """
    today= datetime.now().strftime('%Y-%m-%d')
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Use safe element finding with fixed deprecation warnings
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
            return f"Error: {error_reason} - {file_path}"

        GrantorEIN = GrantorEIN_check.text

        # Create folder based on beginning year
        if year:
            folder = os.path.join(target_location, year)
            os.makedirs(folder, exist_ok=True)
        else:
            error_reason = "No valid year found in XML file"
            logger.warning(f"{error_reason}: {os.path.basename(file_path)}")
            move_error_file(file_path, error_reason=error_reason, logger=logger)
            return f"Error: {error_reason} - {file_path}"

        # Check if file already processed
        filecheck = os.path.join(target_location, year, f'grants_{GrantorEIN}.csv')
        if os.path.isfile(filecheck):
            logger.info(f"File already processed, skipping: {os.path.basename(file_path)}")
            return f"Already processed {file_path}"

        grants_empty_dict = {}

        # Check for Schedule I
        ScheduleI = root[1].find('{http://www.irs.gov/efile}IRS990ScheduleI')
        GrantOrContributionPdDurYrGrp_check = root[1].find(
            "./*/*/{http://www.irs.gov/efile}GrantOrContributionPdDurYrGrp")

        if ScheduleI is not None and ScheduleI.find('{http://www.irs.gov/efile}RecipientTable') is not None:
            # Process RecipientTable format
            RecipientTablelist = ScheduleI.findall('{http://www.irs.gov/efile}RecipientTable')
            rows = []
            
            for recipient in RecipientTablelist:
                # EIN with safe checking
                recipient_EIN_check = safe_find_element(
                    recipient,
                    './{http://www.irs.gov/efile}RecipientEIN',
                    './{http://www.irs.gov/efile}EINOfRecipient'
                )
                recipient_EIN = get_element_text(recipient_EIN_check)

                # Business name line 1 with safe checking
                business_name_check = safe_find_element(
                    recipient,
                    './*/{http://www.irs.gov/efile}BusinessNameLine1Txt',
                    './*/{http://www.irs.gov/efile}BusinessNameLine1'
                )
                business_name_check2 = recipient.find('./{http://www.irs.gov/efile}RecipientPersonNm')
                
                business_name = get_element_text(business_name_check).upper()
                if not business_name and business_name_check2 is not None:
                    business_name = get_element_text(business_name_check2).upper()

                # Business name line 2 with safe checking
                business_name_check_ln2 = safe_find_element(
                    recipient,
                    './*/{http://www.irs.gov/efile}BusinessNameLine2Txt',
                    './*/{http://www.irs.gov/efile}BusinessNameLine2'
                )
                business_name_ln2 = get_element_text(business_name_check_ln2).upper()
                
                business_name = f"{business_name} {business_name_ln2}".strip()

                # Amount with safe checking
                amount_element_check = safe_find_element(
                    recipient,
                    './{http://www.irs.gov/efile}CashGrantAmt',
                    './{http://www.irs.gov/efile}AmountOfCashGrant'
                )
                amount_element = get_element_text(amount_element_check)

                # Status with safe checking
                status_element_check = safe_find_element(
                    recipient,
                    './{http://www.irs.gov/efile}IRCSectionDesc',
                    './{http://www.irs.gov/efile}IRCSection'
                )
                status_element = get_element_text(status_element_check)

                # Purpose with safe checking
                purpose_element_check = safe_find_element(
                    recipient,
                    './{http://www.irs.gov/efile}PurposeOfGrantTxt',
                    './{http://www.irs.gov/efile}PurposeOfGrant'
                )
                purpose_element = get_element_text(purpose_element_check)

                # Check for non-cash assistance
                non_cash_check = recipient.find('./{http://www.irs.gov/efile}NonCashAssistanceAmt')
                if (amount_element == '0' or not amount_element) and non_cash_check is not None:
                    amount_element = get_element_text(non_cash_check)
                    purpose_element = f"{purpose_element}*"

                rows.append([GrantorEIN, recipient_EIN, business_name, amount_element, purpose_element, year])

            df = pd.DataFrame(rows, columns=["grantor_ein", "grantee_ein", "grantee_name", "amount", "purpose", "year"], dtype="object")
            df.to_csv(filecheck, index=False)
            
        elif GrantOrContributionPdDurYrGrp_check is not None:
            # Process GrantOrContributionPdDurYrGrp format
            grants_list = root[1].findall("./*/*/{http://www.irs.gov/efile}GrantOrContributionPdDurYrGrp")
            rows = []
            
            for recipient in grants_list:
                # EIN with safe checking
                recipient_EIN_check = safe_find_element(
                    recipient,
                    './{http://www.irs.gov/efile}RecipientEIN',
                    './{http://www.irs.gov/efile}EINOfRecipient'
                )
                recipient_EIN = get_element_text(recipient_EIN_check)

                # Business name line 1 with safe checking
                business_name_check = safe_find_element(
                    recipient,
                    './*/{http://www.irs.gov/efile}BusinessNameLine1Txt',
                    './*/{http://www.irs.gov/efile}BusinessNameLine1'
                )
                business_name_check2 = recipient.find('./{http://www.irs.gov/efile}RecipientPersonNm')
                
                business_name = get_element_text(business_name_check)
                if not business_name and business_name_check2 is not None:
                    business_name = get_element_text(business_name_check2)

                # Business name line 2 with safe checking
                business_name_check_ln2 = safe_find_element(
                    recipient,
                    './*/{http://www.irs.gov/efile}BusinessNameLine2Txt',
                    './*/{http://www.irs.gov/efile}BusinessNameLine2'
                )
                business_name_ln2 = get_element_text(business_name_check_ln2)

                # Combine business names safely
                if business_name and business_name_ln2:
                    business_name = f"{business_name.upper()} {business_name_ln2.upper()}".strip()
                elif business_name:
                    business_name = business_name.upper()
                elif business_name_ln2:
                    business_name = business_name_ln2.upper()
                else:
                    business_name = ""

                # Amount with safe checking
                amount_element_check = recipient.find('./{http://www.irs.gov/efile}Amt')
                amount_element = get_element_text(amount_element_check)
                
                if not amount_element:
                    amount_check2 = recipient.find('./{http://www.irs.gov/efile}AmountOfCashGrant')
                    if amount_check2 is not None:
                        amount_element = get_element_text(amount_check2)

                # Status with safe checking
                status_element_check = recipient.find('./{http://www.irs.gov/efile}Status')
                status_element = get_element_text(status_element_check)

                # Purpose with safe checking
                purpose_element_check = recipient.find('./{http://www.irs.gov/efile}GrantOrContributionPurposeTxt')
                purpose_element = get_element_text(purpose_element_check)

                # Check for non-cash assistance
                non_cash_check = recipient.find('./{http://www.irs.gov/efile}NonCashAssistanceAmt')
                if (amount_element == '0' or not amount_element) and non_cash_check is not None:
                    amount_element = get_element_text(non_cash_check)
                    purpose_element = f"{purpose_element}*"

                rows.append([GrantorEIN, recipient_EIN, business_name, amount_element, status_element, purpose_element, year])

            df = pd.DataFrame(rows, columns=["grantor_ein", "grantee_ein", "grantee_name", "amount", 'status', "purpose", "year"], dtype="object")
            df.to_csv(filecheck, index=False)

            # Store in grants dictionary for the last processed entry
            if rows:
                grants_dict = {
                    "EIN": GrantorEIN,
                    "Business_name": business_name,
                    "Business_name2": business_name_ln2 if 'business_name_ln2' in locals() else '',
                    "Amount": amount_element,
                    'Status': status_element,
                    'Purpose': purpose_element,
                    'Year': year
                }
                grants_empty_dict[file_path] = grants_dict

        else:
            logger.info(f"No grant data found in file: {os.path.basename(file_path)}")
            return f"No grant data found in {file_path}"

        # Save grants dictionary with improved JSON handling
        if grants_empty_dict:
            grants_json_path = os.path.join(target_location, "grant_profiles_3.json")
            
            # Log the JSON file path for debugging
            logger.info(f"JSON file path determined: {grants_json_path}")
            logger.info(f"Target location: {target_location}")
            logger.info(f"Parent directory: {os.path.dirname(target_location)}")
            logger.info(f"JSON directory exists: {os.path.exists(os.path.dirname(grants_json_path))}")

            # Use file locking to prevent concurrent access during multiprocessing
            lock_path = f"{grants_json_path}.lock"
            
            try:
                # Create lock file
                with open(lock_path, 'w') as lock_file:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    
                    # Load existing data safely
                    existing_data = safe_json_load(grants_json_path, logger)
                    logger.info(f"Loaded existing JSON data: {len(existing_data)} entries")
                    
                    # Convert file path keys to strings
                    grants_empty_dict = {str(k): v for k, v in grants_empty_dict.items()}
                    
                    # Update with new data
                    existing_data.update(grants_empty_dict)
                    logger.info(f"Updated JSON data: {len(existing_data)} total entries")
                    
                    # Save updated data safely
                    if safe_json_save(existing_data, grants_json_path, logger):
                        logger.info(f"Successfully saved grants JSON to: {grants_json_path}")
                        logger.info(f"JSON file size: {os.path.getsize(grants_json_path) if os.path.exists(grants_json_path) else 'Unknown'} bytes")
                    else:
                        logger.error(f"Failed to save grants JSON for file: {os.path.basename(file_path)}")
                    
            except Exception as e:
                logger.error(f"Error handling grants JSON: {str(e)}")
            finally:
                # Clean up lock file
                try:
                    if os.path.exists(lock_path):
                        os.remove(lock_path)
                        logger.debug(f"Cleaned up lock file: {lock_path}")
                except:
                    pass

        logger.info(f"Successfully processed grants file: {os.path.basename(file_path)}")
        print(grants_json_path)
    
        return f"Processed {file_path}"

    except ET.ParseError as e:
        error_reason = f"XML parsing failed: {str(e)}"
        logger.error(f"{error_reason}: {os.path.basename(file_path)}")
        move_error_file(file_path, error_reason=error_reason, logger=logger)
        return f"XML Parse Error: {file_path}"
    except Exception as e:
        error_reason = f"Unexpected error during processing: {str(e)}"
        logger.error(f"{error_reason}: {os.path.basename(file_path)}")
        move_error_file(file_path, error_reason=error_reason, logger=logger)
        return f"Error processing {file_path}: {e}"


def process_file_helper(args):
    """Helper function for multiprocessing."""
    file_path, target_location = args[:2]  # Extract first two args
    # Create new logger instance for this process
    logger = get_standard_logger('grants', target_location)
    return process_single_file(file_path, target_location, logger)


def irs_grants(file_location: str, target_location: str) -> None:
    """
    Process IRS XML files to extract grant data.
    
    Args:
        file_location: Path to XML files or directory
        target_location: Path to save output files
    """
    # Set up logging using the logging_setup module
    logger = get_standard_logger('grants', target_location)
    logger.info(f"Starting grants processing: {file_location} -> {target_location}")

    # Log expected JSON file location FIRST
    expected_json_path = os.path.join(target_location, "grant_profiles.json")
    logger.info(f"=== JSON FILE LOCATION DEBUG ===")
    logger.info(f"Target location parameter: {target_location}")
    logger.info(f"Parent directory: {os.path.dirname(target_location)}")
    logger.info(f"Expected JSON file path: {expected_json_path}")
    logger.info(f"JSON parent directory exists: {os.path.exists(os.path.dirname(target_location))}")
    logger.info(f"JSON file currently exists: {os.path.exists(expected_json_path)}")
    if os.path.exists(expected_json_path):
        logger.info(f"Existing JSON file size: {os.path.getsize(expected_json_path)} bytes")

    # Determine file paths
    files = []
    if os.path.isdir(file_location):
        logger.info(f"Scanning directory for XML files: {file_location}")
        for root, dirs, files_in_dir in os.walk(file_location):
            for file in files_in_dir:
                if file.endswith('.xml'):
                    files.append(os.path.join(root, file))
    elif os.path.isfile(file_location) and file_location.endswith('.xml'):
        files = [file_location]
    else:
        logger.error(f"No valid XML files found in {file_location}")
        return

    if not files:
        logger.warning(f"No XML files found in {file_location}")
        return

    logger.info(f"Found {len(files)} XML files to process")

    # Create argument tuples for multiprocessing (only pass first 2 args)
    args = [(file, target_location) for file in files]

    # Use multiprocessing to process files in parallel
    try:
        with Pool(processes=cpu_count()) as pool:
            results = list(tqdm(pool.imap(process_file_helper, args), total=len(files), desc="Processing grants"))

        # Log results summary
        successful = sum(1 for result in results if result.startswith("Processed"))
        errors = sum(1 for result in results if "Error" in result)
        already_processed = sum(1 for result in results if "Already processed" in result)
        no_data = sum(1 for result in results if "No grant data" in result)

        logger.info(f"Grants processing completed:")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Already processed: {already_processed}")
        logger.info(f"  No grant data: {no_data}")
        logger.info(f"  Errors: {errors}")
        logger.info(f"  Total files: {len(files)}")

        # After processing, check JSON file status again
        logger.info(f"=== POST-PROCESSING JSON CHECK ===")
        final_json_path = os.path.join(target_location, "grant_profiles.json")
        logger.info(f"Final JSON path check: {final_json_path}")
        
        if os.path.exists(final_json_path):
            logger.info(f"✓ JSON file exists at: {final_json_path}")
            logger.info(f"✓ JSON file size: {os.path.getsize(final_json_path)} bytes")
            
            # Try to read and log some info about the JSON content
            try:
                with open(final_json_path, 'r') as f:
                    import json
                    data = json.load(f)
                    logger.info(f"✓ JSON file contains {len(data)} entries")
            except Exception as e:
                logger.warning(f"Could not read JSON file content: {str(e)}")
        else:
            logger.warning(f"✗ JSON file NOT FOUND at: {final_json_path}")
            
            # Check what files exist in the parent directory
            parent_dir = os.path.dirname(target_location)
            if os.path.exists(parent_dir):
                all_files = os.listdir(parent_dir)
                json_files = [f for f in all_files if f.endswith('.json')]
                logger.info(f"Files in parent directory {parent_dir}: {all_files}")
                if json_files:
                    logger.info(f"JSON files found: {json_files}")
                else:
                    logger.info("No JSON files found in parent directory")
            else:
                logger.error(f"Parent directory does not exist: {parent_dir}")

        # Print detailed results for debugging
        for result in results:
            if "Error" in result:
                logger.warning(result)
            else:
                logger.debug(result)

    except Exception as e:
        logger.error(f"Critical error during multiprocessing: {str(e)}")
        raise


if __name__ == '__main__':
    file_location = '/Volumes/TPC/xml/2017/201700069349100000_public.xml'
    target_location = '/Volumes/TPC/2025-07-08/csv'
    irs_grants(file_location, target_location)
