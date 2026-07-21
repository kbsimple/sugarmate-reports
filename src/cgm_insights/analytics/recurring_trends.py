"""Recurring trend detection across multiple days at 30-minute granularity.

Scans the most recent LOOKBACK_DAYS days of readings and identifies time
windows (e.g. 10:30 AM – 2:00 PM) where glucose consistently rises or
falls across multiple days. A trend must appear on at least MIN_DAYS days
to be surfaced.

Algorithm:
  1. Bucket readings into 30-minute slots and average per slot per day.
  2. For each candidate [start_slot, end_slot] window, compute the
     directional slope per day (linear regression over available slots).
  3. Count days that agree on direction with sufficient magnitude.
  4. Score, deduplicate overlapping windows (>50% slot overlap), and
     keep the top MAX_TRENDS results.
  5. For each selected trend, compute per-slot IQR statistics across
     the contributing days.
"""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

LOOKBACK_DAYS: int = 10
SLOT_MINUTES: int = 30
SLOTS_PER_DAY: int = 24 * 60 // SLOT_MINUTES  # 48

MIN_DAYS: int = 3
MIN_CONSISTENCY: float = 0.50  # fraction of covered days showing the trend
MIN_MAGNITUDE_MG_DL: float = 8.0  # minimum start-to-end glucose change
COVERAGE_THRESHOLD: float = 0.40  # fraction of window slots a day must cover
MIN_WINDOW_SLOTS: int = 2  # 1-hour minimum window
MAX_WINDOW_SLOTS: int = 20  # 10-hour maximum window
MAX_TRENDS: int = 5


# ── Models ────────────────────────────────────────────────────────────────────


class TrendSlot(BaseModel):
    label: str
    slot_index: int
    q1: float
    median: float
    q3: float
    day_count: int


class RecurringTrend(BaseModel):
    direction: Literal["rising", "falling"]
    start_slot: int
    end_slot: int
    start_label: str
    end_label: str
    days_observed: int
    days_available: int
    consistency_pct: float
    avg_change_mg_dl: float
    slots: list[TrendSlot]


class RecurringTrendsResult(BaseModel):
    insufficient_data: bool
    days_analyzed: int
    trends: list[RecurringTrend]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _slot_index(ts: datetime) -> int:
    return (ts.hour * 60 + ts.minute) // SLOT_MINUTES


def _slot_label(slot: int) -> str:
    total_min = slot * SLOT_MINUTES
    hour = total_min // 60
    minute = total_min % 60
    period = "AM" if hour < 12 else "PM"
    h12 = hour % 12 or 12
    return f"{h12}:{minute:02d} {period}"


