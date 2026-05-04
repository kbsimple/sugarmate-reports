"""CGM metrics calculation using GlucoStats."""

import math
from typing import Any

from cgm_insights.models import CGMReading, AnalysisResults, TimeInRange, ValidationResult


# Glucose thresholds (mg/dL) — ADA 2019 consensus boundaries
# Each band uses inclusive lower bound and exclusive upper bound, except:
#   target: [70, 180] inclusive on both ends
#   high:   (180, 250] exclusive lower, inclusive upper
GLUCOSE_THRESHOLDS = {
    "very_low_max": 54,   # < 54 mg/dL: very low
    "low_max": 70,        # [54, 70): low
    "target_max": 180,    # [70, 180]: target (180 inclusive)
    "high_max": 250,      # (180, 250]: high (180 exclusive)
    # > 250 mg/dL: very high
}


# Wellness disclaimer for GMI
GMI_CAVEAT = (
    "Glucose Management Indicator (GMI) is an estimate of A1C derived from CGM data. "
    "GMI may differ from laboratory A1C measurements for 25-30% of users. "
    "This is for informational purposes only and is not a medical device."
)

# Data quality warning
QUALITY_WARNING = (
    "Data quality issues detected. Results may be less reliable. "
    "Review quality flags before drawing conclusions."
)


def calculate_metrics(
    readings: list[CGMReading],
    validation_result: ValidationResult | None = None,
) -> AnalysisResults:
    """Calculate comprehensive CGM metrics.

    Uses validated algorithms for Time-in-Range, average glucose,
    standard deviation, GMI, and coefficient of variation.

    Args:
        readings: List of validated CGM readings
        validation_result: Optional validation result for quality flags

    Returns:
        AnalysisResults with all calculated metrics

    Raises:
        ValueError: If readings list is empty
    """
    if not readings:
        raise ValueError("Cannot calculate metrics on empty readings list")

    # Sort readings by timestamp
    sorted_readings = sorted(readings, key=lambda r: r.timestamp)

    # Get date range
    date_range_start = sorted_readings[0].timestamp
    date_range_end = sorted_readings[-1].timestamp
    total_readings = len(sorted_readings)

    # Extract glucose values
    glucose_values = [r.glucose_mg_dl for r in sorted_readings]

    # Calculate metrics
    stats = _calculate_metrics_from_values(glucose_values)

    # Build TimeInRange from calculated percentages
    time_in_range = TimeInRange(
        very_low_pct=_safe_float(stats.get("time_very_low", 0)),
        low_pct=_safe_float(stats.get("time_low", 0)),
        target_pct=_safe_float(stats.get("time_target", 0)),
        high_pct=_safe_float(stats.get("time_high", 0)),
        very_high_pct=_safe_float(stats.get("time_very_high", 0)),
    )

    # Build AnalysisResults
    results = AnalysisResults(
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        total_readings=total_readings,
        time_in_range=time_in_range,
        average_glucose=_safe_float(stats.get("mean", 0)),
        glucose_std=_safe_float(stats.get("std", 0)),
        cv_pct=_safe_float(stats.get("cv", 0)),
        gmi=_safe_float(stats.get("gmi", 0)),
        data_quality_flags=validation_result.quality_flags if validation_result else [],
        sensor_warmup_excluded=True,  # Assuming warmup excluded during parsing
        completeness_pct=validation_result.completeness_pct if validation_result else 100.0,
    )

    return results


def _safe_float(value: Any) -> float:
    """Safely convert value to float.

    Args:
        value: Value to convert

    Returns:
        Float value, or 0.0 if conversion fails
    """
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _calculate_metrics_from_values(glucose_values: list[float]) -> dict:
    """Calculate CGM metrics from glucose values.

    Implements validated algorithms for CGM metrics including:
    - Time-in-Range across all 5 glucose bands
    - Average glucose and standard deviation
    - Coefficient of Variation (%CV)
    - Glucose Management Indicator (GMI)

    Args:
        glucose_values: List of glucose values in mg/dL

    Returns:
        Dictionary with calculated metrics
    """
    n = len(glucose_values)
    if n == 0:
        return {}

    # Basic statistics
    mean = sum(glucose_values) / n

    # Sample standard deviation (Bessel's correction: divide by n-1)
    if n < 2:
        std = 0.0
    else:
        variance = sum((x - mean) ** 2 for x in glucose_values) / (n - 1)
        std = math.sqrt(variance)

    # Coefficient of variation (%)
    cv = (std / mean) * 100 if mean > 0 else 0

    # Time in ranges (percentages) — ADA 2019 consensus boundaries
    # very_low:  [40,  54)  — x < 54
    # low:       [54,  70)  — 54 <= x < 70
    # target:    [70, 180]  — 70 <= x <= 180  (180 is target, NOT high)
    # high:      (180, 250] — 180 < x <= 250  (strictly above 180)
    # very_high: (250, 400] — x > 250
    very_low = sum(1 for x in glucose_values if x < 54) / n * 100
    low = sum(1 for x in glucose_values if 54 <= x < 70) / n * 100
    target = sum(1 for x in glucose_values if 70 <= x <= 180) / n * 100
    high = sum(1 for x in glucose_values if 180 < x <= 250) / n * 100
    very_high = sum(1 for x in glucose_values if x > 250) / n * 100

    # GMI calculation (from average glucose)
    # GMI = 3.31 + 0.02392 * mean_glucose (mg/dL)
    gmi = 3.31 + 0.02392 * mean

    return {
        "mean": mean,
        "std": std,
        "cv": cv,
        "time_very_low": very_low,
        "time_low": low,
        "time_target": target,
        "time_high": high,
        "time_very_high": very_high,
        "time_below_range": very_low + low,
        "time_in_range": target,
        "time_above_range": high + very_high,
        "gmi": gmi,
    }