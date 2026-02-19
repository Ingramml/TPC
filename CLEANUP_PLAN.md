# TPC Pipeline: Full Bug Fix & Cleanup Plan

## Context
The TPC data pipeline processes IRS Form 990 XML filings into CSV/JSON outputs (board members, grants, income/expenses, political contributions). A code review revealed 7 critical bugs, duplicated modules, inconsistent logging, and stale files. This plan addresses everything.

---

## Phase 1: Create shared `xml_helpers.py`

**New file:** `xml_helpers.py`

Extract duplicated helpers from `TPC_grants2.py` (lines 19-54) and `income_expense_fixed.py` (lines 15-50):
- `IRS_NAMESPACE = "{http://www.irs.gov/efile}"`
- `safe_find_element(root, xpath, alternative_xpath)`
- `get_element_text(element, default)`

---

## Phase 2: Fix critical bugs

### Bug A — `TPC_990_Boardmembers.py:208-221` — NameError in except block
- Replace `file_path` with `i` (the actual loop variable) in both except blocks

### Bug B — `TPC_990_Boardmembers.py:121-139` — String iteration on bad return type
- Change line 129 from `boardmemebers = 'errror'` to `continue` with a log warning
- Add explicit `990T` case that also continues
- Remove the `if returnType!='990T':` guard at line 138 (now redundant)

### Bug C — `TPC_990_Boardmembers.py:107` — Hardcoded error path
- Replace `os.rename(i, '/Volumes/Storage/TPC990/Errors/...')` with `error_handler.move_error_file(i, ...)`

### Bug D — `TPC_990_Boardmembers.py:205-206` — CSV write inside inner loop
- Move `df = pd.DataFrame(...)` and `df.to_csv(...)` outside the inner `for board_member` loop
- Add `index=False` to `to_csv()`

### Bug E — `main.py:18` — Duplicate `import datetime`
- Remove the duplicate

### Bug F — `TPC_grants.py:117,167` — Operator precedence
- Add parentheses: `(amount_element == '0' or amount_element is None) and ...`
- *Note: This file gets archived in Phase 3, but fix it anyway for safety*

### Bug G — `TPC_grants.py:151` — `.upper()` on None
- Change to `(business_name or '').upper() + ' ' + (business_name_ln2 or '').upper()`
- *Same note: archived in Phase 3*

---

## Phase 3: Consolidate duplicate modules

### 3a: Create `archive/` directory, move deprecated files
Move to `archive/`:
- `income_expense.py` (old, no error handling)
- `TPC_grants.py` (old, no error handling)
- `income_expense2.py`, `income_expense3.py`, `income_expense_original_backup.py`
- `TPC_political_contributions_DNU.py`
- `subdirectory concats.py` (space in filename)
- `Mass_delete.py`, `propublica_xml_downloading.py`
- `Donors_ScheduleB.py` (incomplete, 43 lines)
- `990 loping` (notes file)

### 3b: Rename improved modules
- `income_expense_fixed.py` -> `income_expense.py`
- `TPC_grants2.py` -> `TPC_grants.py`

### 3c: Update imports in renamed modules
- Both now import from `xml_helpers` instead of defining local copies
- Remove local `safe_find_element` / `get_element_text` definitions

### 3d: Update `main.py` imports
- Remove: import income_expense (old), import income_expense_fixed, duplicate import datetime
- Keep/update: import TPC_grants (now the improved version), import income_expense (now the improved version)
- Change `income_expense_fixed.irs_expense_income(...)` to `income_expense.irs_expense_income(...)`

### 3e: Update `test_files/test_error_handler.py`
- Line 17: `from income_expense_fixed import ...` -> `from income_expense import ...`
- Line 18: `from TPC_grants2 import ...` -> `from TPC_grants import ...`

---

## Phase 4: Centralize logging

### 4a: `TPC_990_Boardmembers.py`
- Remove local `setup_logging()` function (lines 11-51) and `logger = None`
- Import `from logging_setup import get_standard_logger`
- Use `logger = get_standard_logger('boardmembers', file_location)` in `irs_boardmember()`

### 4b: `TPC_990.py`
- Remove local `setup_logging()` function (lines 18-57)
- Import `from logging_setup import get_standard_logger`
- Replace `worker_logger = setup_logging(file_location)` in worker function with `get_standard_logger('tpc_990', file_location)`

### 4c: `main.py`
- Replace manual logging setup (lines 55-67) with `from logging_setup import setup_main_logging`
- Use `logger, run_id = setup_main_logging(file_download_directory)`

---

## Phase 5: Fix typos & minor issues

### 5a: Rename `boardmemebers` -> `board_members` throughout `TPC_990_Boardmembers.py`
- Also rename loop var `boardmemeber` -> `board_member`

### 5b: Remove boilerplate comments in `main.py` (lines 1-4)

### 5c: Clean up commented-out code blocks — replace triple-quote blocks with `# TODO:` comments

---

## Phase 6: Housekeeping

### 6a: Clean `requirements.txt`
Replace with only actually-used packages:
```
beautifulsoup4>=4.13.0
pandas>=2.2.0
patool>=4.0.0
requests>=2.32.0
tqdm>=4.67.0
```

### 6b: Delete stale log files from repo root
- 9 files matching `tpc_run_20250707_*.log`

### 6c: Delete empty `test_tpc_990.py`

### 6d: Update `.gitignore` — add `archive/`

### 6e: Remove tracked `__pycache__/` from git
```bash
git rm -r --cached __pycache__/
git rm --cached .DS_Store
```

---

## Key Files Modified

| File | Phases |
|------|--------|
| `xml_helpers.py` (new) | 1 |
| `TPC_990_Boardmembers.py` | 2, 4, 5 |
| `main.py` | 2, 3, 4, 5 |
| `TPC_grants.py` (old -> archive) | 2, 3 |
| `TPC_grants2.py` -> `TPC_grants.py` | 1, 3 |
| `income_expense_fixed.py` -> `income_expense.py` | 1, 3 |
| `test_files/test_error_handler.py` | 3 |
| `TPC_990.py` | 4 |
| `logging_setup.py` | (reference, no changes needed) |
| `requirements.txt` | 6 |
| `.gitignore` | 6 |

## Verification

1. Run `python -c "import xml_helpers; print('OK')"` to verify the new shared module
2. Run `python -c "import TPC_990_Boardmembers; print('OK')"` to verify imports after logging changes
3. Run `python -c "import main; print('OK')"` to verify main.py imports resolve
4. Run `python test_files/test_error_handler.py` to verify the test suite still works with renamed modules
5. Run `python -c "from TPC_grants import irs_grants; print('OK')"` to verify the renamed grants module
6. Verify no broken imports: `python -c "import income_expense; import TPC_grants; import TPC_990; import TPC_990_Boardmembers; print('All imports OK')"`
