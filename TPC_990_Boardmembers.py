import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
import json
import logging
from datetime import datetime
import error_handler

def setup_logging(base_path=None):
    """Set up logging configuration"""
    # Create date-based directory structure for logs
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    if base_path:
        # Extract the base volume path (e.g., '/Volumes/TPC' from '/Volumes/TPC/2025-07-07/downloads/file.zip')
        # Find the TPC part in the path
        path_parts = base_path.split('/')
        if 'TPC' in path_parts:
            tpc_index = path_parts.index('TPC')
            base_volume = '/'.join(path_parts[:tpc_index + 1])  # e.g., '/Volumes/TPC'
        else:
            base_volume = '/Volumes/TPC'  # fallback
        
        log_dir = os.path.join(base_volume, current_date, 'logs')
    else:
        # Fallback to local directory
        log_dir = os.path.join('TPC', current_date, 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join(log_dir, f'tpc_boardmembers_{timestamp}.log')
    print(log_filename)
    
    # Configure logging - only file handler, no console output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler(log_filename)
            # Removed StreamHandler to prevent console output
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_filename}")
    logger.info(f"Working directory: {base_path}")
    return logger

# Initialize logger
logger = None

# files = glob.glob('/Volumes/SSD/TPC990/TPC_xml/*.xml')
# target_location = '/Volumes/SSD/production'

