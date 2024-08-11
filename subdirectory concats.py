import glob
import pandas as pd
import os
from tqdm import tqdm
import datetime


# all_folders = glob.glob('/Volumes/SSD/production/*')
# keyword = 'boardmember'

"""
Combines all files in a  subdirectory according to the keyword
used at the end of xml scraping to combine all files to upload
"""

def folder_csv_concat (folder_location,keyword):
    all_folders = glob.glob(folder_location+'/*')
    dir_name = os.path.dirname((all_folders[1]))
    li = []
    for folders in tqdm(all_folders):
        files = glob.glob(folders + '/' + keyword + '*.csv')
        #print(files)
        file_suffix = os.path.basename(folders)
        df = pd.DataFrame()
        li = []
        for file in files:
            df = pd.read_csv(file, index_col=None, header=0, low_memory=False, dtype="object")
            if df.empty:
                os.remove(file)
            else:
                li.append(df)
        if len(li) != 0:
            frame = pd.concat(li, axis=0, ignore_index=True)
            frame.to_csv(dir_name + '/' + file_suffix[-4:] + keyword+'conctats_combined.csv', index=False)
    print('all ' + keyword + ' files concated')


folder_csv_concat('/Volumes/TPC/CSV/','profile_')
#folder_csv_concat('/Volumes/TPC/CSV/','income_expenses_')
#folder_csv_concat('/Volumes/TPC/CSV/','grants_')
#folder_csv_concat('/Volumes/TPC/CSV/','boardmember')



