import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
import json
import error_handler
from logging_setup import get_standard_logger
from xml_helpers import safe_find_element, get_element_text


def irs_boardmember(file_location, target_location, log_dir=None):
    logger = get_standard_logger('boardmembers', file_location, log_dir=log_dir)

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
        logger.debug(f'Processing file: {i}')
        
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
                error_handler.move_error_file(i, error_reason="No EIN found in XML file", logger=logger)
                logger.warning(f'{os.path.basename(i)} moved to errors directory')
                continue

            columns = ['ein', 'name', 'title', 'averagehousperweek', 'indivualtrusteeordirector', 'compensation_from_org',
                       'compensation_from_related_org', 'othercompens', 'year']

            return_check1 = root[0].find('./{http://www.irs.gov/efile}ReturnType') or root[0].find(
                './{http://www.irs.gov/efile}ReturnTypeCd')
            returnType = return_check1.text if ET.iselement(return_check1) else ''
            logger.debug(f"Return type: {returnType}")

            if returnType=='990':
                board_members = root[1].findall('./*{http://www.irs.gov/efile}Form990PartVIISectionAGrp')
            elif returnType=='990PF':
                if root[1].find('./*{http://www.irs.gov/efile}OfficerDirTrstKeyEmplInfoGrp') is not None:
                    board_members=root.findall('.//*{http://www.irs.gov/efile}OfficerDirTrstKeyEmplGrp')
                else:
                    logger.warning(f"990PF file missing OfficerDirTrstKeyEmplInfoGrp: {i}")
                    continue
            elif returnType=='990EZ':
                    board_members=root[1].findall('./*{http://www.irs.gov/efile}OfficerDirectorTrusteeEmplGrp')
            elif returnType=='990T':
                continue
            else:
                logger.warning(f"Unknown return type: {returnType} for file: {i}")
                continue

            EIN = get_element_text(root[0].find('.//{http://www.irs.gov/efile}EIN'))
            rows = []

            filecheck = target_location + '/' + year + '/boardmembers_' + EIN + '.csv'
            logger.debug(f"Output file will be: {filecheck}")

            for board_member in board_members:
                    Name = get_element_text(board_member.find("{http://www.irs.gov/efile}PersonNm")) or None

                    Title = get_element_text(board_member.find('.{http://www.irs.gov/efile}TitleTxt')) or None

                    Averagehoursworked = (
                        get_element_text(safe_find_element(
                            board_member,
                            '.{http://www.irs.gov/efile}AverageHoursPerWeek',
                            '.{http://www.irs.gov/efile}AverageHoursPerWeekRt'))
                        or get_element_text(board_member.find('.{http://www.irs.gov/efile}AverageHrsPerWkDevotedToPosRt'))
                        or None)

                    Individualtrusteeordirector = get_element_text(safe_find_element(
                        board_member,
                        '.{http://www.irs.gov/efile}IndividualTrusteeOrDirector',
                        '.{http://www.irs.gov/efile}IndividualTrusteeOrDirectorInd')) or None

                    compensation_from_org = (
                        get_element_text(board_member.find('.{http://www.irs.gov/efile}ReportableCompFromOrganization'))
                        or get_element_text(board_member.find('.{http://www.irs.gov/efile}ReportableCompFromOrgAmt'))
                        or get_element_text(board_member.find('.{http://www.irs.gov/efile}CompensationAmt'))
                        or None)

                    compensation_from_related_org = get_element_text(safe_find_element(
                        board_member,
                        '.{http://www.irs.gov/efile}ReportableCompFromRelatedOrgs',
                        '.{http://www.irs.gov/efile}ReportableCompFromRltdOrgAmt')) or None

                    other_compensation = get_element_text(safe_find_element(
                        board_member,
                        '.{http://www.irs.gov/efile}OtherCompensation',
                        '.{http://www.irs.gov/efile}OtherCompensationAmt')) or None
                            
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

            if rows:
                df = pd.DataFrame(rows, columns=columns, dtype=object)
                df.to_csv(filecheck, index=False)

        except ET.ParseError as e:
            logger.error(f"XML parsing error in file {i}: {e}")
            error_handler.move_error_file(
                i,
                error_reason=f"XML parsing error: {str(e)}",
                logger=logger
            )
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing file {i}: {e}")
            error_handler.move_error_file(
                i,
                error_reason=f"Processing error: {str(e)}",
                logger=logger
            )
            continue

    logger.info("Processing completed for all files")

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
    file_location = '/Volumes/TPC/2025-07-08/xml'
    target_location = '/Volumes/TPC/2025-07-08/csv'
    irs_boardmember(file_location, target_location)