"""Recurring trend detection across the full dataset at 30-minute granularity.

Scans ALL available days and finds specific calendar windows (3–10 consecutive
calendar days) where a time-of-day glucose pattern was consistently active.
This surfaces temporally-localised patterns — things that happened for a week
then stopped — which the aggregate hourly charts cannot show.

Algorithm
---------
1.  Build per-day 30-minute slot averages.
2.  Pre-compute direction (rising / falling / none) and magnitude for every
    (date, [start_slot, end_slot]) pair.
3.  For each slot window, build prefix-sum arrays so any sliding day window
    can be evaluated in O(1).
4.  Slide calendar windows of 3–10 days over all dates; score every window
    that meets the consistency threshold.
5.  Take the top-500 candidates, then greedily pick up to MAX_TRENDS that
    don't overlap (> 50 % IoU) in *both* the slot and date dimensions.
6.  Compute per-slot Q1/median/Q3 statistics from the contributing days for
    Chart.js IQR visualisation.
"""

from __future__ import annotations

import statistics
from datetime import date as _Date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SLOT_MINUTES: int = 30
SLOTS_PER_DAY: int = 24 * 60 // SLOT_MINUTES  # 48

MIN_DAYS: int = 3
MAX_DAYS: int = 10
MIN_CONSISTENCY: float = 0.60   # ≥60 % of covered days must show the trend
MIN_MAGNITUDE_MG_DL: float = 8.0
COVERAGE_THRESHOLD: float = 0.40  # day needs ≥40 % of window slots filled
MIN_WINDOW_SLOTS: int = 2        # 1-hour minimum
MAX_WINDOW_SLOTS: int = 20       # 10-hour maximum
MAX_TRENDS: int = 5


# ── Models ─────────────────────────────────────────────────────────────────────


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
    start_date: str           # ISO date "YYYY-MM-DD" of the identified window
    end_date: str
    calendar_days: int        # calendar span of the window (max 10)
    date_range_label: str     # human-readable "Jan 15–22, 2026"
    days_observed: int        # days within the window that showed the pattern
    days_available: int       # days within the window that had sufficient data
    consistency_pct: float
    avg_change_mg_dl: float
    slots: list[TrendSlot]


class RecurringTrendsResult(BaseModel):
    insufficient_data: bool
    days_analyzed: int
    trends: list[RecurringTrend]


# ── Helpers ────────────────────────────────────────────────────────────────────


def _slot_index(ts: datetime) -> int:
    return (ts.hour * 60 + ts.minute) // SLOT_MINUTES


def _slot_label(slot: int) -> str:
    total_min = slot * SLOT_MINUTES
    hour = total_min // 60
    minute = total_min % 60
    period = "AM" if hour < 12 else "PM"
    h12 = hour % 12 or 12
    return f"{h12}:{minute:02d} {period}"


def _date_range_label(start: str, end: str) -> str:
    sd = datetime.strptime(start, "%Y-%m-%d")
    ed = datetime.strptime(end, "%Y-%m-%d")
    if sd.year == ed.year and sd.month == ed.month:
        return f"{sd.strftime('%b %-d')}–{ed.strftime('%-d, %Y')}"
    if sd.year == ed.year:
        return f"{sd.strftime('%b %-d')}–{ed.strftime('%b %-d, %Y')}"
    return f"{sd.strftime('%b %-d, %Y')}–{ed.strftime('%b %-d, %Y')}"


def _build_daily_avgs(readings: list) -> dict[str, dict[int, float]]:
    from collections import defaultdict

    by: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in readings:
        by[r.timestamp.strftime("%Y-%m-%d")][_slot_index(r.timestamp)].append(
            r.glucose_mg_dl
        )
    return {
        date: {slot: sum(vals) / len(vals) for slot, vals in slots.items()}
        for date, slots in by.items()
    }


