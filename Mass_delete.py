import glob
import os
import shutil
from tqdm import tqdm

#keyword =''
#files = glob.glob("/Volumes/SSD/production/*/*.csv")
def filetype_delete(file_location,filetype):
    try:
        file_path=file_location+'/*'+filetype
        files=glob.glob(file_path)
        for x in tqdm(files):
            if os.path.exists(x):
                os.remove(x)
        print('all'+ filetype+ ' files from ' + file_location + ' deleted.')
    except FileNotFoundError:
        print(file_location + 'not found')


def folder_clean_up(file_location,exclude_folder_name):
    try:
        folder_path=file_location+'/*'
        folders = glob.glob(folder_path)
        for folder in tqdm(folders):
            if exclude_folder_name not in os.path.basename(folder):
               shutil.rmtree(folder)
        print('All folders in ' + file_location + ' deleted')
    except FileNotFoundError:
        print(file_location + ' not found')


def neste_file_folder_delete(file_location,file_type):
    try:
        folder_path = os.scandir(file_location)
        for folders in tqdm(folder_path):
            nested_file = str(folders) + '/*.'+ str(file_type)
            nested_files = glob.glob(nested_file, recursive=True)
            #print('Deleting files from ' + os.path.dirname(csv_files[5]))
            for files in nested_files:
                os.remove(files)
        shutil.rmtree(os.path.dirname(folders))
        print('all files in ' + str(file_location))
    except FileNotFoundError:
        print(file_location + 'not found')


def neste_file_folder_keyword_delete(file_location, file_type):
    try:
        folder_path = os.scandir(file_location)

        for folders in tqdm(folder_path):

            nested_file = str(folders) + '/*.' + str(file_type)
            if os.path.isdir(nested_file):
                nested_files = glob.glob(nested_file, recursive=True)
                print(nested_file)
                for files in nested_files:
                    os.remove(files)
        shutil.rmtree(os.path.dirname(folders))
        print('all files in ' + str(file_location))
    except FileNotFoundError:
        print(file_location + ' not found')




neste_file_folder_keyword_delete('/Users/michaellingram/.Trash','xml')
#filetype_delete('/Users/michaellingram/.Trash','')
#neste_file_folder_delete('/Users/michaellingram/Downloads/TPC','csv')
