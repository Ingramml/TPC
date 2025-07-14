import os
import random
import glob
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def xml_sampling(xml_directory, sample_size=50):

    all_files = [f for f in glob.glob(os.path.join(xml_directory, '**', '*.xml'), recursive=True)]
    sampled_files = random.sample(all_files, min(sample_size, len(all_files)))
    return sampled_files

def copy_sampled_files(sampled_files, target_directory):
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    
    for file in sampled_files:
        try:
            shutil.copy2(file, os.path.join(target_directory, os.path.basename(file)))
            logger.info(f"Copied {os.path.basename(file)} to {target_directory}")
        except Exception as e:
            logger.error(f"Error copying file {file}: {e}")
            print(f"Error copying file {file}: {e}")


if __name__ == "__main__":
    xml_directory = '/Volumes/TPC/2025-07-07/xml'  # Replace with your XML directory
    target_directory = '/Volumes/TPC/xmlsamples'  # Replace with your target directory
    sample_size = 50  # Adjust the sample size as needed

    sampled_files = xml_sampling(xml_directory, sample_size)
    copy_sampled_files(sampled_files, target_directory)

    print(f"Copied {len(sampled_files)} sampled XML files to {target_directory}")