"""
Fast File Cleanup Utility for TPC Pipeline
Simple, high-performance deletion of folder contents
"""

import os
import shutil
import sys
import time
import platform


def play_completion_beep():
    """Play a simple completion beep."""
    try:
        if platform.system() == "Darwin":  # macOS
            os.system('afplay /System/Library/Sounds/Pop.aiff')
        elif platform.system() == "Windows":  # Windows
            import winsound
            winsound.Beep(800, 300)
        else:
            print('\a')  # Bell character
    except:
        print('\a' * 2)


def print_progress_bar(current, total, bar_length=50):
    """Print a simple progress bar."""
    if total == 0:
        return
    
    progress = current / total
    filled_length = int(bar_length * progress)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    percent = progress * 100
    
    print(f'\rProgress: |{bar}| {current}/{total} ({percent:.1f}%)', end='', flush=True)


def fast_delete_folder_contents(folder_path):
    """
    Delete all contents of a folder as fast as possible.
    PERMANENTLY DELETES FILES - BYPASSES TRASH/RECYCLE BIN
    
    Args:
        folder_path (str): Path to folder to clean
        
    Returns:
        tuple: (success, deleted_count, error_count)
    """
    if not os.path.exists(folder_path):
        print(f"ERROR: Folder does not exist: {folder_path}")
        return False, 0, 1
    
    if not os.path.isdir(folder_path):
        print(f"ERROR: Path is not a directory: {folder_path}")
        return False, 0, 1
    
    deleted_count = 0
    error_count = 0
    
    try:
        # Get all items in folder
        print("Scanning folder contents...")
        items = os.listdir(folder_path)
        total_items = len(items)
        
        if total_items == 0:
            print(f"Folder is already empty: {folder_path}")
            return True, 0, 0
        
        print(f"Found {total_items} items to delete from {folder_path}")
        print("Starting deletion...")
        
        start_time = time.time()
        
        # Delete each item with progress tracking
        for i, item in enumerate(items, 1):
            item_path = os.path.join(folder_path, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)  # Permanently deletes directory and contents
                else:
                    os.remove(item_path)      # Permanently deletes file
                deleted_count += 1
            except Exception as e:
                print(f"\nFailed to delete {item}: {e}")
                error_count += 1
            
            # Update progress bar every item or every 10% for large folders
            if total_items <= 100 or i % max(1, total_items // 100) == 0 or i == total_items:
                print_progress_bar(i, total_items)
        
        # Final newline and timing info
        print()  # New line after progress bar
        elapsed_time = time.time() - start_time
        print(f"Cleanup complete in {elapsed_time:.2f} seconds")
        print(f"Results: {deleted_count} deleted, {error_count} errors")
        
        return error_count == 0, deleted_count, error_count
        
    except Exception as e:
        print(f"\nERROR: Failed to clean folder: {e}")
        return False, deleted_count, error_count + 1


def confirm_deletion(folder_path):
    """Ask user for confirmation before deletion."""
    try:
        items = os.listdir(folder_path)
        item_count = len(items)
        
        if item_count == 0:
            print(f"Folder is already empty: {folder_path}")
            return False
        
        print(f"\nFolder: {folder_path}")
        print(f"Items to delete: {item_count}")
        
        # Show first few items
        if item_count > 0:
            print("Contents preview:")
            for i, item in enumerate(items[:5]):
                print(f"  - {item}")
            if item_count > 5:
                print(f"  ... and {item_count - 5} more items")
        
        response = input(f"\nDelete ALL {item_count} items? (yes/no): ").strip().lower()
        return response == 'yes'
        
    except Exception as e:
        print(f"ERROR: Cannot access folder: {e}")
        return False


def main():
    """Main execution function."""
    # Get folder path from command line or prompt
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        skip_confirm = len(sys.argv) > 2 and sys.argv[2] == '--force'
    else:
        folder_path = input("Enter folder path to clean: ").strip()
        skip_confirm = False
    
    # Remove quotes if present
    folder_path = folder_path.strip('"\'')
    
    # Validate path
    if not folder_path:
        print("ERROR: No folder path provided")
        sys.exit(1)
    
    # Confirm deletion unless --force flag is used
    if not skip_confirm:
        if not confirm_deletion(folder_path):
            print("Cleanup cancelled")
            sys.exit(0)
    
    # Perform deletion
    print(f"\nStarting cleanup of: {folder_path}")
    success, deleted, errors = fast_delete_folder_contents(folder_path)
    
    if success:
        print(f"✓ SUCCESS: Deleted {deleted} items")
        sys.exit(0)
    else:
        print(f"✗ PARTIAL SUCCESS: Deleted {deleted} items, {errors} errors")
        sys.exit(1)


if __name__ == '__main__':
    # Quick execution for hardcoded path
    target_folder = '/Volumes/TPC/CSV'
    
    print(f"Fast cleanup starting...")
    print(f"Target: {target_folder}")
    
    if confirm_deletion(target_folder):
        success, deleted, errors = fast_delete_folder_contents(target_folder)
        if success:
            print(f"✓ Cleanup completed successfully: {deleted} items deleted")
            play_completion_beep()  # Add beep on completion
        else:
            print(f"⚠ Cleanup completed with errors: {deleted} deleted, {errors} errors")
            try:
                print('\a' * 3)  # Error beeps
            except:
                pass
    else:
        print("Cleanup cancelled")
