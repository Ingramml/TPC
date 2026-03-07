# Research Organizations

Research organizations in the cerebro_tpc database and generate reports.

The user will provide one or more of:
- An EIN number (9 digits, e.g. 020489703)
- An organization name to search for
- A list of EINs or org names
- A path to a CSV file containing EINs and/or org names

For each input:

1. **If EIN provided**: Query cerebro_tpc database (localhost:5430) directly by EIN
2. **If org name provided**: Search profiles table with LIKE match, show matches and let user confirm
3. **If CSV provided**: Parse the CSV, auto-detect EIN/name/URL columns, extract EINs from URLs if needed

For each organization found in the database, gather and present:
- **Profile**: org name, address, city/state/zip, website, tax-exempt status, mission
- **Financial Summary**: all years of revenue, expenses, assets (BOY/EOY), return type
- **Board of Directors**: names, titles, hours/week, compensation from the most recent year
- **Board Member Affiliations**: all other orgs where each board member serves, with confidence indicator (HIGH = same state, MEDIUM = adjacent state, LOW = different state)
- **Grants Given**: all grants this org has made
- **Grants Received**: all grants made to this org
- **Political Contributions**: any Section 527 political org contributions

Then generate both:
- A **markdown research report** saved to `./reports/research_{EIN}_{OrgName}.md`
- A **PDF report** saved to `./reports/report_{EIN}_{OrgName}.pdf`

Use the existing tools:
- `report_data.py` — `gather_report_data(ein)` returns all data from the database
- `report_pdf.py` — `generate_report(ein, output_dir)` creates the PDF
- `research_orgs.py` — CLI tool for batch processing

Run the research from the TPC project directory: /Users/michaelingram/Documents/GitHub/TPC

$ARGUMENTS
