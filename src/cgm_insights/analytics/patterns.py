"""Pattern detection for CGM glucose data.

This module provides functions to detect patterns in glucose readings
such as time-of-day patterns (morning spikes, afternoon highs) and
day-of-week patterns (weekday vs weekend differences).

All pattern descriptions use wellness language - no medical advice.
"""

from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from cgm_insights.models import CGMReading


# Pattern type enum
class PatternType(str, Enum):
    """Type of glucose pattern detected."""
    TIME_OF_DAY = "time_of_day"
    DAY_OF_WEEK = "day_of_week"


# Pattern severity enum
class PatternSeverity(str, Enum):
    """Severity/importance level of a pattern."""
    INFO = "info"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"


class PatternResult(BaseModel):
    """Detected glucose pattern with metadata.

    Attributes:
        pattern_type: Type of pattern (time_of_day or day_of_week)
        description: Human-readable description of the pattern
        time_period: Time period identifier (e.g., "14:00-16:00" or "Weekends")
        severity: Pattern importance/severity level
        avg_glucose: Average glucose during this pattern (mg/dL)
        reading_count: Number of readings contributing to this pattern
        confidence: Confidence level of pattern detection (0-1)
        details: Additional pattern-specific details
    """

    pattern_type: PatternType = Field(
        ...,
        description="Type of pattern detected"
    )
    description: str = Field(
        ...,
        description="Human-readable description of the pattern"
    )
    time_period: str = Field(
        ...,
        description="Time period identifier"
    )
    severity: PatternSeverity = Field(
        ...,
        description="Pattern importance/severity level"
    )
    avg_glucose: float = Field(
        ...,
        ge=40.0,
        le=400.0,
        description="Average glucose during this pattern (mg/dL)"
    )
    reading_count: int = Field(
        ...,
        ge=1,
        description="Number of readings contributing to this pattern"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence level of pattern detection (0-1)"
    )
    details: dict = Field(
        default_factory=dict,
        description="Additional pattern-specific details"
    )

    model_config = ConfigDict(frozen=True)


# Thresholds for pattern detection
HIGH_GLUCOSE_THRESHOLD = 180  # mg/dL - above this is "high"
LOW_GLUCOSE_THRESHOLD = 70   # mg/dL - below this is "low"
SPIKE_THRESHOLD = 30         # mg/dL increase from baseline to flag as spike
MIN_READINGS_FOR_PATTERN = 10  # Minimum readings in period for confidence
VARIABILITY_CV_THRESHOLD = 40  # CV percentage above this is high variability


# Standard time period labels (2-hour blocks)
TIME_PERIOD_LABELS = {
    (0, 2): "Midnight (12am-2am)",
    (2, 4): "Late night (2am-4am)",
    (4, 6): "Early morning (4am-6am)",
    (6, 8): "Morning (6am-8am)",
    (8, 10): "Mid-morning (8am-10am)",
    (10, 12): "Late morning (10am-12pm)",
    (12, 14): "Early afternoon (12pm-2pm)",
    (14, 16): "Afternoon (2pm-4pm)",
    (16, 18): "Late afternoon (4pm-6pm)",
    (18, 20): "Evening (6pm-8pm)",
    (20, 22): "Late evening (8pm-10pm)",
    (22, 24): "Night (10pm-12am)",
}


