---
plan: 08-04
phase: 08-tod-chart-patterns-ux
status: complete
completed: "2026-06-12"
gap_closure: true
---

## Summary

Closed ROADMAP Success Criterion SC-5 by adding `pct_out_of_range: float` to `BehavioralPattern` and rendering it in `out_of_range_insights.html`.

## What Was Built

- **BehavioralPattern.pct_out_of_range** — new field (`ge=0.0, le=1.0`) representing fraction of readings outside 70–180 mg/dL in a time bucket.
- **_compute_all_buckets computation** — Polars filter `(pl.col("glucose") < 70) | (pl.col("glucose") > 180)` on the per-bucket subset DataFrame; division by `subset.height` (always > 0 due to the existing height == 0 guard above).
- **BehavioralPattern constructor wiring** — `pct_out_of_range=b["pct_out_of_range"]` added as final kwarg.
- **out_of_range_insights.html rendering** — both Above Range and Below Range alert cards now show `avg X mg/dL · Y% out of range` using Jinja2 `(pattern.pct_out_of_range * 100) | round(0) | int`.
- **Test fixture fix** — `test_behavioral_pattern_is_immutable` updated with `pct_out_of_range=0.25`.

## Key Files

- `src/cgm_insights/analytics/behavioral_patterns.py` — field def, computation, constructor kwarg (4 occurrences)
- `src/web/templates/components/out_of_range_insights.html` — rendered in 2 card sections
- `tests/test_analytics/test_behavioral_patterns.py` — fixture updated

## Self-Check: PASSED

- `grep -c "pct_out_of_range" src/cgm_insights/analytics/behavioral_patterns.py` → 4 ✓
- `grep -c "pct_out_of_range" src/web/templates/components/out_of_range_insights.html` → 2 ✓
- All 12 behavioral pattern tests pass ✓
- Full suite: 252 passed, 0 failed ✓
- SC-5 satisfied: each out-of-range insight card shows time window, avg glucose, % out of range, and weekday/weekend split ✓
