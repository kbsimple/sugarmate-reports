---
quick_id: 260612-zym
slug: dow-formatting-tir-day-count
description: "3 display improvements: day-of-week in Time Windows per-date detail, 14-21 day window for Daily TIR chart, day-of-week in Daily TIR x-axis labels"
date: "2026-06-12"
status: ready
---

# Quick Task 260612-zym: DoW Formatting & TIR Day Count

## Task 1: Add day-of-week to Time Windows per-date detail table
**Files:** `src/web/static/js/charts.js`

In `computeWindowDetails()` (line ~427), update the `dispDate` computation.
Currently:
```js
const dispDate = ts.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
```
Change to:
```js
const dispDate = ts.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
```
This produces "Tue, May 12, 2026". The table `Date` column will show day-of-week abbreviation before the date.

**Verify:** `computeWindowDetails` returns `date` values starting with a 3-letter weekday (e.g., "Tue, May 12, 2026"). Inspect via browser console or unit check: `new Date('2026-05-12').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })` → "Tue, May 12, 2026".

**Done:** Expanding any Time Windows row shows dates with weekday prefix like "Tue, May 12, 2026".

---

## Task 2: Limit Daily TIR chart to 14-21 days and add day-of-week to labels
**Files:** `src/web/static/js/charts.js`

Two changes in `computeDailyTIR()` (lines ~83-101) and `createGlucoseTrendChart()` (lines ~103-182):

**2a — Limit to 21 days (14 minimum):**

In `computeDailyTIR()`, after building and sorting the result array, take the last 21 entries:
```js
const all = Object.entries(byDate)
    .sort(([, a], [, b]) => a.ts - b.ts)
    .map(([date, v]) => ({
        date,
        pctInRange: Math.round(v.inRange / v.total * 100),
        total: v.total,
        inRange: v.inRange
    }));
return all.slice(-21);
```
21 bars fit well at the current chart height (300px). If the dataset has fewer than 14 days all are shown (no minimum enforced as a hard floor — just show what exists).

**2b — Add weekday abbreviation to x-axis date labels:**

In `computeDailyTIR()`, update the `dateStr` computation from:
```js
const dateStr = new Date(r.timestamp).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric'
});
```
to:
```js
const dateStr = new Date(r.timestamp).toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric'
});
```
This produces labels like "Tue May 12" on the x-axis.

Also update the `maxTicksLimit` in `createGlucoseTrendChart()` x-axis ticks from `20` to `21` so all 21 labels can render without auto-skipping:
```js
ticks: { maxRotation: 45, autoSkip: true, maxTicksLimit: 21 }
```

**Verify:** Run `npx vitest run` (252 Python tests pass — these are JS-only changes with no Python test coverage). Visually: the Daily TIR chart shows at most 21 bars, each labelled "Mon Jun 09" style.

**Done:** Daily TIR chart shows 14-21 days with weekday-prefixed x-axis labels (e.g., "Tue May 12"). No more than 21 bars displayed even for datasets spanning months.