def _build_daily_avgs(readings: list) -> dict[str, dict[int, float]]:
    """Return {date_str: {slot_index: avg_glucose}} for all readings."""
    from collections import defaultdict

    by_day_slot: dict[str, dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in readings:
        date_key = r.timestamp.strftime("%Y-%m-%d")
        slot = _slot_index(r.timestamp)
        by_day_slot[date_key][slot].append(r.glucose_mg_dl)
    return {
        date: {
            slot: sum(vals) / len(vals) for slot, vals in slots.items()
        }
        for date, slots in by_day_slot.items()
    }


def _linear_slope(ys: list[float]) -> float:
    """Slope of y ~ x via OLS where x = [0, 1, ..., n-1]."""
    n = len(ys)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(ys) / n
    num = sum((i - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


def _has_coverage(day_avgs: dict[int, float], start: int, end: int) -> bool:
    slots = list(range(start, end + 1))
    n_avail = sum(1 for s in slots if s in day_avgs)
    return n_avail >= max(2, int(len(slots) * COVERAGE_THRESHOLD))


def _assess_direction(
    day_avgs: dict[int, float], start: int, end: int
) -> tuple[str | None, float]:
    """Return (direction, magnitude) for the given window, or (None, 0)."""
    avail = [day_avgs[s] for s in range(start, end + 1) if s in day_avgs]
    slope = _linear_slope(avail)
    magnitude = abs(avail[-1] - avail[0]) if len(avail) >= 2 else 0.0
    if magnitude < MIN_MAGNITUDE_MG_DL:
        return None, 0.0
    return ("rising" if slope > 0 else "falling"), magnitude


def _quartiles(vals: list[float]) -> tuple[float, float, float]:
    """Return (Q1, median, Q3) using the same split-median approach as numpy."""
    s = sorted(vals)
    n = len(s)
    med = statistics.median(s)
    lower = s[: n // 2]
    upper = s[(n + 1) // 2 :]
    q1 = statistics.median(lower) if lower else med
    q3 = statistics.median(upper) if upper else med
    return q1, med, q3


def _slot_stats(
    dates: list[str],
    daily_avgs: dict[str, dict[int, float]],
    start: int,
    end: int,
) -> list[TrendSlot]:
    result: list[TrendSlot] = []
    for slot in range(start, end + 1):
        vals = [daily_avgs[d][slot] for d in dates if slot in daily_avgs[d]]
        if not vals:
            continue
        q1, med, q3 = _quartiles(vals)
        result.append(
            TrendSlot(
                label=_slot_label(slot),
                slot_index=slot,
                q1=round(q1, 1),
                median=round(med, 1),
                q3=round(q3, 1),
                day_count=len(vals),
            )
        )
    return result


# ── Public API ────────────────────────────────────────────────────────────────


def analyze_recurring_trends(
    readings: list,
    min_days: int = MIN_DAYS,
    lookback_days: int = LOOKBACK_DAYS,
) -> RecurringTrendsResult:
    """Detect recurring directional glucose trends across multiple days.

    Args:
        readings: List of CGMReading objects.
        min_days: Minimum number of days on which a trend must appear.
        lookback_days: Limit analysis to this many most-recent calendar days.

    Returns:
        RecurringTrendsResult with found trends and metadata.
    """
    if not readings:
        return RecurringTrendsResult(
            insufficient_data=True, days_analyzed=0, trends=[]
        )

    daily_avgs = _build_daily_avgs(readings)
    sorted_dates = sorted(daily_avgs.keys())

    # Use only the most recent lookback_days calendar dates
    if len(sorted_dates) > lookback_days:
        sorted_dates = sorted_dates[-lookback_days:]
    daily_avgs = {d: daily_avgs[d] for d in sorted_dates}

    days_analyzed = len(sorted_dates)
    if days_analyzed < min_days:
        return RecurringTrendsResult(
            insufficient_data=True, days_analyzed=days_analyzed, trends=[]
        )

    candidates: list[dict] = []

    for start in range(SLOTS_PER_DAY - MIN_WINDOW_SLOTS):
        for end in range(
            start + MIN_WINDOW_SLOTS,
            min(start + MAX_WINDOW_SLOTS + 1, SLOTS_PER_DAY),
        ):
            covered = [d for d in sorted_dates if _has_coverage(daily_avgs[d], start, end)]
            if len(covered) < min_days:
                continue

            directions: list[tuple[str, float, str]] = []
            for date in covered:
                direction, magnitude = _assess_direction(daily_avgs[date], start, end)
                if direction:
                    directions.append((direction, magnitude, date))

            if not directions:
                continue

            n_available = len(covered)
            n_rising = sum(1 for d, _, _ in directions if d == "rising")
            n_falling = len(directions) - n_rising
            dominant: Literal["rising", "falling"] = (
                "rising" if n_rising >= n_falling else "falling"
            )
            n_consistent = n_rising if dominant == "rising" else n_falling

            if n_consistent < min_days:
                continue
            consistency = n_consistent / n_available
            if consistency < MIN_CONSISTENCY:
                continue

            avg_mag = (
                sum(m for d, m, _ in directions if d == dominant) / n_consistent
            )
            score = (
                n_consistent * consistency * avg_mag * (end - start + 1) ** 0.5
            )
            consistent_dates = [date for d, _, date in directions if d == dominant]

            candidates.append(
                {
                    "start": start,
                    "end": end,
                    "direction": dominant,
                    "n_consistent": n_consistent,
                    "n_available": n_available,
                    "consistency": consistency,
                    "avg_magnitude": avg_mag,
                    "score": score,
                    "consistent_dates": consistent_dates,
                }
            )

    # Greedy non-max suppression: pick highest-scoring non-overlapping windows
    candidates.sort(key=lambda c: c["score"], reverse=True)
    selected: list[dict] = []
    for cand in candidates:
        window = set(range(cand["start"], cand["end"] + 1))
        overlaps = any(
            len(window & set(range(sel["start"], sel["end"] + 1)))
            / len(window | set(range(sel["start"], sel["end"] + 1)))
            > 0.5
            for sel in selected
        )
        if not overlaps:
            selected.append(cand)
        if len(selected) >= MAX_TRENDS:
            break

    # Sort selected trends by start time for display
    selected.sort(key=lambda c: c["start"])

    trends: list[RecurringTrend] = []
    for cand in selected:
        slots = _slot_stats(
            cand["consistent_dates"], daily_avgs, cand["start"], cand["end"]
        )
        trends.append(
            RecurringTrend(
                direction=cand["direction"],
                start_slot=cand["start"],
                end_slot=cand["end"],
                start_label=_slot_label(cand["start"]),
                end_label=_slot_label(cand["end"]),
                days_observed=cand["n_consistent"],
                days_available=cand["n_available"],
                consistency_pct=round(cand["consistency"] * 100, 1),
                avg_change_mg_dl=round(cand["avg_magnitude"], 1),
                slots=slots,
            )
        )

    return RecurringTrendsResult(
        insufficient_data=False,
        days_analyzed=days_analyzed,
        trends=trends,
    )
