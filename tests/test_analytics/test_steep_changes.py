"""Tests for steep glucose change detection."""

from datetime import datetime, timedelta

import pytest

from cgm_insights.analytics.steep_changes import (
    THRESHOLD_MG_DL,
    WINDOW_MINUTES,
    SteepChangesResult,
    DaySteepChanges,
    SteepChangeEvent,
    analyze_steep_changes,
)
from cgm_insights.models import CGMReading


# ── Fixtures ───────────────────────────────────────────────────────────────────


def _reading(dt: datetime, glucose: float) -> CGMReading:
    return CGMReading(timestamp=dt, glucose_mg_dl=glucose, source="test")


def _flat_readings(
    n_days: int = 3,
    glucose: float = 120.0,
    base: datetime | None = None,
) -> list[CGMReading]:
    """Uniform 5-minute readings at a constant glucose level."""
    start = base or datetime(2026, 1, 1)
    readings = []
    total_minutes = n_days * 24 * 60
    for m in range(0, total_minutes, 5):
        readings.append(_reading(start + timedelta(minutes=m), glucose))
    return readings


def _spike_at(
    ts: datetime,
    before: float = 100.0,
    after: float = 210.0,
    readings: list[CGMReading] | None = None,
) -> list[CGMReading]:
    """Return a minimal set of readings that produce a steep rise at ts.

    Returns enough context so the detector has something to work with.
    The spike is manufactured by placing a high reading 30 minutes after ts.
    """
    r = readings or []
    # Reading at ts (start of spike)
    r.append(_reading(ts, before))
    # Reading 30 min later (peak)
    r.append(_reading(ts + timedelta(minutes=30), after))
    return r


def _drop_at(
    ts: datetime,
    before: float = 210.0,
    after: float = 90.0,
    readings: list[CGMReading] | None = None,
) -> list[CGMReading]:
    r = readings or []
    r.append(_reading(ts, before))
    r.append(_reading(ts + timedelta(minutes=30), after))
    return r


# ── Unit: empty / insufficient data ───────────────────────────────────────────


class TestInsufficientData:
    def test_empty_returns_insufficient(self):
        result = analyze_steep_changes([])
        assert result.insufficient_data is True

    def test_too_few_readings(self):
        readings = [_reading(datetime(2026, 1, 1, h), 120.0) for h in range(5)]
        result = analyze_steep_changes(readings)
        assert result.insufficient_data is True

    def test_sufficient_flat_data_not_insufficient(self):
        result = analyze_steep_changes(_flat_readings(n_days=3))
        assert result.insufficient_data is False


# ── Unit: no events in flat data ──────────────────────────────────────────────


class TestFlatData:
    def test_no_rises_in_flat_data(self):
        result = analyze_steep_changes(_flat_readings(n_days=3))
        assert result.total_rises == 0

    def test_no_drops_in_flat_data(self):
        result = analyze_steep_changes(_flat_readings(n_days=3))
        assert result.total_drops == 0

    def test_events_empty_in_flat_data(self):
        result = analyze_steep_changes(_flat_readings(n_days=3))
        assert result.events == []


# ── Unit: event detection ─────────────────────────────────────────────────────


class TestSteepRiseDetection:
    def test_detects_rise_above_threshold(self):
        base = datetime(2026, 1, 5, 10, 0)
        readings = _flat_readings(n_days=1, glucose=110.0) + _spike_at(base)
        result = analyze_steep_changes(readings)
        assert result.total_rises >= 1

    def test_does_not_detect_rise_below_threshold(self):
        base = datetime(2026, 1, 5, 10, 0)
        # Delta = 90 mg/dL — below 100 threshold
        readings = _flat_readings(n_days=1) + [
            _reading(base, 100.0),
            _reading(base + timedelta(minutes=30), 190.0),
        ]
        result = analyze_steep_changes(readings, threshold_mg_dl=100.0)
        # 90 < 100 so no event
        events = [e for e in result.events if e.direction == "rise" and e.timestamp.startswith("2026-01-05T10:")]
        assert len(events) == 0

    def test_rise_direction_correct(self):
        base = datetime(2026, 1, 5, 10, 0)
        readings = _flat_readings(n_days=1, glucose=110.0) + _spike_at(base)
        result = analyze_steep_changes(readings)
        rise_events = [e for e in result.events if e.direction == "rise"]
        assert len(rise_events) >= 1

    def test_rise_delta_positive(self):
        base = datetime(2026, 1, 5, 10, 0)
        readings = _flat_readings(n_days=1, glucose=110.0) + _spike_at(base, before=100.0, after=220.0)
        result = analyze_steep_changes(readings)
        rises = [e for e in result.events if e.direction == "rise"]
        assert all(e.delta_mg_dl > 0 for e in rises)


