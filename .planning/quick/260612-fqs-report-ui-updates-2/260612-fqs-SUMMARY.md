---
quick_id: 260612-fqs
slug: report-ui-updates-2
status: complete
date: "2026-06-12"
commit: f8fb221
---

# Summary: Report UI Updates 2 (260612-fqs)

## Changes Delivered

1. **Expandable Time Windows rows** — Each out-of-range row uses Alpine.js `x-data`/`x-show` for accordion expand/collapse. On first expand, `computeWindowDetails(bucketStart, windowMin)` computes per-date stats (avg, min, max, readings, % in range) from the `glucoseReadings` JS global and renders a table. `days_with_data` and `pct_out_of_range` also shown in the summary line.

2. **Glucose Trend → Daily Time in Range** — Replaced the time-series line chart with a per-day bar chart. Each bar shows that day's % of readings in 70–180 mg/dL range, color-coded green (≥70%), yellow (50–70%), red (<50%), with a dashed 70% reference line via a custom `afterDatasetsDraw` plugin.

3. **Behavioral Patterns → diurnal line chart** — Removed the DaisyUI tab list. New canvas (`behavioralPatternsChart`) renders a line chart with time-of-day on x-axis, avg glucose on y-axis. Three lines: All Days (indigo), Weekdays (blue dashed), Weekends (amber dashed). Green target-range band (70–180) drawn via `beforeDatasetsDraw` plugin. Insufficient-data fallback preserved.

## Test Results
259 passed, 1 skipped — no regressions.
