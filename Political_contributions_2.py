import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
import json


def political_contributions(file_path, target_location):
    if os.path.isdir(file_path):
        file_path = os.path.join(file_path, '*.xml')
        files = glob.glob(file_path)
    else:
        files = [file_path]

    all_results = {}

    for i in tqdm(files):
        rows = []
        try:
            tree = ET.parse(i)
            root = tree.getroot()
            filename = os.path.basename(i)
            donations = root[1].findall('.//{http://www.irs.gov/efile}Section527PoliticalOrgGrp')

            GrantorEIN_check = root[0].find('.//{http://www.irs.gov/efile}EIN').text
            year = root.find('.//{http://www.irs.gov/efile}TaxYr').text

            result_dict = {
                'EIN': GrantorEIN_check,
                'Year': year,
                'Political Donations': {}
            }
            columns = ['ein', 'business_name1', 'businessname2', 'address_element_line1', 'address_element_line2',
                       'city', 'state', \
                       'zipcode', 'recipient_ein', 'amount_paid', 'year']

            folder = os.path.join(target_location, year)
            os.makedirs(folder, exist_ok=True)

            filecheck = os.path.join(folder, 'political_contributions_' + GrantorEIN_check + '.csv')
            #print(filecheck)

            if donations:
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
                                 address_element_line2,
                                 city_element, state_element, zipcode_element, political_EIN, amount_paid, year])

                df = pd.DataFrame(rows, columns=columns, dtype=object)
                df.to_csv(filecheck, index=False)
            else:
                pass

            all_results[filename] = result_dict

        except ET.ParseError:
            all_results[filename] = {'error': f"Error parsing {i}"}
        except Exception as e:
            all_results[filename] = {'error': f"Error processing {i}: {e}"}

    # Save all results to JSON
    with open(os.path.join(target_location, 'TPC_990_political.json'), 'w') as json_file:
        json.dump(all_results, json_file, indent=4)

    return all_results




if __name__ == "__main__":
    file_location = '/Users/michaellingram/Downloads/xml_test/2020'
    target_location = '/Users/michaellingram/Downloads/xml_test'
    political_contributions(file_location, target_location)
