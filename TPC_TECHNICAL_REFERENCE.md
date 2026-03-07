# TPC Pipeline - Technical Reference

## Purpose

The TPC (Tax Policy Center) Pipeline extracts structured data from IRS Form 990 XML e-file returns and produces CSV datasets for loading into a database. The database powers reports on nonprofit organizations, their finances, leadership, grants, and political contributions.

---

## Data Source

All data comes from the IRS Modernized e-File (MeF) system:

- **Base URL:** `https://apps.irs.gov/pub/epostcard/990/xml`
- **Index files:** `{BASE_URL}/{year}/index_{year}.csv` (years 2019-2026)
- **Zip files:** `{BASE_URL}/{year}/{BATCH_ID}.zip` (batch IDs from index CSV `XML_BATCH_ID` column)
- **Contents:** Each zip contains XML files representing individual e-file returns

IRS schema documentation is published at:
- Form overview: https://www.irs.gov/forms-pubs/about-form-990
- XML schemas: https://www.irs.gov/charities-non-profits/current-valid-xml-schemas-and-business-rules-for-exempt-organizations-modernized-e-file

---

## XML File Structure

Every IRS e-file XML return follows the same top-level structure, regardless of form type. The namespace for all elements is `{http://www.irs.gov/efile}`.

```
Return
  ReturnHeader                    <- Filing metadata
    ReturnTs                      <- Timestamp of filing
    TaxPeriodEndDt                <- End of tax period (e.g. "2023-12-31")
    TaxPeriodBeginDt              <- Start of tax period (e.g. "2023-01-01")
    ReturnTypeCd                  <- "990", "990PF", "990EZ", or "990T"
    TaxYr                         <- Tax year (e.g. "2023")
    Filer                         <- Organization identification
      EIN                         <- Employer Identification Number
      BusinessName
        BusinessNameLine1Txt      <- Organization name
        BusinessNameLine2Txt      <- (optional) DBA or second name line
      PhoneNum
      USAddress
        AddressLine1Txt
        AddressLine2Txt           <- (optional)
        CityNm
        StateAbbreviationCd
        ZIPCd
    PreparerFirmGrp               <- Tax preparer info
    BusinessOfficerGrp            <- Signing officer info
  ReturnData                      <- All form data + schedules
    IRS990 / IRS990PF / IRS990EZ  <- Main form (varies by type)
    IRS990ScheduleA               <- Public charity status
    IRS990ScheduleB               <- Contributors
    IRS990ScheduleC               <- Political campaign / lobbying
    IRS990ScheduleD               <- Financial statements
    IRS990ScheduleI               <- Grants and assistance
    IRS990ScheduleJ               <- Compensation
    IRS990ScheduleO               <- Supplemental information
    IRS990ScheduleR               <- Related organizations
    ... (other schedules as applicable)
```

### Accessing XML Elements in Code

The pipeline uses `root[0]` for `ReturnHeader` and `root[1]` for `ReturnData`. All element searches use the IRS namespace prefix.

---

## Return Type Differences (990 vs 990PF vs 990EZ)

The three main return types serve different organization sizes/types and have significant structural differences in their XML. The pipeline must handle each differently.

### Form 990 (Full Return)
**Used by:** Large tax-exempt organizations (gross receipts >= $200,000 or total assets >= $500,000)

Main element: `IRS990` (typically 200+ child elements)

