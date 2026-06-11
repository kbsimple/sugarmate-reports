---
phase: 4
plan: "04-01"
subsystem: analytics-library
tags: [behavioral-patterns, sliding-window, consistency-scoring, wellness-suggestions]
dependency_graph:
  requires: []
  provides:
    - cgm_insights.analytics.behavioral_patterns (ConsistencyLabel, BehavioralPattern, BehavioralAnalysisResult, analyze_behavioral_patterns)
    - cgm_insights.output.suggestions (generate_behavioral_suggestions, behavioral_consistent/variable/weekday_weekend_diff templates)
  affects:
    - downstream plans that surface behavioral patterns in CLI and web (04-02, 04-03)
tech_stack:
  added: []
  patterns:
    - Sliding-window time-bucket aggregation (288 buckets per window size via Python loop + Polars filter)
    - Per-window quartile labeling (CV scores -> p25/p75 -> Consistent/Moderate/Variable)
    - Polars DataFrame with minute-of-day (mod) and date columns for cross-day consistency
    - Pydantic v2 frozen models for BehavioralPattern and BehavioralAnalysisResult
    - Template-based wellness suggestion generation extending existing SUGGESTION_TEMPLATES pattern
key_files:
  created:
    - path: src/cgm_insights/analytics/behavioral_patterns.py
      description: Core behavioral pattern module — ConsistencyLabel, BehavioralPattern, BehavioralAnalysisResult, analyze_behavioral_patterns(), and private helpers
  modified:
    - path: src/cgm_insights/output/suggestions.py
      description: Added behavioral_consistent/variable/weekday_weekend_diff templates and generate_behavioral_suggestions() function
decisions:
  - "Used CV of daily means (not Pearson r) as consistency metric — simpler, interpretable as %, no scipy needed"
  - "Per-window quartile thresholds (each window size gets its own p25/p75) to avoid cross-window comparison artifacts"
  - "min_days=5 enforced at both bucket level and weekday/weekend segment level (Pitfall 2 and 4 avoidance)"
  - "Midnight-crossing windows handled via OR filter: (mod >= start) OR (mod < end-1440)"
  - "BehavioralPattern kept separate from PatternResult — different semantics, separate concerns"
metrics:
  duration: "6 minutes"
  completed: "2026-06-11"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 4 Plan 01: Behavioral Pattern Library Summary

**One-liner:** Sliding-window CV-based consistency scoring across 30/60/120-min time buckets with per-window quartile labeling and wellness suggestion generation.

## What Was Built

### Task 1: behavioral_patterns.py (322 lines)

Created `src/cgm_insights/analytics/behavioral_patterns.py` with the complete behavioral analysis implementation:

- `ConsistencyLabel` enum: CONSISTENT, MODERATE, VARIABLE
- `BehavioralPattern` Pydantic v2 frozen model with 10 fields including weekday/weekend averages and cv_score
- `BehavioralAnalysisResult` model wrapping all patterns with metadata
- `analyze_behavioral_patterns()` public function supporting configurable window sizes (default: [30, 60, 120] min) and min_days threshold
- Private helpers: `_build_df()`, `_format_bucket_label()`, `_get_subset()`, `_daily_stats()`, `_compute_all_buckets()`, `_apply_consistency_labels()`

**Algorithm:** For each window size, iterates over 288 bucket starts (0-1435, step 5 min), aggregates daily means per bucket, computes CV, then applies per-window quartile thresholds. Total: 864 bucket iterations across all three window sizes.

**Key correctness properties:**
- Midnight-crossing windows (e.g., 120-min window starting at 23:30): handled with `(mod >= start) | (mod < end-1440)`
- Weekend detection: `dt.weekday() >= 6` (Saturday=6, Sunday=7 in Polars 1.40.1 ISO 8601)
- Insufficient data: buckets with < 5 distinct days are skipped entirely; weekday/weekend sub-segments with < 5 days get None averages
- Quartile thresholds computed separately per window size (not pooled across sizes)

### Task 2: suggestions.py additions (113 lines added)

Modified `src/cgm_insights/output/suggestions.py`:

- Import of `BehavioralPattern`, `BehavioralAnalysisResult`, `ConsistencyLabel` from new module
- Three new SUGGESTION_TEMPLATES entries:
  - `behavioral_consistent` (TIMING, priority 3): "Consistent period detected"
  - `behavioral_variable` (VARIABILITY, priority 3): "Variable period detected"
  - `behavioral_weekday_weekend_diff` (CONTROL, priority 4): "Weekday vs weekend difference"
- `generate_behavioral_suggestions()` function: limits to top 3 consistent + top 3 variable patterns, adds weekday/weekend diff suggestion only when both averages exist and differ > 10 mg/dL

All text follows wellness-only language (D-09 / BHVR-06). No medical advice in any template.

## Verification

- All 210 existing tests pass, 2 skipped — no regressions
- End-to-end smoke test: 10 days × 288 readings/day = 2880 readings → 864 patterns, 3 suggestions generated
- All acceptance criteria met for both tasks
- Threat mitigations T-04-01 (Pydantic `ge=40.0, le=400.0` on avg_glucose), T-04-03 (SUGGESTION_TEMPLATES-only text) implemented

## Deviations from Plan

None — plan executed exactly as written.

The plan's verification command uses `cd /Users/ffaber/claude-projects/sugarmate-reports` (the editable install root). In this worktree, verification was run with `PYTHONPATH=<worktree>/src` to target the worktree's implementation rather than the main project's source. This is standard worktree operation, not a deviation.

## Known Stubs

None — all data flows are wired. `analyze_behavioral_patterns()` computes real patterns from real readings. `generate_behavioral_suggestions()` returns real `Suggestion` objects from real analysis results.

## Threat Flags

No new network endpoints, auth paths, or trust boundary crossings introduced. Pure library module with no I/O.

## Self-Check: PASSED

Files exist:
- src/cgm_insights/analytics/behavioral_patterns.py: FOUND (322 lines)
- src/cgm_insights/output/suggestions.py: FOUND (modified with behavioral templates)

Commits exist:
- c3ffe4e: feat(04-01): create behavioral_patterns.py — FOUND
- 3f37a1b: feat(04-01): add behavioral suggestion templates — FOUND
