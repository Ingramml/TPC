import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
from multiprocessing import Pool, cpu_count
import json


def process_single_file(file_path, target_location):
    try:
        """
        if os.path.isdir(file_path):
            # Search for XML files in the directory and all subdirectories
            file_path = os.path.join(file_path, '**', '*.xml')
            print(file_path)
            files = glob.glob(file_path, recursive=True)
        else:
            # If file_path is not a directory, assume it's a single file
            files = [file_path]
        print(files)
        """
        files = []
        if os.path.isdir(file_path):
            # Search for XML files in the directory and all subdirectories
            for root, dirs, files_in_dir in os.walk(file_path):
                for file in files_in_dir:
                    if file.endswith('.xml'):
                        files.append(os.path.join(root, file))
        else:
            # If file_path is not a directory, assume it's a single file
            if file_path.endswith('.xml'):
                files.append(file_path)

        grants_empty_dict={}

        for i in files:
           # print(i)
            tree = ET.parse(i)
            root = tree.getroot()
            GrantorEIN_check = root[0].find('./*{http://www.irs.gov/efile}EIN')
            begindate_check = root[0].find('./{http://www.irs.gov/efile}TaxPeriodBeginDate')
            begindate_chcek2 = root[0].find('./{http://www.irs.gov/efile}TaxPeriodBeginDt')
            begindate = begindate_check.text if ET.iselement(begindate_check) else begindate_chcek2.text if \
                ET.iselement(begindate_chcek2) else ''
            year = begindate[0:4]

            if ET.iselement(GrantorEIN_check):
                folder = os.path.join(target_location, begindate[0:4])
                if os.path.exists(folder):
                    pass
                else:
                    os.makedirs(folder, exist_ok=True)
            else:
                os.rename(i, '/Volumes/Storage/TPC990/Errors/' + os.path.basename(i))

            GrantorEIN = GrantorEIN_check.text
            # filenames
            filecheck = target_location + '/' + year + '/grants_' + GrantorEIN + '.csv'

            if os.path.isfile(filecheck):
                pass
            else:

                ScheduleI = root[1].find('{http://www.irs.gov/efile}IRS990ScheduleI')
                GrantOrContributionPdDurYrGrp_check = root[1].find(
                    "./*/*/{http://www.irs.gov/efile}GrantOrContributionPdDurYrGrp")

                GrantOrContributionPdDurYrGrp = root[1].findall(
                    "./*/*/{http://www.irs.gov/efile}GrantOrContributionPdDurYrGrp")
                if ET.iselement(ScheduleI) == True and ET.iselement(
                        ScheduleI.find('{http://www.irs.gov/efile}RecipientTable')):
                    RecipientTable = ScheduleI.find('{http://www.irs.gov/efile}RecipientTable')
                    RecipientTablelist = ScheduleI.findall('{http://www.irs.gov/efile}RecipientTable')
                    rows = []
                    for recipient in RecipientTablelist:
                        recipient_EIN_check = recipient.find('./{http://www.irs.gov/efile}RecipientEIN')
                        recipient_EIN_check2 = recipient.find('./{http://www.irs.gov/efile}EINOfRecipient')
                        recipient_EIN = recipient_EIN_check.text if ET.iselement(recipient_EIN_check) else \
                            recipient_EIN_check2.text if ET.iselement(recipient_EIN_check2) else ''

                        business_name_check = recipient.find('./*/{http://www.irs.gov/efile}BusinessNameLine1Txt')
                        business_name_check2 = recipient.find('./{http://www.irs.gov/efile}RecipientPersonNm')
                        business_name_check3 = recipient.find('./*/{http://www.irs.gov/efile}BusinessNameLine1')
                        business_name = business_name_check.text if ET.iselement(
                            business_name_check) else business_name_check3.text if ET.iselement(
                            business_name_check3) else business_name_check2.text if ET.iselement(
                            business_name_check2) else ''

                        business_name_check_ln2 = recipient.find('./*/{http://www.irs.gov/efile}BusinessNameLine2Txt')
                        business_name_check2_ln2 = recipient.find('./*/{http://www.irs.gov/efile}BusinessNameLine2')
                        business_name_ln2 = business_name_check_ln2.text if ET.iselement(
                            business_name_check_ln2) else business_name_check2_ln2.text \
                            if ET.iselement(business_name_check2_ln2) else ''

                        business_name = business_name.upper() + ' ' + business_name_ln2.upper()


                        amount_element_check = recipient.find('./{http://www.irs.gov/efile}CashGrantAmt')
                        amount_element_check2 = recipient.find('./{http://www.irs.gov/efile}AmountOfCashGrant')
                        amount_element = amount_element_check.text if ET.iselement(amount_element_check) else \
                            amount_element_check2.text if ET.iselement(amount_element_check2) else None

                        status_element_check = recipient.find('./{http://www.irs.gov/efile}IRCSectionDesc')
                        status_element_check2 = recipient.find('./{http://www.irs.gov/efile}IRCSection')
                        status_element = status_element_check.text if ET.iselement(status_element_check) else \
                            status_element_check2.text if ET.iselement(status_element_check2) else None

                        purpose_element_check = recipient.find('./{http://www.irs.gov/efile}PurposeOfGrantTxt')
                        purpose_element_check2 = recipient.find('./{http://www.irs.gov/efile}PurposeOfGrant')
                        purpose_element = purpose_element_check.text if ET.iselement(purpose_element_check) else  \
                            purpose_element_check2.text if ET.iselement(purpose_element_check2) else None


                        if amount_element == '0' or amount_element is None and recipient.find('./{http://www.irs.gov/efile}NonCashAssistanceAmt') is not None:
                            amount_element = recipient.find('./{http://www.irs.gov/efile}NonCashAssistanceAmt').text
                            purpose_element = purpose_element+'*'


                        rows.append([GrantorEIN, recipient_EIN, business_name, amount_element,
                                     purpose_element, year])

                    df = pd.DataFrame(rows, columns=["grantor_ein", "grantee_ein", "grantee_name", "amount", "purpose",
                                                     "year"], dtype="object")  # creates df of orgs donations
                    df.to_csv(filecheck)
                elif ET.iselement(GrantOrContributionPdDurYrGrp_check):
                    grants_list = root[1].findall("./*/*/{http://www.irs.gov/efile}GrantOrContributionPdDurYrGrp")
                    rows = []
                    for recipient in grants_list:
                        # EINs
                        recipient_EIN_check = recipient.find('./{http://www.irs.gov/efile}RecipientEIN')
                        recipient_EIN = recipient_EIN_check.text if ET.iselement(recipient_EIN_check) \
                            else recipient.find('./{http://www.irs.gov/efile}EINOfRecipient')
                        # Org Names ln1
                        business_name_check = recipient.find('./*/{http://www.irs.gov/efile}BusinessNameLine1Txt')
                        business_name_check2 = recipient.find('./{http://www.irs.gov/efile}RecipientPersonNm')
                        business_name_check3 = recipient.find('./*/{http://www.irs.gov/efile}BusinessNameLine1')
                        business_name = business_name_check.text if ET.iselement(
                            business_name_check) else business_name_check3.text if ET.iselement(
                            business_name_check3) else business_name_check2.text if ET.iselement(
                            business_name_check2) else None
                        # Org name ln2
                        business_name_check_ln2 = recipient.find('./*/{http://www.irs.gov/efile}BusinessNameLine2Txt')
                        business_name_check2_ln2 = recipient.find('./*/{http://www.irs.gov/efile}BusinessNameLine2')
                        business_name_ln2 = business_name_check_ln2.text if ET.iselement(
                            business_name_check_ln2) else business_name_check2_ln2.text \
                            if ET.iselement(business_name_check2_ln2) else None

                        business_name = business_name.upper() + ' ' + business_name_ln2.upper()

                        # Amount
                        amount_element_check = recipient.find('./{http://www.irs.gov/efile}Amt')
                        amount_element = amount_element_check.text if ET.iselement(amount_element_check) \
                            else recipient.find('./{http://www.irs.gov/efile}AmountOfCashGrant').text if \
                            ET.iselement(recipient.find('./{http://www.irs.gov/efile}AmountOfCashGrant')) else None


                        # Org Status
                        status_element_check = recipient.find('./{http://www.irs.gov/efile}Status')
                        status_element = status_element_check.text if ET.iselement(status_element_check) else None
                        # Purpose
                        purpose_element_check = recipient.find('./{http://www.irs.gov/efile}GrantOrContributionPurposeTxt')
                        purpose_element = purpose_element_check.text if ET.iselement(purpose_element_check) else None

                        if amount_element == '0' or amount_element is None and recipient.find('./{http://www.irs.gov/efile}NonCashAssistanceAmt') is not None:
                            amount_element = recipient.find('./{http://www.irs.gov/efile}NonCashAssistanceAmt').text
                            purpose_element = purpose_element + '*'


                        # combines Element
                        rows.append([GrantorEIN, recipient_EIN, business_name, amount_element,status_element, purpose_element, year])

                    df = pd.DataFrame(rows, columns=["grantor_ein", "grantee_ein", "grantee_name", "amount",'status', "purpose",
                                                     "year"], dtype="object")
                    df.to_csv(filecheck)

                    grants_dict = (i,{"EIN":GrantorEIN,
                    "Buisnes name": business_name.upper(),
                    "Busines name2": business_name_ln2.upper(),
                    "Amount"       : amount_element,
                    'Status'       : status_element,
                    'Purpose'       :purpose_element,
                    'Year'          :year

                    })

                    grants_empty_dict[i] = grants_dict[1]
                    print(grants_empty_dict)



                else:
                    pass


            grants_empty_dict = {str(k): v for k, v in grants_empty_dict.items()}


            with open('/Users/michaellingram/Downloads/profiles.json', 'w') as f:
                json.dump(grants_empty_dict, f)



        return f"Processed {file_path}"
    except ET.ParseError:
        # Handle XML parse errors
        return f"Error parsing {file_path}"
    except Exception as e:
        # Handle any other exceptions
        return f"Error processing {file_path}: {e}"


