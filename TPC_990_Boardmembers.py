import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
import json


# files = glob.glob('/Volumes/SSD/TPC990/TPC_xml/*.xml')
# target_location = '/Volumes/SSD/production'

def irs_boardmember(file_location, target_location):

    if os.path.isdir(file_location):
        file_path = os.path.join(file_location,'*/', '*.xml')
        file_location = glob.glob(file_path)
    else:
        file_location = [file_location]

    mydict = {}

    for i in tqdm(file_location):

        tree = ET.parse(i)
        root = tree.getroot()
        GrantorEIN_check = root[0].find('./*{http://www.irs.gov/efile}EIN')
        begindate_check = root[0].find('./{http://www.irs.gov/efile}TaxPeriodBeginDate')
        begindate_chcek2 = root[0].find('./{http://www.irs.gov/efile}TaxPeriodBeginDt')
        begindate = begindate_check.text if ET.iselement(
            begindate_check) else begindate_chcek2.text if ET.iselement(begindate_chcek2) else None
        year = begindate[0:4]
        # Creates folder based on begining year of tax return(begindate)
        if ET.iselement(GrantorEIN_check):
            folder = os.path.join(target_location, begindate[0:4])
            if os.path.exists(folder):
                pass
            else:
                os.makedirs(folder, exist_ok=True)
        else:
            os.rename(i, '/Volumes/Storage/TPC990/Errors/' + os.path.basename(i))
            print(os.path.basename(i) + ' moved')

        columns = ['ein', 'name', 'title', 'averagehousperweek', 'indivualtrusteeordirector', 'compensation_from_org',
                   'compensation_from_related_org', 'othercompens', 'year']

        return_check1 = root[0].find('./{http://www.irs.gov/efile}ReturnType') or root[0].find(
            './{http://www.irs.gov/efile}ReturnTypeCd')
        returnType = return_check1.text if ET.iselement(return_check1) else ''

        if returnType=='990':
            boardmemebers = root[1].findall('./*{http://www.irs.gov/efile}Form990PartVIISectionAGrp')

        elif returnType=='990PF':
            if root[1].find('./*{http://www.irs.gov/efile}OfficerDirTrstKeyEmplInfoGrp') is not None:
                boardmemebers=root.findall('.//*{http://www.irs.gov/efile}OfficerDirTrstKeyEmplGrp')
        elif returnType=='990EZ':
                boardmemebers=root[1].findall('./*{http://www.irs.gov/efile}OfficerDirectorTrusteeEmplGrp')

        else:
            boardmemebers='errror'

        EIN = root[0].find('.//{http://www.irs.gov/efile}EIN').text
        rows = []

        filecheck = target_location + '/' + year + '/boardmembers_' + EIN + '.csv'


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
                    ET.iselement(boardmemeber.find('.{http://www.irs.gov/efile}AverageHrsPerWkDevotedToPosRt')) else None  # boardmember[2].text
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
                filename=os.path.basename(i)
                newdict = (filename,{'returnType':returnType,
                    'Title': Title,
                       'Average hours worked': Averagehoursworked,
                       'Truestee':Individualtrusteeordirector,
                       'Compensation': compensation_from_org,
                       'Related Compensation':compensation_from_related_org,
                       'Other Compensation': other_compensation})

                mydict[i] = newdict[1]

                rows.append([EIN, Name, Title, Averagehoursworked, Individualtrusteeordirector, compensation_from_org,
                             compensation_from_related_org, other_compensation, year[0:4]])
                df = pd.DataFrame(rows, columns=columns, dtype=object)
                df.to_csv(filecheck)
    print(mydict)

    # Convert integer keys to strings
    mydict = {str(k): v for k, v in mydict.items()}

    # Write mydict to a JSON file
    with open('/Users/michaellingram/Downloads/Boardmembers.json', 'w') as f:
        json.dump(mydict, f)


#if __name__ == '__main__':
    #irs_boardmember('/Volumes/flashdrive/xmldownloads','/Volumes/flashdrive/TPC')