| Data Category | XML Location |
|---------------|-------------|
| Revenue | `IRS990/CYTotalRevenueAmt` or `IRS990/TotalRevenueAmt` |
| Expenses | `IRS990/CYTotalExpensesAmt` or `IRS990/TotalExpensesAmt` |
| Total Assets BOY | `IRS990/TotalAssetsBOYAmt` or `IRS990/Form990TotalAssetsGrp/BOYAmt` |
| Total Assets EOY | `IRS990/TotalAssetsEOYAmt` or `IRS990/Form990TotalAssetsGrp/EOYAmt` |
| Mission | `IRS990/ActivityOrMissionDesc` or `IRS990/MissionDesc` |
| Website | `IRS990/WebsiteAddressTxt` |
| Tax-exempt status | `IRS990/Organization501c3Ind` or `IRS990/Organization501cInd` (with attribute `organization501cTypeTx`) |
| Board members | `IRS990/Form990PartVIISectionAGrp` (Part VII Section A) |
| Grants | `IRS990ScheduleI/RecipientTable` (Schedule I) |
| Political contributions | `Section527PoliticalOrgGrp` (found in Schedule C area or main form) |
| Compensation details | `IRS990ScheduleJ/RltdOrgOfficerTrstKeyEmplGrp` (Schedule J) |

### Form 990-PF (Private Foundation)
**Used by:** Private foundations regardless of size

Main element: `IRS990PF` (typically 20 top-level groups, deeply nested)

| Data Category | XML Location |
|---------------|-------------|
| Revenue | `IRS990PF/AnalysisOfRevenueAndExpenses/TotalRevAndExpnssAmt` |
| Expenses | `IRS990PF/AnalysisOfRevenueAndExpenses/TotalExpensesRevAndExpnssAmt` |
| Total Assets BOY | `IRS990PF/Form990PFBalanceSheetsGrp/TotalAssetsBOYAmt` |
| Total Assets EOY | `IRS990PF/Form990PFBalanceSheetsGrp/TotalAssetsEOYAmt` |
| FMV of Assets | `IRS990PF/FMVAssetsEOYAmt` |
| Officers/Directors | `IRS990PF/OfficerDirTrstKeyEmplInfoGrp/OfficerDirTrstKeyEmplGrp` |
| Grants | `IRS990PF/SupplementaryInformationGrp/GrantOrContributionPdDurYrGrp` |

**Key difference:** 990PF nests financial data inside group elements (`AnalysisOfRevenueAndExpenses`, `Form990PFBalanceSheetsGrp`) rather than flat top-level elements. Grant data lives in `SupplementaryInformationGrp` instead of Schedule I.

### Form 990-EZ (Short Form)
**Used by:** Small organizations (gross receipts < $200,000 and total assets < $500,000)

Main element: `IRS990EZ` (typically 40-50 child elements)

| Data Category | XML Location |
|---------------|-------------|
| Revenue | `IRS990EZ/TotalRevenueAmt` |
| Expenses | `IRS990EZ/TotalExpensesAmt` |
| Total Assets BOY | `IRS990EZ/Form990TotalAssetsGrp/BOYAmt` |
| Total Assets EOY | `IRS990EZ/Form990TotalAssetsGrp/EOYAmt` |
| Mission | `IRS990EZ/PrimaryExemptPurposeTxt` |
| Website | `IRS990EZ/WebsiteAddressTxt` |
| Officers | `IRS990EZ/OfficerDirectorTrusteeEmplGrp` (repeated, one per person) |

**Key difference:** 990EZ has fewer fields overall. Officers are listed directly in the main form (not in Part VII or a separate group). No Schedule I for grants. Total assets use `Form990TotalAssetsGrp` with `BOYAmt`/`EOYAmt` children.

### Form 990-T (Unrelated Business Income)
**Used by:** Organizations with unrelated business taxable income

Main element: `IRS990T`

The pipeline currently **skips** 990-T returns as they contain tax computation data, not the organizational/financial/grant data the pipeline extracts.

---

## Tag Name Variations

The IRS XML schema has evolved over the years. Older filings use different tag names for the same data. The pipeline must check both old and new names. Below are the known variations:

