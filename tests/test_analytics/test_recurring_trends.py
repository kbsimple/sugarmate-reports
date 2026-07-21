"""Tests for recurring trend detection."""

import math
from datetime import datetime, timedelta

import pytest

from cgm_insights.analytics.recurring_trends import (
    MIN_MAGNITUDE_MG_DL,
    RecurringTrendsResult,
    TrendSlot,
    _build_daily_avgs,
    _has_coverage,
    _linear_slope,
    _quartiles,
    _slot_index,
    _slot_label,
    analyze_recurring_trends,
)
from cgm_insights.models import CGMReading


# ── Fixtures ───────────────────────────────────────────────────────────────────


def _reading(dt: datetime, glucose: float) -> CGMReading:
    return CGMReading(timestamp=dt, glucose_mg_dl=glucose, source="test")


def _days_with_rise(
    n_days: int,
    rise_start_hour: float = 10.5,   # 10:30
    rise_end_hour: float = 14.0,     # 14:00
    start_glucose: float = 110.0,
    end_glucose: float = 160.0,
    base_date: datetime | None = None,
    flat_days: set[int] | None = None,
) -> list[CGMReading]:
    """Create n_days of readings with a consistent rise in the given window.

    Outside the rise window, glucose is constant at start_glucose.
    flat_days: indices of days where the rise is replaced by a flat line
               (used to test that inconsistent days lower the observed count).
    """
    base = base_date or datetime(2026, 1, 1)
    flat_days = flat_days or set()
    readings: list[CGMReading] = []

    for day_idx in range(n_days):
        day = base + timedelta(days=day_idx)
        # readings every 30 min throughout the day
        for slot in range(48):
            hour = slot * 0.5
            ts = day + timedelta(hours=hour)
            if day_idx in flat_days:
                glucose = start_glucose
            elif rise_start_hour <= hour <= rise_end_hour:
                frac = (hour - rise_start_hour) / (rise_end_hour - rise_start_hour)
                glucose = start_glucose + frac * (end_glucose - start_glucose)
            else:
                glucose = start_glucose
            readings.append(_reading(ts, glucose))

    return readings


def _days_with_fall(
    n_days: int,
    fall_start_hour: float = 16.0,
    fall_end_hour: float = 19.0,
    start_glucose: float = 160.0,
    end_glucose: float = 110.0,
    base_date: datetime | None = None,
) -> list[CGMReading]:
    base = base_date or datetime(2026, 1, 1)
    readings: list[CGMReading] = []
    for day_idx in range(n_days):
        day = base + timedelta(days=day_idx)
        for slot in range(48):
            hour = slot * 0.5
            ts = day + timedelta(hours=hour)
            if fall_start_hour <= hour <= fall_end_hour:
                frac = (hour - fall_start_hour) / (fall_end_hour - fall_start_hour)
                glucose = start_glucose + frac * (end_glucose - start_glucose)
            else:
                glucose = start_glucose
            readings.append(_reading(ts, glucose))
    return readings


# ── Unit tests: helpers ────────────────────────────────────────────────────────


class TestSlotHelpers:
    def test_slot_index_midnight(self):
        assert _slot_index(datetime(2026, 1, 1, 0, 0)) == 0

    def test_slot_index_half_past_ten(self):
        # 10:30 → (10*60 + 30) // 30 = 21
        assert _slot_index(datetime(2026, 1, 1, 10, 30)) == 21

    def test_slot_index_two_pm(self):
        # 14:00 → 14*2 = 28
        assert _slot_index(datetime(2026, 1, 1, 14, 0)) == 28

    def test_slot_label_midnight(self):
        assert _slot_label(0) == "12:00 AM"

    def test_slot_label_noon(self):
        assert _slot_label(24) == "12:00 PM"

    def test_slot_label_half_past_ten(self):
        assert _slot_label(21) == "10:30 AM"

    def test_slot_label_two_pm(self):
        assert _slot_label(28) == "2:00 PM"

    def test_slot_label_eleven_thirty_pm(self):
        assert _slot_label(47) == "11:30 PM"


class TestLinearSlope:
    def test_flat_line_slope_is_zero(self):
        assert _linear_slope([100.0, 100.0, 100.0]) == pytest.approx(0.0)

    def test_rising_slope_positive(self):
        assert _linear_slope([100.0, 110.0, 120.0]) > 0

    def test_falling_slope_negative(self):
        assert _linear_slope([120.0, 110.0, 100.0]) < 0

    def test_single_value_returns_zero(self):
        assert _linear_slope([150.0]) == 0.0


class TestQuartiles:
    def test_symmetric_distribution(self):
        q1, med, q3 = _quartiles([100.0, 110.0, 120.0, 130.0, 140.0])
        assert q1 <= med <= q3

    def test_single_value(self):
        q1, med, q3 = _quartiles([120.0])
        assert q1 == med == q3 == 120.0

    def test_two_values(self):
        q1, med, q3 = _quartiles([100.0, 200.0])
        assert q1 <= med <= q3


class TestHasCoverage:
    def test_full_coverage(self):
        day = {s: 100.0 for s in range(10)}
        assert _has_coverage(day, 0, 3) is True

    def test_empty_day_fails(self):
        assert _has_coverage({}, 0, 5) is False

    def test_sparse_day_below_threshold_fails(self):
        # window has 6 slots (0-5), coverage threshold 40% = needs 2.4 → 3 (int)
        # only 1 slot covered → insufficient
        day = {0: 100.0}
        assert _has_coverage(day, 0, 5) is False


