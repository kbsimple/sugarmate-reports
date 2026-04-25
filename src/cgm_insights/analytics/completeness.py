"""Data completeness checking for analytics."""

from cgm_insights.models import CGMReading


# Minimum readings for reliable analysis
MIN_READINGS_FOR_TIR = 288 * 2  # ~2 days at 5-minute intervals
MIN_READINGS_FOR_PATTERNS = 288 * 14  # ~14 days at 5-minute intervals


def check_minimum_data(
    readings: list[CGMReading],
    analysis_type: str = "basic",
) -> tuple[bool, str]:
    """Check if minimum data requirements are met.

    Args:
        readings: List of CGM readings
        analysis_type: "basic" for TIR/metrics, "patterns" for pattern detection

    Returns:
        Tuple of (is_sufficient, message)
    """
    count = len(readings)
    min_required = (
        MIN_READINGS_FOR_PATTERNS
        if analysis_type == "patterns"
        else MIN_READINGS_FOR_TIR
    )

    if count < min_required:
        days_needed = min_required / 288  # 288 readings per day
        days_have = count / 288
        return (
            False,
            f"Insufficient data for {analysis_type} analysis. "
            f"Need ~{days_needed:.0f} days, have ~{days_have:.0f} days.",
        )

    return True, f"Sufficient data for {analysis_type} analysis."