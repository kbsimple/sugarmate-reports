"""Analytics module - metrics calculation and pattern detection."""

from .metrics import (
    calculate_metrics,
    GLUCOSE_THRESHOLDS,
    GMI_CAVEAT,
    QUALITY_WARNING,
)
from .completeness import check_minimum_data
from .patterns import (
    detect_time_of_day_patterns,
    detect_day_of_week_patterns,
    PatternResult,
    PatternType,
    PatternSeverity,
)

__all__ = [
    # Metrics
    "calculate_metrics",
    "check_minimum_data",
    "GLUCOSE_THRESHOLDS",
    "GMI_CAVEAT",
    "QUALITY_WARNING",
    # Pattern detection
    "detect_time_of_day_patterns",
    "detect_day_of_week_patterns",
    "PatternResult",
    "PatternType",
    "PatternSeverity",
]