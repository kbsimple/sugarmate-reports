"""Results formatting for display."""

from cgm_insights.models import AnalysisResults
from cgm_insights.analytics import GMI_CAVEAT, QUALITY_WARNING


def format_results(results: AnalysisResults, include_caveats: bool = True) -> dict:
    """Format analysis results for display.

    Args:
        results: Analysis results to format
        include_caveats: Whether to include wellness caveats

    Returns:
        Dictionary with formatted results ready for display/serialization
    """
    formatted = {
        "date_range": {
            "start": results.date_range_start.isoformat(),
            "end": results.date_range_end.isoformat(),
        },
        "readings": {
            "total": results.total_readings,
            "completeness_pct": round(results.completeness_pct, 1),
        },
        "glucose_metrics": {
            "average_mg_dl": round(results.average_glucose, 1),
            "std_mg_dl": round(results.glucose_std, 1),
            "cv_pct": round(results.cv_pct, 1),
            "gmi": round(results.gmi, 1),
        },
        "time_in_range": {
            "very_low_pct": round(results.time_in_range.very_low_pct, 1),
            "low_pct": round(results.time_in_range.low_pct, 1),
            "target_pct": round(results.time_in_range.target_pct, 1),
            "high_pct": round(results.time_in_range.high_pct, 1),
            "very_high_pct": round(results.time_in_range.very_high_pct, 1),
        },
        "quality": {
            "flags": results.data_quality_flags,
            "sensor_warmup_excluded": results.sensor_warmup_excluded,
        },
    }

    if include_caveats:
        formatted["caveats"] = {
            "gmi": GMI_CAVEAT,
        }
        if results.data_quality_flags:
            formatted["caveats"]["data_quality"] = QUALITY_WARNING

    return formatted


def format_quality_flags(flags: list[str]) -> list[dict]:
    """Format quality flags into human-readable messages.

    Args:
        flags: List of quality flag identifiers

    Returns:
        List of dictionaries with flag name and description
    """
    flag_descriptions = {
        "sensor_warmup": {
            "flag": "sensor_warmup",
            "message": "Sensor warmup period detected (first 2 hours may be less accurate).",
            "severity": "info",
        },
        "data_gaps": {
            "flag": "data_gaps",
            "message": "Gaps detected in CGM data. Some readings are missing.",
            "severity": "warning",
        },
        "low_completeness": {
            "flag": "low_completeness",
            "message": "Data completeness below 80%. Results may be less reliable.",
            "severity": "warning",
        },
        "compression_lows": {
            "flag": "compression_lows",
            "message": "Potential compression artifacts detected (may indicate sleeping on sensor).",
            "severity": "info",
        },
        "duplicate_timestamps": {
            "flag": "duplicate_timestamps",
            "message": "Duplicate timestamps found in data. Duplicates have been removed.",
            "severity": "info",
        },
    }

    formatted = []
    for flag in flags:
        if flag in flag_descriptions:
            formatted.append(flag_descriptions[flag])
        else:
            formatted.append({
                "flag": flag,
                "message": f"Data quality issue: {flag}",
                "severity": "info",
            })

    return formatted


def format_summary(results: AnalysisResults) -> str:
    """Format results as a concise text summary.

    Args:
        results: Analysis results to format

    Returns:
        Human-readable summary string
    """
    lines = [
        f"Analysis Period: {results.date_range_start.date()} to {results.date_range_end.date()}",
        f"Readings: {results.total_readings} ({results.completeness_pct:.0f}% complete)",
        "",
        "Glucose Metrics:",
        f"  Average: {results.average_glucose:.0f} mg/dL",
        f"  Std Dev: {results.glucose_std:.0f} mg/dL",
        f"  CV: {results.cv_pct:.1f}%",
        f"  GMI: {results.gmi:.1f}%",
        "",
        "Time in Range:",
        f"  Very Low (<54): {results.time_in_range.very_low_pct:.1f}%",
        f"  Low (54-70): {results.time_in_range.low_pct:.1f}%",
        f"  Target (70-180): {results.time_in_range.target_pct:.1f}%",
        f"  High (180-250): {results.time_in_range.high_pct:.1f}%",
        f"  Very High (>250): {results.time_in_range.very_high_pct:.1f}%",
    ]

    if results.data_quality_flags:
        lines.append("")
        lines.append("Quality Flags:")
        for flag in results.data_quality_flags:
            lines.append(f"  - {flag}")

    return "\n".join(lines)