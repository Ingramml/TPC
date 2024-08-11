import requests
import os
from bs4 import BeautifulSoup

def download_xml_for_eins(eins, target_location):
    # Ensure that eins is a list
    if not isinstance(eins, list):
        eins = [eins]

    # Ensure the target directory exists
    os.makedirs(target_location, exist_ok=True)

    base_url = 'https://projects.propublica.org'

    for ein in eins:
        url = f"{base_url}/nonprofits/organizations/{ein}"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        existing_files, non_xml_files, files_downloaded = 0, 0, 0

        # Find all links that contain the specified string in their href attribute
        for link in soup.find_all('a', href=lambda href: href and '/nonprofits/download-xml?object_id' in href):
            href = link.get('href')

            # Check if href is a relative URL and prepend base URL if necessary
            if not href.startswith('http'):
                href = base_url + href

            file_number = href.split('=')[-1]  # Extract file number from the link
            file_path = os.path.join(target_location, f"{file_number}_public.xml")

            if not os.path.exists(file_path):
                xml_response = requests.get(href)
                with open(file_path, 'wb') as outfile:
                    outfile.write(xml_response.content)
                files_downloaded += 1
            else:
                existing_files += 1

        print(f"{ein} searched")
        print(f'Files downloaded: {files_downloaded}')
        print(f'Number of existing files: {existing_files}')
        print(f'Non-XML files: {non_xml_files}')

# Example usage
if __name__ == "__main__":
    ein_list = ['910639892','560552787','223849199','042674079','616038389','680480736','750758523','952942582','952504044','952145967','812350619','510571147','341747398','311774905','311640316','232888152','110303001','591956886']
    target_location = '/Volumes/flashdrive/xmldownloads'
    download_xml_for_eins(ein_list, target_location)
