---
quick_id: 260612-fqs
slug: report-ui-updates-2
description: "3 UI updates: expandable Time Windows rows with per-date detail, Glucose Trend → daily TIR bar chart, Behavioral Patterns → diurnal line chart"
date: "2026-06-12"
status: in_progress
---

# Quick Task 260612-fqs: Report UI Updates 2

## Task 1: Time Windows to Focus On — expandable rows
**Files:** `out_of_range_insights.html`, `charts.js`
- Add Alpine.js x-data open/close toggle to each out-of-range row
- On expand: call `computeWindowDetails(bucketStart, windowMin)` from `glucoseReadings` global
- Show per-date table: date, avg glucose, readings, min, max, % in range
- Add `computeWindowDetails()` to charts.js

## Task 2: Glucose Trend → daily TIR bar chart
**Files:** `charts.js`, `glucose_trend.html`
- Rewrite `createGlucoseTrendChart()`: group glucoseReadings by calendar date, compute daily %
  in-range (70-180), render as bar chart
- Bars colored green (>=70%), yellow (50-70%), red (<50%)
- Reference line at 70%
- Update title/legend in glucose_trend.html

## Task 3: Behavioral Patterns → diurnal line chart
**Files:** `behavioral_patterns.html`, `charts.js`
- Remove DaisyUI tab list; add `<canvas id="behavioralPatternsChart">`
- Add `createBehavioralPatternsLineChart(canvasId, bp)` in charts.js
  - 60-min hourly patterns, x-axis = time of day, y-axis = avg glucose
  - Three datasets: All Days, Weekdays, Weekends (when available)
  - Target range band (70-180) drawn via beforeDraw plugin
- Call from `initializeCharts()`
