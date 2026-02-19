"""
Test script for TPC error handling functions
Tests various error scenarios and file movement functionality
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add parent directory to path to import TPC modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging_setup import get_standard_logger
from error_handler import move_error_file, move_multiple_error_files, create_error_report
from income_expense import process_single_file as process_income_expense
from TPC_grants import process_single_file as process_grants


def setup_test_environment():
    """Create temporary test environment"""
    test_dir = tempfile.mkdtemp(prefix='tpc_error_test_')
    xml_dir = os.path.join(test_dir, 'xml')
    csv_dir = os.path.join(test_dir, 'csv')
    
    os.makedirs(xml_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)
    
    return test_dir, xml_dir, csv_dir


def copy_test_files(xml_dir):
    """Copy test XML files to test directory"""
    test_files_dir = os.path.dirname(__file__)
    
    test_files = [
        'test_error_file.xml',
        'test_malformed.xml'
    ]
    
    copied_files = []
    for test_file in test_files:
        source = os.path.join(test_files_dir, test_file)
        if os.path.exists(source):
            dest = os.path.join(xml_dir, test_file)
            shutil.copy2(source, dest)
            copied_files.append(dest)
            print(f"Copied test file: {dest}")
        else:
            print(f"Warning: Test file not found: {source}")
    
    return copied_files


def test_basic_error_handling(logger):
    """Test basic error file movement"""
    print("\n=== Testing Basic Error Handling ===")
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write('<?xml version="1.0"?><test>Basic test file</test>')
        test_file = f.name
    
    try:
        # Test moving the file
        moved_path = move_error_file(
            test_file, 
            error_reason="Test error - basic functionality", 
            logger=logger
        )
        
        if moved_path and os.path.exists(moved_path):
            print(f"✓ Successfully moved file to: {moved_path}")
            
            # Check if error report was created
            report_path = moved_path.replace('.xml', '_ERROR_REPORT.txt')
            if os.path.exists(report_path):
                print(f"✓ Error report created: {report_path}")
                # Read and display report content
                with open(report_path, 'r') as f:
                    print(f"Report content preview:\n{f.read()[:200]}...")
            else:
                print("✗ Error report not created")
                
        else:
            print("✗ Failed to move file")
            
    except Exception as e:
        print(f"✗ Error in basic test: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)


def test_xml_parsing_errors(xml_dir, csv_dir, logger):
    """Test error handling for XML parsing failures"""
    print("\n=== Testing XML Parsing Error Handling ===")
    
    test_files = copy_test_files(xml_dir)
    
    for test_file in test_files:
        print(f"\nTesting file: {os.path.basename(test_file)}")
        
        try:
            # Test with income_expense processor
            result = process_income_expense(test_file, csv_dir, logger)
            print(f"Income/Expense result: {result}")
            
            # Test with grants processor  
            result = process_grants(test_file, csv_dir, logger)
            print(f"Grants result: {result}")
            
        except Exception as e:
            print(f"✗ Unexpected error processing {test_file}: {str(e)}")


def test_batch_error_handling(logger):
    """Test batch error file handling"""
    print("\n=== Testing Batch Error Handling ===")
    
    # Create multiple temporary test files
    test_files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'_batch_{i}.xml', delete=False) as f:
            f.write(f'<?xml version="1.0"?><test>Batch test file {i}</test>')
            test_files.append(f.name)
    
    try:
        # Test batch move
        results = move_multiple_error_files(
            test_files,
            error_reason="Batch test - multiple file handling",
            logger=logger
        )
        
        print(f"✓ Batch move completed")
        print(f"  Successful: {len(results['success'])}")
        print(f"  Failed: {len(results['failed'])}")
        
        for success_file in results['success']:
            print(f"  Moved: {success_file}")
            
        for failed_file in results['failed']:
            print(f"  Failed: {failed_file}")
            
    except Exception as e:
        print(f"✗ Error in batch test: {str(e)}")
    finally:
        # Cleanup any remaining files
        for test_file in test_files:
            if os.path.exists(test_file):
                os.remove(test_file)


def test_missing_file_handling(logger):
    """Test handling of non-existent files"""
    print("\n=== Testing Missing File Handling ===")
    
    non_existent_file = '/tmp/this_file_does_not_exist.xml'
    
    result = move_error_file(
        non_existent_file,
        error_reason="Test - file does not exist",
        logger=logger
    )
    
    if result is None:
        print("✓ Correctly handled non-existent file")
    else:
        print("✗ Should have returned None for non-existent file")


def main():
    """Run all error handling tests"""
    print("TPC Error Handler Testing Suite")
    print("=" * 50)
    
    # Setup test environment
    test_dir, xml_dir, csv_dir = setup_test_environment()
    print(f"Test directory: {test_dir}")
    
    # Setup logger
    logger = get_standard_logger('error_test', test_dir)
    
    try:
        # Run tests
        test_basic_error_handling(logger)
        test_xml_parsing_errors(xml_dir, csv_dir, logger)
        test_batch_error_handling(logger)
        test_missing_file_handling(logger)
        
        print("\n=== Test Summary ===")
        print("All error handling tests completed.")
        print(f"Check test directory for results: {test_dir}")
        print("Review log files for detailed information.")
        
        # List generated error files
        error_dir = os.path.join(test_dir, datetime.now().strftime('%Y-%m-%d'), 'errors')
        if os.path.exists(error_dir):
            error_files = os.listdir(error_dir)
            if error_files:
                print(f"\nError files generated ({len(error_files)}):")
                for error_file in error_files:
                    print(f"  {error_file}")
            else:
                print("\nNo error files generated in error directory.")
        else:
            print(f"\nError directory not created: {error_dir}")
            
    except Exception as e:
        print(f"✗ Test suite failed: {str(e)}")
    finally:
        # Note: Not automatically cleaning up test_dir so you can inspect results
        print(f"\nTest files preserved in: {test_dir}")
        print("Manual cleanup required when done reviewing results.")


if __name__ == '__main__':
    main()