class TestSteepDropDetection:
    def test_detects_drop_below_threshold(self):
        base = datetime(2026, 1, 5, 14, 0)
        readings = _flat_readings(n_days=1, glucose=180.0) + _drop_at(base)
        result = analyze_steep_changes(readings)
        assert result.total_drops >= 1

    def test_drop_direction_correct(self):
        base = datetime(2026, 1, 5, 14, 0)
        readings = _flat_readings(n_days=1, glucose=180.0) + _drop_at(base)
        result = analyze_steep_changes(readings)
        drop_events = [e for e in result.events if e.direction == "drop"]
        assert len(drop_events) >= 1

    def test_drop_delta_negative(self):
        base = datetime(2026, 1, 5, 14, 0)
        readings = _flat_readings(n_days=1, glucose=180.0) + _drop_at(base, before=220.0, after=90.0)
        result = analyze_steep_changes(readings)
        drops = [e for e in result.events if e.direction == "drop"]
        assert all(e.delta_mg_dl < 0 for e in drops)


# ── Unit: cooldown ────────────────────────────────────────────────────────────


class TestCooldown:
    def test_second_rise_within_cooldown_suppressed(self):
        """Two rises 5 minutes apart should count as one."""
        base = datetime(2026, 1, 5, 10, 0)
        readings = (
            _flat_readings(n_days=1, glucose=110.0)
            + _spike_at(base)
            + _spike_at(base + timedelta(minutes=5))
        )
        result = analyze_steep_changes(readings)
        # Should detect only 1 rise (second is within cooldown)
        rises_at_10 = [
            e for e in result.events
            if e.direction == "rise" and e.timestamp.startswith("2026-01-05T10:")
        ]
        assert len(rises_at_10) == 1

    def test_second_rise_after_cooldown_counted(self):
        """Two rises 25 minutes apart (> 20-min cooldown) should both count."""
        base = datetime(2026, 1, 5, 10, 0)
        readings = (
            _flat_readings(n_days=2, glucose=110.0)
            + _spike_at(base)
            + _spike_at(base + timedelta(minutes=25))
        )
        result = analyze_steep_changes(readings)
        rises = [e for e in result.events if e.direction == "rise"]
        assert len(rises) >= 2

    def test_drop_cooldown_independent_of_rise_cooldown(self):
        """Simultaneous rise and drop events at the same time should both fire."""
        base = datetime(2026, 1, 5, 10, 0)
        readings = _flat_readings(n_days=1, glucose=150.0)
        # Rise: starts at base, ends high
        readings.append(_reading(base, 100.0))
        readings.append(_reading(base + timedelta(minutes=30), 220.0))
        # Drop: starts at base+60, ends low
        readings.append(_reading(base + timedelta(minutes=60), 200.0))
        readings.append(_reading(base + timedelta(minutes=90), 80.0))
        result = analyze_steep_changes(readings)
        assert result.total_rises >= 1
        assert result.total_drops >= 1


# ── Unit: window tolerance ────────────────────────────────────────────────────