| Current Tag | Legacy/Alternative Tag | Purpose |
|-------------|----------------------|---------|
| `TaxPeriodBeginDt` | `TaxPeriodBeginDate` | Tax period start |
| `ReturnTypeCd` | `ReturnType` | Form type code |
| `TaxYr` | `TaxYear` | Tax year |
| `BusinessNameLine1Txt` | `BusinessNameLine1` | Org name line 1 |
| `BusinessNameLine2Txt` | `BusinessNameLine2` | Org name line 2 |
| `AddressLine1Txt` | `AddressLine1` | Address line 1 |
| `AddressLine2Txt` | `AddressLine2` | Address line 2 |
| `CityNm` | `City` | City name |
| `StateAbbreviationCd` | `State` | State code |
| `ZIPCd` | `ZIPCode` | Zip code |
| `AverageHoursPerWeekRt` | `AverageHoursPerWeek` | Hours per week (990) |
| `AverageHrsPerWkDevotedToPosRt` | *(990PF/990EZ specific)* | Hours per week (PF/EZ) |
| `IndividualTrusteeOrDirectorInd` | `IndividualTrusteeOrDirector` | Trustee/director flag |
| `ReportableCompFromOrgAmt` | `ReportableCompFromOrganization` | Compensation from org |
| `ReportableCompFromRltdOrgAmt` | `ReportableCompFromRelatedOrgs` | Comp from related orgs |
| `OtherCompensationAmt` | `OtherCompensation` | Other compensation |
| `CompensationAmt` | *(990PF/990EZ specific)* | Compensation (PF/EZ) |
| `CashGrantAmt` | `AmountOfCashGrant` | Cash grant amount |
| `RecipientEIN` | `EINOfRecipient` | Grantee EIN |
| `PurposeOfGrantTxt` | `PurposeOfGrant` | Grant purpose |
| `IRCSectionDesc` | `IRCSection` | IRC section |
| `RecipientPersonNm` | *(alternative to BusinessName)* | Individual grantee name |
| `PaidInternalFundsAmt` | `AmountPaidFromInternalFunds` | Political: paid from funds |
| `ContributionsRcvdDlvrAmt` | `ContributionsRcvdDeliveredAmt` | Political: contributions received |
| `GrantOrContributionPurposeTxt` | *(990PF grants)* | 990PF grant purpose |
| `Amt` | *(990PF grants)* | 990PF grant amount |
| `ActivityOrMissionDesc` | `ActivityOrMissionDescription` | Mission statement (990) |
| `PrimaryExemptPurposeTxt` | *(990EZ specific)* | Mission statement (EZ) |

The pipeline handles these via `safe_find_element()` (defined in `xml_helpers.py`), which tries a primary XPath first, then falls back to an alternative.

---

## Pipeline Stages

### Stage 1: Download (`download_from_index.py`)

Downloads yearly index CSVs from the IRS, reads `XML_BATCH_ID` column, and downloads each zip file.

- Skips already-downloaded files
- Normalizes batch IDs to uppercase (IRS server requires it)
- Returns list of failed downloads for the run report

### Stage 2: Extract & Organize (`TPC_990.py`)

Extracts zip files and moves XML files into year-based subfolders.

- Uses multiprocessing across all CPU cores
- Auto-retries corrupt/empty zips by re-downloading
- Falls back to `shutil` or `patoolib` if standard `zipfile` fails
- Returns list of failed extractions

### Stage 3a: Board Members (`TPC_990_Boardmembers.py`)

Extracts officer/director/trustee data from each XML file.

**XML sources by return type:**
| Return Type | XML Element |
|-------------|------------|
| 990 | `Form990PartVIISectionAGrp` (Part VII Section A) |
| 990PF | `OfficerDirTrstKeyEmplInfoGrp/OfficerDirTrstKeyEmplGrp` |
| 990EZ | `OfficerDirectorTrusteeEmplGrp` |

**Output columns:** `ein, name, title, averagehousperweek, indivualtrusteeordirector, compensation_from_org, compensation_from_related_org, othercompens, year`

**Output file:** `boardmembers_{EIN}.csv` per organization, plus `Boardmembers.json`

### Stage 3b: Income & Expense (`income_expense.py`)

Extracts financial data and organization profile from each XML file. Produces two CSV files per organization.

