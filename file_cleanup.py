"""
File Cleanup Utilities for TPC Pipeline
Provides functions to delete files and empty trash
"""

import os
import shutil
import subprocess
import logging
from typing import List, Optional
from pathlib import Path


def delete_all_files_in_folder(folder_path: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    Delete all files and subdirectories in a folder, keeping the folder itself.
    
    Args:
        folder_path (str): Path to the folder to clean
        logger (logging.Logger, optional): Logger instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    if not os.path.exists(folder_path):
        logger.warning(f"Folder does not exist: {folder_path}")
        return False
    
    if not os.path.isdir(folder_path):
        logger.error(f"Path is not a directory: {folder_path}")
        return False
    
    try:
        deleted_count = 0
        error_count = 0
        
        # Get list of all items in the folder
        items = os.listdir(folder_path)
        logger.info(f"Found {len(items)} items to delete in {folder_path}")
        
        for item in items:
            item_path = os.path.join(folder_path, item)
            try:
                if os.path.isdir(item_path):
                    # Remove directory and all its contents
                    shutil.rmtree(item_path)
                    logger.debug(f"Deleted directory: {item_path}")
                else:
                    # Remove file
                    os.remove(item_path)
                    logger.debug(f"Deleted file: {item_path}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete {item_path}: {str(e)}")
                error_count += 1
        
        logger.info(f"Cleanup completed - Deleted: {deleted_count}, Errors: {error_count}")
        return error_count == 0
        
    except Exception as e:
        logger.error(f"Failed to clean folder {folder_path}: {str(e)}")
        return False


def delete_folder_contents_recursive(folder_path: str, exclude_patterns: List[str] = None, logger: Optional[logging.Logger] = None) -> bool:
    """
    Recursively delete folder contents with optional exclusion patterns.
    
    Args:
        folder_path (str): Path to the folder to clean
        exclude_patterns (List[str], optional): Patterns to exclude from deletion
        logger (logging.Logger, optional): Logger instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    try:
        deleted_count = 0
        skipped_count = 0
        
        for root, dirs, files in os.walk(folder_path, topdown=False):
            # Delete files
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if file should be excluded
                should_exclude = any(pattern in file_path for pattern in exclude_patterns)
                if should_exclude:
                    logger.debug(f"Skipping excluded file: {file_path}")
                    skipped_count += 1
                    continue
                
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.debug(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete file {file_path}: {str(e)}")
            
            # Delete empty directories
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                
                # Check if directory should be excluded
                should_exclude = any(pattern in dir_path for pattern in exclude_patterns)
                if should_exclude:
                    logger.debug(f"Skipping excluded directory: {dir_path}")
                    skipped_count += 1
                    continue
                
                try:
                    if not os.listdir(dir_path):  # Only delete if empty
                        os.rmdir(dir_path)
                        deleted_count += 1
                        logger.debug(f"Deleted empty directory: {dir_path}")
                except Exception as e:
                    logger.debug(f"Could not delete directory {dir_path}: {str(e)}")
        
        logger.info(f"Recursive cleanup completed - Deleted: {deleted_count}, Skipped: {skipped_count}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to recursively clean {folder_path}: {str(e)}")
        return False


def empty_trash(logger: Optional[logging.Logger] = None) -> bool:
    """
    Empty the system trash/recycle bin.
    
    Args:
        logger (logging.Logger, optional): Logger instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    try:
        import platform
        system = platform.system()
        
        if system == "Darwin":  # macOS
            logger.info("Emptying macOS Trash...")
            # Use AppleScript to empty trash
            script = '''
            tell application "Finder"
                empty trash
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("Successfully emptied macOS Trash")
                return True
            else:
                logger.error(f"Failed to empty macOS Trash: {result.stderr}")
                return False
                
        elif system == "Windows":  # Windows
            logger.info("Emptying Windows Recycle Bin...")
            # Use PowerShell to empty recycle bin
            powershell_cmd = "Clear-RecycleBin -Force"
            result = subprocess.run(['powershell', '-Command', powershell_cmd],
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("Successfully emptied Windows Recycle Bin")
                return True
            else:
                logger.error(f"Failed to empty Windows Recycle Bin: {result.stderr}")
                return False
                
        elif system == "Linux":  # Linux
            logger.info("Emptying Linux Trash...")
            # Try to empty user's trash directory
            trash_dirs = [
                os.path.expanduser("~/.local/share/Trash/files"),
                os.path.expanduser("~/.local/share/Trash/info")
            ]
            
            success = True
            for trash_dir in trash_dirs:
                if os.path.exists(trash_dir):
                    if not delete_all_files_in_folder(trash_dir, logger):
                        success = False
            
            if success:
                logger.info("Successfully emptied Linux Trash")
            else:
                logger.error("Failed to completely empty Linux Trash")
            return success
            
        else:
            logger.warning(f"Unsupported operating system for trash emptying: {system}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout while trying to empty trash")
        return False
    except Exception as e:
        logger.error(f"Failed to empty trash: {str(e)}")
        return False


def cleanup_old_files(folder_path: str, days_old: int = 7, file_patterns: List[str] = None, logger: Optional[logging.Logger] = None) -> int:
    """
    Delete files older than specified number of days.
    
    Args:
        folder_path (str): Path to folder to clean
        days_old (int): Files older than this many days will be deleted
        file_patterns (List[str], optional): Patterns to match for deletion (e.g., ['*.log', '*.tmp'])
        logger (logging.Logger, optional): Logger instance
        
    Returns:
        int: Number of files deleted
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    if not os.path.exists(folder_path):
        logger.warning(f"Folder does not exist: {folder_path}")
        return 0
    
    import time
    import fnmatch
    
    cutoff_time = time.time() - (days_old * 24 * 60 * 60)
    deleted_count = 0
    
    try:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check file pattern if specified
                if file_patterns:
                    matches_pattern = any(fnmatch.fnmatch(file, pattern) for pattern in file_patterns)
                    if not matches_pattern:
                        continue
                
                # Check file age
                try:
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.debug(f"Deleted old file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not delete {file_path}: {str(e)}")
        
        logger.info(f"Cleanup completed - Deleted {deleted_count} old files")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error during old file cleanup: {str(e)}")
        return deleted_count


def get_folder_size(folder_path: str) -> int:
    """
    Get the total size of a folder in bytes.
    
    Args:
        folder_path (str): Path to folder
        
    Returns:
        int: Total size in bytes
    """
    total_size = 0
    try:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, FileNotFoundError):
                    pass
    except Exception:
        pass
    
    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


# Example usage and testing
if __name__ == '__main__':
    delete_all_files_in_folder('/Volumes/TPC/2025-07-07')
    """
    import logging
    
    # Setup logging
    logging.basicConfig(level=logging.ERROR, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Test folder path (use a safe test directory)
    test_folder = "/Volumes/TPC/2025-07-07"
    
    # Create test folder and files
    os.makedirs(test_folder, exist_ok=True)
    with open(os.path.join(test_folder, "test_file.txt"), "w") as f:
        f.write("Test content")
    
    logger.info(f"Created test folder: {test_folder}")
    
    # Test cleanup
    size_before = get_folder_size(test_folder)
    logger.info(f"Folder size before cleanup: {format_file_size(size_before)}")
    
    # Test deletion
    success = delete_all_files_in_folder(test_folder, logger)
    logger.info(f"Cleanup successful: {success}")
    
    size_after = get_folder_size(test_folder)
    logger.info(f"Folder size after cleanup: {format_file_size(size_after)}")
    
    # Clean up test folder
    os.rmdir(test_folder)
    logger.info("Test completed")
    """