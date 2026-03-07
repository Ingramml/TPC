"""
Research organizations in the cerebro_tpc database and generate PDF reports.

Accepts EINs, org names, or CSV files. For each org found, generates a full
PDF report with profile, financials, board, affiliations, grants, and
political contributions.

Usage:
    python3 research_orgs.py 020489703                           # single EIN
    python3 research_orgs.py "NEA - NEW HAMPSHIRE"               # org name search
    python3 research_orgs.py 020489703 020226432                 # multiple EINs
    python3 research_orgs.py --csv /path/to/file.csv             # CSV with EINs/names
    python3 research_orgs.py --csv file.csv --ein-col D --name-col A  # specify columns
    python3 research_orgs.py --output-dir ./reports 020489703    # custom output
"""

import sys
import os
import re
import argparse
import pandas as pd
from sqlalchemy import create_engine, text

from report_data import gather_report_data
from report_pdf import build_pdf

DB_HOST = 'localhost'
DB_PORT = 5430
DB_NAME = 'cerebro_tpc'
DB_USER = os.environ.get('USER', 'postgres')
ENGINE_URL = f'postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


def search_by_name(name, engine):
    """Search for orgs by name. Returns list of (ein, org_name) tuples."""
    name_pattern = f'%{name.strip().upper()}%'
    df = pd.read_sql(text(
        "SELECT DISTINCT ein, org_name1, year FROM profiles "
        "WHERE UPPER(org_name1) LIKE :name "
        "ORDER BY year DESC"
    ), engine, params={'name': name_pattern})

    if df.empty:
        return []

    # Deduplicate by EIN, keep most recent
    seen = {}
    for _, row in df.iterrows():
        ein = row['ein']
        if ein not in seen:
            seen[ein] = row['org_name1']
    return list(seen.items())


def extract_ein_from_url(url):
    """Extract EIN from causeiq or similar URLs."""
    if not url or pd.isna(url):
        return None
    match = re.search(r'/(\d{9})(?:[/\s]|$)', str(url))
    if match:
        return match.group(1)
    match = re.search(r'(\d{2}-?\d{7})', str(url))
    if match:
        return match.group(1).replace('-', '')
    return None


def is_ein(value):
    """Check if a string looks like an EIN (9 digits, optional dash)."""
    if not value:
        return False
    cleaned = str(value).strip().replace('-', '')
    return bool(re.match(r'^\d{9}$', cleaned))


def clean_ein(value):
    """Normalize EIN to 9 digits."""
    return str(value).strip().replace('-', '')


def process_csv(csv_path, ein_col=None, name_col=None, url_col=None, engine=None):
    """Parse CSV and extract EINs and/or org names to research."""
    df = pd.read_csv(csv_path, dtype=str)
    columns = list(df.columns)

    # Auto-detect columns if not specified
    if ein_col:
        # Convert letter column refs (A, B, C...) to index
        if len(ein_col) == 1 and ein_col.isalpha():
            idx = ord(ein_col.upper()) - ord('A')
            ein_col = columns[idx] if idx < len(columns) else None
    if name_col:
        if len(name_col) == 1 and name_col.isalpha():
            idx = ord(name_col.upper()) - ord('A')
            name_col = columns[idx] if idx < len(columns) else None
    if url_col:
        if len(url_col) == 1 and url_col.isalpha():
            idx = ord(url_col.upper()) - ord('A')
            url_col = columns[idx] if idx < len(columns) else None

    # If no columns specified, try to auto-detect
    if not ein_col and not name_col and not url_col:
        for col in columns:
            col_lower = col.lower()
            if 'ein' in col_lower:
                ein_col = col
            elif 'name' in col_lower or 'org' in col_lower:
                name_col = col
            elif 'url' in col_lower or 'link' in col_lower or 'causeiq' in col_lower:
                url_col = col

        # If still nothing, use first column as name, check all cols for URLs
        if not ein_col and not name_col and not url_col:
            name_col = columns[0]
            # Check each column for URL patterns
            for col in columns:
                sample = df[col].dropna().head(5)
                if any('causeiq' in str(v).lower() or 'http' in str(v).lower() for v in sample):
                    url_col = col
                    break

    results = []  # list of (ein, org_name, source)

    for _, row in df.iterrows():
        ein = None
        name = None

        # Try EIN column
        if ein_col and ein_col in row.index:
            val = str(row[ein_col]).strip()
            if is_ein(val):
                ein = clean_ein(val)

        # Try URL column for embedded EIN
        if not ein and url_col and url_col in row.index:
            ein = extract_ein_from_url(row[url_col])

        # Get name
        if name_col and name_col in row.index:
            name = str(row[name_col]).strip()
            if name == 'nan' or name == '':
                name = None

        if ein:
            results.append((ein, name, 'ein'))
        elif name:
            results.append((None, name, 'name'))

    return results