**Income/Expense output columns:** `ein, revenue, expenses, total_assets_boy, total_assets_eoy, return_type, year`

**Profile output columns:** `ein, org_name1, org_name2, address_1, address_2, city, state, zipcode, website, mission, status, year`

**Output files:** `income_expenses_{EIN}.csv` and `profile_{EIN}.csv` per organization, plus JSON summaries.

**Revenue/Expense sources by return type:**
| Return Type | Revenue Element | Expense Element |
|-------------|----------------|-----------------|
| 990 | `TotalRevenueAmt` or `CYTotalRevenueAmt` | `TotalExpensesAmt` or `CYTotalExpensesAmt` |
| 990PF | `AnalysisOfRevenueAndExpenses/TotalRevAndExpnssAmt` | `AnalysisOfRevenueAndExpenses/TotalExpensesRevAndExpnssAmt` |
| 990EZ | `TotalRevenueAmt` | `TotalExpensesAmt` |

**Total Assets sources by return type:**
| Return Type | BOY Element | EOY Element |
|-------------|-------------|-------------|
| 990 | `TotalAssetsBOYAmt` or `Form990TotalAssetsGrp/BOYAmt` | `TotalAssetsEOYAmt` or `Form990TotalAssetsGrp/EOYAmt` |
| 990PF | `Form990PFBalanceSheetsGrp/TotalAssetsBOYAmt` | `Form990PFBalanceSheetsGrp/TotalAssetsEOYAmt` |
| 990EZ | `Form990TotalAssetsGrp/BOYAmt` | `Form990TotalAssetsGrp/EOYAmt` |

### Stage 3c: Grants (`TPC_grants.py`)

Extracts grant and contribution data. Uses multiprocessing.

**XML sources by return type:**
| Return Type | XML Element |
|-------------|------------|
| 990 (Schedule I) | `IRS990ScheduleI/RecipientTable` |
| 990PF | `SupplementaryInformationGrp/GrantOrContributionPdDurYrGrp` |

**Output columns:** `grantor_ein, grantee_ein, grantee_name, amount, purpose, year` (Schedule I) or `grantor_ein, grantee_ein, grantee_name, amount, status, purpose, year` (990PF)

**Output file:** `grants_{EIN}.csv` per organization, plus `grant_profiles.json`

**Note:** Non-cash assistance amounts are captured when `CashGrantAmt` is 0 or empty. These are flagged with `*` appended to the purpose text.

### Stage 3d: Political Contributions (`TPC_political_contributions.py`)

Extracts Section 527 political organization contribution data. Uses multiprocessing.

**XML source:** `Section527PoliticalOrgGrp` (found in Schedule C / Part IV area of 990 returns)

**Section527PoliticalOrgGrp structure:**
```
Section527PoliticalOrgGrp
  OrganizationBusinessName
    BusinessNameLine1Txt          <- Political org name
    BusinessNameLine2Txt          <- (optional)
  USAddress
    AddressLine1Txt
    AddressLine2Txt               <- (optional)
    CityNm
    StateAbbreviationCd
    ZIPCd
  EIN                             <- Political org's EIN
  PaidInternalFundsAmt            <- Amount paid from internal funds
  ContributionsRcvdDlvrAmt        <- Contributions received and delivered
```

Each `Section527PoliticalOrgGrp` entry represents one political organization. A single entry has **either** `PaidInternalFundsAmt` or `ContributionsRcvdDlvrAmt` (not both).

**Output columns:** `filer_ein, recipient_name, address_line1, address_line2, city, state, zipcode, recipient_ein, amount_paid, contributions_received, year`

**Output file:** `political_contributions_{EIN}.csv` per organization, plus `political_contributions_profiles.json`

### Stage 4: Concatenation (`subdirectory_concat_gpt.py`)

Combines per-EIN CSV files into year-combined files, then merges all years into final datasets.

**Process:**
1. `folder_csv_concat()` — For each year subfolder, concatenates all CSVs with matching prefix into `{year}{prefix}_combined.csv`
2. `process_folder()` — Merges all combined CSVs into `{prefix}_all_{date}.csv`