def irs_boardmember(file_location, target_location):
    global logger
    
    # Initialize logging if not already done
    if logger is None:
        logger = setup_logging(file_location)
    
    logger.info(f"Starting boardmember processing from {file_location} to {target_location}")

    if os.path.isdir(file_location):
        file_path = os.path.join(file_location,'*/', '*.xml')
        file_location = glob.glob(file_path)
        logger.info(f"Found {len(file_location)} XML files in directory")
    else:
        file_location = [file_location]
        logger.info(f"Processing single file: {file_location[0]}")

    mydict = {}

    for i in tqdm(file_location):
        logger.info(f'Processing file: {i}')
        # print('Processing file: ' + i)  # Removed print statement
        
        try:
            tree = ET.parse(i)
            root = tree.getroot()
            GrantorEIN_check = root[0].find('./*{http://www.irs.gov/efile}EIN')
            begindate_check = root[0].find('./{http://www.irs.gov/efile}TaxPeriodBeginDate')
            begindate_chcek2 = root[0].find('./{http://www.irs.gov/efile}TaxPeriodBeginDt')
            begindate = begindate_check.text if ET.iselement(
                begindate_check) else begindate_chcek2.text if ET.iselement(begindate_chcek2) else None
            
            if begindate is None:
                logger.error(f"Could not find begin date for file: {i}")
                continue
                
            year = begindate[0:4]
            logger.debug(f"Processing file for year: {year}")
            
            # Creates folder based on begining year of tax return(begindate)
            if ET.iselement(GrantorEIN_check):
                folder = os.path.join(target_location, begindate[0:4])
                if os.path.exists(folder):
                    pass
                else:
                    os.makedirs(folder, exist_ok=True)
                    logger.info(f"Created directory: {folder}")
            else:
                error_path = '/Volumes/Storage/TPC990/Errors/' + os.path.basename(i)
                os.rename(i, error_path)
                logger.warning(f'{os.path.basename(i)} moved to errors directory: {error_path}')
                # print(os.path.basename(i) + ' moved')  # Removed print statement
                continue

            columns = ['ein', 'name', 'title', 'averagehousperweek', 'indivualtrusteeordirector', 'compensation_from_org',
                       'compensation_from_related_org', 'othercompens', 'year']

            return_check1 = root[0].find('./{http://www.irs.gov/efile}ReturnType') or root[0].find(
                './{http://www.irs.gov/efile}ReturnTypeCd')
            returnType = return_check1.text if ET.iselement(return_check1) else ''
            logger.debug(f"Return type: {returnType}")

            if returnType=='990':
                boardmemebers = root[1].findall('./*{http://www.irs.gov/efile}Form990PartVIISectionAGrp')
            elif returnType=='990PF':
                if root[1].find('./*{http://www.irs.gov/efile}OfficerDirTrstKeyEmplInfoGrp') is not None:
                    boardmemebers=root.findall('.//*{http://www.irs.gov/efile}OfficerDirTrstKeyEmplGrp')
            elif returnType=='990EZ':
                    boardmemebers=root[1].findall('./*{http://www.irs.gov/efile}OfficerDirectorTrusteeEmplGrp')
            else:
                boardmemebers='errror'
                logger.warning(f"Unknown return type: {returnType} for file: {i}")

            EIN = root[0].find('.//{http://www.irs.gov/efile}EIN').text
            rows = []

            filecheck = target_location + '/' + year + '/boardmembers_' + EIN + '.csv'
            logger.debug(f"Output file will be: {filecheck}")

            if returnType!='990T':
                for boardmemeber in boardmemebers:
                    """
                    #finds board members names
                    name_check=boardmemeber.find("{http://www.irs.gov/efile}NamePerson")
                    name_check2 = boardmemeber.find("{http://www.irs.gov/efile}PersonNm")
        
                    """

                    Name = boardmemeber.find("{http://www.irs.gov/efile}PersonNm").text if ET.iselement(
                        boardmemeber.find("{http://www.irs.gov/efile}PersonNm")) \
                        else None
                    """
                    finds board members title
                    title_check = boardmemeber.find('{http://www.irs.gov/efile}Title')
                    title_check2 = boardmemeber.find('{http://www.irs.gov/efile}TitleTxt')
        
                    """

                    Title = boardmemeber.find('.{http://www.irs.gov/efile}TitleTxt').text if ET.iselement(
                        boardmemeber.find('.{http://www.irs.gov/efile}TitleTxt')) \
                        else None

                    Averagehoursworked = boardmemeber.find('.{http://www.irs.gov/efile}AverageHoursPerWeek').text if \
                        ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}AverageHoursPerWeek')) \
                        else boardmemeber.find('.{http://www.irs.gov/efile}AverageHoursPerWeekRt').text if \
                        ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}AverageHoursPerWeekRt')) else \
                        boardmemeber.find('.{http://www.irs.gov/efile}AverageHrsPerWkDevotedToPosRt').text if  \
                        ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}AverageHrsPerWkDevotedToPosRt')) else None
                        
                    Individualtrusteeordirector = boardmemeber.find('.{http://www.irs.gov/efile}IndividualTrusteeOrDirector').text \
                        if ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}IndividualTrusteeOrDirector')) else \
                        boardmemeber.find('.{http://www.irs.gov/efile}IndividualTrusteeOrDirectorInd').text if \
                            ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}IndividualTrusteeOrDirectorInd')) else None

                    compensation_from_org = boardmemeber.find(
                        '.{http://www.irs.gov/efile}ReportableCompFromOrganization').text if \
                        ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}ReportableCompFromOrganization')) else \
                        boardmemeber.find('.{http://www.irs.gov/efile}ReportableCompFromOrgAmt').text if \
                            ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}ReportableCompFromOrgAmt')) else \
                            boardmemeber.find('.{http://www.irs.gov/efile}CompensationAmt').text if \
                            ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}CompensationAmt')) else None

                    compensation_from_related_org = boardmemeber.find(
                        '.{http://www.irs.gov/efile}ReportableCompFromRelatedOrgs').text \
                        if ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}ReportableCompFromRelatedOrgs')) \
                        else boardmemeber.find('.{http://www.irs.gov/efile}ReportableCompFromRltdOrgAmt').text if \
                        ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}ReportableCompFromRltdOrgAmt')) else None

                    other_compensation = boardmemeber.find('.{http://www.irs.gov/efile}OtherCompensation').text if \
                        ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}OtherCompensation')) else \
                        boardmemeber.find('.{http://www.irs.gov/efile}OtherCompensationAmt').text if \
                            ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}OtherCompensationAmt')) else None
                            
                    filename = os.path.basename(i)
                    newdict = (filename, {'returnType': returnType,
                        'Title': Title,
                        'Average hours worked': Averagehoursworked,
                        'Truestee': Individualtrusteeordirector,
                        'Compensation': compensation_from_org,
                        'Related Compensation': compensation_from_related_org,
                        'Other Compensation': other_compensation})

                    mydict[i] = newdict[1]

                    rows.append([EIN, Name, Title, Averagehoursworked, Individualtrusteeordirector, compensation_from_org,
                                 compensation_from_related_org, other_compensation, year[0:4]])
                    df = pd.DataFrame(rows, columns=columns, dtype=object)
                    df.to_csv(filecheck)
                    
        except ET.ParseError as e:
            logger.error(f"XML parsing error in file {file_path}: {e}")
            error_handler.move_error_file(file_path, 
        error_reason=f"XML parsing error: {str(e)}", 
        logger=logger)
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing file {file_path}: {e}")
            error_handler.move_error_file(
                file_path, 
                error_reason=f"Processing error: {str(e)}", 
                logger=logger
            )
            continue

    logger.info("Processing completed for all files")
    # print(mydict)  # Removed print statement

    # Convert integer keys to strings
    mydict = {str(k): v for k, v in mydict.items()}

    # Write mydict to a JSON file
    json_output = f"{target_location}/Boardmembers.json"
    try:
        with open(json_output, 'w') as f:
            json.dump(mydict, f)
        logger.info(f"Successfully wrote JSON output to: {json_output}")
    except Exception as e:
        logger.error(f"Error writing JSON file {json_output}: {e}")


if __name__ == '__main__':
    # Example usage
    file_location = '/Volumes/TPC/2025-07-08/xml'
    target_location = '/Volumes/TPC/2025-07-08/csv'
    
    # Initialize logging
    logger = setup_logging(file_location)
    logger.info("Starting boardmember processing script")
    
    irs_boardmember(file_location, target_location)
    
    logger.info("Script completed")