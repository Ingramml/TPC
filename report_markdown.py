"""
Markdown report generator for TPC organization reports.

Generates .md reports matching the sample_report.md format with all sections:
profile, financials, board, affiliations, grants, and political contributions.

Usage:
    from report_markdown import generate_markdown_report
    generate_markdown_report('020489703', output_dir='./reports')
"""

import os
from report_data import gather_report_data, ADJACENT_STATES


def fmt_money(val):
    if val is None or val == '' or val == 'None':
        return '-'
    try:
        num = float(val)
        if num < 0:
            return f'-${abs(num):,.0f}'
        return f'${num:,.0f}'
    except (ValueError, TypeError):
        return str(val)


def fmt_val(val, default='-'):
    if val is None or val == '' or val == 'None' or str(val) == 'nan':
        return default
    return str(val).strip()


def build_markdown(data):
    profile = data['profile']
    ein = data['ein']
    org_name = fmt_val(profile.get('org_name1'), 'Unknown Organization')
    org_state = fmt_val(profile.get('state')).upper()
    adjacent = ', '.join(sorted(ADJACENT_STATES.get(org_state, [])))

    lines = []
    lines.append(f'# Organization Report: EIN {ein}')
    lines.append(f'\n**Report Generated:** {data["report_date"]}')
    lines.append('\n---')

    # Profile
    lines.append('\n## Organization Profile')
    lines.append('\n| Field | Value |')
    lines.append('|-------|-------|')
    lines.append(f'| **EIN** | {ein} |')

    name2 = fmt_val(profile.get('org_name2'))
    display_name = org_name if name2 == '-' else f'{org_name} / {name2}'
    lines.append(f'| **Organization Name** | {display_name} |')

    addr = fmt_val(profile.get('address_1'))
    addr2 = fmt_val(profile.get('address_2'))
    if addr2 != '-':
        addr = f'{addr}, {addr2}'
    lines.append(f'| **Address** | {addr} |')

    city = fmt_val(profile.get('city'))
    state = fmt_val(profile.get('state'))
    zipcode = fmt_val(profile.get('zipcode'))
    lines.append(f'| **City, State ZIP** | {city}, {state} {zipcode} |')
    lines.append(f'| **Website** | {fmt_val(profile.get("website"))} |')
    lines.append(f'| **Tax-Exempt Status** | {fmt_val(profile.get("status"))} |')
    lines.append(f'| **Mission** | {fmt_val(profile.get("mission"))} |')

    lines.append('\n---')

    # Financials
    lines.append('\n## Financial Summary')
    fin_df = data['financials']
    if fin_df.empty:
        lines.append('\n*No financial data on record.*')
    else:
        lines.append('\n| Year | Revenue | Expenses | Total Assets (BOY) | Total Assets (EOY) | Return Type |')
        lines.append('|------|--------:|---------:|-------------------:|-------------------:|-------------|')
        for _, row in fin_df.iterrows():
            lines.append(
                f'| {fmt_val(row.get("year"))} '
                f'| {fmt_money(row.get("revenue"))} '
                f'| {fmt_money(row.get("expenses"))} '
                f'| {fmt_money(row.get("total_assets_boy"))} '
                f'| {fmt_money(row.get("total_assets_eoy"))} '
                f'| {fmt_val(row.get("return_type"))} |'
            )

    lines.append('\n---')

    # Board
    board_year = data.get('board_year', '')
    lines.append(f'\n## Board of Directors ({board_year})')
    board_df = data['board']
    if board_df.empty:
        lines.append('\n*No board member data on record.*')
    else:
        lines.append('\n| Name | Title | Hours/Week | Comp (Org) | Comp (Related) | Other Comp |')
        lines.append('|------|-------|------------|------------|----------------|------------|')
        for _, row in board_df.iterrows():
            lines.append(
                f'| {fmt_val(row.get("name"))} '
                f'| {fmt_val(row.get("title"))} '
                f'| {fmt_val(row.get("averagehousperweek"), "0")} '
                f'| {fmt_money(row.get("compensation_from_org"))} '
                f'| {fmt_money(row.get("compensation_from_related_org"))} '
                f'| {fmt_money(row.get("othercompens"))} |'
            )

    lines.append('\n---')

    # Affiliations
    lines.append('\n## Board Member Affiliations')
    lines.append(f'\nFor each board member, all other organizations where they serve as an officer, director, or trustee.')
    lines.append(f'\n**Confidence Indicator:** Based on geographic proximity to the filing organization\'s state ({org_state}).')
    lines.append(f'- **HIGH** = Same state ({org_state}) — very likely the same person')
    lines.append(f'- **MEDIUM** = Adjacent state ({adjacent}) — likely the same person')
    lines.append(f'- **LOW** = Different state — possibly a different person with the same name')

    for member_name, member_data in data['affiliations'].items():
        title = member_data['title']
        affs = member_data['affiliations']

        lines.append(f'\n### {member_name} — {fmt_val(title)}')

        if not affs:
            lines.append('\n*No other organizational affiliations found.*')
        else:
            lines.append('\n| Confidence | EIN | Organization | State | Title | Year |')
            lines.append('|:----------:|-----|-------------|:-----:|-------|------|')
            for aff in affs:
                conf = aff['confidence']
                conf_display = f'**{conf}**' if conf == 'HIGH' else conf
                lines.append(
                    f'| {conf_display} '
                    f'| {fmt_val(aff["ein"])} '
                    f'| {fmt_val(aff["org_name"])} '
                    f'| {fmt_val(aff["state"])} '
                    f'| {fmt_val(aff["title"])} '
                    f'| {fmt_val(aff["year"])} |'
                )

    lines.append('\n---')

    # Grants Given
    lines.append('\n## Grants Given')
    grants_given = data['grants_given']
    if grants_given.empty:
        lines.append('\n*No grants given on record.*')
    else:
        lines.append('\n| Year | Grantee | EIN | Amount | Purpose | Status |')
        lines.append('|------|---------|-----|-------:|---------|--------|')
        for _, row in grants_given.iterrows():
            lines.append(
                f'| {fmt_val(row.get("year"))} '
                f'| {fmt_val(row.get("grantee_name"))} '
                f'| {fmt_val(row.get("grantee_ein"))} '
                f'| {fmt_money(row.get("amount"))} '
                f'| {fmt_val(row.get("purpose"))} '
                f'| {fmt_val(row.get("status"))} |'
            )

    lines.append('\n---')

    # Grants Received
    lines.append('\n## Grants Received')
    grants_received = data['grants_received']
    if grants_received.empty:
        lines.append('\n*No grants received on record.*')
    else:
        lines.append('\n| Year | Grantor EIN | Amount | Purpose | Status |')
        lines.append('|------|------------|-------:|---------|--------|')
        for _, row in grants_received.iterrows():
            lines.append(
                f'| {fmt_val(row.get("year"))} '
                f'| {fmt_val(row.get("grantor_ein"))} '
                f'| {fmt_money(row.get("amount"))} '
                f'| {fmt_val(row.get("purpose"))} '
                f'| {fmt_val(row.get("status"))} |'
            )

    lines.append('\n---')

    # Political Contributions
    lines.append('\n## Political Contributions')
    political = data['political_contributions']
    if political.empty:
        lines.append('\n*No political contributions on record.*')
    else:
        lines.append('\n| Year | Recipient | EIN | City, State | Amount Paid | Contrib Received |')
        lines.append('|------|-----------|-----|------------|------------:|-----------------:|')
        for _, row in political.iterrows():
            pc_city = fmt_val(row.get('city'))
            pc_state = fmt_val(row.get('state'))
            location = f'{pc_city}, {pc_state}' if pc_city != '-' else pc_state
            lines.append(
                f'| {fmt_val(row.get("year"))} '
                f'| {fmt_val(row.get("recipient_name"))} '
                f'| {fmt_val(row.get("recipient_ein"))} '
                f'| {location} '
                f'| {fmt_money(row.get("amount_paid"))} '
                f'| {fmt_money(row.get("contributions_received"))} |'
            )

    lines.append('\n---')
    lines.append('\n*Report generated by TPC Pipeline | Data source: IRS Form 990 e-file returns*')

    return '\n'.join(lines)


def generate_markdown_report(ein, output_dir='.'):
    data = gather_report_data(ein)
    if data is None:
        print(f"No data found for EIN {ein}")
        return None

    md_content = build_markdown(data)

    org_name = (data['profile'].get('org_name1') or 'unknown').replace(' ', '_').replace('/', '_')[:40]
    filename = f'research_{ein}_{org_name}.md'
    output_path = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(md_content)

    print(f"Markdown report saved: {output_path}")
    return output_path


if __name__ == '__main__':
    import sys
    ein = sys.argv[1] if len(sys.argv) > 1 else '020489703'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else './reports'
    generate_markdown_report(ein, output_dir)
