---
quick_id: 260612-zym
slug: dow-formatting-tir-day-count
status: complete
date: "2026-06-12"
commit: c8c9b2a
---

# Quick Task 260612-zym: DoW Formatting & TIR Day Count

## What was done

Two display improvements to `src/web/static/js/charts.js`:

**Task 1 — Day-of-week in Time Windows per-date detail**
- Updated `computeWindowDetails()` `dispDate` format: added `weekday: 'short'` to locale options
- Expandable Time Windows rows now show "Tue, May 12, 2026" in the Date column

**Task 2 — Daily TIR: 14-21 day window + day-of-week labels**
- Updated `computeDailyTIR()` to add `weekday: 'short'` to x-axis date labels ("Tue May 12")
- Added `all.slice(-21)` to cap chart at most-recent 21 days
- Fixed grouping key to use stable ISO date string (`YYYY-MM-DD`) instead of locale-formatted display string
- Increased `maxTicksLimit` from 20 → 21 to prevent auto-skipping at 21 bars

## Test results

267 passed, 1 skipped — no regressions.

## Files changed

- `src/web/static/js/charts.js` — 14 insertions, 10 deletions
