import os
import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm

def extract_irs_data(file_location, target_location):
    if not os.path.exists(file_location) or not os.path.exists(target_location):
        print("One or both directories do not exist.")
        return

    def get_text(element):
        return element.text if ET.iselement(element) else ''

    def get_attribute(element, attribute):
        return element.attrib[attribute] if ET.iselement(element) and attribute in element.attrib else ''

    def create_folder_if_not_exists(path):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    files = glob.glob(os.path.join(file_location, '*.xml'))

    for file in tqdm(files):
        tree = ET.parse(file)
        root = tree.getroot()

        GrantorEIN = get_text(root[0].find('./*{http://www.irs.gov/efile}EIN'))


        year = begindate[0:4]

        folder = os.path.join(target_location, year)
        create_folder_if_not_exists(folder)

        GrantorEIN_check = root[0].find('./*{http://www.irs.gov/efile}EIN')
        if not ET.iselement(GrantorEIN_check):
            os.rename(file, os.path.join('/Volumes/Storage/TPC990/Errors', os.path.basename(file)))
            continue

        filecheck_income = os.path.join(target_location, year, f'income_expenses_{GrantorEIN}.csv')
        filecheck_profile = os.path.join(target_location, year, f'profile_{GrantorEIN}.csv')

        returnType = get_text(root[0].find('./{http://www.irs.gov/efile}ReturnType'))



        Revenue = get_text(root[1].find('./*{http://www.irs.gov/efile}TotalRevenueCurrentYear') or
                           root[1].find('./*{http://www.irs.gov/efile}Revenue') or
                           root[1].find('./*{http://www.irs.gov/efile}CYTotalRevenueAmt') or
                           root[1].find('./*{http://www.irs.gov/efile}TotalRevenueAmt') or
                           root[1].find('./*{http://www.irs.gov/efile}TotalRevenue'))
        Expense = get_text(root[1].find('./*{http://www.irs.gov/efile}TotalExpensesCurrentYear') or
                           root[1].find('./*{http://www.irs.gov/efile}Expenses') or
                           root[1].find('./*{http://www.irs.gov/efile}CYTotalExpensesAmt') or
                           root[1].find('./*{http://www.irs.gov/efile}TotalExpensesAmt') or
                           root[1].find('./*{http://www.irs.gov/efile}TotalExpenses'))


        # Other data extractions...

        # Create income expense csv
        df_income_expense = pd.DataFrame([[GrantorEIN, Revenue, Expense, returnType, year]],
                                         columns=["ein", "revenue", "expenses", "return_type", "year"],
                                         dtype="object")
        df_income_expense.to_csv(filecheck_income, index=False)

        # Create profile csv
        df_profile = pd.DataFrame([[GrantorEIN, returnType, year]], columns=["ein", "return_type", "year"], dtype="object")
        df_profile.to_csv(filecheck_profile, index=False)

if __name__ == "__main__":
    #file_location = '/Volumes/TPC/xml'
    #target_location = '/Users/michaellingram/Downloads/TPC'

    extract_irs_data('/Volumes/TPC/xml', '/Users/michaellingram/Downloads/TPC')
