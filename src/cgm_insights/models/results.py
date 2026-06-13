"""Analysis results and validation models."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


# Data quality flag types
QualityFlag = Literal[
    "sensor_warmup",
    "data_gaps",
    "low_completeness",
    "compression_lows",
    "duplicate_timestamps",
]


class ValidationResult(BaseModel):
    """Results of data validation checks.

    Attributes:
        is_valid: Whether data passes minimum quality thresholds
        completeness_pct: Percentage of expected readings present (0-100)
        expected_readings: Number of readings expected based on time span
        actual_readings: Number of readings actually present
        gap_count: Number of gaps >10 minutes detected
        sensor_warmup_minutes: Minutes of sensor warmup detected (0 if none)
        quality_flags: List of data quality issues detected
    """

    is_valid: bool = Field(
        ...,
        description="True if data meets minimum quality thresholds"
    )
    completeness_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of expected readings present"
    )
    expected_readings: int = Field(
        ...,
        ge=0,
        description="Number of readings expected based on time span"
    )
    actual_readings: int = Field(
        ...,
        ge=0,
        description="Number of readings actually present"
    )
    gap_count: int = Field(
        0,
        ge=0,
        description="Number of gaps greater than 10 minutes"
    )
    sensor_warmup_minutes: int = Field(
        0,
        ge=0,
        description="Minutes of sensor warmup detected (first 2 hours)"
    )
    quality_flags: list[QualityFlag] = Field(
        default_factory=list,
        description="Data quality issues detected"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "is_valid": True,
                    "completeness_pct": 92.5,
                    "expected_readings": 288,
                    "actual_readings": 266,
                    "gap_count": 3,
                    "sensor_warmup_minutes": 120,
                    "quality_flags": ["sensor_warmup"]
                }
            ]
        }
    )


class TimeInRange(BaseModel):
    """Time-in-range breakdown for all 5 glucose bands.

    The five ranges follow clinical standards:
    - Very Low: <54 mg/dL (severe hypoglycemia risk)
    - Low: 54-70 mg/dL (hypoglycemia)
    - Target: 70-180 mg/dL (euglycemia)
    - High: 180-250 mg/dL (hyperglycemia)
    - Very High: >250 mg/dL (severe hyperglycemia)
    """

    very_low_pct: float = Field(..., ge=0, le=100, description="Time <54 mg/dL")
    low_pct: float = Field(..., ge=0, le=100, description="Time 54-70 mg/dL")
    target_pct: float = Field(..., ge=0, le=100, description="Time 70-180 mg/dL")
    high_pct: float = Field(..., ge=0, le=100, description="Time 180-250 mg/dL")
    very_high_pct: float = Field(..., ge=0, le=100, description="Time >250 mg/dL")

    @property
    def total_pct(self) -> float:
        """Sum of all percentages should equal ~100."""
        return self.very_low_pct + self.low_pct + self.target_pct + self.high_pct + self.very_high_pct


class AnalysisResults(BaseModel):
    """Complete analysis results for a date range.

    Contains all calculated metrics, data quality information,
    and metadata for the analyzed period.

    Attributes:
        date_range_start: Start of analysis period
        date_range_end: End of analysis period
        total_readings: Number of readings included in analysis
        time_in_range: Time-in-range percentages for all 5 bands
        average_glucose: Mean glucose value in mg/dL
        glucose_std: Standard deviation of glucose values
        cv_pct: Coefficient of variation (%)
        gmi: Glucose Management Indicator (A1C estimate)
        data_quality_flags: List of data quality issues detected
        sensor_warmup_excluded: Whether sensor warmup was excluded
    """

    # Date range metadata
    date_range_start: datetime = Field(..., description="Start of analysis period")
    date_range_end: datetime = Field(..., description="End of analysis period")
    total_readings: int = Field(..., ge=0, description="Number of readings analyzed")

    # Time-in-Range (all 5 bands)
    time_in_range: TimeInRange = Field(
        ...,
        description="Time-in-range percentages for all glucose bands"
    )

    # Core metrics
    average_glucose: float = Field(..., ge=40, le=400, description="Mean glucose (mg/dL)")
    glucose_std: float = Field(..., ge=0, description="Standard deviation of glucose")
    cv_pct: float = Field(
        ...,
        ge=0,
        le=100,
        description="Coefficient of variation (%)"
    )
    gmi: float = Field(
        ...,
        ge=4.0,
        le=14.0,
        description="Glucose Management Indicator (estimated A1C)"
    )

    # Glucose percentiles
    p50_glucose: float = Field(0.0, ge=0, description="50th percentile glucose (mg/dL)")
    p70_glucose: float = Field(0.0, ge=0, description="70th percentile glucose (mg/dL)")
    p90_glucose: float = Field(0.0, ge=0, description="90th percentile glucose (mg/dL)")

    # Quality metadata
    data_quality_flags: list[QualityFlag] = Field(
        default_factory=list,
        description="Data quality issues detected"
    )
    sensor_warmup_excluded: bool = Field(
        True,
        description="Whether sensor warmup period was excluded"
    )
    completeness_pct: float = Field(
        ...,
        ge=0,
        le=100,
        description="Data completeness percentage"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "date_range_start": "2026-04-01T00:00:00",
                    "date_range_end": "2026-04-14T23:59:59",
                    "total_readings": 4032,
                    "time_in_range": {
                        "very_low_pct": 1.2,
                        "low_pct": 3.5,
                        "target_pct": 72.8,
                        "high_pct": 18.3,
                        "very_high_pct": 4.2
                    },
                    "average_glucose": 148.5,
                    "glucose_std": 42.3,
                    "cv_pct": 28.5,
                    "gmi": 6.8,
                    "data_quality_flags": ["sensor_warmup"],
                    "sensor_warmup_excluded": True,
                    "completeness_pct": 95.2
                }
            ]
        }
    )