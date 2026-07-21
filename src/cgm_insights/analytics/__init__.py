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
from .behavioral_patterns import (
    analyze_behavioral_patterns,
    BehavioralPattern,
    BehavioralAnalysisResult,
    ConsistencyLabel,
)
from .overnight_patterns import (
    analyze_overnight_patterns,
    OvernightAnalysisResult,
)
from .anomaly_detection import (
    analyze_anomalies,
    AnomalyDetectionResult,
)
from .recurring_trends import (
    analyze_recurring_trends,
    RecurringTrend,
    RecurringTrendsResult,
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
    # Behavioral pattern analysis
    "analyze_behavioral_patterns",
    "BehavioralPattern",
    "BehavioralAnalysisResult",
    "ConsistencyLabel",
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
]