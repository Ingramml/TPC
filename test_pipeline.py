"""
Test Pipeline — runs all processing stages on a small sample of existing XML files.
Skips download and extraction entirely.

Usage:
  python3 test_pipeline.py                  # 50 files from latest xmlfiles on disk
  python3 test_pipeline.py --files 200      # 200 files
  python3 test_pipeline.py --source /path/to/xmlfiles  # custom source
"""

import argparse
import datetime
import glob
import logging
import os
import random
import shutil

import subdirectory_concat_gpt
import TPC_990_Boardmembers
import TPC_grants
import income_expense
from folder_check import folder_check
from logging_setup import setup_main_logging


BASE_DIR = "/Volumes/TPC"


def find_latest_xmlfiles(base=BASE_DIR):
    """Find the most recent YYYY-MM-DD/xmlfiles/ folder that contains files."""
    candidates = sorted(glob.glob(os.path.join(base, "????-??-??", "xmlfiles")), reverse=True)
    for path in candidates:
        if any(os.scandir(path)):
            return path
    raise FileNotFoundError(f"No xmlfiles folder with data found under {base}")


def copy_sample(source_xml, dest_xml, n_files):
    """Copy n_files random XMLs from source, spread across year subfolders."""
    year_dirs = sorted(
        d for d in os.listdir(source_xml)
        if os.path.isdir(os.path.join(source_xml, d))
    )
    if not year_dirs:
        raise FileNotFoundError(f"No year subfolders found in {source_xml}")

    per_year = max(1, n_files // len(year_dirs))
    total_copied = 0

    for year in year_dirs:
        src = os.path.join(source_xml, year)
        dst = os.path.join(dest_xml, year)
        folder_check(dst)

        xmls = [f for f in os.listdir(src) if f.lower().endswith(".xml")]
        chosen = random.sample(xmls, min(per_year, len(xmls)))
        for fname in chosen:
            shutil.copy2(os.path.join(src, fname), os.path.join(dst, fname))
            total_copied += 1

    print(f"Copied {total_copied} XML files across {len(year_dirs)} year folders")
    return total_copied


def main():
    parser = argparse.ArgumentParser(description="Run TPC pipeline on a small XML sample")
    parser.add_argument("--files", type=int, default=50, help="Number of XML files to process (default 50)")
    parser.add_argument("--source", type=str, default=None, help="Path to xmlfiles/ folder (auto-detects latest if omitted)")
    parser.add_argument("--output", type=str, default=None, help="Output directory (default: /Volumes/TPC/YYYY-MM-DD_test)")
    args = parser.parse_args()

    start = datetime.datetime.now()
    today = datetime.date.today()
    test_dir = args.output or os.path.join(BASE_DIR, f"{today.strftime('%Y-%m-%d')}_test")

    # --- Resolve source ---
    source_xml = args.source or find_latest_xmlfiles()
    print(f"Source XML folder: {source_xml}")

    # --- Create date_test folder structure ---
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    xml_location = os.path.join(test_dir, "xmlfiles")
    target_location = os.path.join(test_dir, "csv")
    log_location = os.path.join(test_dir, "logs")
    error_location = os.path.join(test_dir, "errors")
    folder_check([test_dir, xml_location, target_location, log_location, error_location])

    # --- Copy sample ---
    n_copied = copy_sample(source_xml, xml_location, args.files)

    # --- Logging ---
    logger, run_id = setup_main_logging(test_dir, console_output=False)
    logging.info("=== Test pipeline run started ===")

    # --- Processing ---
    timings = {}

    t0 = datetime.datetime.now()
    logging.info("Processing BoardMembers")
    print("Processing BoardMembers...")
    TPC_990_Boardmembers.irs_boardmember(xml_location, target_location, log_dir=log_location)
    timings["BoardMembers"] = datetime.datetime.now() - t0

    t0 = datetime.datetime.now()
    logging.info("Processing Income/Expenses")
    print("Processing Income/Expenses...")
    income_expense.irs_expense_income(xml_location, target_location, log_dir=log_location)
    timings["Income/Expenses"] = datetime.datetime.now() - t0

    t0 = datetime.datetime.now()
    logging.info("Processing Grants")
    print("Processing Grants...")
    TPC_grants.irs_grants(xml_location, target_location, log_dir=log_location)
    timings["Grants"] = datetime.datetime.now() - t0

    t0 = datetime.datetime.now()
    logging.info("Concatenating CSVs")
    print("Concatenating CSVs...")
    for prefix in ["income_expenses_", "profile_", "grants_", "boardmembers_"]:
        subdirectory_concat_gpt.folder_csv_concat(target_location, prefix, num_processes=4)
        subdirectory_concat_gpt.process_folder((target_location, prefix))
    timings["Concatenation"] = datetime.datetime.now() - t0

    elapsed = datetime.datetime.now() - start

    # --- Count outputs ---
    csv_files = glob.glob(os.path.join(target_location, "**", "*.csv"), recursive=True)
    log_files = glob.glob(os.path.join(log_location, "*.log"))

    # --- Run report (md) ---
    report_path = os.path.join(error_location, f"run_report_{today.strftime('%Y-%m-%d')}.md")
    md = []
    md.append(f"# Test Run Report - {today.strftime('%Y-%m-%d')}")
    md.append("")
    md.append(f"**Mode:** TEST ({n_copied} XML files sampled)")
    md.append(f"**Source:** `{source_xml}`")
    md.append(f"**Status:** SUCCESS")
    md.append(f"**Total runtime:** {elapsed}")
    md.append("")
    md.append("## Timing")
    md.append("")
    md.append("| Stage | Duration |")
    md.append("|-------|----------|")
    for stage, dur in timings.items():
        md.append(f"| {stage} | {dur} |")
    md.append(f"| **Total** | **{elapsed}** |")
    md.append("")
    md.append("## Output")
    md.append("")
    md.append(f"- CSV files created: {len(csv_files)}")
    md.append(f"- Log files created: {len(log_files)}")
    md.append("")

    with open(report_path, "w") as f:
        f.write("\n".join(md))

    # --- Run report (txt) ---
    txt_path = os.path.join(error_location, f"run_report_{today.strftime('%Y-%m-%d')}.txt")
    txt = []
    txt.append(f"Test Run Report - {today.strftime('%Y-%m-%d')}")
    txt.append("=" * 50)
    txt.append(f"Mode:          TEST ({n_copied} XML files sampled)")
    txt.append(f"Source:        {source_xml}")
    txt.append(f"Status:        SUCCESS")
    txt.append(f"Total runtime: {elapsed}")
    txt.append("")
    txt.append("TIMING")
    txt.append("-" * 50)
    for stage, dur in timings.items():
        txt.append(f"  {stage + ':':<20} {dur}")
    txt.append(f"  {'TOTAL:':<20} {elapsed}")
    txt.append("")
    txt.append("OUTPUT")
    txt.append("-" * 50)
    txt.append(f"  CSV files created: {len(csv_files)}")
    txt.append(f"  Log files created: {len(log_files)}")
    txt.append("")

    with open(txt_path, "w") as f:
        f.write("\n".join(txt))

    # --- Console summary ---
    print(f"\n{'='*50}")
    print(f"TEST PIPELINE SUMMARY")
    print(f"{'='*50}")
    print(f"  XML files sampled:   {n_copied}")
    print(f"  CSV files created:   {len(csv_files)}")
    print(f"  Log files created:   {len(log_files)}")
    print(f"{'='*50}")
    for stage, dur in timings.items():
        print(f"  {stage + ':':<20} {dur}")
    print(f"{'='*50}")
    print(f"  TOTAL:               {elapsed}")
    print(f"{'='*50}")
    print(f"\nReports: {error_location}")
    print(f"CSVs:    {target_location}")
    print(f"Logs:    {log_location}")

    logging.info(f"Test pipeline completed in {elapsed}")
    logging.info("=== Test run completed ===")


if __name__ == "__main__":
    main()
