import glob
import pandas as pd
import os
from tqdm import tqdm
from multiprocessing import Pool
from datetime import date

#Takes all created files and comibes them into keywordfiles by year
def process_subfolder(folder_and_keyword):
    folder, keyword = folder_and_keyword
    files = glob.glob(folder + '/' + keyword + '*.csv') #used for subfolders

    file_suffix = os.path.basename(folder)
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
        dir_name = os.path.dirname(folder)
        frame.to_csv(dir_name + '/' + file_suffix[-4:] + keyword + '_combined.csv', index=False) #used for sub folders

def folder_csv_concat(folder_location, keyword, num_processes=4):
    all_folders = glob.glob(folder_location + '/*')
    folder_and_keyword = [(folder, keyword) for folder in all_folders]

    with Pool(num_processes) as pool:
        list(tqdm(pool.imap(process_subfolder, folder_and_keyword), total=len(folder_and_keyword)))

    print('All ' + keyword + ' files concatenated')

#Commine the Keyword _all files into one lareg file to be uploaded
def process_folder(folder_and_keyword):
    today = date.today()
    folder, keyword = folder_and_keyword
    files = glob.glob(folder+'/*'+keyword+'*.csv')
    #print(files)
    file_suffix = os.path.basename(folder)
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
        dir_name = os.path.dirname(folder)
        frame.to_csv(dir_name + '/' + keyword + '_all_ '+str(today)+'.csv', index=False)# used for sub folders






# Example usage
if __name__ == '__main__':
    process_folder(('/Volumes/TPC/CSV','grants'))
    process_folder(('/Volumes/TPC/CSV', 'profile'))
    process_folder(('/Volumes/TPC/CSV', 'income_expenses'))
    process_folder(('/Volumes/TPC/CSV', 'boardmember'))

