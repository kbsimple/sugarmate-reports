"""CGM Insights - Core analysis library for glucose data.

This library provides tools for analyzing CGM (Continuous Glucose Monitor)
data, including parsing, validation, and metric calculation.

Example usage:
    from cgm_insights import analyze_file, format_results

    results = analyze_file("data.csv")
    formatted = format_results(results)
    print(formatted)

Note: This library is for informational purposes only and is not a medical device.
All glucose insights should be discussed with a healthcare provider.
"""

from .models import (
    CGMReading,
    ValidationResult,
    AnalysisResults,
    TimeInRange,
)
from .ingestion import (
    SugarmateParser,
    get_parser,
    validate_completeness,
    filter_by_date_range,
    exclude_warmup_period,
    normalize_for_glucostats,
)
from .analytics import (
    calculate_metrics,
    check_minimum_data,
    GMI_CAVEAT,
    QUALITY_WARNING,
    analyze_behavioral_patterns,
    BehavioralPattern,
    analyze_overnight_patterns,
    OvernightAnalysisResult,
    analyze_anomalies,
    AnomalyDetectionResult,
    analyze_recurring_trends,
    RecurringTrend,
    RecurringTrendsResult,
)
from .output import (
    format_results,
    format_quality_flags,
    format_summary,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Models
    "CGMReading",
    "ValidationResult",
    "AnalysisResults",
    "TimeInRange",
    # Ingestion
    "SugarmateParser",
    "get_parser",
    "validate_completeness",
    "filter_by_date_range",
    "exclude_warmup_period",
    "normalize_for_glucostats",
    # Analytics
    "calculate_metrics",
    "check_minimum_data",
    "GMI_CAVEAT",
    "QUALITY_WARNING",
    # Behavioral pattern analysis
    "analyze_behavioral_patterns",
    "BehavioralPattern",
    # Overnight pattern analysis (Phase 5)
    "analyze_overnight_patterns",
    "OvernightAnalysisResult",
    # Anomaly detection (Phase 6)
    "analyze_anomalies",
    "AnomalyDetectionResult",
    # Recurring trend detection
    "analyze_recurring_trends",
    "RecurringTrend",
    "RecurringTrendsResult",
    # Output
    "format_results",
    "format_quality_flags",
    "format_summary",
]


def analyze_file(
    file_path: str,
    start_date: str | None = None,
    end_date: str | None = None,
    exclude_warmup: bool = True,
) -> AnalysisResults:
    """Analyze a CGM data file and return results.

    This is the main entry point for CGM analysis. It:
    1. Parses the file using the appropriate parser
    2. Validates data completeness
    3. Optionally excludes sensor warmup period
    4. Calculates all metrics
    5. Returns comprehensive analysis results

    Args:
        file_path: Path to CGM data file (CSV supported)
        start_date: Optional start date filter (ISO format: YYYY-MM-DD)
        end_date: Optional end date filter (ISO format: YYYY-MM-DD)
        exclude_warmup: Whether to exclude sensor warmup period (default True)

    Returns:
        AnalysisResults with all calculated metrics

    Raises:
        ValueError: If file cannot be parsed or data is insufficient

    Example:
        >>> results = analyze_file("readings.csv")
        >>> print(f"Time in Range: {results.time_in_range.target_pct:.1f}%")
    """
    from datetime import datetime
    from pathlib import Path

    from .ingestion import get_parser, validate_completeness, exclude_warmup_period
    from .analytics import calculate_metrics

    # Resolve path to prevent path traversal attacks
    resolved_path = str(Path(file_path).resolve())

    # Parse dates if provided
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    # Get appropriate parser and parse file
    parser = get_parser(resolved_path)
    readings = parser.parse(resolved_path, start_date=start, end_date=end)

    if not readings:
        raise ValueError(f"No readings found in {file_path}")

    # Validate data quality
    validation = validate_completeness(readings)

    # Optionally exclude sensor warmup period
    if exclude_warmup:
        readings = exclude_warmup_period(readings)
        if not readings:
            raise ValueError(
                "No readings remain after excluding the 2-hour sensor warmup period. "
                "The dataset may be shorter than 2 hours, or use exclude_warmup=False."
            )
        # Re-validate on trimmed readings to get accurate completeness/gaps
        validation = validate_completeness(readings)

    # Calculate metrics
    results = calculate_metrics(readings, validation)

    return results