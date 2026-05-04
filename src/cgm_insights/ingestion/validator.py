"""Data validation for CGM readings."""

from datetime import datetime, timedelta

from ..models import CGMReading, ValidationResult, QualityFlag


# Validation thresholds
MIN_COMPLETENESS_PCT = 80.0  # Minimum data completeness percentage
STANDARD_INTERVAL_MINUTES = 5  # Standard CGM reading interval
GAP_THRESHOLD_MINUTES = 10  # Gap size to flag as data gap
SENSOR_WARMUP_HOURS = 2  # Hours of sensor warmup to exclude


def validate_completeness(
    readings: list[CGMReading],
    minimum_completeness: float = MIN_COMPLETENESS_PCT,
    standard_interval: int = STANDARD_INTERVAL_MINUTES,
    gap_threshold: int = GAP_THRESHOLD_MINUTES,
) -> ValidationResult:
    """Validate CGM data completeness and quality.

    Checks for:
    - Data completeness percentage (expected vs actual readings)
    - Gaps in data (missing readings > threshold)
    - Sensor warmup period (first 2 hours typically inaccurate)

    Args:
        readings: List of CGM readings to validate
        minimum_completeness: Minimum completeness percentage (default 80%)
        standard_interval: Expected reading interval in minutes (default 5)
        gap_threshold: Gap size to flag in minutes (default 10)

    Returns:
        ValidationResult with completeness info and quality flags
    """
    if not readings:
        return ValidationResult(
            is_valid=False,
            completeness_pct=0.0,
            expected_readings=0,
            actual_readings=0,
            quality_flags=["low_completeness"],
        )

    # Sort readings by timestamp
    sorted_readings = sorted(readings, key=lambda r: r.timestamp)

    # Calculate time span
    first_ts = sorted_readings[0].timestamp
    last_ts = sorted_readings[-1].timestamp
    time_span = last_ts - first_ts

    # Calculate expected readings
    total_minutes = time_span.total_seconds() / 60
    expected_readings = int(total_minutes / standard_interval) + 1
    actual_readings = len(sorted_readings)

    # Calculate completeness
    completeness = (
        (actual_readings / expected_readings) * 100 if expected_readings > 0 else 100.0
    )

    # Detect gaps
    gap_count = 0
    for i in range(1, len(sorted_readings)):
        time_diff = sorted_readings[i].timestamp - sorted_readings[i - 1].timestamp
        if time_diff > timedelta(minutes=gap_threshold):
            gap_count += 1

    # Detect sensor warmup period
    sensor_warmup_minutes = detect_sensor_warmup(sorted_readings)

    # Build quality flags
    quality_flags: list[QualityFlag] = []
    if completeness < minimum_completeness:
        quality_flags.append("low_completeness")
    if gap_count > 0:
        quality_flags.append("data_gaps")
    if sensor_warmup_minutes > 0:
        quality_flags.append("sensor_warmup")

    return ValidationResult(
        is_valid=completeness >= minimum_completeness,
        completeness_pct=round(completeness, 2),
        expected_readings=expected_readings,
        actual_readings=actual_readings,
        gap_count=gap_count,
        sensor_warmup_minutes=sensor_warmup_minutes,
        quality_flags=quality_flags,
    )


def detect_sensor_warmup(
    readings: list[CGMReading],
    warmup_hours: int = SENSOR_WARMUP_HOURS,
) -> int:
    """Detect sensor warmup period from data start.

    Returns 0 — actual warmup detection requires sensor-change event data
    that is not present in standard CSV exports. Warmup exclusion is
    handled explicitly by :func:`exclude_warmup_period` when the caller
    opts in via ``exclude_warmup=True``.

    Args:
        readings: Sorted list of CGM readings (chronological order)
        warmup_hours: Unused; retained for API compatibility

    Returns:
        Always 0; warmup period is controlled by exclude_warmup_period()
    """
    return 0


def filter_by_date_range(
    readings: list[CGMReading],
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[CGMReading]:
    """Filter readings by date range.

    Args:
        readings: List of CGM readings
        start_date: Optional start date (inclusive)
        end_date: Optional end date (inclusive)

    Returns:
        Filtered list of CGMReading objects
    """
    filtered = readings

    if start_date:
        filtered = [r for r in filtered if r.timestamp >= start_date]
    if end_date:
        filtered = [r for r in filtered if r.timestamp <= end_date]

    return filtered


def exclude_warmup_period(
    readings: list[CGMReading],
    warmup_hours: int = SENSOR_WARMUP_HOURS,
) -> list[CGMReading]:
    """Exclude sensor warmup period from readings.

    Args:
        readings: Sorted list of CGM readings (chronological order)
        warmup_hours: Number of hours to exclude (default 2)

    Returns:
        Readings after warmup period
    """
    if not readings:
        return []

    first_ts = readings[0].timestamp
    warmup_end = first_ts + timedelta(hours=warmup_hours)

    return [r for r in readings if r.timestamp >= warmup_end]