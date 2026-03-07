"""Generate a high-level summary PDF of all researched organizations."""

import json
import sys
import os
import pandas as pd
from sqlalchemy import create_engine, text
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable
)
from datetime import date

DB_HOST = 'localhost'
DB_PORT = 5430
DB_NAME = 'cerebro_tpc'
DB_USER = os.environ.get('USER', 'postgres')
ENGINE_URL = f'postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


def fmt_money(val):
    if not val or val == '' or val == 'None' or val == 'nan':
        return '-'
    try:
        num = float(val)
        if num >= 1_000_000:
            return f'${num/1_000_000:.1f}M'
        elif num >= 1_000:
            return f'${num/1_000:.0f}K'
        return f'${num:,.0f}'
    except (ValueError, TypeError):
        return str(val)


def build_summary_pdf(data, output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('Title2', parent=styles['Title'], fontSize=18, spaceAfter=4))
    styles.add(ParagraphStyle('SmallText', parent=styles['Normal'], fontSize=7, textColor=colors.grey))
    styles.add(ParagraphStyle('CellText', parent=styles['Normal'], fontSize=7))
    styles.add(ParagraphStyle('SectionHead', parent=styles['Heading2'], fontSize=12, spaceAfter=6, spaceBefore=10))

    elements = []

    # Title page info
    elements.append(Paragraph('Organization Research Summary', styles['Title2']))
    elements.append(Paragraph(f'Report Generated: {date.today().isoformat()} | {len(data)} Organizations', styles['SmallText']))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceAfter=10))

    def safe_float(val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    # Sort by revenue descending
    data.sort(key=lambda r: -safe_float(r.get('revenue')))

    # Summary statistics
    total_revenue = sum(safe_float(r.get('revenue')) for r in data)
    total_assets = sum(safe_float(r.get('assets_eoy')) for r in data)
    total_board = sum(r.get('board_count', 0) for r in data)
    total_grants_given = sum(r.get('grants_given', 0) for r in data)
    total_grants_recv = sum(r.get('grants_received', 0) for r in data)
    total_political = sum(r.get('political', 0) for r in data)
    states = set(r.get('state', '') for r in data if r.get('state'))

    stats_data = [
        ['Metric', 'Value'],
        ['Total Organizations', str(len(data))],
        ['States Represented', str(len(states))],
        ['Combined Latest Revenue', fmt_money(str(total_revenue))],
        ['Combined Latest Assets', fmt_money(str(total_assets))],
        ['Total Board Members', f'{total_board:,}'],
        ['Total Grants Given', f'{total_grants_given:,}'],
        ['Total Grants Received', f'{total_grants_recv:,}'],
        ['Total Political Contributions', f'{total_political:,}'],
    ]
    stats_table = Table(stats_data, colWidths=[2.5*inch, 2.5*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 16))

    # Main table — all organizations
    elements.append(Paragraph('All Organizations (sorted by revenue)', styles['SectionHead']))

    header = ['#', 'EIN', 'Organization', 'State', 'Status', 'Year',
              'Revenue', 'Expenses', 'Assets', 'Board', 'Grants Given', 'Grants Recv', 'Political']
    rows = [header]

    for i, r in enumerate(data, 1):
        rows.append([
            str(i),
            r['ein'],
            Paragraph(r.get('name', '')[:50], styles['CellText']),
            r.get('state', ''),
            Paragraph(r.get('status', ''), styles['CellText']),
            r.get('latest_year', ''),
            fmt_money(r.get('revenue')),
            fmt_money(r.get('expenses')),
            fmt_money(r.get('assets_eoy')),
            str(r.get('board_count', 0)),
            str(r.get('grants_given', 0)),
            str(r.get('grants_received', 0)),
            str(r.get('political', 0)),
        ])

    col_widths = [0.3*inch, 0.7*inch, 2.2*inch, 0.4*inch, 0.6*inch, 0.4*inch,
                  0.8*inch, 0.8*inch, 0.8*inch, 0.5*inch, 0.7*inch, 0.7*inch, 0.6*inch]

    main_table = Table(rows, colWidths=col_widths, repeatRows=1)
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'CENTER'),
        ('ALIGN', (6, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(main_table)

    # --- Shared Funders ---
    engine = create_engine(ENGINE_URL)
    eins = [r['ein'] for r in data]
    ein_name_map = {r['ein']: r.get('name', '') for r in data}

    if eins:
        placeholders = ','.join(f"'{e}'" for e in eins)
        shared_funders_df = pd.read_sql(text(f'''
            SELECT g.grantor_ein, p.org_name1 as grantor_name, p.state as grantor_state,
                   COUNT(DISTINCT g.grantee_ein) as num_orgs_funded,
                   SUM(CAST(NULLIF(g.amount, '') AS NUMERIC)) as total_amount
            FROM grants g
            LEFT JOIN (SELECT DISTINCT ON (ein) ein, org_name1, state FROM profiles ORDER BY ein, year DESC) p
                ON g.grantor_ein = p.ein
            WHERE g.grantee_ein IN ({placeholders})
            GROUP BY g.grantor_ein, p.org_name1, p.state
            HAVING COUNT(DISTINCT g.grantee_ein) >= 2
            ORDER BY num_orgs_funded DESC, total_amount DESC
        '''), engine)

        if not shared_funders_df.empty:
            elements.append(Spacer(1, 16))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
            elements.append(Paragraph(
                f'Shared Funders — Organizations that fund 2+ orgs in this research set',
                styles['SectionHead']
            ))

            sf_header = ['#', 'Funder', 'EIN', 'State', '# Orgs Funded', 'Total Amount']
            sf_rows = [sf_header]
            for i, (_, row) in enumerate(shared_funders_df.iterrows(), 1):
                fname = str(row['grantor_name'] or row['grantor_ein'])[:45]
                amt = fmt_money(str(row['total_amount'])) if pd.notna(row['total_amount']) else '-'
                sf_rows.append([
                    str(i),
                    Paragraph(fname, styles['CellText']),
                    str(row['grantor_ein']),
                    str(row.get('grantor_state') or ''),
                    str(int(row['num_orgs_funded'])),
                    amt,
                ])

            sf_widths = [0.3*inch, 2.8*inch, 0.8*inch, 0.4*inch, 0.8*inch, 1.0*inch]
            sf_table = Table(sf_rows, colWidths=sf_widths, repeatRows=1)
            sf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (4, -1), 'CENTER'),
                ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(sf_table)

    # Query all grants given by these orgs
    if eins:
        placeholders = ','.join(f"'{e}'" for e in eins)
        grants_given_df = pd.read_sql(text(
            f"SELECT grantor_ein, grantee_name, grantee_ein, amount, purpose, year "
            f"FROM grants WHERE grantor_ein IN ({placeholders}) "
            f"ORDER BY grantor_ein, year DESC, amount DESC"
        ), engine)

        if not grants_given_df.empty:
            elements.append(Spacer(1, 16))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
            elements.append(Paragraph('Grants Given (All Organizations)', styles['SectionHead']))

            gg_header = ['Grantor', 'Year', 'Grantee', 'Grantee EIN', 'Amount', 'Purpose']
            gg_rows = [gg_header]
            for _, row in grants_given_df.head(500).iterrows():
                grantor_name = ein_name_map.get(row['grantor_ein'], row['grantor_ein'])
                gg_rows.append([
                    Paragraph(str(grantor_name)[:35], styles['CellText']),
                    str(row.get('year', '')),
                    Paragraph(str(row.get('grantee_name', ''))[:35], styles['CellText']),
                    str(row.get('grantee_ein', '')),
                    fmt_money(row.get('amount')),
                    Paragraph(str(row.get('purpose', ''))[:50], styles['CellText']),
                ])

            gg_widths = [1.8*inch, 0.4*inch, 1.8*inch, 0.8*inch, 0.8*inch, 3.0*inch]
            gg_table = Table(gg_rows, colWidths=gg_widths, repeatRows=1)
            gg_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(gg_table)
            if len(grants_given_df) > 500:
                elements.append(Paragraph(
                    f'<i>Showing first 500 of {len(grants_given_df):,} grants given</i>',
                    styles['SmallText']
                ))

        # Grants Received
        grants_recv_df = pd.read_sql(text(
            f"SELECT grantee_ein, grantor_ein, grantee_name, amount, purpose, year "
            f"FROM grants WHERE grantee_ein IN ({placeholders}) "
            f"ORDER BY grantee_ein, year DESC, amount DESC"
        ), engine)

        if not grants_recv_df.empty:
            elements.append(Spacer(1, 16))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
            elements.append(Paragraph('Grants Received (All Organizations)', styles['SectionHead']))

            gr_header = ['Grantee', 'Year', 'Grantor EIN', 'Amount', 'Purpose']
            gr_rows = [gr_header]
            for _, row in grants_recv_df.head(500).iterrows():
                grantee_name = ein_name_map.get(row['grantee_ein'], row['grantee_ein'])
                gr_rows.append([
                    Paragraph(str(grantee_name)[:40], styles['CellText']),
                    str(row.get('year', '')),
                    str(row.get('grantor_ein', '')),
                    fmt_money(row.get('amount')),
                    Paragraph(str(row.get('purpose', ''))[:60], styles['CellText']),
                ])

            gr_widths = [2.0*inch, 0.4*inch, 0.8*inch, 0.8*inch, 4.6*inch]
            gr_table = Table(gr_rows, colWidths=gr_widths, repeatRows=1)
            gr_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(gr_table)
            if len(grants_recv_df) > 500:
                elements.append(Paragraph(
                    f'<i>Showing first 500 of {len(grants_recv_df):,} grants received</i>',
                    styles['SmallText']
                ))

        # Political Contributions
        political_df = pd.read_sql(text(
            f"SELECT filer_ein, recipient_name, recipient_ein, city, state, "
            f"amount_paid, contributions_received, year "
            f"FROM political_contributions WHERE filer_ein IN ({placeholders}) "
            f"ORDER BY filer_ein, year DESC"
        ), engine)

        if not political_df.empty:
            elements.append(Spacer(1, 16))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
            elements.append(Paragraph('Political Contributions (All Organizations)', styles['SectionHead']))

            pc_header = ['Filer', 'Year', 'Recipient', 'Recipient EIN', 'City, State', 'Amt Paid', 'Contrib Recv']
            pc_rows = [pc_header]
            for _, row in political_df.iterrows():
                filer_name = ein_name_map.get(row['filer_ein'], row['filer_ein'])
                pc_city = str(row.get('city', '') or '')
                pc_state = str(row.get('state', '') or '')
                location = f'{pc_city}, {pc_state}' if pc_city else pc_state
                pc_rows.append([
                    Paragraph(str(filer_name)[:30], styles['CellText']),
                    str(row.get('year', '')),
                    Paragraph(str(row.get('recipient_name', ''))[:30], styles['CellText']),
                    str(row.get('recipient_ein', '')),
                    location,
                    fmt_money(row.get('amount_paid')),
                    fmt_money(row.get('contributions_received')),
                ])

            pc_widths = [1.6*inch, 0.4*inch, 1.6*inch, 0.8*inch, 1.2*inch, 0.8*inch, 0.8*inch]
            pc_table = Table(pc_rows, colWidths=pc_widths, repeatRows=1)
            pc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (5, 1), (6, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(pc_table)

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceAfter=4))
    elements.append(Paragraph(
        'Report generated by TPC Pipeline | Data source: IRS Form 990 e-file returns',
        styles['SmallText']
    ))

    doc.build(elements)
    return output_path


if __name__ == '__main__':
    data_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/summary_data.json'
    output_path = sys.argv[2] if len(sys.argv) > 2 else './reports/SUMMARY_all_organizations.pdf'

    with open(data_path) as f:
        data = json.load(f)

    build_summary_pdf(data, output_path)
    print(f"Summary PDF saved: {output_path}")