def main():
    parser = argparse.ArgumentParser(description='Research orgs in cerebro_tpc and generate PDF reports')
    parser.add_argument('queries', nargs='*', help='EINs or org names to research')
    parser.add_argument('--csv', help='CSV file with EINs/org names')
    parser.add_argument('--ein-col', help='CSV column for EINs (letter or name)')
    parser.add_argument('--name-col', help='CSV column for org names (letter or name)')
    parser.add_argument('--url-col', help='CSV column with URLs containing EINs')
    parser.add_argument('--output-dir', default='./reports', help='Output directory for PDFs')
    parser.add_argument('--summary', action='store_true', help='Print summary only, no PDF generation')
    args = parser.parse_args()

    if not args.queries and not args.csv:
        parser.print_help()
        sys.exit(1)

    engine = create_engine(ENGINE_URL)

    # Collect all research targets
    targets = []  # list of (ein, name, source)

    # From command line args
    for q in (args.queries or []):
        if is_ein(q):
            targets.append((clean_ein(q), None, 'ein'))
        else:
            targets.append((None, q, 'name'))

    # From CSV
    if args.csv:
        csv_targets = process_csv(args.csv, args.ein_col, args.name_col, args.url_col, engine)
        targets.extend(csv_targets)
        print(f"Loaded {len(csv_targets)} entries from {args.csv}")

    print(f"\nResearching {len(targets)} organizations...\n")

    found = []
    not_found = []
    name_matches = []

    for ein, name, source in targets:
        if ein:
            # Direct EIN lookup
            data = gather_report_data(ein)
            if data:
                db_name = data['profile'].get('org_name1', 'Unknown')
                found.append((ein, db_name, data))
                print(f"  FOUND     {ein}  {db_name}")
            else:
                not_found.append((ein, name or 'N/A'))
                print(f"  NOT FOUND {ein}  {name or ''}")
        else:
            # Name search
            matches = search_by_name(name, engine)
            if matches:
                for match_ein, match_name in matches:
                    data = gather_report_data(match_ein)
                    if data:
                        found.append((match_ein, match_name, data))
                        print(f"  FOUND     {match_ein}  {match_name}  (matched: \"{name}\")")
                        name_matches.append((name, match_ein, match_name))
            else:
                not_found.append((None, name))
                print(f"  NOT FOUND (name) \"{name}\"")

    print(f"\n--- Summary ---")
    print(f"Found: {len(found)}")
    print(f"Not found: {len(not_found)}")

    if not_found:
        print(f"\nNot found:")
        for ein, name in not_found:
            if ein:
                print(f"  EIN {ein} ({name})")
            else:
                print(f"  Name: \"{name}\"")

    if args.summary:
        return

    # Generate reports
    if found:
        os.makedirs(args.output_dir, exist_ok=True)
        print(f"\nGenerating {len(found)} PDF reports to {args.output_dir}...")

        for ein, db_name, data in found:
            org_name_safe = (db_name or 'unknown').replace(' ', '_').replace('/', '_')[:40]
            pdf_filename = f'report_{ein}_{org_name_safe}.pdf'
            pdf_path = os.path.join(args.output_dir, pdf_filename)
            build_pdf(data, pdf_path)
            print(f"  {pdf_filename}")

        # Generate summary PDF if multiple orgs
        if len(found) > 1:
            import json
            from report_summary_pdf import build_summary_pdf

            summary_data = []
            for ein, db_name, data in found:
                profile = data['profile']
                fin = data['financials']
                summary_data.append({
                    'ein': ein,
                    'name': db_name,
                    'state': str(profile.get('state', '')),
                    'status': str(profile.get('status', '')),
                    'latest_year': str(fin.iloc[0].get('year', '')) if not fin.empty else '',
                    'revenue': str(fin.iloc[0].get('revenue', '')) if not fin.empty else '',
                    'expenses': str(fin.iloc[0].get('expenses', '')) if not fin.empty else '',
                    'assets_eoy': str(fin.iloc[0].get('total_assets_eoy', '')) if not fin.empty else '',
                    'board_count': len(data['board']),
                    'grants_given': len(data['grants_given']),
                    'grants_received': len(data['grants_received']),
                    'political': len(data['political_contributions']),
                })

            summary_path = os.path.join(args.output_dir, 'SUMMARY_all_organizations.pdf')
            build_summary_pdf(summary_data, summary_path)
            print(f"\n  SUMMARY_all_organizations.pdf")

        print(f"\nDone. {len(found)} reports saved to {args.output_dir}")


if __name__ == '__main__':
    main()
