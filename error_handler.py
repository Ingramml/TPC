"""
Error Handler Module for TPC Pipeline
Handles moving problematic files to error directories to prevent pipeline interruption
"""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path


def setup_error_logging(base_path=None):
    """Set up logging configuration for error handling"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    if base_path:
        # Extract the base volume path
        path_parts = base_path.split('/')
        if 'TPC' in path_parts:
            tpc_index = path_parts.index('TPC')
            base_volume = '/'.join(path_parts[:tpc_index + 1])
        else:
            base_volume = '/Volumes/TPC'
        
        log_dir = os.path.join(base_volume, current_date, 'logs')
    else:
        log_dir = os.path.join('TPC', current_date, 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join(log_dir, f'tpc_error_handler_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Error handler logging initialized. Log file: {log_filename}")
    return logger


def move_error_file(source_file_path, error_directory=None, error_reason="Unknown error", logger=None):
    """
    Move a problematic file to an error directory with detailed logging
    
    Args:
        source_file_path (str): Path to the file that caused an error
        error_directory (str, optional): Custom error directory path
        error_reason (str): Reason for moving the file
        logger (logging.Logger, optional): Logger instance to use
    
    Returns:
        str: New path of the moved file, or None if move failed
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    try:
        # Validate source file exists
        if not os.path.exists(source_file_path):
            logger.error(f"Source file does not exist: {source_file_path}")
            return None
        
        # Determine error directory
        if error_directory is None:
            # Default error directory structure
            current_date = datetime.now().strftime('%Y-%m-%d')
            source_dir = os.path.dirname(source_file_path)
            
            # Try to find TPC base path
            path_parts = source_dir.split('/')
            if 'TPC' in path_parts:
                tpc_index = path_parts.index('TPC')
                base_volume = '/'.join(path_parts[:tpc_index + 1])
                error_directory = os.path.join(base_volume, current_date, 'errors')
            else:
                # Fallback to creating errors directory relative to source
                error_directory = os.path.join(source_dir, '..', 'errors')
                error_directory = os.path.abspath(error_directory)
        
        # Create error directory if it doesn't exist
        os.makedirs(error_directory, exist_ok=True)
        
        # Generate unique filename to avoid conflicts
        filename = os.path.basename(source_file_path)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{name}_ERROR_{timestamp}{ext}"
        destination_path = os.path.join(error_directory, new_filename)
        
        # Move the file
        shutil.move(source_file_path, destination_path)
        
        # Log the move
        logger.warning(f"File moved to error directory - Reason: {error_reason}")
        logger.warning(f"Source: {source_file_path}")
        logger.warning(f"Destination: {destination_path}")
        
        # Create error report file
        create_error_report(destination_path, source_file_path, error_reason, logger)
        
        return destination_path
        
    except Exception as e:
        logger.error(f"Failed to move error file {source_file_path}: {str(e)}")
        return None


def create_error_report(error_file_path, original_path, error_reason, logger=None):
    """
    Create a detailed error report file alongside the moved file
    
    Args:
        error_file_path (str): Path where the error file was moved
        original_path (str): Original path of the file
        error_reason (str): Reason for the error
        logger (logging.Logger, optional): Logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    try:
        # Create report filename
        name, ext = os.path.splitext(error_file_path)
        report_path = f"{name}_ERROR_REPORT.txt"
        
        # Generate report content
        report_content = f"""
ERROR REPORT
============
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Original File Path: {original_path}
Error File Path: {error_file_path}
Error Reason: {error_reason}
File Size: {os.path.getsize(error_file_path) if os.path.exists(error_file_path) else 'Unknown'} bytes
File Modified: {datetime.fromtimestamp(os.path.getmtime(error_file_path)).strftime('%Y-%m-%d %H:%M:%S') if os.path.exists(error_file_path) else 'Unknown'}

PIPELINE IMPACT:
- File removed from processing queue to prevent pipeline interruption
- Processing can continue with remaining files
- Manual review required for this file

RECOMMENDED ACTIONS:
1. Review the error reason above
2. Check file integrity and format
3. Manually process or fix the file if possible
4. Update pipeline logic if this is a recurring issue
"""
        
        # Write report file
        with open(report_path, 'w') as f:
            f.write(report_content.strip())
        
        logger.info(f"Error report created: {report_path}")
        
    except Exception as e:
        logger.error(f"Failed to create error report for {error_file_path}: {str(e)}")


def move_multiple_error_files(file_list, error_directory=None, error_reason="Batch error move", logger=None):
    """
    Move multiple files to error directory in batch
    
    Args:
        file_list (list): List of file paths to move
        error_directory (str, optional): Custom error directory path
        error_reason (str): Reason for moving the files
        logger (logging.Logger, optional): Logger instance
    
    Returns:
        dict: Dictionary with 'success' and 'failed' lists containing file paths
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    results = {'success': [], 'failed': []}
    
    logger.info(f"Starting batch move of {len(file_list)} files to error directory")
    
    for file_path in file_list:
        moved_path = move_error_file(file_path, error_directory, error_reason, logger)
        if moved_path:
            results['success'].append(moved_path)
        else:
            results['failed'].append(file_path)
    
    logger.info(f"Batch move completed - Success: {len(results['success'])}, Failed: {len(results['failed'])}")
    
    return results


def cleanup_old_error_files(error_directory, days_old=30, logger=None):
    """
    Clean up error files older than specified days
    
    Args:
        error_directory (str): Path to error directory
        days_old (int): Number of days after which files should be deleted
        logger (logging.Logger, optional): Logger instance
    
    Returns:
        int: Number of files deleted
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    if not os.path.exists(error_directory):
        logger.info(f"Error directory does not exist: {error_directory}")
        return 0
    
    cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    deleted_count = 0
    
    try:
        for root, dirs, files in os.walk(error_directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Deleted old error file: {file_path}")
        
        logger.info(f"Cleanup completed - Deleted {deleted_count} files older than {days_old} days")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return deleted_count


# Example usage and testing
if __name__ == '__main__':
    # Example usage
    logger = setup_error_logging('/Volumes/TPC')
    
    # Test moving a single file (replace with actual file path for testing)
    # moved_path = move_error_file('/path/to/problematic/file.xml', 
    #                             error_reason="XML parsing failed", 
    #                             logger=logger)
    
    # Test batch move (replace with actual file list for testing)
    # results = move_multiple_error_files(['/path/to/file1.xml', '/path/to/file2.xml'],
    #                                   error_reason="Batch processing error",
    #                                   logger=logger)
    
    logger.info("Error handler module loaded successfully")
