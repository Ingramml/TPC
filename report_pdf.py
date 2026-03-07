"""
PDF report generator for TPC organization reports.

Uses reportlab to create professional PDF reports matching the sample_report.md format.

Usage:
    python3 report_pdf.py 020489703                    # single EIN
    python3 report_pdf.py 020489703 061234567          # multiple EINs
    python3 report_pdf.py --output-dir ./reports 020489703  # custom output dir
"""

import sys
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, KeepTogether
)

from report_data import gather_report_data


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
    if val is None or val == '' or val == 'None' or val == 'nan':
        return default
    return str(val).strip()


def build_pdf(data, output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'ReportTitle', parent=styles['Title'], fontSize=16, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        'SectionHeader', parent=styles['Heading2'], fontSize=13,
        spaceAfter=6, spaceBefore=12, textColor=colors.HexColor('#1a1a1a')
    ))
    styles.add(ParagraphStyle(
        'SubHeader', parent=styles['Heading3'], fontSize=11,
        spaceAfter=4, spaceBefore=8
    ))
    styles.add(ParagraphStyle(
        'SmallText', parent=styles['Normal'], fontSize=8,
        textColor=colors.grey
    ))
    styles.add(ParagraphStyle(
        'ConfNote', parent=styles['Normal'], fontSize=8,
        textColor=colors.HexColor('#555555'), spaceAfter=6
    ))

    elements = []
    profile = data['profile']
    ein = data['ein']

    # Title
    org_name = fmt_val(profile.get('org_name1'), 'Unknown Organization')
    elements.append(Paragraph(f'Organization Report: EIN {ein}', styles['ReportTitle']))
    elements.append(Paragraph(f'Report Generated: {data["report_date"]}', styles['SmallText']))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceAfter=10))

    # --- Organization Profile ---
    elements.append(Paragraph('Organization Profile', styles['SectionHeader']))

    name2 = fmt_val(profile.get('org_name2'))
    display_name = org_name
    if name2 != '-':
        display_name = f'{org_name} / {name2}'

    addr_parts = [fmt_val(profile.get('address_1'))]
    addr2 = fmt_val(profile.get('address_2'))
    if addr2 != '-':
        addr_parts.append(addr2)
    address = ', '.join(a for a in addr_parts if a != '-')

    city = fmt_val(profile.get('city'))
    state = fmt_val(profile.get('state'))
    zipcode = fmt_val(profile.get('zipcode'))
    city_state_zip = f'{city}, {state} {zipcode}'

    profile_data = [
        ['Field', 'Value'],
        ['EIN', ein],
        ['Organization Name', display_name],
        ['Address', address],
        ['City, State ZIP', city_state_zip],
        ['Website', fmt_val(profile.get('website'))],
        ['Tax-Exempt Status', fmt_val(profile.get('status'))],
        ['Mission', Paragraph(fmt_val(profile.get('mission')), styles['Normal'])],
    ]

    profile_table = Table(profile_data, colWidths=[1.8 * inch, 5.0 * inch])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(profile_table)
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

    # --- Financial Summary ---
    elements.append(Paragraph('Financial Summary', styles['SectionHeader']))

    fin_df = data['financials']
    if fin_df.empty:
        elements.append(Paragraph('<i>No financial data on record.</i>', styles['Normal']))
    else:
        fin_header = ['Year', 'Revenue', 'Expenses', 'Assets (BOY)', 'Assets (EOY)', 'Return Type']
        fin_rows = [fin_header]
        for _, row in fin_df.iterrows():
            fin_rows.append([
                fmt_val(row.get('year')),
                fmt_money(row.get('revenue')),
                fmt_money(row.get('expenses')),
                fmt_money(row.get('total_assets_boy')),
                fmt_money(row.get('total_assets_eoy')),
                fmt_val(row.get('return_type')),
            ])

        fin_table = Table(fin_rows, colWidths=[0.6*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.0*inch],
                         repeatRows=1)
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 1), (-2, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(fin_table)

    # Financial Insights (inline after financials)
    insights = []
    revenue_trend = data.get('revenue_trend', [])
    if revenue_trend:
        for t in revenue_trend:
            direction = 'increased' if t['change_pct'] > 0 else 'decreased'
            insights.append(
                f"Revenue {direction} <b>{abs(t['change_pct'])}%</b> "
                f"from {t['prev_year']} to {t['year']} "
                f"({fmt_money(str(t['prev_revenue']))} → {fmt_money(str(t['curr_revenue']))})"
            )

    ratio = data.get('asset_revenue_ratio')
    if ratio is not None:
        if ratio > 5:
            insights.append(f"Asset-to-Revenue ratio: <b>{ratio}x</b> — large endowment relative to operations")
        elif ratio > 2:
            insights.append(f"Asset-to-Revenue ratio: <b>{ratio}x</b>")

    # Return type context
    if not fin_df.empty:
        rtype = fmt_val(fin_df.iloc[0].get('return_type'))
        if rtype == '990PF':
            insights.append("Files <b>990-PF</b> (Private Foundation) — subject to 5% minimum payout requirement")
        elif rtype == '990EZ':
            insights.append("Files <b>990-EZ</b> (Short Form) — gross receipts &lt; $200K and assets &lt; $500K")

    comp_flags = data.get('comp_flags', [])
    if comp_flags:
        for cf in comp_flags:
            insights.append(
                f"<b>{cf['name']}</b> ({cf['title']}) receives "
                f"<b>{fmt_money(str(cf['compensation']))}</b> in compensation"
            )

    if insights:
        elements.append(Spacer(1, 6))
        for insight in insights:
            elements.append(Paragraph(f"• {insight}", styles['ConfNote']))

    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

    # --- Board of Directors ---
    board_year = data.get('board_year', '')
    elements.append(Paragraph(f'Board of Directors ({board_year})', styles['SectionHeader']))

    board_df = data['board']
    if board_df.empty:
        elements.append(Paragraph('<i>No board member data on record.</i>', styles['Normal']))
    else:
        board_header = ['Name', 'Title', 'Hrs/Wk', 'Comp (Org)', 'Comp (Related)', 'Other Comp']
        board_rows = [board_header]
        for _, row in board_df.iterrows():
            board_rows.append([
                Paragraph(fmt_val(row.get('name')), styles['Normal']),
                Paragraph(fmt_val(row.get('title')), styles['Normal']),
                fmt_val(row.get('averagehousperweek'), '0'),
                fmt_money(row.get('compensation_from_org')),
                fmt_money(row.get('compensation_from_related_org')),
                fmt_money(row.get('othercompens')),
            ])

        board_table = Table(board_rows, colWidths=[1.8*inch, 1.3*inch, 0.6*inch, 1.0*inch, 1.0*inch, 1.0*inch],
                            repeatRows=1)
        board_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(board_table)

    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

    # --- Board Member Affiliations ---
    elements.append(Paragraph('Board Member Affiliations', styles['SectionHeader']))
    org_state = fmt_val(profile.get('state'))
    adjacent = ', '.join(sorted(
        __import__('report_data').ADJACENT_STATES.get(org_state.upper(), [])
    ))
    elements.append(Paragraph(
        f'Confidence based on geographic proximity to filing org state ({org_state}):<br/>'
        f'<b>HIGH</b> = Same state ({org_state}) | '
        f'<b>MEDIUM</b> = Adjacent state ({adjacent}) | '
        f'<b>LOW</b> = Different state',
        styles['ConfNote']
    ))

    conf_colors = {
        'HIGH': colors.HexColor('#27ae60'),
        'MEDIUM': colors.HexColor('#f39c12'),
        'LOW': colors.HexColor('#95a5a6'),
    }

    # Separate HIGH/MEDIUM from LOW affiliations
    low_confidence_data = []  # collect for addendum

    for member_name, member_data in data['affiliations'].items():
        title = member_data['title']
        affs = member_data['affiliations']

        high_med = [a for a in affs if a['confidence'] in ('HIGH', 'MEDIUM')]
        low = [a for a in affs if a['confidence'] == 'LOW']

        if low:
            low_confidence_data.append((member_name, title, low))

        member_elements = []
        member_elements.append(Paragraph(
            f'<b>{member_name}</b> — {fmt_val(title)}', styles['SubHeader']
        ))

        if not high_med:
            if low:
                member_elements.append(Paragraph(
                    '<i>No HIGH/MEDIUM confidence affiliations. See Addendum for LOW confidence matches.</i>', styles['Normal']
                ))
            else:
                member_elements.append(Paragraph(
                    '<i>No other organizational affiliations found.</i>', styles['Normal']
                ))
        else:
            aff_header = ['Conf.', 'EIN', 'Organization', 'State', 'Title', 'Year']
            aff_rows = [aff_header]
            row_confidences = []
            for aff in high_med:
                aff_rows.append([
                    aff['confidence'],
                    fmt_val(aff['ein']),
                    Paragraph(fmt_val(aff['org_name']), styles['Normal']),
                    fmt_val(aff['state']),
                    Paragraph(fmt_val(aff['title']), styles['Normal']),
                    fmt_val(aff['year']),
                ])
                row_confidences.append(aff['confidence'])

            aff_table = Table(aff_rows, colWidths=[0.5*inch, 0.9*inch, 2.4*inch, 0.5*inch, 1.6*inch, 0.5*inch])
            style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                ('ALIGN', (5, 0), (5, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]
            for i, conf in enumerate(row_confidences):
                row_idx = i + 1
                style_cmds.append(('TEXTCOLOR', (0, row_idx), (0, row_idx), conf_colors.get(conf, colors.grey)))
                style_cmds.append(('FONTNAME', (0, row_idx), (0, row_idx), 'Helvetica-Bold'))

            aff_table.setStyle(TableStyle(style_cmds))
            member_elements.append(aff_table)
            if low:
                member_elements.append(Paragraph(
                    f'<i>+ {len(low)} LOW confidence match(es) in Addendum</i>', styles['SmallText']
                ))

        member_elements.append(Spacer(1, 6))
        elements.append(KeepTogether(member_elements))

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

    # --- Grants Given ---
    elements.append(Paragraph('Grants Given', styles['SectionHeader']))
    grants_given = data['grants_given']
    if grants_given.empty:
        elements.append(Paragraph('<i>No grants given on record.</i>', styles['Normal']))
    else:
        g_header = ['Year', 'Grantee', 'EIN', 'Amount', 'Purpose', 'Status']
        g_rows = [g_header]
        total_given = 0.0
        grantee_totals = {}
        for _, row in grants_given.iterrows():
            amt_raw = row.get('amount')
            try:
                amt_num = float(amt_raw) if amt_raw and str(amt_raw) not in ('', 'None', 'nan') else 0
            except (ValueError, TypeError):
                amt_num = 0
            total_given += amt_num
            gname = fmt_val(row.get('grantee_name'))
            grantee_totals[gname] = grantee_totals.get(gname, 0) + amt_num
            g_rows.append([
                fmt_val(row.get('year')),
                Paragraph(gname, styles['Normal']),
                fmt_val(row.get('grantee_ein')),
                fmt_money(row.get('amount')),
                Paragraph(fmt_val(row.get('purpose')), styles['Normal']),
                fmt_val(row.get('status')),
            ])

        g_table = Table(g_rows, colWidths=[0.5*inch, 1.8*inch, 0.9*inch, 0.9*inch, 2.0*inch, 0.7*inch],
                        repeatRows=1)
        g_table.setStyle(TableStyle([
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
        elements.append(g_table)

        # Aggregation summary
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            f'<b>Total Grants Given: {fmt_money(str(total_given))}</b> across '
            f'<b>{len(grants_given)}</b> grants to <b>{len(grantee_totals)}</b> unique grantees',
            styles['ConfNote']
        ))
        # Top grantees by total
        top_grantees = sorted(grantee_totals.items(), key=lambda x: -x[1])[:10]
        if len(top_grantees) > 1:
            agg_header = ['Grantee', 'Total Amount', '# Grants']
            agg_rows = [agg_header]
            # Count grants per grantee
            from collections import Counter
            grantee_counts = Counter(fmt_val(r.get('grantee_name')) for _, r in grants_given.iterrows())
            for gname, gtotal in top_grantees:
                agg_rows.append([
                    Paragraph(gname, styles['Normal']),
                    fmt_money(str(gtotal)),
                    str(grantee_counts.get(gname, 0)),
                ])
            agg_table = Table(agg_rows, colWidths=[3.5*inch, 1.2*inch, 0.8*inch], repeatRows=1)
            agg_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (1, 1), (2, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(Paragraph('Top Grantees by Total Amount', styles['SubHeader']))
            elements.append(agg_table)

    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

    # --- Funding Sources (Grants Received) ---
    elements.append(Paragraph('Funding Sources (Grants Received)', styles['SectionHeader']))
    grants_received = data['grants_received']
    if grants_received.empty:
        elements.append(Paragraph('<i>No grants received on record.</i>', styles['Normal']))
    else:
        gr_header = ['Year', 'Funder', 'Funder EIN', 'State', 'Amount', 'Purpose']
        gr_rows = [gr_header]
        total_received = 0.0
        funder_totals = {}
        for _, row in grants_received.iterrows():
            amt_raw = row.get('amount')
            try:
                amt_num = float(amt_raw) if amt_raw and str(amt_raw) not in ('', 'None', 'nan') else 0
            except (ValueError, TypeError):
                amt_num = 0
            total_received += amt_num
            grantor_name = fmt_val(row.get('grantor_name'), fmt_val(row.get('grantor_ein')))
            funder_totals[grantor_name] = funder_totals.get(grantor_name, 0) + amt_num
            gr_rows.append([
                fmt_val(row.get('year')),
                Paragraph(grantor_name[:45], styles['Normal']),
                fmt_val(row.get('grantor_ein')),
                fmt_val(row.get('grantor_state')),
                fmt_money(row.get('amount')),
                Paragraph(fmt_val(row.get('purpose'))[:50], styles['Normal']),
            ])

        gr_table = Table(gr_rows, colWidths=[0.4*inch, 2.0*inch, 0.8*inch, 0.4*inch, 0.8*inch, 2.4*inch],
                         repeatRows=1)
        gr_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(gr_table)

        # Aggregation summary
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            f'<b>Total Funding Received: {fmt_money(str(total_received))}</b> across '
            f'<b>{len(grants_received)}</b> grants from <b>{len(funder_totals)}</b> unique funders',
            styles['ConfNote']
        ))
        # Top funders by total
        top_funders = sorted(funder_totals.items(), key=lambda x: -x[1])[:10]
        if len(top_funders) > 1:
            from collections import Counter
            funder_counts = Counter(
                fmt_val(r.get('grantor_name'), fmt_val(r.get('grantor_ein')))
                for _, r in grants_received.iterrows()
            )
            fagg_header = ['Funder', 'Total Amount', '# Grants']
            fagg_rows = [fagg_header]
            for fname, ftotal in top_funders:
                fagg_rows.append([
                    Paragraph(fname[:50], styles['Normal']),
                    fmt_money(str(ftotal)),
                    str(funder_counts.get(fname, 0)),
                ])
            fagg_table = Table(fagg_rows, colWidths=[3.5*inch, 1.2*inch, 0.8*inch], repeatRows=1)
            fagg_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980b9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (1, 1), (2, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(Paragraph('Top Funders by Total Amount', styles['SubHeader']))
            elements.append(fagg_table)

    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

    # --- Political Contributions ---
    elements.append(Paragraph('Political Contributions', styles['SectionHeader']))
    political = data['political_contributions']
    if political.empty:
        elements.append(Paragraph('<i>No political contributions on record.</i>', styles['Normal']))
    else:
        pc_header = ['Year', 'Recipient', 'EIN', 'City, State', 'Amount Paid', 'Contrib Recv']
        pc_rows = [pc_header]
        for _, row in political.iterrows():
            pc_city = fmt_val(row.get('city'))
            pc_state = fmt_val(row.get('state'))
            location = f'{pc_city}, {pc_state}' if pc_city != '-' else pc_state
            pc_rows.append([
                fmt_val(row.get('year')),
                Paragraph(fmt_val(row.get('recipient_name')), styles['Normal']),
                fmt_val(row.get('recipient_ein')),
                location,
                fmt_money(row.get('amount_paid')),
                fmt_money(row.get('contributions_received')),
            ])

        pc_table = Table(pc_rows, colWidths=[0.5*inch, 1.8*inch, 0.9*inch, 1.2*inch, 0.9*inch, 0.9*inch],
                        repeatRows=1)
        pc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (4, 1), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(pc_table)

    # --- Addendum: LOW Confidence Affiliations ---
    if low_confidence_data:
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=6))
        elements.append(Paragraph('Addendum: LOW Confidence Affiliations', styles['SectionHeader']))
        elements.append(Paragraph(
            'The following name matches are from different states and may represent different '
            'individuals who share the same name. Listed for reference only.',
            styles['ConfNote']
        ))

        for member_name, title, low_affs in low_confidence_data:
            member_elements = []
            member_elements.append(Paragraph(
                f'<b>{member_name}</b> — {fmt_val(title)}', styles['SubHeader']
            ))

            aff_header = ['EIN', 'Organization', 'State', 'Title', 'Year']
            aff_rows = [aff_header]
            for aff in low_affs:
                aff_rows.append([
                    fmt_val(aff['ein']),
                    Paragraph(fmt_val(aff['org_name']), styles['Normal']),
                    fmt_val(aff['state']),
                    Paragraph(fmt_val(aff['title']), styles['Normal']),
                    fmt_val(aff['year']),
                ])

            aff_table = Table(aff_rows, colWidths=[0.9*inch, 2.6*inch, 0.5*inch, 1.6*inch, 0.5*inch],
                             repeatRows=1)
            aff_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7f8c8d')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('ALIGN', (4, 0), (4, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f5f5f5'), colors.HexColor('#ebebeb')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            member_elements.append(aff_table)
            member_elements.append(Spacer(1, 4))
            elements.append(KeepTogether(member_elements))

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceAfter=4))
    elements.append(Paragraph(
        'Report generated by TPC Pipeline | Data source: IRS Form 990 e-file returns',
        styles['SmallText']
    ))

    doc.build(elements)
    return output_path


def generate_report(ein, output_dir='.'):
    data = gather_report_data(ein)
    if data is None:
        print(f"No data found for EIN {ein}")
        return None

    org_name = (data['profile'].get('org_name1') or 'unknown').replace(' ', '_').replace('/', '_')[:40]
    filename = f'report_{ein}_{org_name}.pdf'
    output_path = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)
    build_pdf(data, output_path)
    print(f"Report saved: {output_path}")
    return output_path


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate TPC organization PDF reports')
    parser.add_argument('eins', nargs='+', help='One or more EIN numbers')
    parser.add_argument('--output-dir', default='.', help='Output directory for PDFs')
    args = parser.parse_args()

    for ein in args.eins:
        generate_report(ein, args.output_dir)
