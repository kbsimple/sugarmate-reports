"""Anomaly detection for CGM glucose data.

Detects readings that deviate significantly from the user's personal
time-of-day/day-of-week baseline. All insights use wellness language —
no medical advice. Output is aggregated into weekly summaries only;
individual anomalous readings are never surfaced to the user.

PISA (Pressure-Induced Sensor Attenuation) artifacts are filtered
before baseline comparison to prevent false positives.
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime
from enum import Enum
from typing import Optional

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from cgm_insights.analytics.behavioral_patterns import _build_df
from cgm_insights.models import CGMReading


BUCKET_MINUTES: int = 30              # Fixed non-overlapping 30-min bucket grid
MIN_DAYS_FOR_BASELINE: int = 5        # Minimum distinct days for a valid bucket baseline
MAX_WEEKLY_SUMMARIES: int = 8         # Most recent N weeks to surface

# PISA artifact detection constants
PISA_DROP_THRESHOLD_PCT: float = 20.0     # >=20% glucose drop from reference triggers check
PISA_RECOVERY_WINDOW_MINUTES: int = 60   # Recovery must occur within 60 min of drop start
PISA_MIN_RECOVERY_RETURN_PCT: float = 15.0  # Must return within 15% of pre-drop level

# Severity SD thresholds
ANOMALY_SD_MILD: float = 2.0
ANOMALY_SD_MODERATE: float = 3.0
ANOMALY_SD_SEVERE: float = 4.0


class AnomalySeverity(str, Enum):
    """Severity classification for a detected anomaly.

    Based on absolute SD deviation from the per-bucket historical baseline.
    """

    MILD = "mild"         # 2.0 <= |sd| < 3.0
    MODERATE = "moderate" # 3.0 <= |sd| < 4.0
    SEVERE = "severe"     # |sd| >= 4.0


class WeeklySummary(BaseModel):
    """Anomaly count summary for a single calendar week.

    Attributes:
        iso_week: ISO week number (1–53).
        year: Calendar year of the week.
        week_label: Human-readable label, e.g. "Week of Jan 6".
        total_anomalies: Total anomaly readings detected this week.
        mild_count: Anomalies in the 2–3 SD range.
        moderate_count: Anomalies in the 3–4 SD range.
        severe_count: Anomalies >=4 SD from baseline.
        high_count: Anomalies where glucose was above bucket baseline.
        low_count: Anomalies where glucose was below bucket baseline.
        weekday_count: Anomalies occurring on weekdays.
        weekend_count: Anomalies occurring on weekends.
        most_affected_period: 2-hour time-period label with highest anomaly
            count for this week, or None if no anomalies.
    """

    iso_week: int = Field(..., ge=1, le=53)
    year: int
    week_label: str
    total_anomalies: int = Field(..., ge=0)
    mild_count: int = Field(0, ge=0)
    moderate_count: int = Field(0, ge=0)
    severe_count: int = Field(0, ge=0)
    high_count: int = Field(0, ge=0)
    low_count: int = Field(0, ge=0)
    weekday_count: int = Field(0, ge=0)
    weekend_count: int = Field(0, ge=0)
    most_affected_period: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class AnomalyDetectionResult(BaseModel):
    """Results from anomaly detection analysis.

    IMPORTANT: This model never contains individual anomalous readings.
    All output is aggregated into WeeklySummary objects.

    Attributes:
        total_anomalies: Total anomalies across all analyzed weeks.
        mild_total: Total mild anomalies (2–3 SD).
        moderate_total: Total moderate anomalies (3–4 SD).
        severe_total: Total severe anomalies (>=4 SD).
        pisa_artifacts_filtered: Count of readings removed as PISA artifacts
            before baseline comparison.
        weekly_summaries: Per-ISO-week breakdown, most recent first,
            capped at MAX_WEEKLY_SUMMARIES entries.
        days_analyzed: Distinct calendar days in the reading set.
        insufficient_data: True when days_analyzed < MIN_DAYS_FOR_BASELINE.
    """

    total_anomalies: int = Field(0, ge=0)
    mild_total: int = Field(0, ge=0)
    moderate_total: int = Field(0, ge=0)
    severe_total: int = Field(0, ge=0)
    pisa_artifacts_filtered: int = Field(0, ge=0)
    weekly_summaries: list[WeeklySummary] = Field(default_factory=list)
    days_analyzed: int = Field(0, ge=0)
    insufficient_data: bool = Field(False)

    model_config = ConfigDict(frozen=True)


def _detect_pisa_artifact(
    glucose_values: list[float],
    timestamps: list[datetime],
) -> list[bool]:
    """Return per-reading mask: True = likely PISA artifact, False = keep.

    Scans chronologically ordered readings for the rapid-drop / recovery
    signature characteristic of Pressure-Induced Sensor Attenuation.
    Runs on all readings (not just overnight) since sensor compression
    can occur during any sustained contact period.

    Args:
        glucose_values: Glucose readings ordered by ascending timestamp.
        timestamps: Matching timestamps (same length, same order).

    Returns:
        List of bool, same length as glucose_values. True = PISA artifact.
    """
    n = len(glucose_values)
    mask = [False] * n

    i = 1
    while i < n:
        reference = glucose_values[i - 1]
        if reference <= 0:
            i += 1
            continue

        drop_pct = (reference - glucose_values[i]) / reference * 100
        if drop_pct < PISA_DROP_THRESHOLD_PCT:
            i += 1
            continue

        # Potential PISA artifact start at index i.
        # Find the nadir within the recovery window.
        drop_start_ts = timestamps[i]
        window_end = drop_start_ts.timestamp() + PISA_RECOVERY_WINDOW_MINUTES * 60

        nadir_idx = i
        nadir_val = glucose_values[i]
        j = i + 1
        while j < n and timestamps[j].timestamp() <= window_end:
            if glucose_values[j] < nadir_val:
                nadir_val = glucose_values[j]
                nadir_idx = j
            j += 1

        # Check for recovery: any reading after nadir (still within window)
        # that returns within PISA_MIN_RECOVERY_RETURN_PCT of reference.
        recovery_threshold = reference * (1.0 - PISA_MIN_RECOVERY_RETURN_PCT / 100.0)
        recovered = False
        k = nadir_idx + 1
        while k < n and timestamps[k].timestamp() <= window_end:
            if glucose_values[k] >= recovery_threshold:
                recovered = True
                break
            k += 1

        if recovered:
            # Flag readings from drop start through nadir as artifacts.
            for idx in range(i, nadir_idx + 1):
                mask[idx] = True
            # Skip past the nadir so its readings aren't used as reference
            # for the next iteration, preventing spurious secondary PISA detections.
            i = nadir_idx + 1
        else:
            i += 1

    return mask


def _filter_pisa_artifacts(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    """Remove PISA artifact readings from the DataFrame.

    Processes each calendar-day segment independently. Only readings
    matching the drop/recovery PISA signature are removed.

    Args:
        df: DataFrame from _build_df() with timestamp, glucose, date columns.

    Returns:
        Tuple of (filtered_df, pisa_count). filtered_df has artifact rows
        removed. pisa_count is the number of readings removed.
    """
    total_pisa = 0
    keep_indices: list[int] = []

    df_indexed = df.with_row_index(name="_row_idx")

    dates = df_indexed.select("date").unique().sort("date")["date"].to_list()

    for day in dates:
        day_df = (
            df_indexed
            .filter(pl.col("date") == day)
            .sort("timestamp")
        )
        glucose_values = day_df["glucose"].to_list()
        timestamps = day_df["timestamp"].to_list()
        row_indices = day_df["_row_idx"].to_list()

        if not glucose_values:
            continue

        pisa_mask = _detect_pisa_artifact(glucose_values, timestamps)

        for idx, is_artifact in enumerate(pisa_mask):
            if is_artifact:
                total_pisa += 1
            else:
                keep_indices.append(row_indices[idx])

    filtered_df = (
        df_indexed
        .filter(pl.col("_row_idx").is_in(keep_indices))
        .drop("_row_idx")
    )
    return filtered_df, total_pisa


def _compute_bucket_baselines(df: pl.DataFrame) -> pl.DataFrame:
    """Compute per-(bucket, day_type) mean and std from historical data.

    Two-step aggregation to avoid inflated SD:
      Step 1: per-day bucket means  (group_by bucket_start, day_type, date)
      Step 2: baseline stats        (group_by bucket_start, day_type)

    Only returns buckets with >= MIN_DAYS_FOR_BASELINE days AND non-null,
    non-zero bucket_std (single-day buckets are dropped).

    Args:
        df: DataFrame from _build_df() with mod, date, day_type, glucose columns.

    Returns:
        DataFrame with columns: bucket_start (int), day_type (str),
        bucket_mean (float), bucket_std (float), days_with_data (int).
    """
    df = df.with_columns(
        (pl.col("mod") // BUCKET_MINUTES * BUCKET_MINUTES).alias("bucket_start")
    )
    per_day = (
        df.group_by(["bucket_start", "day_type", "date"])
        .agg(pl.col("glucose").mean().alias("daily_mean"))
    )
    baselines = (
        per_day.group_by(["bucket_start", "day_type"])
        .agg(
            pl.col("daily_mean").mean().alias("bucket_mean"),
            pl.col("daily_mean").std().alias("bucket_std"),
            pl.col("daily_mean").count().alias("days_with_data"),
        )
        .filter(pl.col("days_with_data") >= MIN_DAYS_FOR_BASELINE)
        .filter(pl.col("bucket_std").is_not_null())
        .filter(pl.col("bucket_std") > 0.0)
    )
    return baselines


def _classify_severity(abs_sd: float) -> Optional[AnomalySeverity]:
    """Classify anomaly severity from absolute SD deviation.

    Returns None for readings within ±2 SD (not anomalous).

    Args:
        abs_sd: Absolute value of SD deviation from bucket baseline.

    Returns:
        AnomalySeverity or None if not anomalous.
    """
    if abs_sd < ANOMALY_SD_MILD:
        return None
    elif abs_sd < ANOMALY_SD_MODERATE:
        return AnomalySeverity.MILD
    elif abs_sd < ANOMALY_SD_SEVERE:
        return AnomalySeverity.MODERATE
    else:
        return AnomalySeverity.SEVERE


def _format_period_label(period_hour: int) -> str:
    """Format a 2-hour period as a human-readable label like '2pm–4pm'.

    Args:
        period_hour: Start hour of the 2-hour period (0–22).

    Returns:
        Label such as '2pm–4pm' or '12am–2am'.
    """
    def _hour_label(h: int) -> str:
        h = h % 24
        if h == 0:
            return "12am"
        elif h < 12:
            return f"{h}am"
        elif h == 12:
            return "12pm"
        else:
            return f"{h - 12}pm"

    end_hour = (period_hour + 2) % 24
    return f"{_hour_label(period_hour)}–{_hour_label(end_hour)}"


def _build_weekly_summaries(anomaly_df: pl.DataFrame) -> list[WeeklySummary]:
    """Build WeeklySummary objects from classified anomaly readings.

    Args:
        anomaly_df: DataFrame of anomalous readings with columns:
            timestamp (datetime), severity (str), direction (str "high"/"low"),
            day_type (str), bucket_start (int).

    Returns:
        List of WeeklySummary sorted by most recent first,
        capped at MAX_WEEKLY_SUMMARIES entries. Empty list if anomaly_df
        has no rows.
    """
    if anomaly_df.height == 0:
        return []

    # Add iso_year and iso_week columns.
    # dt.iso_year() must be paired with dt.week() (ISO week number) so that
    # year-boundary dates (e.g. 2021-01-01 = ISO week 53 of 2020) are grouped
    # into the correct week.  Using dt.year() (calendar year) here would cause
    # dt.date.fromisocalendar(2021, 53, 1) to raise ValueError for years that
    # only have 52 ISO weeks, crashing the entire upload response.
    anomaly_df = anomaly_df.with_columns([
        pl.col("timestamp").dt.iso_year().alias("year"),
        pl.col("timestamp").dt.week().alias("iso_week"),
    ])

    # Collect unique (year, iso_week) pairs sorted descending.
    week_pairs = (
        anomaly_df
        .select(["year", "iso_week"])
        .unique()
        .sort(["year", "iso_week"], descending=True)
    )

    summaries: list[WeeklySummary] = []

    for row in week_pairs.iter_rows(named=True):
        year = int(row["year"])
        iso_week = int(row["iso_week"])

        week_df = anomaly_df.filter(
            (pl.col("year") == year) & (pl.col("iso_week") == iso_week)
        )

        total = week_df.height
        mild_count = int((week_df["severity"] == "mild").sum())
        moderate_count = int((week_df["severity"] == "moderate").sum())
        severe_count = int((week_df["severity"] == "severe").sum())
        high_count = int((week_df["direction"] == "high").sum())
        low_count = int((week_df["direction"] == "low").sum())
        weekday_count = int((week_df["day_type"] == "weekday").sum())
        weekend_count = int((week_df["day_type"] == "weekend").sum())

        # Find most affected 2-hour period.
        most_affected_period: Optional[str] = None
        if total > 0:
            period_df = (
                week_df
                .with_columns(
                    (pl.col("bucket_start") // 120 * 2).alias("period_hour")
                )
                .group_by("period_hour")
                .agg(pl.len().alias("count"))
                .sort(["count", "period_hour"], descending=[True, False])
            )
            top_period_hour = int(period_df["period_hour"][0])
            most_affected_period = _format_period_label(top_period_hour)

        # Build week label from the Monday of the ISO week.
        monday = dt.date.fromisocalendar(year, iso_week, 1)
        week_label = f"Week of {monday.strftime('%b')} {monday.day}"

        summaries.append(WeeklySummary(
            iso_week=iso_week,
            year=year,
            week_label=week_label,
            total_anomalies=total,
            mild_count=mild_count,
            moderate_count=moderate_count,
            severe_count=severe_count,
            high_count=high_count,
            low_count=low_count,
            weekday_count=weekday_count,
            weekend_count=weekend_count,
            most_affected_period=most_affected_period,
        ))

    return summaries[:MAX_WEEKLY_SUMMARIES]


def analyze_anomalies(
    readings: list[CGMReading],
    min_days: int = MIN_DAYS_FOR_BASELINE,
) -> AnomalyDetectionResult:
    """Detect glucose anomalies relative to personal time-bucketed baseline.

    Algorithm:
      1. Build DataFrame via _build_df() (adds mod, date, day_type).
      2. Filter PISA artifacts (rapid drop/recovery sensor artifacts).
      3. Compute per-(bucket_start, day_type) baseline (mean + std).
      4. Join baseline to each reading, compute signed SD deviation.
      5. Classify readings with |sd| >= 2.0 by severity and direction.
      6. Aggregate classified anomalies into weekly summaries.

    Args:
        readings: List of CGM readings (sorted or unsorted).
        min_days: Minimum distinct days required for valid baseline.

    Returns:
        AnomalyDetectionResult. Never raises — returns
        insufficient_data=True on empty input or insufficient days.
    """
    if not readings:
        return AnomalyDetectionResult(insufficient_data=True)

    df = _build_df(readings)
    days_analyzed = df.select(pl.col("date").n_unique()).item()

    if days_analyzed < min_days:
        return AnomalyDetectionResult(
            days_analyzed=days_analyzed,
            insufficient_data=True,
        )

    # Step 1: Filter PISA artifacts
    df_clean, pisa_count = _filter_pisa_artifacts(df)

    # Step 2: Compute baselines
    baselines = _compute_bucket_baselines(df_clean)

    if baselines.height == 0:
        # No buckets with non-zero std (e.g. perfectly uniform data).
        # Data is sufficient (days_analyzed >= min_days), but there is no
        # variance to detect anomalies against — return 0 anomalies, not
        # insufficient_data, so callers know analysis ran successfully.
        return AnomalyDetectionResult(
            days_analyzed=days_analyzed,
            pisa_artifacts_filtered=pisa_count,
            insufficient_data=False,
        )

    # Step 3: Join and compute SD deviation per reading
    df_with_bucket = df_clean.with_columns(
        (pl.col("mod") // BUCKET_MINUTES * BUCKET_MINUTES).alias("bucket_start")
    )
    df_joined = df_with_bucket.join(
        baselines, on=["bucket_start", "day_type"], how="left"
    ).filter(
        pl.col("bucket_mean").is_not_null() & pl.col("bucket_std").is_not_null()
    )

    df_joined = df_joined.with_columns(
        ((pl.col("glucose") - pl.col("bucket_mean")) / pl.col("bucket_std"))
        .alias("sd_deviation")
    )

    # Step 4: Classify anomalies (|sd| >= 2.0)
    anomaly_rows = df_joined.filter(pl.col("sd_deviation").abs() >= ANOMALY_SD_MILD)

    if anomaly_rows.height == 0:
        return AnomalyDetectionResult(
            days_analyzed=days_analyzed,
            pisa_artifacts_filtered=pisa_count,
            insufficient_data=False,
        )

    # Add severity and direction columns for aggregation.
    # Build Python-side lists to avoid complex Polars when/then chains for enum.
    severity_values = [
        _classify_severity(abs(v)).value  # type: ignore[union-attr]
        for v in anomaly_rows["sd_deviation"].to_list()
    ]
    direction_values = [
        "high" if v > 0 else "low"
        for v in anomaly_rows["sd_deviation"].to_list()
    ]
    anomaly_df = anomaly_rows.with_columns([
        pl.Series("severity", severity_values),
        pl.Series("direction", direction_values),
    ])

    # Step 5: Build weekly summaries
    weekly_summaries = _build_weekly_summaries(anomaly_df)

    total = anomaly_df.height
    mild = int((anomaly_df["severity"] == "mild").sum())
    moderate = int((anomaly_df["severity"] == "moderate").sum())
    severe = int((anomaly_df["severity"] == "severe").sum())

    return AnomalyDetectionResult(
        total_anomalies=total,
        mild_total=mild,
        moderate_total=moderate,
        severe_total=severe,
        pisa_artifacts_filtered=pisa_count,
        weekly_summaries=weekly_summaries,
        days_analyzed=days_analyzed,
        insufficient_data=False,
    )
