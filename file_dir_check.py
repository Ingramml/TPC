#Deterimes if directory or single file
import os
import glob
import sys


def check_file_location(file_location):
    """
    Check if the file location is a directory or a single file.
    If it's a directory, return all XML files in it.
    If it's a single file, return the file path.
    """
    if os.path.isdir(file_location):
        file_path = os.path.join(file_location,'*/', '*.xml')
        file_location = glob.glob(file_path)
    else:
        file_location = [file_location]