def detect_time_of_day_patterns(
    readings: list[CGMReading],
    hours_per_period: int = 2
) -> list[PatternResult]:
    """Detect glucose patterns by time of day.

    Groups readings into time periods (default 2-hour blocks) and
    identifies patterns like morning spikes, afternoon highs, etc.

    Wellness language is used throughout - no medical advice.

    Args:
        readings: List of CGM readings sorted by timestamp
        hours_per_period: Hours per time period block (default 2)

    Returns:
        List of detected patterns with confidence scores,
        sorted by severity (significant first)
    """
    if not readings:
        return []

    # Group readings by time period
    period_readings = _group_by_time_period(readings, hours_per_period)

    # Calculate overall baseline
    all_glucose = [r.glucose_mg_dl for r in readings]
    baseline_avg = sum(all_glucose) / len(all_glucose)

    # Calculate metrics for each period
    patterns = []

    for period_key, period_data in period_readings.items():
        period_glucose = [r.glucose_mg_dl for r in period_data]

        if len(period_glucose) < MIN_READINGS_FOR_PATTERN:
            continue

        avg_glucose = sum(period_glucose) / len(period_glucose)

        # Calculate variability (CV)
        variance = sum((g - avg_glucose) ** 2 for g in period_glucose) / len(period_glucose)
        std = variance ** 0.5
        cv = (std / avg_glucose * 100) if avg_glucose > 0 else 0

        # Determine pattern type based on comparison to baseline
        percent_from_baseline = ((avg_glucose - baseline_avg) / baseline_avg * 100) if baseline_avg > 0 else 0

        # Pattern detection logic
        pattern_description = None
        severity = PatternSeverity.INFO

        # Get period label or fallback
        period_label = TIME_PERIOD_LABELS.get(period_key, f"{period_key[0]:02d}:00-{period_key[1]:02d}:00")

        # High glucose pattern (>20% above baseline)
        if percent_from_baseline > 20:
            severity = PatternSeverity.MODERATE if percent_from_baseline < 30 else PatternSeverity.SIGNIFICANT
            pattern_description = f"Higher glucose in {period_label} ({avg_glucose:.0f} mg/dL, {percent_from_baseline:.0f}% above average)"

        # Low glucose pattern (>20% below baseline)
        elif percent_from_baseline < -20:
            severity = PatternSeverity.MODERATE if abs(percent_from_baseline) < 30 else PatternSeverity.SIGNIFICANT
            pattern_description = f"Lower glucose in {period_label} ({avg_glucose:.0f} mg/dL, {abs(percent_from_baseline):.0f}% below average)"

        # High variability pattern
        elif cv > VARIABILITY_CV_THRESHOLD:
            pattern_description = f"High variability in {period_label} (CV: {cv:.0f}%)"
            severity = PatternSeverity.INFO

        if pattern_description:
            # Calculate confidence based on sample size
            confidence = min(1.0, len(period_glucose) / (MIN_READINGS_FOR_PATTERN * 3))

            pattern = PatternResult(
                pattern_type=PatternType.TIME_OF_DAY,
                description=pattern_description,
                time_period=f"{period_key[0]:02d}:00-{period_key[1]:02d}:00",
                severity=severity,
                avg_glucose=avg_glucose,
                reading_count=len(period_glucose),
                confidence=confidence,
                details={
                    "baseline_avg": baseline_avg,
                    "percent_from_baseline": percent_from_baseline,
                    "cv": cv,
                    "period_label": TIME_PERIOD_LABELS.get(period_key, ""),
                }
            )
            patterns.append(pattern)

    # Sort by severity (significant first)
    severity_order = {PatternSeverity.SIGNIFICANT: 0, PatternSeverity.MODERATE: 1, PatternSeverity.INFO: 2}
    patterns.sort(key=lambda p: severity_order.get(p.severity, 3))

    return patterns


