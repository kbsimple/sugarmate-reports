"""Sample data generators for web interface tests.

Provides functions to generate realistic CGM readings and test fixtures.
"""

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import uuid
from typing import Optional

from cgm_insights.models import CGMReading, AnalysisResults, TimeInRange


def generate_sample_readings(
    count: int = 100,
    days: int = 1,
    start_date: Optional[datetime] = None,
    avg_glucose: float = 140.0,
    std_dev: float = 30.0,
) -> list[CGMReading]:
    """Generate realistic CGM readings for testing.

    Creates readings distributed over the specified number of days with
    realistic glucose values centered around avg_glucose with std_dev variance.

    Args:
        count: Number of readings to generate
        days: Number of days to span
        start_date: Starting datetime (defaults to now - days)
        avg_glucose: Average glucose value in mg/dL
        std_dev: Standard deviation for glucose values

    Returns:
        List of CGMReading objects
    """
    import random

    if start_date is None:
        start_date = datetime.now() - timedelta(days=days)

    readings = []
    interval = timedelta(minutes=(days * 24 * 60) / count) if count > 0 else timedelta(minutes=5)

    for i in range(count):
        timestamp = start_date + (interval * i)
        # Generate glucose with normal-ish distribution
        glucose = random.gauss(avg_glucose, std_dev)
        # Clamp to realistic CGM range
        glucose = max(40, min(400, glucose))

        readings.append(CGMReading(
            timestamp=timestamp,
            glucose_mg_dl=round(glucose, 1),
        ))

    return readings


def generate_sample_results(
    avg_glucose: float = 140.0,
    tir_target: float = 70.0,
    total_readings: int = 288,
) -> AnalysisResults:
    """Generate sample AnalysisResults for testing.

    Creates realistic analysis results for use in web tests.

    Args:
        avg_glucose: Average glucose in mg/dL
        tir_target: Time in target range percentage
        total_readings: Total number of readings

    Returns:
        AnalysisResults object with sample data
    """
    # Calculate remaining TIR percentages
    remaining = 100.0 - tir_target
    very_low = 1.0
    low = remaining * 0.15
    high = remaining * 0.35
    very_high = remaining * 0.50

    return AnalysisResults(
        date_range_start=datetime.now() - timedelta(days=14),
        date_range_end=datetime.now(),
        total_readings=total_readings,
        time_in_range=TimeInRange(
            very_low_pct=round(very_low, 1),
            low_pct=round(low, 1),
            target_pct=round(tir_target, 1),
            high_pct=round(high, 1),
            very_high_pct=round(very_high, 1),
        ),
        average_glucose=avg_glucose,
        glucose_std=30.0,
        cv_pct=round(30.0 / avg_glucose * 100, 1),
        gmi=round(avg_glucose / 28.7 - 42, 1),
        completeness_pct=95.0,
        data_quality_flags=[],
        sensor_warmup_excluded=True,
    )


def create_sample_csv(
    readings: Optional[list[CGMReading]] = None,
    include_header: bool = True,
) -> Path:
    """Create a temporary CSV file with CGM data.

    Uses Sugarmate CSV format: datetime, mg_dl columns.

    Args:
        readings: List of readings (generates 288 if None)
        include_header: Whether to include CSV header row

    Returns:
        Path to temporary CSV file (caller must delete)
    """
    if readings is None:
        readings = generate_sample_readings(count=288, days=1)

    # Create temp file
    fd, path = tempfile.mkstemp(suffix=".csv")

    with open(path, "w") as f:
        if include_header:
            f.write("datetime,mg_dl\n")

        for reading in readings:
            # Use Sugarmate datetime format: YYYY-MM-DD HH:MM
            dt_str = reading.timestamp.strftime("%Y-%m-%d %H:%M")
            f.write(f"{dt_str},{reading.glucose_mg_dl}\n")

    return Path(path)


def create_sample_csv_content(
    readings: Optional[list[CGMReading]] = None,
    include_header: bool = True,
) -> str:
    """Create CSV content string for upload testing.

    Uses Sugarmate CSV format: datetime, mg_dl columns.

    Args:
        readings: List of readings (generates 288 if None)
        include_header: Whether to include CSV header row

    Returns:
        CSV content as string
    """
    if readings is None:
        readings = generate_sample_readings(count=288, days=1)

    lines = []
    if include_header:
        lines.append("datetime,mg_dl")

    for reading in readings:
        # Use Sugarmate datetime format: YYYY-MM-DD HH:MM
        dt_str = reading.timestamp.strftime("%Y-%m-%d %H:%M")
        lines.append(f"{dt_str},{reading.glucose_mg_dl}")

    return "\n".join(lines)


# Pre-computed sample results dictionary for quick test fixtures
SAMPLE_RESULTS_DICT = {
    "avg_glucose": 140.0,
    "tir_target": 70.0,
    "total_readings": 288,
    "gmi": 6.6,
    "cv_pct": 21.4,
    "completeness_pct": 95.0,
}


def get_sample_session_id() -> str:
    """Generate a sample session ID for testing.

    Returns:
        UUID v4 string
    """
    return str(uuid.uuid4())


# Large file content for size limit testing
def create_large_csv_content(size_mb: float = 11.0) -> bytes:
    """Create CSV content larger than the upload limit.

    Uses Sugarmate CSV format: datetime, mg_dl columns.

    Args:
        size_mb: Target size in megabytes

    Returns:
        CSV content as bytes
    """
    # Create minimal rows until we exceed size
    header = b"datetime,mg_dl\n"
    row_template = b"2026-04-25 12:00,140\n"

    target_size = int(size_mb * 1024 * 1024)
    content = header

    while len(content) < target_size:
        content += row_template

    return content


# Empty/invalid file content for error testing
EMPTY_CSV_CONTENT = b""

INVALID_CSV_CONTENT = b"not,a,valid,cgm,file\n1,2,3,4\n"

INSUFFICIENT_CSV_CONTENT = b"datetime,mg_dl\n2026-04-25 12:00,140\n"