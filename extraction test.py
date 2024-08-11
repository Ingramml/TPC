import subprocess

zip_file = '/Volumes/TPC/downloads/2022_TEOS_XML_11A.zip'
unzip_location = '/Volumes/TPC/downloads'
#subprocess.run(['7z', 'x', zip_file, f'-o{unzip_location}'])



from rarfile import RarFile

rar_file = '/Volumes/TPC/downloads/2022_TEOS_XML_11A.zip'
unzip_location = '/Volumes/TPC/downloads'

#with RarFile(rar_file, 'r') as rf:
 #   rf.extractall(unzip_location)

import patoolib

zip_file = '/Volumes/TPC/downloads/2022_TEOS_XML_11A.zip'
unzip_location = '/Volumes/TPC/downloads'
patoolib.extract_archive(zip_file, outdir=unzip_location)
