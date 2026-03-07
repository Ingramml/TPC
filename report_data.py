"""
Data gathering layer for TPC organization reports.

Queries the cerebro_tpc database and returns structured data for a given EIN,
ready to be rendered by report_pdf.py.

Usage:
    from report_data import gather_report_data
    data = gather_report_data('020489703')
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os
from datetime import date

DB_HOST = 'localhost'
DB_PORT = 5430
DB_NAME = 'cerebro_tpc'
DB_USER = os.environ.get('USER', 'postgres')
ENGINE_URL = f'postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Adjacent states for confidence scoring
ADJACENT_STATES = {
    'AL': ['FL', 'GA', 'MS', 'TN'],
    'AK': [],
    'AZ': ['CA', 'CO', 'NM', 'NV', 'UT'],
    'AR': ['LA', 'MO', 'MS', 'OK', 'TN', 'TX'],
    'CA': ['AZ', 'NV', 'OR'],
    'CO': ['AZ', 'KS', 'NE', 'NM', 'OK', 'UT', 'WY'],
    'CT': ['MA', 'NY', 'RI'],
    'DE': ['MD', 'NJ', 'PA'],
    'FL': ['AL', 'GA'],
    'GA': ['AL', 'FL', 'NC', 'SC', 'TN'],
    'HI': [],
    'ID': ['MT', 'NV', 'OR', 'UT', 'WA', 'WY'],
    'IL': ['IN', 'IA', 'KY', 'MO', 'WI'],
    'IN': ['IL', 'KY', 'MI', 'OH'],
    'IA': ['IL', 'MN', 'MO', 'NE', 'SD', 'WI'],
    'KS': ['CO', 'MO', 'NE', 'OK'],
    'KY': ['IL', 'IN', 'MO', 'OH', 'TN', 'VA', 'WV'],
    'LA': ['AR', 'MS', 'TX'],
    'ME': ['NH'],
    'MD': ['DE', 'PA', 'VA', 'WV', 'DC'],
    'MA': ['CT', 'NH', 'NY', 'RI', 'VT'],
    'MI': ['IN', 'OH', 'WI'],
    'MN': ['IA', 'ND', 'SD', 'WI'],
    'MS': ['AL', 'AR', 'LA', 'TN'],
    'MO': ['AR', 'IL', 'IA', 'KS', 'KY', 'NE', 'OK', 'TN'],
    'MT': ['ID', 'ND', 'SD', 'WY'],
    'NE': ['CO', 'IA', 'KS', 'MO', 'SD', 'WY'],
    'NV': ['AZ', 'CA', 'ID', 'OR', 'UT'],
    'NH': ['ME', 'VT', 'MA', 'CT', 'RI', 'NY'],
    'NJ': ['DE', 'NY', 'PA'],
    'NM': ['AZ', 'CO', 'OK', 'TX', 'UT'],
    'NY': ['CT', 'MA', 'NJ', 'PA', 'VT'],
    'NC': ['GA', 'SC', 'TN', 'VA'],
    'ND': ['MN', 'MT', 'SD'],
    'OH': ['IN', 'KY', 'MI', 'PA', 'WV'],
    'OK': ['AR', 'CO', 'KS', 'MO', 'NM', 'TX'],
    'OR': ['CA', 'ID', 'NV', 'WA'],
    'PA': ['DE', 'MD', 'NJ', 'NY', 'OH', 'WV'],
    'RI': ['CT', 'MA'],
    'SC': ['GA', 'NC'],
    'SD': ['IA', 'MN', 'MT', 'ND', 'NE', 'WY'],
    'TN': ['AL', 'AR', 'GA', 'KY', 'MO', 'MS', 'NC', 'VA'],
    'TX': ['AR', 'LA', 'NM', 'OK'],
    'UT': ['AZ', 'CO', 'ID', 'NM', 'NV', 'WY'],
    'VT': ['MA', 'NH', 'NY'],
    'VA': ['KY', 'MD', 'NC', 'TN', 'WV', 'DC'],
    'WA': ['ID', 'OR'],
    'WV': ['KY', 'MD', 'OH', 'PA', 'VA'],
    'WI': ['IA', 'IL', 'MI', 'MN'],
    'WY': ['CO', 'ID', 'MT', 'NE', 'SD', 'UT'],
    'DC': ['MD', 'VA'],
}


def get_confidence(org_state, other_state):
    if not org_state or not other_state:
        return 'LOW'
    org_state = org_state.strip().upper()
    other_state = other_state.strip().upper()
    if org_state == other_state:
        return 'HIGH'
    if other_state in ADJACENT_STATES.get(org_state, []):
        return 'MEDIUM'
    return 'LOW'


def gather_report_data(ein):
    engine = create_engine(ENGINE_URL)

    # Get profile (most recent year)
    profile_df = pd.read_sql(text(
        "SELECT * FROM profiles WHERE ein = :ein ORDER BY year DESC LIMIT 1"
    ), engine, params={'ein': ein})

    if profile_df.empty:
        return None

    profile = profile_df.iloc[0].to_dict()
    org_state = (profile.get('state') or '').strip().upper()

    # Financial summary (all years, descending)
    financials_df = pd.read_sql(text(
        "SELECT * FROM income_expenses WHERE ein = :ein ORDER BY year DESC"
    ), engine, params={'ein': ein})

    # Board members (most recent year)
    latest_year_result = pd.read_sql(text(
        "SELECT MAX(year) as max_year FROM boardmembers WHERE ein = :ein"
    ), engine, params={'ein': ein})
    latest_board_year = latest_year_result.iloc[0]['max_year'] if not latest_year_result.empty else None

    board_df = pd.DataFrame()
    if latest_board_year:
        board_df = pd.read_sql(text(
            "SELECT * FROM boardmembers WHERE ein = :ein AND year = :year ORDER BY name"
        ), engine, params={'ein': ein, 'year': latest_board_year})

    # Board member affiliations
    affiliations = {}
    if not board_df.empty:
        for _, member in board_df.iterrows():
            name = member['name']
            if not name or name.strip() == '':
                continue
            # Find this name at OTHER organizations
            affs_df = pd.read_sql(text(
                "SELECT b.ein, b.name, b.title, b.year, p.org_name1, p.state "
                "FROM boardmembers b "
                "LEFT JOIN profiles p ON b.ein = p.ein AND b.year = p.year "
                "WHERE b.name = :name AND b.ein <> :ein "
                "ORDER BY b.year DESC, p.org_name1"
            ), engine, params={'name': name, 'ein': ein})

            aff_list = []
            for _, aff in affs_df.iterrows():
                aff_state = (aff.get('state') or '').strip().upper()
                confidence = get_confidence(org_state, aff_state)
                aff_list.append({
                    'confidence': confidence,
                    'ein': aff['ein'],
                    'org_name': aff.get('org_name1', ''),
                    'state': aff_state,
                    'title': aff.get('title', ''),
                    'year': aff.get('year', ''),
                })
            # Sort: HIGH first, then MEDIUM, then LOW
            conf_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
            aff_list.sort(key=lambda x: (conf_order.get(x['confidence'], 3), x['year']), reverse=False)
            aff_list.sort(key=lambda x: conf_order.get(x['confidence'], 3))
            affiliations[name] = {
                'title': member.get('title', ''),
                'affiliations': aff_list,
            }

    # Grants given (this org as grantor)
    grants_given_df = pd.read_sql(text(
        "SELECT * FROM grants WHERE grantor_ein = :ein ORDER BY year DESC, grantee_name"
    ), engine, params={'ein': ein})

    # Grants received (this org as grantee) — enriched with grantor name
    grants_received_df = pd.read_sql(text(
        "SELECT g.*, p.org_name1 as grantor_name, p.state as grantor_state "
        "FROM grants g "
        "LEFT JOIN (SELECT DISTINCT ON (ein) ein, org_name1, state FROM profiles ORDER BY ein, year DESC) p "
        "ON g.grantor_ein = p.ein "
        "WHERE g.grantee_ein = :ein ORDER BY g.year DESC, g.amount DESC"
    ), engine, params={'ein': ein})

    # Political contributions
    political_df = pd.read_sql(text(
        "SELECT * FROM political_contributions WHERE filer_ein = :ein ORDER BY year DESC"
    ), engine, params={'ein': ein})

    # Compute revenue trend
    revenue_trend = []
    if len(financials_df) >= 2:
        for i in range(len(financials_df) - 1):
            curr = financials_df.iloc[i]
            prev = financials_df.iloc[i + 1]
            try:
                curr_rev = float(curr.get('revenue', 0) or 0)
                prev_rev = float(prev.get('revenue', 0) or 0)
                if prev_rev != 0:
                    pct = ((curr_rev - prev_rev) / abs(prev_rev)) * 100
                    revenue_trend.append({
                        'year': curr.get('year', ''),
                        'prev_year': prev.get('year', ''),
                        'change_pct': round(pct, 1),
                        'curr_revenue': curr_rev,
                        'prev_revenue': prev_rev,
                    })
            except (ValueError, TypeError):
                pass

    # Compensation flags — board members with comp > 0
    comp_flags = []
    if not board_df.empty:
        for _, member in board_df.iterrows():
            try:
                comp = float(member.get('compensation_from_org', 0) or 0)
                if comp > 0:
                    comp_flags.append({
                        'name': member.get('name', ''),
                        'title': member.get('title', ''),
                        'compensation': comp,
                    })
            except (ValueError, TypeError):
                pass

    # Asset-to-revenue ratio (latest year)
    asset_revenue_ratio = None
    if not financials_df.empty:
        try:
            latest = financials_df.iloc[0]
            rev = float(latest.get('revenue', 0) or 0)
            assets = float(latest.get('total_assets_eoy', 0) or 0)
            if rev > 0:
                asset_revenue_ratio = round(assets / rev, 1)
        except (ValueError, TypeError):
            pass

    return {
        'ein': ein,
        'report_date': date.today().isoformat(),
        'profile': profile,
        'financials': financials_df,
        'revenue_trend': revenue_trend,
        'asset_revenue_ratio': asset_revenue_ratio,
        'comp_flags': comp_flags,
        'board_year': latest_board_year,
        'board': board_df,
        'affiliations': affiliations,
        'grants_given': grants_given_df,
        'grants_received': grants_received_df,
        'political_contributions': political_df,
    }


if __name__ == '__main__':
    import sys
    import json

    ein = sys.argv[1] if len(sys.argv) > 1 else '020489703'
    data = gather_report_data(ein)

    if data is None:
        print(f"No data found for EIN {ein}")
        sys.exit(1)

    print(f"Profile: {data['profile'].get('org_name1', 'N/A')}")
    print(f"Financial years: {len(data['financials'])}")
    print(f"Board members ({data['board_year']}): {len(data['board'])}")
    print(f"Board affiliations found for: {len([k for k, v in data['affiliations'].items() if v['affiliations']])}")
    print(f"Grants given: {len(data['grants_given'])}")
    print(f"Grants received: {len(data['grants_received'])}")
    print(f"Political contributions: {len(data['political_contributions'])}")
