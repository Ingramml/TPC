import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
import json


def irs_expense_income(file_location,target_location):
    if os.path.isdir(file_location):
        file_path = os.path.join(file_location,'*/', '*.xml')
        #print(file_location)
        files = glob.glob(file_path)
    else:
        files=[file_location]

    profile_empty_dict={}
    income_expense_empty_dict={}

    for i in tqdm(files):
        #print(i)
        rows_income_expense = []
        rows2_profile = []
        tree = ET.parse(i)
        root = tree.getroot()
        GrantorEIN_check = root[0].find('./*{http://www.irs.gov/efile}EIN')
        begindate_check = root[0].find('./{http://www.irs.gov/efile}TaxPeriodBeginDate')
        begindate_chcek2 = root[0].find('./{http://www.irs.gov/efile}TaxPeriodBeginDt')
        begindate = begindate_check.text if ET.iselement(begindate_check) else begindate_chcek2.text if \
            ET.iselement(begindate_chcek2) else ''

        year = begindate[0:4]

        GrantorEIN = GrantorEIN_check.text
        # Creates folder based on begining year of tax return(begindate)

        if ET.iselement(GrantorEIN_check):
            folder = os.path.join(target_location, begindate[0:4])
            if os.path.exists(folder):
                pass
            else:
                os.makedirs(folder, exist_ok=True)
        else:
            os.rename(i,'/Volumes/Storage/TPC990/Errors/'+os.path.basename(i))
            # print(os.path.basename(i) + ' moved')

        GrantorEIN = GrantorEIN_check.text

        filecheck_income = target_location + '/' + year + '/income_expenses_' + GrantorEIN + '.csv'
        filecheck_Profile = target_location + '/' + year + '/profile_' + GrantorEIN + '.csv'
        """
        if os.path.exists(filecheck_income) and os.path.exists(filecheck_Profile):
            pass
        else:
        """
        Filer = root[0].find('./{http://www.irs.gov/efile}Filer')

        # line 1 check
        businessname_check_ln1 = Filer.find('./*{http://www.irs.gov/efile}BusinessNameLine1')  # 2010 2013
        businessname_check2_ln1 = Filer.find('./*{http://www.irs.gov/efile}BusinessNameLine1Txt')  # 2020 2014 2016

        businessname_ln1 = businessname_check_ln1.text.upper() if ET.iselement(businessname_check_ln1) else \
            businessname_check2_ln1.text.upper() if ET.iselement(businessname_check2_ln1) else ''
        # line 2 check
        businessname_check_ln2 = Filer.find('./*{http://www.irs.gov/efile}BusinessNameLine2')
        businessname_check2_ln2 = Filer.find('./*{http://www.irs.gov/efile}BusinessNameLine2Txt')
        businessname_ln2 = businessname_check_ln2.text.upper() if ET.iselement(businessname_check_ln2) else \
            businessname_check2_ln2.text.upper() if ET.iselement(businessname_check2_ln2) else ''


        # returnType
        return_check1 = root[0].find('./{http://www.irs.gov/efile}ReturnType') or root[0].find('./{http://www.irs.gov/efile}ReturnTypeCd')


        returnType = return_check1.text if ET.iselement(return_check1) else ''


        #Expenses and Revenue
        total_revenue_check = root[1].find('./*{http://www.irs.gov/efile}TotalRevenueAmt') or root[1].find('./*{http://www.irs.gov/efile}CYTotalRevenueAmt')

        total_expenses_check    = root[1].find('./*{http://www.irs.gov/efile}TotalExpensesAmt') or root[1].find('./*{http://www.irs.gov/efile}CYTotalExpensesAmt')

        if returnType =='990PF':
            pf_AnalysisOfRevenueAndExpenses_check = root[1].find(
                './/*{http://www.irs.gov/efile}AnalysisOfRevenueAndExpenses')
            pf_TotalRevAndExpnssAmt_check = root[1].find('.//*{http://www.irs.gov/efile}TotalRevAndExpnssAmt')
            pf_TotalExpensesRevAndExpnssAmt = root[1].find('.//{http://www.irs.gov/efile}TotalExpensesRevAndExpnssAmt')
            if pf_AnalysisOfRevenueAndExpenses_check is not None:
                if pf_TotalRevAndExpnssAmt_check is not None:
                    Expense = pf_TotalRevAndExpnssAmt_check.text
                    Revenue = pf_TotalExpensesRevAndExpnssAmt.text
        elif returnType =='990EZ':
            total_revenue_check = root[1].find('./*{http://www.irs.gov/efile}TotalRevenueAmt')
            total_expenses_check = root[1].find('./*{http://www.irs.gov/efile}TotalExpensesAmt')
            Revenue = total_revenue_check.text if ET.iselement(total_revenue_check) and total_revenue_check is not None else None
            Expense = total_expenses_check.text if ET.iselement(total_expenses_check) and total_expenses_check is not None else None
        elif returnType != '990PF':
            Revenue = total_revenue_check.text if ET.iselement(total_revenue_check)==True and total_revenue_check is not None else None
            Expense = total_expenses_check.text if ET.iselement(total_expenses_check)==True and total_expenses_check  is not None else None
        elif returnType !='990T':
            Revenue = None
            Expense = None
        else:
            Revenue = None
            Expense = None


        address_element_check = root[0].find('.*/*{http://www.irs.gov/efile}AddressLine1Txt')
        address_element_check2 = root[0].find('.*/*{http://www.irs.gov/efile}AddressLine1')
        address_element_line1 = address_element_check.text if ET.iselement(
            address_element_check) else address_element_check2.text if ET.iselement(
            address_element_check2) else ''

        address_element_line2_check = root[0].find('.*/*{http://www.irs.gov/efile}AddressLine2Txt')
        address_element_line22_check = root[0].find('.*/*{http://www.irs.gov/efile}AddressLine2')
        address_element_line2 = address_element_line2_check.text if ET.iselement(
            address_element_line2_check) else address_element_line22_check.text if ET.iselement(
            address_element_line22_check) else ''

        address_element_city_check = root[0].find('.*/*{http://www.irs.gov/efile}CityNm')
        address_element_city_check2 = root[0].find('.*/*{http://www.irs.gov/efile}City')
        address_element_city = address_element_city_check.text if ET.iselement(
            address_element_city_check) else address_element_city_check2.text if ET.iselement(
            address_element_city_check2) else ''

        address_element_state_check = root[0].find('.*/*{http://www.irs.gov/efile}StateAbbreviationCd')
        address_element_state_check2 = root[0].find('.*/*{http://www.irs.gov/efile}State')
        address_element_state = address_element_state_check.text if ET.iselement(
            address_element_state_check) else address_element_state_check2.text if ET.iselement(
            address_element_state_check2) else ''

        address_element_zip_check = root[0].find('.*/*{http://www.irs.gov/efile}ZIPCd')
        address_element_zip_check2 = root[0].find('.*/*{http://www.irs.gov/efile}ZIPCode')
        address_element_zip = address_element_zip_check.text if ET.iselement(
            address_element_zip_check) else address_element_zip_check2.text if ET.iselement(
            address_element_zip_check2) else ''
        # Website
        website_element_check = root[1].find('./*{http://www.irs.gov/efile}WebsiteAddressTxt')
        website_element_check2 = root[1].find('./*{http://www.irs.gov/efile}WebSite')

        website_element = website_element_check.text.upper() if ET.iselement(website_element_check) \
            else website_element_check2.text.upper() if ET.iselement(website_element_check2) else ''


        #Total Assest EOY and BOY
        if returnType == '990PF':
            Form990TotalAssetsGrpy_check = root[1].find('./*{http://www.irs.gov/efile}Form990PFBalanceSheetsGrp')
            BOY_check = root[1].find('.//*{http://www.irs.gov/efile}TotalAssetsBOYAmt')
            EOY_check = root[1].find('.//*{http://www.irs.gov/efile}TotalAssetsEOYAmt')
            if Form990TotalAssetsGrpy_check is not None:
                total_assets_eoy = EOY_check.text if ET.iselement(EOY_check) and  EOY_check is not None else None
                total_assets_boy = BOY_check.text if ET.iselement(BOY_check) and BOY_check is not None else None
            else:
                total_assets_boy= None
                total_assets_eoy = None
        elif returnType == '990':
            total_assets_boy_check1 = root[1].find('./*{http://www.irs.gov/efile}TotalAssetsBOY') or root[1].find(
                './/*{http://www.irs.gov/efile}Form990TotalAssetsGrp/BOYAmt>') \
                                      or root[1].find('.{http://www.irs.gov/efile}Form990TotalAssetsGrp/{http://www.irs.gov/efile}BOYAmt>') or \
                                      root[1].find('./*{http://www.irs.gov/efile}Form990TotalAssetsGrp/{http://www.irs.gov/efile}BOYAmt') \
                                      or root[1].find('./*{http://www.irs.gov/efile}TotalAssetsBOYAmt') or root[1].find('./*{http://www.irs.gov/efile}TotalAssetsGrp/{http://www.irs.gov/efile}BOYAmt')

            total_assets_eoy_check1 = root[1].find('./*{http://www.irs.gov/efile}TotalAssetsEOY') or root[1].find(
                './/*{http://www.irs.gov/efile}Form990TotalAssetsGrp/{http://www.irs.gov/efile}EOYAmt>') \
                                      or root[1].find('.{http://www.irs.gov/efile}Form990TotalAssetsGrp/{http://www.irs.gov/efile}EOYAmt>') or \
                                      root[1].find('./*{http://www.irs.gov/efile}Form990TotalAssetsGrp/{http://www.irs.gov/efile}EOYAmt') \
                                      or root[1].find('./*{http://www.irs.gov/efile}TotalAssetsEOYAmt')
            total_assets_boy = total_assets_boy_check1.text if ET.iselement(total_assets_boy_check1) and total_assets_boy_check1 is not None else '990 error_1'
            total_assets_eoy = total_assets_eoy_check1.text if ET.iselement(total_assets_eoy_check1) and total_assets_eoy_check1 is not None else '990 error_1'


        elif returnType == '990EZ':
            assets_check = root[1].find('./*{http://www.irs.gov/efile}Form990TotalAssetsGrp')
            if assets_check is not None:
                BOY_check = root[1].find('.//*{http://www.irs.gov/efile}BOYAmt')
                EOY_check = root[1].find('.//*{http://www.irs.gov/efile}EOYAmt')
                total_assets_boy = BOY_check.text if ET.iselement(BOY_check) and BOY_check is not None else '990EZ error_2'
                total_assets_eoy = EOY_check.text if ET.iselement(EOY_check) and EOY_check is not None else '990EZ error_2'
        else:
            # Define a default value if none of the conditions are met
            total_assets_boy = 'General error'
            total_assets_eoy = 'General Error'


        # Status
        #TODO need to deal with dictionary reuslts
        status_check = root[1].find(
            './*{http://www.irs.gov/efile}Organization501cInd')  # need attribute['organization501cTypeTx'] taxyears 2013,2016
        status_check2 = root[1].find(
            './*{http://www.irs.gov/efile}Organization501c')  # needs attribtue['typeOf501cOrganization'] taxyears 2010,2011,2012
        status_check3 = root[1].find('./*{http://www.irs.gov/efile}Organization501c3Ind')  # if equals x use 1st
        status_check4 = root[1].find('./*{http://www.irs.gov/efile}Organization501c3')
        status = "501(c)3" if ET.iselement(status_check3) and status_check3.text == 'X' else '501(c)' + str(
            status_check.attrib['organization501cTypeTx']) \
            if ET.iselement(status_check) and ET.iselement(status_check.attrib) == 'organization501cTypeTxt' else \
            '501(c)' + str(status_check2.attrib['typeOf501cOrganization']) if ET.iselement(status_check2) else '501(c)3' if \
                ET.iselement(status_check4) and status_check4.text == 'X' else ''

        #mission
        mission_check1 = root[1].find("./*{http://www.irs.gov/efile}ActivityOrMissionDesc")
        mission_check2 = root[1].find('./*{http://www.irs.gov/efile}PrimaryExemptPurposeTxt')
        mission_check3 = root[1].find('./*{http://www.irs.gov/efile}MissionDesc')
        mission_check4 = root[1].find('./*{http://www.irs.gov/efile}ActivityOrMissionDescription')


        mission = mission_check1.text if ET.iselement(mission_check1) else mission_check2.text if ET.iselement(mission_check2) \
            else mission_check3.text if ET.iselement(mission_check3) else mission_check4.text if ET.iselement(mission_check4) \
            else ''

        # Creates income expense csv
        rows_income_expense.append([GrantorEIN, Revenue, Expense, total_assets_boy, total_assets_eoy,
                                   returnType, year])

        df = pd.DataFrame(rows_income_expense, columns=["ein","revenue", "expenses", "total_assets_boy",
                                                        "total_assets_eoy","return_type","year"], dtype="object")

        # Creates profiles Csv
        rows2_profile.append([GrantorEIN, businessname_ln1.upper(), businessname_ln2.upper(), address_element_line1.upper(),
                              address_element_line2.upper(), address_element_city.upper(), address_element_state,
                              address_element_zip, website_element, mission.upper(), status, year])

        df2 = pd.DataFrame(rows2_profile, columns=["ein", "org_name1", "org_name2", "address_1", "address_2", "city",
                                                   "state", "zipcode", "website", "mission","status", "year"], dtype="object")

        """
        print(f"Total Assets EOY is: {total_assets_eoy} for type {returnType} document {i} ")
        print(f"Total Assets BOY is: {total_assets_boy} for type {returnType} document {i} ")
        print(f"Revenue is: {Revenue} for type {returnType} document {i} ")
        print(f"Expense is: {Expense} for type {returnType} document {i} ")
        """

        df.to_csv(filecheck_income)
        df2.to_csv(filecheck_Profile)

        profile_dict=(i,{"EIN":GrantorEIN,
                    "Buisnes name": businessname_ln2.upper(),
                    "Busines name2": businessname_ln2.upper(),
                    "address"       : address_element_line1.upper(),
                    "Address2"      : address_element_line2.upper(),
                    "City"          : address_element_city.upper(),
                    "State"         : address_element_state.upper(),
                    "Zip"           : address_element_zip,
                    "Website"       : website_element,
                    "Mission"       : mission.upper(),
                    "Status"        :  status.upper() if status else None,
                    "Year"          : year,
                 })

        income_expense_dict=(i,{"ein": GrantorEIN ,
                                "revenue": Revenue ,
                                "expenses":Expense ,
                                "total_assets_boy":total_assets_boy ,
                                "total_assets_eoy": total_assets_eoy,
                                "return_type":returnType,
                                "year": year})

        profile_empty_dict[i] = profile_dict[1]

        income_expense_empty_dict[i] = income_expense_dict[1]


    # Convert integer keys to strings
    profile_empty_dict = {str(k): v for k, v in profile_empty_dict.items()}
    income_expense_empty_dict = {str(k): v for k, v in income_expense_empty_dict.items()}


    # Write mydict to a JSON file
    with open('/Users/michaellingram/Downloads/profiles.json', 'w') as f:
        json.dump(profile_empty_dict, f)
    with open('/Users/michaellingram/Downloads/income_expense.json', 'w') as f:
        json.dump(income_expense_empty_dict, f)

if __name__ == "__main__":
    file_location = '/Volumes/TPC/xml'
    target_location = '/Users/michaellingram/Downloads'
    irs_expense_income(file_location, target_location)