import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
from multiprocessing import Pool, cpu_count


def political_contributions(file_path, target_location):
    if os.path.isdir(file_path):
        file_path = os.path.join(file_path, '*.xml')
        files = glob.glob(file_path)
    else:
        files = [file_path]

    results = []
    rows=[]

    try:
        for i in tqdm(files):
            tree = ET.parse(i)
            root = tree.getroot()
            filename = os.path.basename(i)
            donations = root[1].findall('.//{http://www.irs.gov/efile}Section527PoliticalOrgGrp')

            GrantorEIN_check = root[0].find('.//{http://www.irs.gov/efile}EIN').text
            year = root.find('.//{http://www.irs.gov/efile}TaxYr').text

            result_dict = {
                'file': filename,
                'EIN': GrantorEIN_check,
                'Year': year
            }
            columns=['ein','business_name1','businessname2','address_element_line1','address_element_line2','city','state', \
                    'zipcode','recipeint_ein','amount_paid','year']

            if ET.iselement(GrantorEIN_check):
                folder = os.path.join(target_location,year)
                if os.path.exists(folder):
                    pass
                else:
                    os.makedirs(folder, exist_ok=True)
            else:
                os.rename(i, '/Volumes/Storage/TPC990/Errors/' + os.path.basename(i))


            filecheck = target_location + '/' + year + '/political_contributions_' + GrantorEIN_check + '.csv'

            if donations is not None:
                result_dict['Political Donations'] = []
                for recipeint in donations:
                    donation_dict = {}
                    business_name_line1 = recipeint.find('.//{http://www.irs.gov/efile}BusinessNameLine1Txt').text or None
                    business_name_line2 = recipeint.find('.//{http://www.irs.gov/efile}BusinessNameLine2Txt').text if \
                        ET.iselement(recipeint.find('.//{http://www.irs.gov/efile}BusinessNameLine2Txt')) else None
                    address_element_line1 = recipeint.find('.//{http://www.irs.gov/efile}AddressLine1Txt').text
                    address_element_line2 = recipeint.find('.//{http://www.irs.gov/efile}AddressLine2Txt').text if \
                        ET.iselement(recipeint.find('.//{http://www.irs.gov/efile}AddressLine2Txt')) else ''
                    city_element = recipeint.find('.//{http://www.irs.gov/efile}CityNm').text or None
                    state_element = recipeint.find('.//{http://www.irs.gov/efile}StateAbbreviationCd').text
                    zipcode_element = recipeint.find('.//{http://www.irs.gov/efile}ZIPCd').text
                    political_EIN = recipeint.find('.//{http://www.irs.gov/efile}EIN').text or None

                    amount_paid = recipeint.find('.//{http://www.irs.gov/efile}PaidInternalFundsAmt').text
                    if amount_paid=='0' and recipeint.find('.//{http://www.irs.gov/efile}ContributionsRcvdDlvrAmt') is not None:
                        amount_paid = recipeint.find('.//{http://www.irs.gov/efile}ContributionsRcvdDlvrAmt').text





                    donation_dict['recipient_ein'] = political_EIN
                    donation_dict['Business_name'] = business_name_line1
                    donation_dict['Business_name_2'] = business_name_line2
                    donation_dict['City'] = city_element
                    donation_dict['State'] = state_element
                    donation_dict['ZipCode'] = zipcode_element
                    donation_dict['Donation amount'] = amount_paid

                    result_dict['Political Donations'].append(donation_dict)

                    rows.append([GrantorEIN_check, business_name_line1,business_name_line2,address_element_line1,address_element_line2, \
                                 city_element,state_element,zipcode_element,political_EIN,amount_paid,year])

                df = pd.DataFrame(rows, columns=columns, dtype=object)
            print(result_dict)
            print(filecheck)
            df.to_csv(filecheck)

        results.append(result_dict)


    except ET.ParseError:
        # Handle XML parse errors
        results.append({'file': i, 'error': f"Error parsing {i}"})
    except Exception as e:
        # Handle any other exceptions
        results.append({'file': i, 'error': f"Error processing {i}: {e}"})

    # TODO Create DF for export as well as file for json doc
    print(result_dict)
    return results


# Running the function on the provided file


if __name__ == "__main__":
    file_location = ('/Users/michaellingram/Downloads/xmlsamples/202341739349301804_public.xml')
    target_location = '/Users/michaellingram/Downloads/TPC'

political_contributions(file_location, target_location)
