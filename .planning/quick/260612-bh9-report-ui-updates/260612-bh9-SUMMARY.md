---
quick_id: 260612-bh9
slug: report-ui-updates
status: complete
date: "2026-06-12"
commit: a9c6d1b
---

# Summary: Report UI Updates (260612-bh9)

## Changes Delivered

1. **Dismissable Data Quality Notes banner** — Added Alpine.js `x-data`/`x-show` to the alert; X button closes it without page reload.

2. **Time Windows to Focus On relocated** — Component now renders directly after the TIR chart (before Glucose Trend), making prioritized time windows immediately visible.

3. **Weekdays/Weekends as primary grouping in Time Windows** — `out_of_range_insights.html` restructured: out-of-range status is determined per day type using `weekday_avg_glucose` / `weekend_avg_glucose`. Falls back to blended avg when split unavailable.

4. **Time-of-Day Patterns dropdown** — New `<select>` in `daily_patterns.html` lets users toggle All / Weekdays / Weekends. Dropdown is disabled (with tooltip) when no weekday/weekend split is available in the data.

5. **Hourly blocks for Time-of-Day Patterns** — Chart now uses 60-min behavioral pattern windows at hourly boundaries instead of legacy 2-hour patterns; `updateToDChart()` function re-renders on dropdown change.

6. **3-week diurnal average overlay on Glucose Trend** — Second Chart.js dataset (dashed indigo line) computed from the last 21 days of readings, bucketed into 48 × 30-min slots. For each actual reading, the overlay value is the average for that 30-min time-of-day slot.

7. **Behavioral Patterns colors updated** — Consistent: `badge-info` (blue); Variable: `badge-warning` (yellow, unchanged); Moderate: light yellow (`#fef9c3` background, `#854d0e` text, `#fde68a` border).

## Test Results

259 passed, 1 skipped — no regressions.
