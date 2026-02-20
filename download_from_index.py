"""
Download IRS 990 XML zip files using index CSVs instead of scraping the IRS webpage.

Downloads the index CSV for each year (2019-2026) from the IRS server, reads
the XML_BATCH_ID column to get exact zip filenames, then downloads those zips.
No web scraping, no 404 errors.

Usage:
    from download_from_index import download_all
    download_all('/path/to/download/dir')
"""

import os
import csv
import requests
import logging
from TPC_990 import download_file
from logging_setup import get_standard_logger

BASE_URL = 'https://apps.irs.gov/pub/epostcard/990/xml'
INDEX_YEARS = range(2019, 2027)


def download_index_files(download_dir, logger):
    """
    Download all yearly index CSVs from the IRS server.

    Args:
        download_dir: Directory to save index CSVs
        logger: Logger instance

    Returns:
        list: Paths to successfully downloaded index CSV files
    """
    index_dir = os.path.join(download_dir, 'indexes')
    os.makedirs(index_dir, exist_ok=True)

    index_paths = []
    for year in INDEX_YEARS:
        url = f"{BASE_URL}/{year}/index_{year}.csv"
        dest = os.path.join(index_dir, f"index_{year}.csv")

        if os.path.exists(dest):
            logger.info(f"Index file already exists: index_{year}.csv")
            index_paths.append(dest)
            continue

        logger.info(f"Downloading index: index_{year}.csv")
        try:
            response = requests.get(url, allow_redirects=True)
            response.raise_for_status()
            with open(dest, 'wb') as f:
                f.write(response.content)
            logger.info(f"Downloaded index_{year}.csv ({len(response.content)} bytes)")
            index_paths.append(dest)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not download index_{year}.csv: {e}")

    return index_paths


def get_batch_ids_from_index(index_csv_path):
    """
    Read an index CSV and return unique XML_BATCH_IDs.

    Args:
        index_csv_path: Path to the IRS index CSV file

    Returns:
        set: Unique batch IDs (e.g., {'2025_TEOS_XML_12A', '2025_TEOS_XML_09A'})
    """
    batch_ids = set()
    with open(index_csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            batch_id = row.get('XML_BATCH_ID', '').strip()
            if batch_id:
                batch_ids.add(batch_id)
    return batch_ids


def batch_id_to_url(batch_id):
    """
    Convert a batch ID to its download URL.

    Example: '2025_TEOS_XML_12A' -> 'https://apps.irs.gov/.../2025/2025_TEOS_XML_12A.zip'
    """
    year = batch_id[:4]
    return f"{BASE_URL}/{year}/{batch_id}.zip"


def download_all(download_dir, logger=None):
    """
    Download all index CSVs, then download all zip files referenced in them.
    Skips files that already exist in download_dir.

    Args:
        download_dir: Directory to save downloaded files
        logger: Optional logger instance
    """
    if logger is None:
        logger = get_standard_logger('tpc_990', download_dir)

    os.makedirs(download_dir, exist_ok=True)

    # Step 1: Download all index CSVs
    logger.info("Downloading index files...")
    index_paths = download_index_files(download_dir, logger)
    logger.info(f"Downloaded {len(index_paths)} index files")

    # Step 2: Collect all unique batch IDs across all indexes
    all_batch_ids = set()
    for index_path in index_paths:
        batch_ids = get_batch_ids_from_index(index_path)
        logger.info(f"{os.path.basename(index_path)}: {len(batch_ids)} unique zip files")
        all_batch_ids.update(batch_ids)

    logger.info(f"Total unique zip files across all years: {len(all_batch_ids)}")

    # Step 3: Download zip files
    sorted_ids = sorted(all_batch_ids)
    for i, batch_id in enumerate(sorted_ids, 1):
        url = batch_id_to_url(batch_id)
        logger.info(f"Downloading {i}/{len(sorted_ids)}: {batch_id}.zip")
        download_file(url, download_dir, logger)

    logger.info("All downloads complete")


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python download_from_index.py <download_dir>")
        sys.exit(1)
    download_all(sys.argv[1])
