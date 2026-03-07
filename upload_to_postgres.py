"""
Upload TPC pipeline CSV files to PostgreSQL database.

Reads all *_combined.csv files from a run directory and loads them into
the cerebro_tpc database. Creates tables if they don't exist, appends data.

Usage:
    python3 upload_to_postgres.py /Volumes/TPC/2026-02-22
"""

import os
import sys
import glob
import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm

DB_HOST = 'localhost'
DB_PORT = 5430
DB_NAME = 'cerebro_tpc'
DB_USER = os.environ.get('USER', 'postgres')

ENGINE_URL = f'postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Map CSV prefix patterns to table names and column types
TABLE_CONFIG = {
    'boardmembers': {
        'table': 'boardmembers',
        'dtype': {
            'ein': 'TEXT',
            'name': 'TEXT',
            'title': 'TEXT',
            'averagehousperweek': 'TEXT',
            'indivualtrusteeordirector': 'TEXT',
            'compensation_from_org': 'TEXT',
            'compensation_from_related_org': 'TEXT',
            'othercompens': 'TEXT',
            'year': 'TEXT',
        },
    },
    'income_expenses': {
        'table': 'income_expenses',
        'dtype': {
            'ein': 'TEXT',
            'revenue': 'TEXT',
            'expenses': 'TEXT',
            'total_assets_boy': 'TEXT',
            'total_assets_eoy': 'TEXT',
            'return_type': 'TEXT',
            'year': 'TEXT',
        },
    },
    'profile': {
        'table': 'profiles',
        'dtype': {
            'ein': 'TEXT',
            'org_name1': 'TEXT',
            'org_name2': 'TEXT',
            'address_1': 'TEXT',
            'address_2': 'TEXT',
            'city': 'TEXT',
            'state': 'TEXT',
            'zipcode': 'TEXT',
            'website': 'TEXT',
            'mission': 'TEXT',
            'status': 'TEXT',
            'year': 'TEXT',
        },
    },
    'grants': {
        'table': 'grants',
        'dtype': {
            'grantor_ein': 'TEXT',
            'grantee_ein': 'TEXT',
            'grantee_name': 'TEXT',
            'amount': 'TEXT',
            'purpose': 'TEXT',
            'year': 'TEXT',
            'status': 'TEXT',
        },
    },
    'political_contributions': {
        'table': 'political_contributions',
        'dtype': {
            'filer_ein': 'TEXT',
            'recipient_name': 'TEXT',
            'address_line1': 'TEXT',
            'address_line2': 'TEXT',
            'city': 'TEXT',
            'state': 'TEXT',
            'zipcode': 'TEXT',
            'recipient_ein': 'TEXT',
            'amount_paid': 'TEXT',
            'contributions_received': 'TEXT',
            'year': 'TEXT',
        },
    },
}


def create_tables(engine):
    """Create tables if they don't exist."""
    with engine.connect() as conn:
        for key, config in TABLE_CONFIG.items():
            table = config['table']
            cols = ', '.join(f'"{col}" {dtype}' for col, dtype in config['dtype'].items())
            sql = f'CREATE TABLE IF NOT EXISTS {table} ({cols})'
            conn.execute(text(sql))
        conn.commit()
    print("Tables created/verified.")


def create_indexes(engine):
    """Create indexes on EIN and year columns for query performance."""
    index_defs = [
        ('idx_boardmembers_ein_year', 'boardmembers', 'ein, year'),
        ('idx_income_expenses_ein_year', 'income_expenses', 'ein, year'),
        ('idx_profiles_ein_year', 'profiles', 'ein, year'),
        ('idx_grants_grantor_ein_year', 'grants', 'grantor_ein, year'),
        ('idx_grants_grantee_ein', 'grants', 'grantee_ein'),
        ('idx_political_filer_ein_year', 'political_contributions', 'filer_ein, year'),
    ]
    with engine.connect() as conn:
        for idx_name, table, columns in index_defs:
            sql = f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})'
            conn.execute(text(sql))
        conn.commit()
    print("Indexes created/verified.")


def find_csv_files(run_dir):
    """Find all combined CSV files and map them to table configs."""
    csv_dir = os.path.join(run_dir, 'csv')
    if not os.path.isdir(csv_dir):
        print(f"Error: {csv_dir} not found")
        sys.exit(1)

    files_by_table = {}
    all_csvs = sorted(glob.glob(os.path.join(csv_dir, '*_combined.csv')))

    for csv_path in all_csvs:
        basename = os.path.basename(csv_path)
        for key in TABLE_CONFIG:
            if key + '_' in basename:
                if key not in files_by_table:
                    files_by_table[key] = []
                files_by_table[key].append(csv_path)
                break

    return files_by_table


def upload_csv(engine, csv_path, table_name, chunk_size=50000):
    """Upload a single CSV file to a table in chunks."""
    total_rows = sum(1 for _ in open(csv_path)) - 1  # subtract header
    if total_rows <= 0:
        return 0

    uploaded = 0
    for chunk in pd.read_csv(csv_path, dtype=str, chunksize=chunk_size, low_memory=False):
        chunk.to_sql(table_name, engine, if_exists='append', index=False, method='multi')
        uploaded += len(chunk)

    return uploaded


def main(run_dir):
    print(f"Connecting to {DB_NAME} on {DB_HOST}:{DB_PORT}...")
    engine = create_engine(ENGINE_URL)

    # Verify connection
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print("Connected.")

    create_tables(engine)

    files_by_table = find_csv_files(run_dir)

    if not files_by_table:
        print("No combined CSV files found.")
        return

    print(f"\nFound CSV files for {len(files_by_table)} tables:")
    for key, files in files_by_table.items():
        print(f"  {TABLE_CONFIG[key]['table']}: {len(files)} files")

    total_rows = 0
    for key, files in files_by_table.items():
        table_name = TABLE_CONFIG[key]['table']
        print(f"\nUploading to '{table_name}'...")

        table_rows = 0
        for csv_path in tqdm(files, desc=f"  {table_name}"):
            rows = upload_csv(engine, csv_path, table_name)
            table_rows += rows

        print(f"  {table_name}: {table_rows:,} rows uploaded")
        total_rows += table_rows

    create_indexes(engine)

    print(f"\nDone. {total_rows:,} total rows uploaded to {len(files_by_table)} tables.")

    # Print row counts
    print("\nTable row counts:")
    with engine.connect() as conn:
        for key, config in TABLE_CONFIG.items():
            table = config['table']
            result = conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
            count = result.scalar()
            print(f"  {table}: {count:,}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 upload_to_postgres.py <run_directory>")
        print("Example: python3 upload_to_postgres.py /Volumes/TPC/2026-02-22")
        sys.exit(1)
    main(sys.argv[1])