**Prefixes processed:** `income_expenses_`, `profile_`, `grants_`, `boardmembers_`, `political_contributions_`

---

## Output Files (Database Input)

These are the final combined CSV files produced by the pipeline. Each is intended to be loaded into a database table.

### boardmembers__all_{date}.csv
One row per officer/director/trustee per organization per year.

| Column | Type | Description |
|--------|------|-------------|
| ein | text | Organization EIN (filer) |
| name | text | Person name |
| title | text | Title/role (e.g., PRESIDENT, DIRECTOR) |
| averagehousperweek | text | Average hours per week |
| indivualtrusteeordirector | text | "X" if individual trustee/director |
| compensation_from_org | text | Compensation from filing organization |
| compensation_from_related_org | text | Compensation from related organizations |
| othercompens | text | Other compensation |
| year | text | Tax year |

### income_expenses__all_{date}.csv
One row per organization per year.

| Column | Type | Description |
|--------|------|-------------|
| ein | text | Organization EIN |
| revenue | text | Total revenue |
| expenses | text | Total expenses |
| total_assets_boy | text | Total assets beginning of year |
| total_assets_eoy | text | Total assets end of year |
| return_type | text | "990", "990PF", or "990EZ" |
| year | text | Tax year |

### profile__all_{date}.csv
One row per organization per year.

| Column | Type | Description |
|--------|------|-------------|
| ein | text | Organization EIN |
| org_name1 | text | Organization name (line 1) |
| org_name2 | text | Organization name (line 2 / DBA) |
| address_1 | text | Street address line 1 |
| address_2 | text | Street address line 2 |
| city | text | City |
| state | text | State abbreviation |
| zipcode | text | ZIP code |
| website | text | Website URL |
| mission | text | Mission statement / exempt purpose |
| status | text | Tax-exempt status (e.g., "501(c)3") |
| year | text | Tax year |

### grants__all_{date}.csv
One row per grant per organization per year.

| Column | Type | Description |
|--------|------|-------------|
| grantor_ein | text | Granting organization EIN |
| grantee_ein | text | Recipient EIN (if available) |
| grantee_name | text | Recipient name |
| amount | text | Grant amount (cash or non-cash*) |
| status | text | IRC section (990PF grants only) |
| purpose | text | Grant purpose (* = non-cash amount) |
| year | text | Tax year |

### political_contributions__all_{date}.csv
One row per political contribution per organization per year.

| Column | Type | Description |
|--------|------|-------------|
| filer_ein | text | Filing organization EIN |
| recipient_name | text | Political organization name |
| address_line1 | text | Recipient street address |
| address_line2 | text | Recipient address line 2 |
| city | text | Recipient city |
| state | text | Recipient state |
| zipcode | text | Recipient ZIP |
| recipient_ein | text | Political organization EIN |
| amount_paid | text | Amount paid from internal funds |
| contributions_received | text | Contributions received and delivered |
| year | text | Tax year |

---

## Database Relationships

The EIN (Employer Identification Number) is the primary key that links all tables:

```
profile (ein, year)              <- Organization identity
  |
  |-- income_expenses (ein, year)   <- Financial data for same org/year
  |
  |-- boardmembers (ein, year)      <- Multiple rows per org/year (one per person)
  |
  |-- grants (grantor_ein, year)    <- Multiple rows per org/year (one per grant)
  |
  |-- political_contributions (filer_ein, year) <- Multiple rows per org/year
```

**Join keys:**
- `profile.ein` = `income_expenses.ein` (1:1 per year)
- `profile.ein` = `boardmembers.ein` (1:many per year)
- `profile.ein` = `grants.grantor_ein` (1:many per year)
- `profile.ein` = `political_contributions.filer_ein` (1:many per year)
- `grants.grantee_ein` can join back to `profile.ein` to identify grantee organizations

---

## Schedules Reference