def _linear_slope(ys: list[float]) -> float:
    n = len(ys)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(ys) / n
    num = sum((i - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den if den else 0.0


def _has_coverage(day_avgs: dict[int, float], start: int, end: int) -> bool:
    slots = list(range(start, end + 1))
    avail = sum(1 for s in slots if s in day_avgs)
    return avail >= max(2, int(len(slots) * COVERAGE_THRESHOLD))


def _assess_direction(
    day_avgs: dict[int, float], start: int, end: int
) -> tuple[str | None, float]:
    avail = [day_avgs[s] for s in range(start, end + 1) if s in day_avgs]
    slope = _linear_slope(avail)
    magnitude = abs(avail[-1] - avail[0]) if len(avail) >= 2 else 0.0
    if magnitude < MIN_MAGNITUDE_MG_DL:
        return None, 0.0
    return ("rising" if slope > 0 else "falling"), magnitude


def _quartiles(vals: list[float]) -> tuple[float, float, float]:
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
        vals = [daily_avgs[d][slot] for d in dates if slot in daily_avgs.get(d, {})]
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


# ── Public API ─────────────────────────────────────────────────────────────────


def analyze_recurring_trends(
    readings: list,
    min_days: int = MIN_DAYS,
    max_days: int = MAX_DAYS,
) -> RecurringTrendsResult:
    """Detect recurring glucose trends within specific calendar windows.

    Searches the full dataset for 3–10 day periods where a particular
    time-of-day directional pattern (rise or fall) was consistently active.
    Surfaces patterns that are localised to a specific stretch of time —
    not just aggregate tendencies across all days.

    Args:
        readings:  List of CGMReading objects.
        min_days:  Minimum calendar window size (days).
        max_days:  Maximum calendar window size (days).

    Returns:
        RecurringTrendsResult with up to MAX_TRENDS localised trends.
    """
    if not readings:
        return RecurringTrendsResult(
            insufficient_data=True, days_analyzed=0, trends=[]
        )

    daily_avgs = _build_daily_avgs(readings)
    sorted_dates = sorted(daily_avgs.keys())
    days_analyzed = len(sorted_dates)

    if days_analyzed < min_days:
        return RecurringTrendsResult(
            insufficient_data=True, days_analyzed=days_analyzed, trends=[]
        )

    # Pre-parse date strings once for fast calendar-span arithmetic
    parsed: dict[str, _Date] = {
        d: datetime.strptime(d, "%Y-%m-%d").date() for d in sorted_dates
    }

    # ── Pre-compute per-slot-window, per-day direction vectors ──────────────
    # slot_data[(s, e)] = {
    #   'covered':      [bool]*N        — day has ≥ threshold data coverage
    #   'rising_mags':  [float]*N       — magnitude if rising, else 0
    #   'falling_mags': [float]*N       — magnitude if falling, else 0
    # }
    N = len(sorted_dates)
    slot_data: dict[tuple[int, int], dict] = {}

    for s in range(SLOTS_PER_DAY - MIN_WINDOW_SLOTS):
        for e in range(
            s + MIN_WINDOW_SLOTS,
            min(s + MAX_WINDOW_SLOTS + 1, SLOTS_PER_DAY),
        ):
            covered = []
            rising_mags: list[float] = []
            falling_mags: list[float] = []

            for date in sorted_dates:
                avgs = daily_avgs[date]
                if _has_coverage(avgs, s, e):
                    covered.append(True)
                    direction, magnitude = _assess_direction(avgs, s, e)
                    if direction == "rising":
                        rising_mags.append(magnitude)
                        falling_mags.append(0.0)
                    elif direction == "falling":
                        rising_mags.append(0.0)
                        falling_mags.append(magnitude)
                    else:
                        rising_mags.append(0.0)
                        falling_mags.append(0.0)
                else:
                    covered.append(False)
                    rising_mags.append(0.0)
                    falling_mags.append(0.0)

            slot_data[(s, e)] = {
                "covered": covered,
                "rising_mags": rising_mags,
                "falling_mags": falling_mags,
            }

    # ── Slide calendar windows using prefix sums ────────────────────────────
    candidates: list[dict] = []

    for (s, e), data in slot_data.items():
        covered = data["covered"]
        rm = data["rising_mags"]
        fm = data["falling_mags"]

        # Build prefix sums for O(1) window queries
        pc = [0] * (N + 1)   # covered count
        pr = [0] * (N + 1)   # rising count
        pf = [0] * (N + 1)   # falling count
        prs = [0.0] * (N + 1)  # sum of rising magnitudes
        pfs = [0.0] * (N + 1)  # sum of falling magnitudes
        for k in range(N):
            pc[k + 1] = pc[k] + (1 if covered[k] else 0)
            pr[k + 1] = pr[k] + (1 if rm[k] > 0 else 0)
            pf[k + 1] = pf[k] + (1 if fm[k] > 0 else 0)
            prs[k + 1] = prs[k] + rm[k]
            pfs[k + 1] = pfs[k] + fm[k]

        for i in range(N):
            for j in range(i + min_days - 1, N):
                span = (parsed[sorted_dates[j]] - parsed[sorted_dates[i]]).days + 1
                if span > max_days:
                    break  # increasing j only grows the span
                if span < min_days:
                    continue

                n_cov = pc[j + 1] - pc[i]
                if n_cov < min_days:
                    continue

                n_r = pr[j + 1] - pr[i]
                n_f = pf[j + 1] - pf[i]
                dominant: Literal["rising", "falling"] = (
                    "rising" if n_r >= n_f else "falling"
                )
                n_con = n_r if dominant == "rising" else n_f
                if n_con < min_days:
                    continue

                consistency = n_con / n_cov
                if consistency < MIN_CONSISTENCY:
                    continue

                avg_mag = (
                    (prs[j + 1] - prs[i]) / n_r
                    if dominant == "rising" and n_r > 0
                    else (pfs[j + 1] - pfs[i]) / n_f
                    if n_f > 0
                    else 0.0
                )

                score = (
                    n_con * consistency * avg_mag * (e - s + 1) ** 0.3
                )

                candidates.append(
                    {
                        "start_slot": s,
                        "end_slot": e,
                        "start_date": sorted_dates[i],
                        "end_date": sorted_dates[j],
                        "calendar_span": span,
                        "direction": dominant,
                        "n_consistent": n_con,
                        "n_available": n_cov,
                        "consistency": consistency,
                        "avg_magnitude": avg_mag,
                        "score": score,
                        "date_range_i": i,
                        "date_range_j": j,
                    }
                )

    if not candidates:
        return RecurringTrendsResult(
            insufficient_data=False, days_analyzed=days_analyzed, trends=[]
        )

    # ── Greedy dedup: reject if >50 % IoU in BOTH slot AND date dimensions ──
    candidates.sort(key=lambda c: c["score"], reverse=True)
    candidates = candidates[:1000]  # bound dedup work

    selected: list[dict] = []
    for cand in candidates:
        slot_set = set(range(cand["start_slot"], cand["end_slot"] + 1))
        date_set = set(
            range(cand["date_range_i"], cand["date_range_j"] + 1)
        )

        is_dup = False
        for sel in selected:
            sel_slots = set(range(sel["start_slot"], sel["end_slot"] + 1))
            sel_dates = set(range(sel["date_range_i"], sel["date_range_j"] + 1))

            s_iou = len(slot_set & sel_slots) / len(slot_set | sel_slots)
            d_iou = len(date_set & sel_dates) / len(date_set | sel_dates)
            if s_iou > 0.5 and d_iou > 0.5:
                is_dup = True
                break

        if not is_dup:
            selected.append(cand)
        if len(selected) >= MAX_TRENDS:
            break

    # Sort by start_date then start_slot for chronological display
    selected.sort(key=lambda c: (c["start_date"], c["start_slot"]))

    # ── Build trend objects with IQR slot stats ─────────────────────────────
    trends: list[RecurringTrend] = []
    for cand in selected:
        s, e = cand["start_slot"], cand["end_slot"]
        i, j = cand["date_range_i"], cand["date_range_j"]
        dominant = cand["direction"]

        # Collect the specific dates in the window that showed the pattern
        rm = slot_data[(s, e)]["rising_mags"]
        fm = slot_data[(s, e)]["falling_mags"]
        consistent_dates = [
            sorted_dates[k]
            for k in range(i, j + 1)
            if (dominant == "rising" and rm[k] > 0)
            or (dominant == "falling" and fm[k] > 0)
        ]

        slots = _slot_stats(consistent_dates, daily_avgs, s, e)

        trends.append(
            RecurringTrend(
                direction=dominant,
                start_slot=s,
                end_slot=e,
                start_label=_slot_label(s),
                end_label=_slot_label(e),
                start_date=cand["start_date"],
                end_date=cand["end_date"],
                calendar_days=cand["calendar_span"],
                date_range_label=_date_range_label(
                    cand["start_date"], cand["end_date"]
                ),
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
