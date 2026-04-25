"""AGP (Ambulatory Glucose Profile) report PDF generation.

This module provides PDF generation for standardized AGP reports
suitable for healthcare provider sharing.

Uses ReportLab for PDF generation, providing consistent rendering
across platforms without system dependencies.
"""

import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from cgm_insights.models import AnalysisResults
from cgm_insights.analytics import PatternResult


# Color scheme for glucose ranges
COLORS = {
    "very_low": colors.HexColor("#dc2626"),      # Red
    "low": colors.HexColor("#f97316"),           # Orange
    "target": colors.HexColor("#16a34a"),        # Green
    "high": colors.HexColor("#eab308"),          # Yellow
    "very_high": colors.HexColor("#b91c1c"),     # Dark red
    "header": colors.HexColor("#1f2937"),        # Dark gray
    "text": colors.HexColor("#374151"),          # Gray
    "light_bg": colors.HexColor("#f9fafb"),      # Light gray
    "border": colors.HexColor("#e5e7eb"),         # Light gray border
}


def generate_agp_report(
    session_id: str,
    results: AnalysisResults,
    patterns: Optional[list[PatternResult]] = None,
    generated_date: Optional[datetime] = None,
) -> bytes:
    """Generate AGP report PDF from analysis results.

    Creates a standardized Ambulatory Glucose Profile report suitable
    for healthcare provider sharing. Includes all standard AGP elements:
    glucose profile, time-in-range breakdown, daily patterns, and
    data statistics.

    Args:
        session_id: Unique session identifier (truncated in report)
        results: Analysis results from CGM data processing
        patterns: Optional list of detected patterns
        generated_date: Optional timestamp for report (defaults to now)

    Returns:
        PDF bytes ready for download

    Raises:
        RuntimeError: If PDF generation fails
    """
    if generated_date is None:
        generated_date = datetime.utcnow()

    if patterns is None:
        patterns = []

    try:
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )

        # Get styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="ReportTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=COLORS["header"],
            alignment=1,  # Center
            spaceAfter=4,
        ))
        styles.add(ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=COLORS["text"],
            alignment=1,  # Center
            spaceAfter=12,
        ))
        styles.add(ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=COLORS["header"],
            spaceAfter=8,
            spaceBefore=12,
        ))
        styles.add(ParagraphStyle(
            name="MetricLabel",
            parent=styles["Normal"],
            fontSize=8,
            textColor=COLORS["text"],
        ))
        styles.add(ParagraphStyle(
            name="Disclaimer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=COLORS["text"],
            leading=10,
        ))

        # Build document content
        story = []

        # Header
        story.append(Paragraph(
            "Ambulatory Glucose Profile (AGP) Report",
            styles["ReportTitle"],
        ))
        story.append(Paragraph(
            "Standardized CGM Report for Healthcare Provider Review",
            styles["ReportSubtitle"],
        ))
        story.append(Spacer(1, 12))

        # Session Info Table
        info_data = [
            ["Generated:", generated_date.strftime("%B %d, %Y at %I:%M %p"),
             "Report ID:", session_id[:8]],
            ["Analysis Period:", f"{results.date_range_start.strftime('%B %d, %Y')} - {results.date_range_end.strftime('%B %d, %Y')}",
             "Total Readings:", str(results.total_readings)],
        ]
        info_table = Table(info_data, colWidths=[1.2*inch, 2.5*inch, 1.2*inch, 2.5*inch])
        info_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLORS["light_bg"]),
            ("TEXTCOLOR", (0, 0), (0, -1), COLORS["text"]),
            ("TEXTCOLOR", (2, 0), (2, -1), COLORS["text"]),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 16))

        # Section 1: Glucose Profile
        story.append(Paragraph("Glucose Profile", styles["SectionTitle"]))

        # Key Metrics Grid
        metrics_data = [
            [f"{results.average_glucose:.0f}", f"{results.gmi:.1f}", f"{results.cv_pct:.1f}", f"{results.time_in_range.target_pct:.1f}"],
            ["mg/dL", "%", "%", "% (70-180)"],
            ["Average Glucose", "GMI", "CV (Variability)", "Time in Target"],
        ]
        metrics_table = Table(metrics_data, colWidths=[1.75*inch, 1.75*inch, 1.75*inch, 1.75*inch])
        metrics_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLORS["light_bg"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["header"]),
            ("TEXTCOLOR", (0, 1), (-1, 1), COLORS["text"]),
            ("TEXTCOLOR", (0, 2), (-1, 2), COLORS["text"]),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 16),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border"]),
            ("LINEABOVE", (0, 2), (-1, 2), 0.5, COLORS["border"]),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 12))

        # Time in Range Table
        story.append(Paragraph("Time in Range Breakdown", styles["MetricLabel"]))
        story.append(Spacer(1, 6))

        tir_data = [
            ["Range", "Percentage", "Category"],
            ["Very Low (<54 mg/dL)", f"{results.time_in_range.very_low_pct:.1f}%", "Severe hypoglycemia"],
            ["Low (54-70 mg/dL)", f"{results.time_in_range.low_pct:.1f}%", "Hypoglycemia"],
            ["Target (70-180 mg/dL)", f"{results.time_in_range.target_pct:.1f}%", "Euglycemia (goal)"],
            ["High (180-250 mg/dL)", f"{results.time_in_range.high_pct:.1f}%", "Hyperglycemia"],
            ["Very High (>250 mg/dL)", f"{results.time_in_range.very_high_pct:.1f}%", "Severe hyperglycemia"],
        ]
        tir_table = Table(tir_data, colWidths=[2.5*inch, 1.5*inch, 2.5*inch])
        tir_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["header"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border"]),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fecaca")),  # Very low - red tint
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fed7aa")),  # Low - orange tint
            ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#bbf7d0")),  # Target - green tint
            ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#fef08a")),  # High - yellow tint
            ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#fecaca")),  # Very high - red tint
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tir_table)
        story.append(Spacer(1, 8))

        # GMI Disclaimer
        story.append(Paragraph(
            "<b>GMI Note:</b> Glucose Management Indicator estimates A1C but may not match lab values for 25-30% of people.",
            styles["Disclaimer"],
        ))
        story.append(Spacer(1, 16))

        # Section 2: Daily Glucose Pattern
        story.append(Paragraph("Daily Glucose Pattern", styles["SectionTitle"]))

        # Patterns summary
        if patterns:
            story.append(Paragraph("Detected Patterns:", styles["MetricLabel"]))
            story.append(Spacer(1, 6))

            for pattern in patterns[:5]:  # Limit to 5 patterns
                severity_color = {
                    "significant": colors.HexColor("#fecaca"),
                    "moderate": colors.HexColor("#fed7aa"),
                    "info": colors.HexColor("#fef08a"),
                }.get(pattern.severity.value, COLORS["light_bg"])

                pattern_data = [[pattern.description, pattern.severity.value.title()]]
                pattern_table = Table(pattern_data, colWidths=[5.5*inch, 1*inch])
                pattern_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), severity_color),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border"]),
                ]))
                story.append(pattern_table)
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph(
                "No significant patterns detected in this analysis period.",
                styles["MetricLabel"],
            ))
        story.append(Spacer(1, 16))

        # Section 3: Data Statistics
        story.append(Paragraph("Data Statistics", styles["SectionTitle"]))

        stats_data = [
            [str(results.total_readings), f"{results.completeness_pct:.1f}%", f"{results.glucose_std:.1f}"],
            ["Total Readings", "Data Completeness", "Std Dev (mg/dL)"],
        ]
        stats_table = Table(stats_data, colWidths=[2.33*inch, 2.33*inch, 2.33*inch])
        stats_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLORS["light_bg"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["header"]),
            ("TEXTCOLOR", (0, 1), (-1, 1), COLORS["text"]),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 14),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border"]),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 8))

        # Quality flags
        if results.data_quality_flags:
            flags_text = "Data Quality Notes: " + ", ".join(
                f.replace("_", " ").title() for f in results.data_quality_flags
            )
            story.append(Paragraph(flags_text, styles["Disclaimer"]))

        if results.sensor_warmup_excluded:
            story.append(Paragraph(
                "Sensor warmup period (first 2 hours) was excluded from analysis.",
                styles["Disclaimer"],
            ))
        story.append(Spacer(1, 16))

        # Section 4: Notes for Healthcare Provider
        story.append(Paragraph("Notes for Healthcare Provider", styles["SectionTitle"]))
        story.append(Paragraph(
            "Space for healthcare provider notes:",
            styles["MetricLabel"],
        ))
        story.append(Spacer(1, 8))

        # Lines for notes
        for _ in range(3):
            notes_line = Table([[""]], colWidths=[7*inch])
            notes_line.setStyle(TableStyle([
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, COLORS["border"]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ]))
            story.append(notes_line)

        story.append(Spacer(1, 16))

        # Wellness Disclaimer
        disclaimer_text = (
            "<b>Wellness Information Only:</b> This report is provided for informational purposes only "
            "and is not a medical diagnosis. Glucose Management Indicator (GMI) estimates may not match laboratory "
            "A1C values for 25-30% of individuals. This tool does not provide medical advice, insulin recommendations, "
            "or treatment suggestions. Always discuss glucose management with your healthcare provider before making "
            "any changes to your care plan."
        )
        story.append(Paragraph(disclaimer_text, styles["Disclaimer"]))

        # Footer
        story.append(Spacer(1, 20))
        footer_text = f"Generated by CGM Insights | {generated_date.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        story.append(Paragraph(footer_text, styles["Disclaimer"]))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    except Exception as e:
        raise RuntimeError(f"Failed to generate AGP report: {e}") from e