class TestBuildDailyAvgs:
    def test_averages_multiple_readings_per_slot(self):
        readings = [
            _reading(datetime(2026, 1, 1, 10, 0), 100.0),
            _reading(datetime(2026, 1, 1, 10, 15), 120.0),  # same slot
        ]
        avgs = _build_daily_avgs(readings)
        slot = _slot_index(datetime(2026, 1, 1, 10, 0))
        assert avgs["2026-01-01"][slot] == pytest.approx(110.0)

    def test_groups_by_calendar_day(self):
        readings = [
            _reading(datetime(2026, 1, 1, 8, 0), 100.0),
            _reading(datetime(2026, 1, 2, 8, 0), 140.0),
        ]
        avgs = _build_daily_avgs(readings)
        assert "2026-01-01" in avgs
        assert "2026-01-02" in avgs


# ── Integration tests: analyze_recurring_trends ────────────────────────────────


class TestAnalyzeRecurringTrends:
    def test_empty_readings_returns_insufficient(self):
        result = analyze_recurring_trends([])
        assert result.insufficient_data is True
        assert result.trends == []

    def test_too_few_days_returns_insufficient(self):
        readings = _days_with_rise(n_days=2)
        result = analyze_recurring_trends(readings, min_days=3)
        assert result.insufficient_data is True

    def test_detects_consistent_rise(self):
        readings = _days_with_rise(n_days=7, start_glucose=110.0, end_glucose=165.0)
        result = analyze_recurring_trends(readings, min_days=3)
        assert result.insufficient_data is False
        assert len(result.trends) >= 1
        trend = result.trends[0]
        assert trend.direction == "rising"
        assert trend.days_observed >= 3

    def test_detects_consistent_fall(self):
        readings = _days_with_fall(n_days=7)
        result = analyze_recurring_trends(readings, min_days=3)
        assert result.insufficient_data is False
        assert any(t.direction == "falling" for t in result.trends)

    def test_no_trend_for_flat_glucose(self):
        """Constant glucose across all days yields no directional trends."""
        base = datetime(2026, 1, 1)
        readings = [
            _reading(base + timedelta(days=d, hours=h), 130.0)
            for d in range(7)
            for h in range(0, 24, 1)
        ]
        result = analyze_recurring_trends(readings, min_days=3)
        assert result.insufficient_data is False
        assert result.trends == []

    def test_inconsistent_days_not_surfaced(self):
        """If rise only occurs on 2 of 5 days, it should not be surfaced (below min_days=3)."""
        readings = _days_with_rise(
            n_days=5, start_glucose=110.0, end_glucose=165.0, flat_days={1, 2, 3}
        )
        result = analyze_recurring_trends(readings, min_days=3)
        # Only 2 rising days remain; trend should not be returned
        for t in result.trends:
            assert t.days_observed >= 3

    def test_days_analyzed_respects_lookback(self):
        """analyze_recurring_trends uses only the most recent lookback_days days."""
        readings = _days_with_rise(n_days=15)
        result = analyze_recurring_trends(readings, lookback_days=10)
        assert result.days_analyzed <= 10

    def test_slot_stats_populated(self):
        readings = _days_with_rise(n_days=7, start_glucose=100.0, end_glucose=160.0)
        result = analyze_recurring_trends(readings, min_days=3)
        assert result.insufficient_data is False
        assert len(result.trends) >= 1
        trend = result.trends[0]
        assert len(trend.slots) >= 2
        for slot in trend.slots:
            assert isinstance(slot, TrendSlot)
            assert slot.q1 <= slot.median <= slot.q3

    def test_start_before_end_label(self):
        """start_slot < end_slot always holds (trends sorted by time window)."""
        readings = _days_with_rise(n_days=7, start_glucose=100.0, end_glucose=160.0)
        result = analyze_recurring_trends(readings, min_days=3)
        for t in result.trends:
            assert t.start_slot < t.end_slot

    def test_max_five_trends_returned(self):
        """The algorithm caps output at MAX_TRENDS (5)."""
        # Use data with multiple distinct trend windows
        base = datetime(2026, 1, 1)
        readings = _days_with_rise(
            n_days=10, rise_start_hour=2.0, rise_end_hour=4.0,
            start_glucose=90.0, end_glucose=140.0, base_date=base,
        ) + _days_with_rise(
            n_days=10, rise_start_hour=10.0, rise_end_hour=13.0,
            start_glucose=120.0, end_glucose=180.0, base_date=base,
        ) + _days_with_fall(
            n_days=10, fall_start_hour=16.0, fall_end_hour=19.0,
            start_glucose=170.0, end_glucose=110.0, base_date=base,
        )
        result = analyze_recurring_trends(readings, min_days=3)
        assert len(result.trends) <= 5

    def test_consistency_pct_within_range(self):
        readings = _days_with_rise(n_days=7, start_glucose=100.0, end_glucose=160.0)
        result = analyze_recurring_trends(readings, min_days=3)
        for t in result.trends:
            assert 0.0 <= t.consistency_pct <= 100.0

    def test_result_is_pydantic_model(self):
        readings = _days_with_rise(n_days=5)
        result = analyze_recurring_trends(readings, min_days=3)
        assert isinstance(result, RecurringTrendsResult)
        dumped = result.model_dump()
        assert "trends" in dumped
        assert "days_analyzed" in dumped
        assert "insufficient_data" in dumped
