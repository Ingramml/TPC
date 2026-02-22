# TPC Pipeline - Project Overview

## Purpose

The TPC (Tax Policy Center) Pipeline is an automated data extraction system that downloads IRS Form 990 XML filings, parses them, and produces structured CSV datasets. It processes the full IRS e-file archive (2019-present) to extract:

- **Organization profiles** (name, address, EIN, mission, tax-exempt status)
- **Income and expense data** (revenue, expenses, total assets)
- **Board member and officer compensation**
- **Grant and contribution records** (grantor, grantee, amounts, purposes)

The final output is a set of combined CSV files suitable for analysis, research, or upload to a database.

---

## How It Works

Running `python3 main_noscraping.py` executes the full pipeline end-to-end:

```
IRS Server
    |
    v
[1] Download index CSVs (one per year, 2019-2026)
    |
    v
[2] Download zip files listed in indexes (~100+ zips)
    |
    v
[3] Extract zips -> move XML files into year-based folders
    |
    v
[4] Parse XML files (3 parallel processing stages):
    |--- Board Members  -> boardmembers_<EIN>.csv
    |--- Income/Expense -> income_expenses_<EIN>.csv + profile_<EIN>.csv
    |--- Grants         -> grants_<EIN>.csv
    |
    v
[5] Concatenate per-EIN CSVs into combined files by year
    |
    v
[6] Merge year files into final "_all_" datasets
    |
    v
[7] Generate run report (errors/run_report_YYYY-MM-DD.md + .txt)
```

---

## Directory Structure (per run)

```
/Volumes/TPC/
  YYYY-MM-DD/
    downloads/          Zip files from IRS + index CSVs
      indexes/          Yearly index CSV files
    xmlfiles/           Extracted XML files organized by year prefix
      2019/
      2020/
      ...
    csv/                Output CSV files
      2019/             Per-EIN CSVs (boardmembers_, income_expenses_, profile_, grants_)
      2020/
      ...
      *_combined.csv    Year-combined CSVs
      *_all_*.csv       Final merged datasets
    logs/               Log files for each module
    errors/             Error reports and problematic XML files
      run_report_YYYY-MM-DD.md
      run_report_YYYY-MM-DD.txt
```

---

## File Reference

### Entry Points

| File | Purpose |
|------|---------|
| `main_noscraping.py` | **Primary entry point.** Orchestrates the full pipeline using index-based downloads. Run this. |
| `main.py` | Legacy entry point that uses web scraping to find zip files. Superseded by `main_noscraping.py`. |

### Pipeline Stages

| File | Stage | Description |
|------|-------|-------------|
| `download_from_index.py` | Download | Downloads yearly index CSVs from the IRS, reads `XML_BATCH_ID` column to get zip filenames, downloads each zip. Uses `tqdm` progress bar. Returns list of failed downloads. |
| `TPC_990.py` | Download + Extract | `download_file()` downloads a single zip (returns True/False). `extract_zip()` extracts with retry logic (re-downloads corrupt/empty zips). `extract_and_move_xml_files()` uses multiprocessing to extract all zips and move XMLs into year-based folders. Returns list of failed extractions. |
| `TPC_990_Boardmembers.py` | Parse | Extracts board member/officer data from 990, 990PF, and 990EZ returns: names, titles, hours worked, compensation. Outputs per-EIN CSVs and a JSON summary. |
| `income_expense.py` | Parse | Extracts organization profile info (name, address, mission, status) and financial data (revenue, expenses, total assets). Handles 990, 990PF, and 990EZ return types. Outputs per-EIN CSVs and JSON summaries. |
| `TPC_grants.py` | Parse | Extracts grant/contribution data from Schedule I and 990PF forms. Uses multiprocessing. Outputs per-EIN CSVs and a JSON summary. |
| `subdirectory_concat_gpt.py` | Concatenate | Combines per-EIN CSVs into year-combined files, then merges those into final `_all_` datasets. Uses multiprocessing. |

### Shared Utilities

