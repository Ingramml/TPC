import os
import glob
import pandas as pd
import xml.etree.ElementTree as ET
from multiprocessing import Pool, cpu_count


def extract_ein(root):
    # Your extraction logic here
    # For this example, let's extract the EIN element only if it's a child tag of Filer
    ein_check = root[0].find('./*{http://www.irs.gov/efile}EIN')
    if ein_check is not None:
      return ein_check.text

def business_name_line1(root):
    filer = root[0].find('./{http://www.irs.gov/efile}Filer')
    business_name_line1_check = filer.find('./*{http://www.irs.gov/efile}BusinessNameLine1Txt')
    if business_name_line1_check is not None:
        return business_name_line1_check.text.upper()

def business_name_line2(root):
    filer = root[0].find('./{http://www.irs.gov/efile}Filer')
    business_name_line2_check = filer.find('.//{http://www.irs.gov/efile}BusinessNameLine2Txt')
    if business_name_line2_check is not None:
        return business_name_line2_check.text.upper()

def address_line_1(root):
    filer = root[0].find('./{http://www.irs.gov/efile}Filer')
    address_line_1_check = filer.find('.//{http://www.irs.gov/efile}AddressLine1Txt')
    if address_line_1_check is not None:
        return address_line_1_check.text.upper()
def address_line_2(root):
    filer = root[0].find('./{http://www.irs.gov/efile}Filer')
    address_line_2_check = filer.find('.//{http://www.irs.gov/efile}AddressLine2Txt')
    if address_line_2_check is not None:
        return address_line_2_check.text.upper()
def address_state(root):
    filer = root[0].find('./{http://www.irs.gov/efile}Filer')
    address_state_check = filer.find('.//{http://www.irs.gov/efile}StateAbbreviationCd')
    if address_state_check is not None:
        return address_state_check.text.upper()

def address_state(root):
    filer = root[0].find('./{http://www.irs.gov/efile}Filer')
    address_city_check = filer.find('.//{http://www.irs.gov/efile}StateAbbreviationCd')
    if address_city_check is not None:
        return address_city_check.text.upper()

def address_zipcd(root):
    filer = root[0].find('./{http://www.irs.gov/efile}Filer')
    address_zipcd_check = filer.find('.//{http://www.irs.gov/efile}ZIPCd')
    if address_zipcd_check is not None:
        return address_zipcd_check.text.upper()

def total_assets_boy(root):
    Form990TotalAssetsGrpy_check = root[1].find('.//{http://www.irs.gov/efile}Form990TotalAssetsGrp')
    BOY_check = root[1].find('.//*{http://www.irs.gov/efile}BOYAmt')
    if Form990TotalAssetsGrpy_check is not None:
        if BOY_check is not None:
            return BOY_check.text

def total_assets_eoy(root):
    Form990TotalAssetsGrpy_check = root[1].find('.//{http://www.irs.gov/efile}Form990TotalAssetsGrp')
    EOY_check = root[1].find('.//*{http://www.irs.gov/efile}EOYAmt')
    if Form990TotalAssetsGrpy_check is not None:
        if EOY_check is not None:
            return EOY_check.text


def website(root):
    website_check = root[1].find('./*{http://www.irs.gov/efile}WebsiteAddressTxt')
    if website_check is not None:
        return website_check.text


def tax_year(root):
    tax_year_check       = root[0].find('./{http://www.irs.gov/efile}TaxYr')
    if tax_year_check is not None:
        return tax_year_check.text


def total_revenue(root):
    total_revenue_check = root[1].find('./*{http://www.irs.gov/efile}TotalRevenueAmt') or root[1].find('./*{http://www.irs.gov/efile}CYTotalRevenueAmt')
    if total_revenue_check is not None:
        return total_revenue_check.text


def total_expense(root):
    total_expense_check = root[1].find('./*{http://www.irs.gov/efile}TotalExpensesAmt') or root[1].find('./*{http://www.irs.gov/efile}CYTotalExpensesAmt')
    if total_expense_check is not None:
        return  total_expense_check.text


def return_type(root):
    return_type_check = root[0].find('./{http://www.irs.gov/efile}ReturnTypeCd')
    if return_type_check is not None:
        return return_type_check.text

def mission(root):
    mission_check = root[1].find()






def process_file(file):
    tree = ET.parse(file)
    root = tree.getroot()
    data = extract_ein(root)
    return data




def extract_all_data(file_location):
    if not os.path.exists(file_location):
        print("Directory does not exist.")
        return

    files = glob.glob(os.path.join(file_location, '*.xml'))

    # Use all available CPU cores for parallel processing
    num_cores = min(cpu_count(), len(files))
    with Pool(processes=num_cores) as pool:
        extracted_data = pool.map(process_file, files)

    # Remove any None values from the extracted data
    extracted_data = [data for data in extracted_data if data is not None]

    # Create a pandas DataFrame from the extracted data
    df = pd.DataFrame(extracted_data, columns=["EIN"])

    return df


if __name__ == "__main__":
    # Test the extract_data function with an individual XML file
    sample_xml_file = '/Users/michaellingram/Downloads/xml_test/202143129349301304_public.xml'
    tree = ET.parse(sample_xml_file)
    root = tree.getroot()
    extracted_ein = extract_ein(root)
    business_name_line1 = business_name_line1(root)
    business_name_line2 = business_name_line2(root)
    address_line_1      =  address_line_1(root)
    total_assets_boy    = total_assets_boy(root)
    website             =  website(root)
    tax_year          = tax_year(root)
    total_revenue       = total_revenue(root)
    total_expense       = total_expense(root)
    return_type         = return_type(root)

    print(f"Extracted EIN: {extracted_ein}")
    print(f"Extracted Business Name line 1: {business_name_line1}")
    print(f"Extractec Business Name Line 2: {business_name_line2}")
    print(f"Extracted Address Line 1: {address_line_1}")
    print(f"Total assest Begion of the Year: {total_assets_boy}")
    print(f"Total assets end of the year: {total_assets_eoy(root)}")
    print(f"Return type: {return_type}")
    print(f"Website is :{website}")
    print(f"Tax year is :{tax_year}")
    print(f"Total Revenue: {total_revenue}")
    print(f"Total Expense: {total_expense}")

    # Run the extract_all_data function on a directory containing XML files
    # file_location = '/path/to/xml_files_directory'
    # extracted_data_df = extract_all_data(file_location)
    # print(extracted_data_df)
