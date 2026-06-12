---
phase: 08-tod-chart-patterns-ux
status: advisory
findings: 3
severity_high: 0
severity_medium: 1
severity_low: 2
reviewed_at: 2026-06-11
---

# Code Review — Phase 8: Time-of-Day Chart & Patterns UX

## Findings

### MEDIUM — Color collision: `badge-warning` used for two unrelated meanings
**File:** `src/web/templates/components/behavioral_patterns.html` line ~56, ~65
**Finding:** `badge-warning` (yellow) is used for both the "Variable" consistency badge and the "Above Range" glucose badge on the same row. A user scanning the list sees two yellow badges on a row and cannot instantly distinguish "this pattern is variable in timing" from "this pattern is above target range."
**Fix:** Use `badge-info` or `badge-secondary` for the "Moderate" and "Variable" consistency states, reserving `badge-warning` exclusively for glucose range status (already used in `out_of_range_insights.html`).

### LOW — Triple iteration over `hourly_patterns` in `out_of_range_insights.html`
**File:** `src/web/templates/components/out_of_range_insights.html` lines 21-26, 39-57, 64-82
**Finding:** The component builds `has_above`/`has_below` sentinel lists in one pass, then renders Above Range cards in a second pass, then Below Range cards in a third pass — three full iterations over the same ~24-element list. The sentinel lists use an `.append(1)` pattern when only a boolean is needed.
**Fix:** Replace the sentinel loop with Jinja2 selectattr: `{% set above_patterns = hourly_patterns | selectattr("avg_glucose", "gt", 180) | list %}` and `{% set below_patterns = ... | selectattr("avg_glucose", "lt", 70) | list %}`. Then iterate each sub-list once for rendering. This halves the iterations and removes the sentinel pattern.

### LOW — Glucose thresholds (70 / 180) hardcoded in two templates
**File:** `src/web/templates/components/behavioral_patterns.html` lines 63-65; `src/web/templates/components/out_of_range_insights.html` lines 25, 27
**Finding:** The target range boundaries are duplicated across both new template files. If the threshold values ever change, both files must be updated manually.
**Fix:** Pass `tir_low=70` and `tir_high=180` as template context variables from `results.py` (they are already implicitly known there) and reference them as `{{ tir_low }}` / `{{ tir_high }}` in templates. This creates a single source of truth.

## What Passed

- Chart fix (08-01): single-line injection, no side effects, 252 tests pass
- Behavioral patterns redesign (08-02): null-safe WD/WE guard correct, density filter logic verified against behavioral_patterns.py sliding window structure
- Out-of-range wiring (08-03): component guard (`not behavioral_patterns.insufficient_data`) present and correct; wellness disclaimer preserved
- No regressions: 252 tests pass post-merge
