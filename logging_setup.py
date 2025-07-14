"""
Centralized Logging Setup Module for TPC Pipeline
Provides consistent logging configuration across all TPC modules
"""

import os
import logging
from datetime import datetime


def setup_logging(base_path=None, module_name="tpc", level=logging.INFO, console_output=False):
    """
    Set up logging configuration for TPC modules
    
    Args:
        base_path (str, optional): Base path to determine log directory location
        module_name (str): Name of the module for log file naming
        level (int): Logging level (default: logging.INFO)
        console_output (bool): Whether to include console output (default: False)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create date-based directory structure for logs
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    if base_path:
        # Extract the base volume path
        path_parts = base_path.split('/')
        if 'TPC' in path_parts:
            tpc_index = path_parts.index('TPC')
            base_volume = '/'.join(path_parts[:tpc_index + 1])
        else:
            base_volume = '/Volumes/TPC'  # fallback
        
        log_dir = os.path.join(base_volume, current_date, 'logs')
    else:
        # Fallback to local directory
        log_dir = os.path.join('TPC', current_date, 'logs')
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join(log_dir, f'tpc_{module_name}_{timestamp}.log')
    
    # Create handlers list
    handlers: list[logging.Handler] = [logging.FileHandler(log_filename)]
    
    # Add console handler if requested
    if console_output:
        handlers.append(logging.StreamHandler())
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=handlers,
        force=True  # Force reconfiguration if logging was already set up
    )
    
    # Get logger for the calling module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized for module: {module_name}")
    logger.info(f"Log file: {log_filename}")
    logger.info(f"Working directory: {base_path}")
    logger.info(f"Console output: {'Enabled' if console_output else 'Disabled'}")
    
    return logger


def setup_main_logging(base_path=None, run_id=None, console_output=True):
    """
    Special logging setup for main.py with run ID tracking
    
    Args:
        base_path (str, optional): Base path to determine log directory location
        run_id (str, optional): Unique run identifier for this execution
        console_output (bool): Whether to include console output (default: True)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    import uuid
    
    # Generate run ID if not provided
    if run_id is None:
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    # Determine log directory
    if base_path:
        current_date = datetime.now().strftime('%Y-%m-%d')
        working_directory = os.path.join(base_path, current_date)
        log_dir = os.path.join(working_directory, 'logs')
    else:
        log_dir = 'logs'
    
    # Create log directory
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file path
    log_file = os.path.join(log_dir, f'tpc_run_{run_id}.log')
    
    # Create handlers list
    handlers = [logging.FileHandler(log_file)]
    
    # Add console handler if requested
    if console_output:
        handlers.append(logging.StreamHandler())
    
    # Configure logging with run ID in format
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s [RUN_ID: {run_id}] %(levelname)s: %(message)s',
        handlers=handlers,
        force=True
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=== Main pipeline run started ===")
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Base path: {base_path}")
    
    return logger, run_id


def get_module_logger(module_name, base_path=None, console_output=False):
    """
    Get a logger for a specific module with standardized configuration
    
    Args:
        module_name (str): Name of the module requesting the logger
        base_path (str, optional): Base path for log directory
        console_output (bool): Whether to include console output
    
    Returns:
        logging.Logger: Configured logger instance
    """
    return setup_logging(base_path, module_name, logging.INFO, console_output)


def configure_existing_logger(logger_name, log_level=logging.INFO):
    """
    Configure an existing logger with standard settings
    
    Args:
        logger_name (str): Name of the logger to configure
        log_level (int): Logging level to set
    
    Returns:
        logging.Logger: The configured logger
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    return logger


# Common logging configurations for different modules
MODULE_CONFIGS = {
    'boardmembers': {
        'module_name': 'boardmembers',
        'console_output': False
    },
    'political_contributions': {
        'module_name': 'political_contributions',
        'console_output': False
    },
    'income_expense': {
        'module_name': 'income_expense',
        'console_output': False
    },
    'grants': {
        'module_name': 'grants',
        'console_output': False
    },
    'tpc_990': {
        'module_name': 'tpc_990',
        'console_output': False
    },
    'error_handler': {
        'module_name': 'error_handler',
        'console_output': True  # Error handler might want console output
    }
}


def get_standard_logger(module_type, base_path=None):
    """
    Get a logger with predefined configuration for common TPC modules
    
    Args:
        module_type (str): Type of module ('boardmembers', 'political_contributions', etc.)
        base_path (str, optional): Base path for log directory
    
    Returns:
        logging.Logger: Configured logger instance
    """
    if module_type not in MODULE_CONFIGS:
        raise ValueError(f"Unknown module type: {module_type}. Available: {list(MODULE_CONFIGS.keys())}")
    
    config = MODULE_CONFIGS[module_type]
    return setup_logging(
        base_path=base_path,
        module_name=config['module_name'],
        console_output=config['console_output']
    )


# Example usage and testing
if __name__ == '__main__':
    # Test different logging configurations
    print("Testing TPC logging setup...")
    
    # Test standard module logger
    logger1 = setup_logging('/Volumes/TPC', 'test_module', console_output=True)
    logger1.info("This is a test log message from standard setup")
    
    # Test main logger
    main_logger, run_id = setup_main_logging('/Volumes/TPC')
    main_logger.info("This is a test log message from main setup")
    
    # Test predefined module logger
    board_logger = get_standard_logger('boardmembers', '/Volumes/TPC')
    board_logger.info("This is a test log message from boardmembers module")
    
    print("Logging setup module loaded successfully")
