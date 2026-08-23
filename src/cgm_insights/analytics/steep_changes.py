"""Steep glucose change detection — rises and drops > 100 mg/dL in 30 minutes.

A "steep change" is defined as a glucose shift of more than THRESHOLD_MG_DL
within a WINDOW_MINUTES window (using the reading closest to that target
duration, accepted within ±WINDOW_TOLERANCE_MINUTES).

A cooldown of COOLDOWN_MINUTES prevents double-counting the same underlying
spike or crash: once an event is recorded, events in the same direction are
suppressed for that duration.

Outputs
-------
- Total steep rises and drops over the full dataset.
- Average counts per day and the day with the maximum count.
- Event counts bucketed by hour-of-day (for a frequency-by-time chart).
- Per-day rise/drop totals for trend display.
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel

THRESHOLD_MG_DL: float = 100.0
WINDOW_MINUTES: int = 30
WINDOW_TOLERANCE_MINUTES: int = 5   # accept 25–35 min windows
COOLDOWN_MINUTES: int = 20          # min gap between events of same direction

MIN_READINGS: int = 10              # need at least this many readings


# ── Models ─────────────────────────────────────────────────────────────────────


class SteepChangeEvent(BaseModel):
    """A single steep-change event."""

    timestamp: str                          # ISO string "YYYY-MM-DDTHH:MM"
    start_glucose: float
    end_glucose: float
    delta_mg_dl: float                      # positive = rise, negative = drop
    direction: Literal["rise", "drop"]
    duration_minutes: int                   # actual window used


class DaySteepChanges(BaseModel):
    """Per-day tally."""

    date: str                               # "YYYY-MM-DD"
    rises: int
    drops: int


class SteepChangesResult(BaseModel):
    """Full result from steep-change analysis."""

    insufficient_data: bool
    threshold_mg_dl: float
    total_rises: int
    total_drops: int
    days_analyzed: int
    avg_rises_per_day: float
    avg_drops_per_day: float
    max_rises_in_day: int
    max_drops_in_day: int
    by_day: list[DaySteepChanges]
    rises_by_hour: list[int]                # length 24 — count by hour of day
    drops_by_hour: list[int]
    events: list[SteepChangeEvent]


# ── Public API ─────────────────────────────────────────────────────────────────


def analyze_steep_changes(
    readings: list,
    threshold_mg_dl: float = THRESHOLD_MG_DL,
) -> SteepChangesResult:
    """Detect steep glucose rises and drops (> threshold in 30 minutes).

    Args:
        readings: List of CGMReading objects with .timestamp and .glucose_mg_dl.
        threshold_mg_dl: Magnitude that constitutes a "steep" change.

    Returns:
        SteepChangesResult with per-day and hourly aggregates plus individual
        events, or insufficient_data=True when the dataset is too small.
    """
    _empty = SteepChangesResult(
        insufficient_data=True,
        threshold_mg_dl=threshold_mg_dl,
        total_rises=0,
        total_drops=0,
        days_analyzed=0,
        avg_rises_per_day=0.0,
        avg_drops_per_day=0.0,
        max_rises_in_day=0,
        max_drops_in_day=0,
        by_day=[],
        rises_by_hour=[0] * 24,
        drops_by_hour=[0] * 24,
        events=[],
    )

    if not readings or len(readings) < MIN_READINGS:
        return _empty

    sorted_readings = sorted(readings, key=lambda r: r.timestamp)
    n = len(sorted_readings)

    timestamps: list[datetime] = [r.timestamp for r in sorted_readings]
    glucoses: list[float] = [r.glucose_mg_dl for r in sorted_readings]

    target_td = timedelta(minutes=WINDOW_MINUTES)
    min_td = timedelta(minutes=WINDOW_MINUTES - WINDOW_TOLERANCE_MINUTES)
    max_td = timedelta(minutes=WINDOW_MINUTES + WINDOW_TOLERANCE_MINUTES)
    cooldown_td = timedelta(minutes=COOLDOWN_MINUTES)

    events: list[SteepChangeEvent] = []
    last_rise_ts: datetime | None = None
    last_drop_ts: datetime | None = None

    for i in range(n):
        ts_i = timestamps[i]
        min_ts = ts_i + min_td
        max_ts = ts_i + max_td
        target_ts = ts_i + target_td

        # Binary-search for readings in the acceptance window [min_ts, max_ts]
        lo = bisect.bisect_left(timestamps, min_ts)
        hi = bisect.bisect_right(timestamps, max_ts)
        if lo >= hi:
            continue

        # Pick the reading closest to the 30-minute target
        best_j = min(range(lo, hi), key=lambda k: abs(timestamps[k] - target_ts))

        delta = glucoses[best_j] - glucoses[i]

        if delta > threshold_mg_dl:
            if last_rise_ts is None or (ts_i - last_rise_ts) >= cooldown_td:
                duration = int((timestamps[best_j] - ts_i).total_seconds() / 60)
                events.append(
                    SteepChangeEvent(
                        timestamp=ts_i.strftime("%Y-%m-%dT%H:%M"),
                        start_glucose=round(glucoses[i], 1),
                        end_glucose=round(glucoses[best_j], 1),
                        delta_mg_dl=round(delta, 1),
                        direction="rise",
                        duration_minutes=duration,
                    )
                )
                last_rise_ts = ts_i
        elif delta < -threshold_mg_dl:
            if last_drop_ts is None or (ts_i - last_drop_ts) >= cooldown_td:
                duration = int((timestamps[best_j] - ts_i).total_seconds() / 60)
                events.append(
                    SteepChangeEvent(
                        timestamp=ts_i.strftime("%Y-%m-%dT%H:%M"),
                        start_glucose=round(glucoses[i], 1),
                        end_glucose=round(glucoses[best_j], 1),
                        delta_mg_dl=round(delta, 1),
                        direction="drop",
                        duration_minutes=duration,
                    )
                )
                last_drop_ts = ts_i

    # ── Aggregate ──────────────────────────────────────────────────────────────
    day_rises: dict[str, int] = defaultdict(int)
    day_drops: dict[str, int] = defaultdict(int)
    rises_by_hour: list[int] = [0] * 24
    drops_by_hour: list[int] = [0] * 24

    for ev in events:
        date_str = ev.timestamp[:10]        # "YYYY-MM-DD"
        hour = int(ev.timestamp[11:13])     # "HH"
        if ev.direction == "rise":
            day_rises[date_str] += 1
            rises_by_hour[hour] += 1
        else:
            day_drops[date_str] += 1
            drops_by_hour[hour] += 1

    all_dates = sorted({ts.strftime("%Y-%m-%d") for ts in timestamps})
    days_analyzed = len(all_dates)

    by_day = [
        DaySteepChanges(date=d, rises=day_rises.get(d, 0), drops=day_drops.get(d, 0))
        for d in all_dates
    ]

    total_rises = sum(1 for e in events if e.direction == "rise")
    total_drops = sum(1 for e in events if e.direction == "drop")

    max_rises = max((d.rises for d in by_day), default=0)
    max_drops = max((d.drops for d in by_day), default=0)

    return SteepChangesResult(
        insufficient_data=False,
        threshold_mg_dl=threshold_mg_dl,
        total_rises=total_rises,
        total_drops=total_drops,
        days_analyzed=days_analyzed,
        avg_rises_per_day=round(total_rises / days_analyzed, 2) if days_analyzed else 0.0,
        avg_drops_per_day=round(total_drops / days_analyzed, 2) if days_analyzed else 0.0,
        max_rises_in_day=max_rises,
        max_drops_in_day=max_drops,
        by_day=by_day,
        rises_by_hour=rises_by_hour,
        drops_by_hour=drops_by_hour,
        events=events,
    )
