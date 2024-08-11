import glob
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import os
import json

e
# files = glob.glob('/Volumes/SSD/TPC990/TPC_xml/*.xml')
# target_location = '/Volumes/SSD/production'

def scheduleB(file_location, target_location):

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

        columns=['ein',]