def generate_agp_preview(
    session_id: str,
    results: AnalysisResults,
    patterns: Optional[list[PatternResult]] = None,
    generated_date: Optional[datetime] = None,
) -> str:
    """Generate HTML preview of AGP report.

    Useful for checking report content before downloading PDF.

    Args:
        session_id: Unique session identifier
        results: Analysis results from CGM data processing
        patterns: Optional list of detected patterns
        generated_date: Optional timestamp for report

    Returns:
        HTML string of the report preview
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from pathlib import Path

    if generated_date is None:
        generated_date = datetime.utcnow()

    if patterns is None:
        patterns = []

    # Template directory
    templates_dir = Path(__file__).resolve().parent.parent / "templates"

    # Jinja2 environment
    jinja_env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    formatted_patterns = [
        {
            "pattern_type": p.pattern_type.value,
            "description": p.description,
            "time_period": p.time_period,
            "severity": p.severity.value,
            "avg_glucose": round(p.avg_glucose, 1),
            "reading_count": p.reading_count,
            "confidence": round(p.confidence, 2),
        }
        for p in patterns
    ]

    template = jinja_env.get_template("agp_report.html")

    return template.render(
        session_id=session_id,
        results=results,
        patterns=formatted_patterns,
        generated_date=generated_date,
    )