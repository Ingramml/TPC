# Test Pipeline

Quickly validate code changes by running the full TPC processing pipeline on a small sample of existing XML files. Skips the ~9 hour download and extraction steps entirely.

## Requirements

- A previous full run must exist on disk (e.g. `/Volumes/TPC/2026-02-20/xmlfiles/`) with extracted XML files in year subfolders.
- All project dependencies installed (pandas, tqdm, etc.).

## Usage

```bash
# Default: 50 random files, auto-detects latest xmlfiles on disk
python3 test_pipeline.py

# Process 200 files instead
python3 test_pipeline.py --files 200

# Point to a specific xmlfiles folder
python3 test_pipeline.py --source /Volumes/TPC/2026-02-20/xmlfiles

# Write output to a custom directory
python3 test_pipeline.py --output /Volumes/TPC/my_test_run
```

### Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--files N` | 50 | Number of XML files to sample |
| `--source PATH` | auto-detect | Path to an `xmlfiles/` folder. If omitted, scans `/Volumes/TPC/YYYY-MM-DD/xmlfiles/` and picks the most recent one containing files. |
| `--output PATH` | `/Volumes/TPC/YYYY-MM-DD_test` | Output directory for all results. If omitted, uses today's date with `_test` suffix. |

## What It Does

1. **Auto-detects source XML** — finds the latest `/Volumes/TPC/YYYY-MM-DD/xmlfiles/` folder with data (or uses `--source`).
2. **Creates output folder** — `/Volumes/TPC/YYYY-MM-DD_test/` (or the path given via `--output`) with subdirectories:
   ```
   /Volumes/TPC/2026-02-21_test/
   ├── xmlfiles/      # sampled XML files by year
   ├── csv/           # output CSVs from all modules
   ├── logs/          # per-module log files
   └── errors/        # run reports (.md and .txt)
   ```
   If the `_test` folder already exists it is deleted and recreated fresh.
3. **Copies N random XML files** — distributed evenly across year subfolders (e.g. 50 files / 5 years = 10 per year).
4. **Runs all processing modules** in the same order as `main_noscraping.py`:
   - `TPC_990_Boardmembers.irs_boardmember()`
   - `income_expense.irs_expense_income()`
   - `TPC_grants.irs_grants()`
5. **Runs CSV concatenation** for all 4 prefixes: `income_expenses_`, `profile_`, `grants_`, `boardmembers_`.
6. **Generates run reports** — both `.md` and `.txt` in the `errors/` folder with timing, file counts, and source info.
7. **Prints a console summary** — files processed, CSVs created, per-stage timing.

## Expected Runtime

With 50 files: under 2 minutes. Scales roughly linearly with `--files`.

## Verifying a Test Run

After running, check:

| What to check | Where |
|----------------|-------|
| Output CSVs exist for all modules | `/Volumes/TPC/YYYY-MM-DD_test/csv/` |
| Run report generated | `/Volumes/TPC/YYYY-MM-DD_test/errors/run_report_*.md` |
| Log files for each module | `/Volumes/TPC/YYYY-MM-DD_test/logs/` |
| Console summary shows no unexpected errors | Terminal output |

## How It Differs from a Full Run

| | Full run (`main_noscraping.py`) | Test run (`test_pipeline.py`) |
|---|---|---|
| Downloads ZIP files | Yes | No |
| Extracts XML from ZIPs | Yes | No |
| Source XML | Freshly downloaded | Copied from previous run |
| File count | ~360,000+ | 50 (configurable) |
| Output location | `/Volumes/TPC/YYYY-MM-DD/` | `/Volumes/TPC/YYYY-MM-DD_test/` (or `--output`) |
| Runtime | ~9 hours | ~1-2 minutes |
| Run report includes download/extract errors | Yes | No (those stages are skipped) |