"""
Centralized Logging Setup Module for TPC Pipeline
Provides consistent logging configuration across all TPC modules
"""

import os
import logging
from datetime import datetime


def _resolve_log_dir(base_path):
    """Determine log directory from a base path."""
    current_date = datetime.now().strftime('%Y-%m-%d')

    if base_path:
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
    return log_dir


def setup_logging(base_path=None, module_name="tpc", level=logging.INFO, console_output=False):
    """
    Create a named logger with its own file handler.

    Args:
        base_path: Base path to determine log directory location
        module_name: Name of the module (used for logger name and log filename)
        level: Logging level (default: logging.INFO)
        console_output: Whether to also log to console

    Returns:
        logging.Logger: Configured logger instance
    """
    log_dir = _resolve_log_dir(base_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join(log_dir, f'tpc_{module_name}_{timestamp}.log')

    logger = logging.getLogger(f'tpc.{module_name}')
    logger.setLevel(level)

    # Avoid adding duplicate handlers if called multiple times
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )

        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    logger.info(f"Logging initialized for module: {module_name}")
    logger.info(f"Log file: {log_filename}")
    logger.info(f"Working directory: {base_path}")

    return logger


def setup_main_logging(base_path=None, run_id=None, console_output=True):
    """
    Special logging setup for main.py with run ID tracking.
    Configures the root logger so all modules' log messages also
    appear in the main run log.

    Args:
        base_path: Base path to determine log directory location
        run_id: Unique run identifier (auto-generated if None)
        console_output: Whether to also log to console

    Returns:
        tuple: (logger, run_id)
    """
    import uuid

    if run_id is None:
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    if base_path:
        current_date = datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(base_path, current_date, 'logs')
    else:
        log_dir = 'logs'

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'tpc_run_{run_id}.log')

    formatter = logging.Formatter(
        f'%(asctime)s [RUN_ID: {run_id}] %(levelname)s: %(message)s'
    )

    # Configure the root logger so all module loggers propagate here
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear any pre-existing root handlers
    root_logger.handlers.clear()

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    logger = logging.getLogger('tpc.main')
    logger.info("=== Main pipeline run started ===")
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Base path: {base_path}")

    return logger, run_id


# Predefined module configurations
MODULE_CONFIGS = {
    'boardmembers':             {'console_output': False},
    'political_contributions':  {'console_output': False},
    'income_expense':           {'console_output': False},
    'grants':                   {'console_output': False},
    'tpc_990':                  {'console_output': False},
    'error_handler':            {'console_output': True},
    'error_test':               {'console_output': False},
}


def get_standard_logger(module_type, base_path=None):
    """
    Get a logger with predefined configuration for a TPC module.

    Args:
        module_type: Module key from MODULE_CONFIGS
        base_path: Base path for log directory

    Returns:
        logging.Logger: Configured logger instance
    """
    if module_type not in MODULE_CONFIGS:
        raise ValueError(f"Unknown module type: {module_type}. Available: {list(MODULE_CONFIGS.keys())}")

    config = MODULE_CONFIGS[module_type]
    return setup_logging(
        base_path=base_path,
        module_name=module_type,
        console_output=config['console_output']
    )