# Move the helper function to the top-level scope
def process_file_helper(args):
    return process_single_file(*args)


def irs_grants(file_location, target_location):
    """
    my_extension = "*.xml"
    my_pattern = file_location + "/" + my_extension
    print(my_pattern)
    files = glob.glob(my_pattern)

    # Create a list of argument tuples
    args = [(file, target_location) for file in files]

    # Use multiprocessing to process files in parallel
    with Pool(processes=cpu_count()) as pool:
        results = list(tqdm(pool.imap(process_file_helper, args), total=len(files)))

    # Print the results
    for result in results:
        print(result)
    """
    if os.path.isdir(file_location):
        # If file_location is a directory, prepare to process all XML files in it
        files = []
        for root, dirs, files_in_dir in tqdm(os.walk(file_location)):
            for file in files_in_dir:
                if file.endswith('.xml'):
                    files.append(os.path.join(root, file))
    elif os.path.isfile(file_location) and file_location.endswith('.xml'):
        # If file_location is a single XML file, prepare to process it
        files = [file_location]
    else:
        print(f"No valid XML files found in {file_location}")
        return

    args = [(file, target_location) for file in files]

    with Pool(processes=cpu_count()) as pool:
        results = list(tqdm(pool.imap(process_file_helper, args), total=len(files)))

    for result in results:
        print(result)



# Add the if __name__ guard to ensure the code runs only in the main process
if __name__ == '__main__':
    irs_grants('/Volumes/TPC/xml', '/Users/michaellingram/Downloads/TPC')
    #process_single_file('/Users/michaellingram/Downloads/xmlsamples/202341739349301804_public.xml','/Users/michaellingram/Downloads')