| File | Purpose |
|------|---------|
| `xml_helpers.py` | `safe_find_element()` and `get_element_text()` — safe XML element access with fallback XPaths. Used by boardmembers, income_expense, and grants modules. |
| `logging_setup.py` | Centralized logging configuration. `setup_main_logging()` configures the root logger. `get_standard_logger()` creates per-module loggers. Supports `log_dir` override to prevent date folder drift on long runs. |
| `error_handler.py` | Moves problematic XML files to the errors directory with timestamped names and error reports. Prevents one bad file from stopping the pipeline. |
| `folder_check.py` | Creates directories if they don't exist. |
| `file_cleanup.py` | Utilities for deleting folder contents, emptying trash (macOS/Windows/Linux), and cleaning up old files. |

### Not Used by Pipeline

| File | Purpose |
|------|---------|
| `income_expense_original_backup.py` | Deprecated backup of income_expense.py before refactoring. |
| `Political_contributions_2.py` | Political contribution extraction (not integrated into main pipeline). |
| `990 loping.py` | Development/test script. |
| `xmlsampling.py` | XML sampling utility for testing. |
| `fast_cleanup.py` | Quick cleanup script. |
| `file_dir_check.py` | Directory checking utility. |
| `vscode_notification_helper.py` | VS Code notification helper. |
| `archive/` | Archived old versions of scripts. |

---

## Data Sources

All data comes from the IRS e-file system:

- **Base URL:** `https://apps.irs.gov/pub/epostcard/990/xml`
- **Index files:** `{BASE_URL}/{year}/index_{year}.csv` (one per year, 2019-2026)
- **Zip files:** `{BASE_URL}/{year}/{BATCH_ID}.zip` (batch IDs from index CSV `XML_BATCH_ID` column)
- **Contents:** Each zip contains XML files representing individual 990/990PF/990EZ/990T e-file returns

---

## Key Design Decisions

### Index-Based Downloads (not scraping)
The pipeline uses IRS-published index CSVs to discover zip files rather than scraping HTML pages. This is more reliable and avoids 404 errors from page layout changes.

### Batch ID Uppercase Normalization
The IRS index CSVs have inconsistent casing for batch IDs (e.g., `04a` vs `04A`). The server URLs require uppercase. All batch IDs are normalized with `.upper()` before building download URLs.

### Corrupt Zip Auto-Retry
When a zip file fails to extract (empty file or `BadZipFile`), the pipeline automatically re-downloads it from the IRS server and retries extraction before falling back to alternative extraction methods (`shutil`, `patoolib`).

### Multiprocessing
Zip extraction (`TPC_990.py`) and grants processing (`TPC_grants.py`) use Python `multiprocessing.Pool` to parallelize work across all CPU cores. CSV concatenation also uses multiprocessing.

### Error Isolation
Bad XML files are moved to an `errors/` directory rather than crashing the pipeline. Failed downloads and extractions are tracked and reported at the end of the run.

### Log Directory Pinning
All modules accept a `log_dir` parameter that pins log files to the date folder created at startup. This prevents logs from splitting across date folders when a run crosses midnight.

---

## Output Files

| File Pattern | Contents |
|-------------|----------|
| `boardmembers_<EIN>.csv` | Board member names, titles, hours, compensation for one org |
| `income_expenses_<EIN>.csv` | Revenue, expenses, total assets for one org |
| `profile_<EIN>.csv` | Name, address, website, mission, tax status for one org |
| `grants_<EIN>.csv` | Grant recipients, amounts, purposes for one org |
| `<year>boardmembers__combined.csv` | All boardmember data for one year |
| `boardmembers__all_<date>.csv` | All boardmember data across all years |
| `run_report_<date>.md` / `.txt` | Run timing and error summary |

---

## Running the Pipeline

```bash
python3 main_noscraping.py
```

The default download directory is `/Volumes/TPC`. To change it, edit the last line of `main_noscraping.py`:

```python
if __name__ == '__main__':
    main('/Volumes/TPC')
```

### Dependencies

- `requests` — HTTP downloads
- `beautifulsoup4` — HTML parsing (legacy scraping path only)
- `pandas` — CSV/DataFrame operations
- `tqdm` — Progress bars
- `patoolib` (optional) — Fallback zip extraction