class TestWindowTolerance:
    def test_reading_at_27_min_accepted(self):
        """27 minutes is within the ±5 tolerance."""
        base = datetime(2026, 1, 5, 10, 0)
        readings = _flat_readings(n_days=1, glucose=110.0) + [
            _reading(base, 100.0),
            _reading(base + timedelta(minutes=27), 220.0),
        ]
        result = analyze_steep_changes(readings)
        assert result.total_rises >= 1

    def test_reading_at_20_min_rejected(self):
        """20 minutes is outside the 25-35 min acceptance window."""
        base = datetime(2026, 1, 5, 10, 0)
        readings = _flat_readings(n_days=1, glucose=110.0) + [
            _reading(base, 100.0),
            _reading(base + timedelta(minutes=20), 220.0),
        ]
        result = analyze_steep_changes(readings)
        rises = [
            e for e in result.events
            if e.direction == "rise" and e.timestamp.startswith("2026-01-05T10:")
        ]
        assert len(rises) == 0


# ── Integration: aggregates ───────────────────────────────────────────────────


class TestAggregates:
    def test_days_analyzed_matches_dataset(self):
        result = analyze_steep_changes(_flat_readings(n_days=5))
        assert result.days_analyzed == 5

    def test_by_day_has_entry_per_day(self):
        result = analyze_steep_changes(_flat_readings(n_days=3))
        assert len(result.by_day) == 3

    def test_rises_by_hour_length_24(self):
        result = analyze_steep_changes(_flat_readings(n_days=3))
        assert len(result.rises_by_hour) == 24

    def test_drops_by_hour_length_24(self):
        result = analyze_steep_changes(_flat_readings(n_days=3))
        assert len(result.drops_by_hour) == 24

    def test_avg_per_day_consistency(self):
        """avg_rises_per_day * days_analyzed should approximately equal total_rises."""
        base = datetime(2026, 1, 1)
        readings = _flat_readings(n_days=7, glucose=110.0)
        # Add one rise on day 3
        day3 = base + timedelta(days=2, hours=10)
        readings += _spike_at(day3)
        result = analyze_steep_changes(readings)
        assert abs(result.avg_rises_per_day * result.days_analyzed - result.total_rises) < 0.01

    def test_hourly_bucket_matches_event_hour(self):
        base = datetime(2026, 1, 5, 8, 0)  # hour 8
        readings = _flat_readings(n_days=2, glucose=110.0) + _spike_at(base)
        result = analyze_steep_changes(readings)
        assert result.rises_by_hour[8] >= 1

    def test_max_rises_in_day_correct(self):
        base = datetime(2026, 1, 1)
        readings = _flat_readings(n_days=3, glucose=110.0)
        # Use non-5-minute offsets to avoid clashing with flat readings
        t1 = base + timedelta(hours=6, minutes=1)
        t2 = base + timedelta(hours=14, minutes=1)
        readings += [
            _reading(t1, 100.0),
            _reading(t1 + timedelta(minutes=30), 220.0),
            _reading(t2, 100.0),
            _reading(t2 + timedelta(minutes=30), 220.0),
        ]
        result = analyze_steep_changes(readings)
        assert result.max_rises_in_day >= 2

    def test_day_with_no_events_present_in_by_day(self):
        base = datetime(2026, 1, 1)
        readings = _flat_readings(n_days=5, glucose=120.0)
        # One rise on day 2
        readings += _spike_at(base + timedelta(days=1, hours=10))
        result = analyze_steep_changes(readings)
        flat_days = [d for d in result.by_day if d.rises == 0 and d.drops == 0]
        assert len(flat_days) >= 4

    def test_result_serialises_to_dict(self):
        result = analyze_steep_changes(_flat_readings(n_days=3))
        d = result.model_dump()
        assert "total_rises" in d
        assert "total_drops" in d
        assert "by_day" in d
        assert "rises_by_hour" in d
        assert "events" in d

    def test_threshold_configurable(self):
        """Using a lower threshold should detect more events."""
        base = datetime(2026, 1, 5, 10, 0)
        readings = _flat_readings(n_days=2, glucose=110.0) + [
            _reading(base, 100.0),
            _reading(base + timedelta(minutes=30), 165.0),  # delta = 65
        ]
        result_strict = analyze_steep_changes(readings, threshold_mg_dl=100.0)
        result_loose = analyze_steep_changes(readings, threshold_mg_dl=60.0)
        assert result_loose.total_rises > result_strict.total_rises
