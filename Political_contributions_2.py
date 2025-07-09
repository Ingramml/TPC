import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
import json
import logging
from datetime import datetime
import error_handler
import logging_setup


# Initialize logger
logger = None


def political_contributions(file_path, target_location):
    global logger
    
    # Initialize logging if not already done
    if logger is None:
        logger = logging_setup.get_standard_logger('political_contributions', file_path)
    
    logger.info(f"Starting political contributions processing from {file_path} to {target_location}")
    
    if os.path.isdir(file_path):
        file_path_pattern = os.path.join(file_path, '*.xml')
        files = glob.glob(file_path_pattern)
        logger.info(f"Found {len(files)} XML files in directory")
    else:
        files = [file_path]
        logger.info(f"Processing single file: {file_path}")

    all_results = {}

    for i in tqdm(files):
        logger.info(f'Processing file: {i}')
        rows = []
        filename = os.path.basename(i)
        
        try:
            tree = ET.parse(i)
            root = tree.getroot()
            donations = root[1].findall('.//{http://www.irs.gov/efile}Section527PoliticalOrgGrp')

            GrantorEIN_check = root[0].find('.//{http://www.irs.gov/efile}EIN').text
            year = root.find('.//{http://www.irs.gov/efile}TaxYr').text
            
            logger.debug(f"Processing EIN: {GrantorEIN_check}, Year: {year}")

            result_dict = {
                'EIN': GrantorEIN_check,
                'Year': year,
                'Political Donations': {}
            }
            columns = ['ein', 'business_name1', 'businessname2', 'address_element_line1', 'address_element_line2',
                       'city', 'state', 'zipcode', 'recipient_ein', 'amount_paid', 'year']

            folder = os.path.join(target_location, year)
            os.makedirs(folder, exist_ok=True)

            filecheck = os.path.join(folder, 'political_contributions_' + GrantorEIN_check + '.csv')
            logger.debug(f"Output file will be: {filecheck}")

            if donations:
                logger.info(f"Found {len(donations)} political donations in file: {filename}")
                for recipient in donations:
                    donation_dict = {}
                    political_EIN = recipient.find('.//{http://www.irs.gov/efile}EIN').text or ''

                    business_name_line1 = recipient.find('.//{http://www.irs.gov/efile}BusinessNameLine1Txt').text or ''
                    business_name_line2 = recipient.find('.//{http://www.irs.gov/efile}BusinessNameLine2Txt').text if \
                        ET.iselement(recipient.find('.//{http://www.irs.gov/efile}BusinessNameLine2Txt')) else ''
                    address_element_line1 = recipient.find('.//{http://www.irs.gov/efile}AddressLine1Txt').text or ''
                    address_element_line2 = recipient.find('.//{http://www.irs.gov/efile}AddressLine2Txt').text if \
                        ET.iselement(recipient.find('.//{http://www.irs.gov/efile}AddressLine2Txt')) else ''
                    city_element = recipient.find('.//{http://www.irs.gov/efile}CityNm').text or ''
                    state_element = recipient.find('.//{http://www.irs.gov/efile}StateAbbreviationCd').text or ''
                    zipcode_element = recipient.find('.//{http://www.irs.gov/efile}ZIPCd').text or ''
                    amount_paid = recipient.find('.//{http://www.irs.gov/efile}PaidInternalFundsAmt').text or ''

                    donation_dict['Business_name'] = business_name_line1
                    donation_dict['Business_name_2'] = business_name_line2
                    donation_dict['City'] = city_element
                    donation_dict['State'] = state_element
                    donation_dict['ZipCode'] = zipcode_element
                    donation_dict['Donation amount'] = amount_paid

                    result_dict['Political Donations'][political_EIN] = donation_dict

                    rows.append([GrantorEIN_check, business_name_line1, business_name_line2, address_element_line1,
                                 address_element_line2, city_element, state_element, zipcode_element, political_EIN, amount_paid, year])

                df = pd.DataFrame(rows, columns=columns, dtype=object)
                df.to_csv(filecheck, index=False)
                logger.info(f"Successfully saved {len(rows)} political contributions to: {filecheck}")
            else:
                logger.info(f"No political donations found in file: {filename}")

            all_results[filename] = result_dict

        except ET.ParseError as e:
            logger.error(f"XML parsing error in file {i}: {e}")
            error_handler.move_error_file(
                i, 
                error_reason=f"XML parsing error: {str(e)}", 
                logger=logger
            )
            all_results[filename] = {'error': f"Error parsing {i}"}
            continue
            
        except Exception as e:
            logger.error(f"Unexpected error processing file {i}: {e}")
            error_handler.move_error_file(
                i, 
                error_reason=f"Processing error: {str(e)}", 
                logger=logger
            )
            all_results[filename] = {'error': f"Error processing {i}: {e}"}
            continue

    logger.info("Processing completed for all files")

    # Save all results to JSON
    json_output = os.path.join(target_location, 'TPC_990_political.json')
    try:
        with open(json_output, 'w') as json_file:
            json.dump(all_results, json_file, indent=4)
        logger.info(f"Successfully wrote JSON output to: {json_output}")
    except Exception as e:
        logger.error(f"Error writing JSON file {json_output}: {e}")

    return all_results




if __name__ == "__main__":
    file_location = '/Users/michaellingram/Downloads/xml_test/2020'
    target_location = '/Users/michaellingram/Downloads/xml_test'
    
    # Initialize logging
    logger = logging_setup.get_standard_logger('political_contributions', file_location)
    logger.info("Starting political contributions processing script")
    
    political_contributions(file_location, target_location)
    
    logger.info("Script completed")