def detect_day_of_week_patterns(
    readings: list[CGMReading]
) -> list[PatternResult]:
    """Detect glucose patterns by day of week.

    Compares weekday vs weekend patterns and identifies
    specific days with unusual glucose control.

    Wellness language is used throughout - no medical advice.

    Args:
        readings: List of CGM readings sorted by timestamp

    Returns:
        List of detected patterns with confidence scores,
        sorted by severity (significant first)
    """
    if not readings:
        return []

    # Group readings by day of week
    day_groups = _group_by_day_of_week(readings)

    # Need at least some data for comparison
    if len(day_groups) < 2:
        return []

    # Calculate metrics for each day
    day_metrics = {}
    for day_name, day_readings in day_groups.items():
        day_metrics[day_name] = _calculate_day_metrics(day_readings)

    # Calculate weekday vs weekend averages
    weekday_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    weekend_days = ["Saturday", "Sunday"]

    weekday_glucose = []
    weekday_cv_sum = 0
    weekday_count = 0

    weekend_glucose = []
    weekend_cv_sum = 0
    weekend_count = 0

    for day_name, metrics in day_metrics.items():
        if metrics["count"] < MIN_READINGS_FOR_PATTERN:
            continue

        if day_name in weekday_days:
            weekday_glucose.append(metrics["avg"])
            weekday_cv_sum += metrics["cv"]
            weekday_count += 1
        elif day_name in weekend_days:
            weekend_glucose.append(metrics["avg"])
            weekend_cv_sum += metrics["cv"]
            weekend_count += 1

    patterns = []

    # Compare weekday vs weekend
    if weekday_glucose and weekend_glucose and weekday_count > 0 and weekend_count > 0:
        weekday_avg = sum(weekday_glucose) / len(weekday_glucose)
        weekend_avg = sum(weekend_glucose) / len(weekend_glucose)

        weekday_cv_avg = weekday_cv_sum / weekday_count if weekday_count > 0 else 0
        weekend_cv_avg = weekend_cv_sum / weekend_count if weekend_count > 0 else 0

        percent_diff = ((weekend_avg - weekday_avg) / weekday_avg * 100) if weekday_avg > 0 else 0

        # Weekend significantly different from weekday
        if abs(percent_diff) > 15:
            severity = PatternSeverity.MODERATE if abs(percent_diff) < 25 else PatternSeverity.SIGNIFICANT

            if percent_diff > 0:
                description = f"Weekend glucose tends to be higher ({weekend_avg:.0f} mg/dL vs {weekday_avg:.0f} mg/dL weekdays, {percent_diff:.0f}% difference)"
            else:
                description = f"Weekend glucose tends to be lower ({weekend_avg:.0f} mg/dL vs {weekday_avg:.0f} mg/dL weekdays, {abs(percent_diff):.0f}% difference)"

            # Confidence based on sample size
            total_readings = sum(m["count"] for m in day_metrics.values())
            confidence = min(1.0, total_readings / (MIN_READINGS_FOR_PATTERN * 10))

            patterns.append(PatternResult(
                pattern_type=PatternType.DAY_OF_WEEK,
                description=description,
                time_period="Weekends",
                severity=severity,
                avg_glucose=weekend_avg,
                reading_count=total_readings,
                confidence=confidence,
                details={
                    "weekday_avg": weekday_avg,
                    "weekend_avg": weekend_avg,
                    "percent_difference": percent_diff,
                }
            ))

        # Weekend variability higher
        if weekend_cv_avg > weekday_cv_avg * 1.5 and weekend_cv_avg > VARIABILITY_CV_THRESHOLD:
            description = f"Weekend glucose variability is higher (CV: {weekend_cv_avg:.0f}% vs {weekday_cv_avg:.0f}% weekdays)"

            total_readings = sum(m["count"] for m in day_metrics.values())
            confidence = min(1.0, total_readings / (MIN_READINGS_FOR_PATTERN * 10))

            patterns.append(PatternResult(
                pattern_type=PatternType.DAY_OF_WEEK,
                description=description,
                time_period="Weekends",
                severity=PatternSeverity.INFO,
                avg_glucose=weekend_avg,
                reading_count=total_readings,
                confidence=confidence,
                details={
                    "weekday_cv": weekday_cv_avg,
                    "weekend_cv": weekend_cv_avg,
                }
            ))

    # Check for specific day patterns
    overall_avg = sum(m["avg"] * m["count"] for m in day_metrics.values()) / sum(m["count"] for m in day_metrics.values()) if day_metrics else 0

    for day_name, metrics in day_metrics.items():
        if metrics["count"] < MIN_READINGS_FOR_PATTERN:
            continue

        percent_from_avg = ((metrics["avg"] - overall_avg) / overall_avg * 100) if overall_avg > 0 else 0

        if abs(percent_from_avg) > 20:
            severity = PatternSeverity.MODERATE if abs(percent_from_avg) < 30 else PatternSeverity.SIGNIFICANT

            if percent_from_avg > 0:
                description = f"{day_name} glucose tends to be higher ({metrics['avg']:.0f} mg/dL, {percent_from_avg:.0f}% above average)"
            else:
                description = f"{day_name} glucose tends to be lower ({metrics['avg']:.0f} mg/dL, {abs(percent_from_avg):.0f}% below average)"

            confidence = min(1.0, metrics["count"] / (MIN_READINGS_FOR_PATTERN * 2))

            patterns.append(PatternResult(
                pattern_type=PatternType.DAY_OF_WEEK,
                description=description,
                time_period=day_name,
                severity=severity,
                avg_glucose=metrics["avg"],
                reading_count=metrics["count"],
                confidence=confidence,
                details={
                    "overall_avg": overall_avg,
                    "percent_difference": percent_from_avg,
                }
            ))

    # Sort by severity
    severity_order = {PatternSeverity.SIGNIFICANT: 0, PatternSeverity.MODERATE: 1, PatternSeverity.INFO: 2}
    patterns.sort(key=lambda p: severity_order.get(p.severity, 3))

    return patterns


# Helper functions

def _group_by_time_period(
    readings: list[CGMReading],
    hours_per_period: int = 2
) -> dict[tuple[int, int], list[CGMReading]]:
    """Group readings by time period.

    Args:
        readings: List of CGM readings
        hours_per_period: Hours per time block

    Returns:
        Dictionary mapping (start_hour, end_hour) to readings
    """
    groups = {}

    for reading in readings:
        hour = reading.timestamp.hour
        # Calculate which period this hour falls into
        period_start = (hour // hours_per_period) * hours_per_period
        period_end = period_start + hours_per_period

        key = (period_start, period_end)
        if key not in groups:
            groups[key] = []
        groups[key].append(reading)

    return groups


def _group_by_day_of_week(readings: list[CGMReading]) -> dict[str, list[CGMReading]]:
    """Group readings by day of week name.

    Args:
        readings: List of CGM readings

    Returns:
        Dictionary mapping day name to readings
    """
    groups = {}
    for reading in readings:
        day_name = reading.timestamp.strftime("%A")
        if day_name not in groups:
            groups[day_name] = []
        groups[day_name].append(reading)
    return groups


def _calculate_day_metrics(readings: list[CGMReading]) -> dict:
    """Calculate glucose metrics for a group of readings.

    Args:
        readings: List of CGM readings

    Returns:
        Dictionary with avg, std, cv, tir, and count
    """
    values = [r.glucose_mg_dl for r in readings]
    if not values:
        return {"avg": 0, "std": 0, "cv": 0, "tir": 0, "count": 0}

    avg = sum(values) / len(values)
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    std = variance ** 0.5
    cv = (std / avg * 100) if avg > 0 else 0
    in_range = sum(1 for v in values if 70 <= v <= 180) / len(values) * 100

    return {"avg": avg, "std": std, "cv": cv, "tir": in_range, "count": len(values)}