| Schedule | IRS Name | XML Element | What It Contains | Extracted? |
|----------|----------|-------------|-----------------|------------|
| A | Public Charity Status | `IRS990ScheduleA` | Public charity classification, donor support tests | No |
| B | Contributors | `IRS990ScheduleB` | Individual contributor details (often redacted in public files) | No |
| C | Political/Lobbying | `IRS990ScheduleC` | Political campaign activity, lobbying expenditures, Section 527 orgs | Partially (Section527PoliticalOrgGrp) |
| D | Financial Statements | `IRS990ScheduleD` | Donor-advised funds, conservation easements, endowments, investments | No |
| E | Schools | `IRS990ScheduleE` | Private school nondiscrimination policies | No |
| F | Foreign Activities | `IRS990ScheduleF` | International activities, grants, offices | No |
| G | Fundraising/Gaming | `IRS990ScheduleG` | Professional fundraising, special events, gaming | No |
| H | Hospitals | `IRS990ScheduleH` | Hospital facility information, community benefit | No |
| I | Grants | `IRS990ScheduleI` | Domestic grants and assistance to organizations and individuals | Yes |
| J | Compensation | `IRS990ScheduleJ` | Detailed compensation for officers, directors, key employees | Partially (via Part VII) |
| K | Tax-Exempt Bonds | `IRS990ScheduleK` | Bond issuer information, proceeds use | No |
| L | Transactions | `IRS990ScheduleL` | Excess benefit transactions, loans, business relationships | No |
| M | Non-Cash Contributions | `IRS990ScheduleM` | Types and amounts of non-cash contributions received | No |
| N | Dissolution | `IRS990ScheduleN` | Liquidation, termination, dissolution, significant asset disposition | No |
| O | Supplemental Info | `IRS990ScheduleO` | Narrative explanations (free text) | No |
| R | Related Organizations | `IRS990ScheduleR` | Related/controlled entities, unrelated partnerships | No |

---

## Additional Data Available (Not Currently Extracted)

The following data exists in the XML files and could be extracted for additional reporting:

### From the Main Form (990)
- **Prior year comparisons:** `PYContributionsGrantsAmt`, `PYProgramServiceRevenueAmt`, `PYInvestmentIncomeAmt`, etc. (allows trend analysis)
- **Employee/volunteer counts:** `TotalEmployeeCnt`, `TotalVolunteersCnt`
- **Governance:** `VotingMembersGoverningBodyCnt`, `VotingMembersIndependentCnt`
- **Formation year:** `FormationYr`
- **Legal domicile:** `LegalDomicileStateCd`
- **Program service revenue:** `CYProgramServiceRevenueAmt`
- **Investment income:** `CYInvestmentIncomeAmt`
- **Fundraising expenses:** `CYTotalFundraisingExpenseAmt`
- **Net assets:** `NetAssetsOrFundBalancesBOYAmt`, `NetAssetsOrFundBalancesEOYAmt`
- **Gross receipts:** `GrossReceiptsAmt`

### From Schedule J (Compensation Detail)
- **Base compensation:** `BaseCompensationFilingOrgAmt`
- **Bonus:** `BonusFilingOrganizationAmount`
- **Deferred compensation:** `DeferredCompensationFlngOrgAmt`
- **Other compensation:** `OtherCompensationFilingOrgAmt`
- **Benefits from related orgs:** `CompensationBasedOnRltdOrgsAmt`

### From Schedule D (Financial Statements)
- **Endowment balances:** beginning, contributions, investment earnings, grants, end of year
- **Investment details:** corporate stock, corporate bonds, real estate

### From 990PF Specific
- **Fair market value of assets:** `FMVAssetsEOYAmt`
- **Minimum investment return:** `MinimumInvestmentReturnGrp`
- **Distributable amount:** `DistributableAmountGrp`
- **Qualifying distributions:** `PFQualifyingDistributionsGrp`
- **Capital gains detail:** `CapGainsLossTxInvstIncmDetail`

