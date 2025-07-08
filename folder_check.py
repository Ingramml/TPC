import os


def folder_check(folders):
    """
    Check if the specified directories exist, and create them if they do not.
    Accepts a single folder path or a list/tuple of folder paths.
    :param folders: Directory or list/tuple of directories to check/create
    """
    if isinstance(folders, (str, os.PathLike)):
        folders = [folders]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            print(f"Created directory: {folder}")
        else:
            print(f"Directory already exists: {folder}")


if __name__ == "__main__":
    pass
    # folder_check('/tmp/test_folder1','/tmp/test_folder2/subfolder')