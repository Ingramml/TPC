# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.


import income_expense
import subdirectory_concat_gpt
import TPC_990_Boardmembers
import TPC_grants
import TPC_990




def main():
    file_location = '/Volumes/TPC/downloads'
    xml_location = '/Volumes/TPC/xml'
    #TPC_990.download_zip_files('https://www.irs.gov/charities-non-profits/form-990-series-downloads', file_location)
    #TPC_990.extract_and_move_xml_files(file_location, xml_location)
    file_location = '/Volumes/TPC/xml'
    target_location = '/Volumes/TPC/CSV'
    #TPC_990_Boardmembers.irs_boardmember(file_location, target_location)
    #income_expense.irs_expense_income(file_location, target_location)
    #TPC_grants.irs_grants(file_location, target_location)
    #Political_contributions_2.political_contributions(file_location, target_location)
    #subdirectory_concat_gpt.folder_csv_concat(target_location, 'income_expenses_', num_processes=4)
    subdirectory_concat_gpt.process_folder((target_location, 'income_expenses_'))
    #subdirectory_concat_gpt.folder_csv_concat(target_location, 'profile_', num_processes=4)
    subdirectory_concat_gpt.process_folder((target_location, 'profile_'))
    #subdirectory_concat_gpt.folder_csv_concat(target_location, 'grants_', num_processes=4)
    subdirectory_concat_gpt.process_folder((target_location, 'grants_'))
    #subdirectory_concat_gpt.folder_csv_concat(target_location, 'boardmembers_', num_processes=4)
    #subdirectory_concat_gpt.process_folder((target_location, 'boardmembers_'))


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/