### From Schedule R (Related Organizations)
- **Related tax-exempt organizations:** names, EINs, relationship types
- **Controlled entities:** names, EINs, ownership percentages

---

## File Reference

### Pipeline Files (Active)

| File | Stage | Description |
|------|-------|-------------|
| `main_noscraping.py` | Entry point | Orchestrates the full pipeline end-to-end |
| `download_from_index.py` | Download | Downloads yearly index CSVs, then downloads zip files listed in them |
| `TPC_990.py` | Extract | Downloads individual zips, extracts with retry logic, moves XMLs into year folders |
| `TPC_990_Boardmembers.py` | Parse | Extracts board member/officer data from 990, 990PF, 990EZ |
| `income_expense.py` | Parse | Extracts organization profile and financial data |
| `TPC_grants.py` | Parse | Extracts grant/contribution data from Schedule I and 990PF |
| `TPC_political_contributions.py` | Parse | Extracts Section 527 political organization contribution data |
| `subdirectory_concat_gpt.py` | Concatenate | Combines per-EIN CSVs into year files, then into final datasets |
| `xml_helpers.py` | Utility | `safe_find_element()` and `get_element_text()` for safe XML access |
| `logging_setup.py` | Utility | Centralized logging with per-module loggers and log directory pinning |
| `error_handler.py` | Utility | Moves bad XML files to errors directory with reports |
| `folder_check.py` | Utility | Creates directories if they don't exist |
| `file_cleanup.py` | Utility | Deletes folder contents, empties trash, cleans up old files |

### Not Used by Pipeline

| File | Purpose |
|------|---------|
| `main.py` | Legacy entry point (web scraping, superseded by `main_noscraping.py`) |
| `Political_contributions_2.py` | Old political contributions script (superseded by `TPC_political_contributions.py`) |
| `income_expense_original_backup_depreciaterd.py` | Deprecated backup |
| `990 loping.py` | Development/test script |
| `xmlsampling.py` | XML sampling utility |
| `fast_cleanup.py` | Quick cleanup script |
| `file_dir_check.py` | Directory checking utility |
| `vscode_notification_helper.py` | VS Code notification helper |
| `archive/` | Archived old versions |

---

## Directory Structure (Per Run)

```
/Volumes/TPC/
  YYYY-MM-DD/                     <- Date-stamped run folder
    downloads/                    <- Zip files from IRS
      indexes/                    <- Yearly index CSV files
    xmlfiles/                     <- Extracted XML files
      2019/                       <- Year-based subfolders
      2020/
      ...
    csv/                          <- Output CSV files
      2019/                       <- Per-EIN CSVs
        boardmembers_{EIN}.csv
        income_expenses_{EIN}.csv
        profile_{EIN}.csv
        grants_{EIN}.csv
        political_contributions_{EIN}.csv
      2020/
      ...
      {year}boardmembers__combined.csv     <- Year-combined
      {year}income_expenses__combined.csv
      {year}profile__combined.csv
      {year}grants__combined.csv
      {year}political_contributions__combined.csv
      boardmembers__all_{date}.csv         <- Final merged datasets
      income_expenses__all_{date}.csv
      profile__all_{date}.csv
      grants__all_{date}.csv
      political_contributions__all_{date}.csv
    logs/                         <- Per-module log files
    errors/                       <- Error reports + problematic XML files
      run_report_YYYY-MM-DD.md
      run_report_YYYY-MM-DD.txt
```

---

## Running the Pipeline

```bash
python3 main_noscraping.py
```

Default output directory is `/Volumes/TPC`. To change, edit the last line of `main_noscraping.py`:

```python
if __name__ == '__main__':
    main('/Volumes/TPC')
```

### Dependencies

```
requests        - HTTP downloads
beautifulsoup4  - HTML parsing (legacy scraping path only)
pandas          - CSV/DataFrame operations
tqdm            - Progress bars
patoolib        - Fallback zip extraction (optional)
```
