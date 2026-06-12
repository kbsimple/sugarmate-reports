---
phase: 08-tod-chart-patterns-ux
verified: 2026-06-12T00:00:00Z
status: human_needed
score: 6/6 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "Each out-of-range insight includes enough specific detail (time window, average value, % out of range, weekday/weekend split) to motivate action"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Upload a Sugarmate Excel file (covering 7+ days), navigate to results page, scroll to Daily Patterns section"
    expected: "Chart renders with colored line data — not a blank canvas"
    why_human: "Requires browser with real CGM data file; chart rendering cannot be verified by template parsing alone"
  - test: "Upload a file where no 60-min hourly-boundary patterns fall outside 70–180 mg/dL"
    expected: "No 'Time Windows to Focus On' card appears — page goes directly from Daily Patterns chart to Behavioral Patterns tabs"
    why_human: "Requires a specific test file with in-range-only patterns"
  - test: "Upload a file with 14+ days of data (sufficient weekdays and weekend days), navigate to out_of_range_insights and behavioral_patterns components"
    expected: "'WD 145 · WE 162' style split visible inline in behavioral_patterns rows; 'Weekdays: 152 mg/dL · Weekends: 171 mg/dL' and '63% out of range' visible in out-of-range insights"
    why_human: "Requires data with sufficient weekday and weekend coverage to trigger the WD/WE split conditional"
---

# Phase 8: Time-of-Day Chart & Patterns UX Verification Report

**Phase Goal:** Users can see a working Time-of-Day chart, understand their behavioral patterns with inline range status (no accordion), and immediately identify which time windows consistently fall outside range — segmented by weekday/weekend — with enough detail to take action.
**Verified:** 2026-06-12T00:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after SC-5 gap closure (plan 08-04)

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Time-of-Day Patterns chart renders data (not blank) for any uploaded file | VERIFIED | `const patterns = {{ patterns \| tojson }};` at results.html line 207; `<script src="/static/js/charts.js">` at line 209 — order correct; `typeof patterns !== 'undefined'` guard at charts.js line 327 |
| 2 | Behavioral patterns section shows range status inline without accordion/collapse | VERIFIED | 0 `<details>`, 0 `<summary>`, 0 `collapse` occurrences in behavioral_patterns.html; badge-error, badge-warning, badge-success, badge-ghost badge-sm all rendered inline |
| 3 | Variability and range status are both visible simultaneously (two dimensions per window) | VERIFIED | Each row renders consistency badge (Consistent/Variable/Moderate) + range status badge (Below/Above/In Range) side-by-side in left zone; avg_glucose in right zone; both always-visible on first render with no expansion needed |
| 4 | Out-of-range time windows are surfaced as high-priority insights, segmented by weekday vs weekend | VERIFIED | out_of_range_insights.html included at results.html line 104 (above behavioral_patterns at line 111); alert-warning Above Range and alert-error Below Range sections; WD/WE split rendered null-safely with conditional guard |
| 5 | Each out-of-range insight includes: time window, average value, % out of range, weekday/weekend split | VERIFIED | out_of_range_insights.html lines 45 and 70 render `avg X mg/dL · Y% out of range` using `(pattern.pct_out_of_range * 100) \| round(0) \| int`; bucket_label (time window), avg_glucose, pct_out_of_range, and WD/WE split all present in both Above/Below cards |
| 6 | Wellness language maintained throughout; no medical advice | VERIFIED | Wellness disclaimer present in behavioral_patterns.html, out_of_range_insights.html, and page-level results.html; no prescriptive language found in any modified file |

**Score: 6/6 truths verified**

### Gap Closure: SC-5 (Closed in plan 08-04)

The previously-failed SC-5 is now fully satisfied:

- `BehavioralPattern.pct_out_of_range: float = Field(..., ge=0.0, le=1.0)` declared at behavioral_patterns.py line 60
- Computed in `_compute_all_buckets` at lines 225–228 via Polars filter `(pl.col("glucose") < 70) | (pl.col("glucose") > 180)` — division by `subset.height` (always > 0 due to the height == 0 guard at line 206)
- Wired through `BehavioralPattern(...)` constructor at line 335: `pct_out_of_range=b["pct_out_of_range"]`
- Rendered in out_of_range_insights.html at lines 45 and 70: both Above Range and Below Range alert cards show `avg X mg/dL · Y% out of range`

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/web/templates/results.html` | `const patterns` JS injection before charts.js | VERIFIED | Line 207: `const patterns = {{ patterns \| tojson }};` — line 209: `<script src="/static/js/charts.js">` |
| `src/web/templates/results.html` | out_of_range_insights include above behavioral_patterns | VERIFIED | Line 104 (out_of_range_insights) < line 111 (behavioral_patterns) |
| `src/web/templates/components/behavioral_patterns.html` | Inline two-dimensional badge rows; no accordion | VERIFIED | 0 `<details>`, 0 `<summary>`, 0 `collapse`; all six badge variants present and always-visible |
| `src/web/templates/components/out_of_range_insights.html` | Priority out-of-range insights component with % out of range | VERIFIED | File exists; `pct_out_of_range` rendered 2× (Above Range line 45, Below Range line 70); `% out of range` text appears in both cards |
| `src/cgm_insights/analytics/behavioral_patterns.py` | `pct_out_of_range` field, computation, and constructor wiring | VERIFIED | 4 occurrences confirmed: field def (line 60), Polars filter computation (lines 225–228), dict key (line 238), constructor kwarg (line 335) |
| `tests/test_analytics/test_behavioral_patterns.py` | Test fixture updated with `pct_out_of_range=0.25` | VERIFIED | Line 287: `pct_out_of_range=0.25` in `test_behavioral_pattern_is_immutable` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `results.html` | `charts.js` | `const patterns` declaration before script tag | WIRED | const at line 207, script at line 209 — order correct |
| `results.html` | `out_of_range_insights.html` | `{% include 'components/out_of_range_insights.html' %}` | WIRED | Line 104; `{% with behavioral_patterns=behavioral_patterns %}` scoping correct |
| `results.html` | `behavioral_patterns.html` | `{% include 'components/behavioral_patterns.html' %}` | WIRED | Line 111; include order below out_of_range_insights (priority ordering satisfied) |
| `behavioral_patterns.html` | `BehavioralPattern.avg_glucose` | `{% if pattern.avg_glucose < 70 %}` / `> 180` range badge logic | WIRED | Both threshold guards present and rendering to inline badges |
| `out_of_range_insights.html` | `behavioral_patterns.patterns` | 60-min window filter + hourly boundary density filter | WIRED | `selectattr("window_size_min", "equalto", 60)` + `bucket_start_minute % 60 == 0` both present |
| `out_of_range_insights.html` | `BehavioralPattern.pct_out_of_range` | `(pattern.pct_out_of_range * 100) \| round(0) \| int` | WIRED | 2 occurrences in template (lines 45, 70); field populated via `_compute_all_buckets` → `BehavioralPattern(...)` constructor chain |
| `behavioral_patterns.py` | Polars glucose threshold filter | `(pl.col("glucose") < 70) \| (pl.col("glucose") > 180)` | WIRED | Lines 225–227; out_of_range_count / subset.height at line 228; result stored in dict at line 238 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `results.html` scripts block | `patterns` | `results.py`: `session_data.patterns` — real PatternResult objects from analytics pipeline | Yes — not a static return | FLOWING |
| `behavioral_patterns.html` | `behavioral_patterns` | `results.py`: `session_data.behavioral_patterns` — real BehavioralAnalysisResult from upload pipeline | Yes — populated by `analyze_behavioral_patterns()` on upload; only `None` if skipped | FLOWING |
| `out_of_range_insights.html` | `behavioral_patterns` | Same as above — same `{% with %}` scope | Yes | FLOWING |
| `out_of_range_insights.html` | `pct_out_of_range` | `_compute_all_buckets` Polars filter per bucket; wired via `BehavioralPattern(pct_out_of_range=b["pct_out_of_range"])` | Yes — computed from real glucose readings per bucket | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite (252 tests) | `python -m pytest tests/ -q` | 252 passed, 1 skipped, 0 FAILED | PASS |
| Template syntax valid | `pytest tests/web/test_results.py::TestResultsTemplateRendering::test_all_templates_parse_without_syntax_errors` | PASSED (implied by full suite pass) | PASS |
| No accordion in behavioral_patterns.html | `grep -c "<details\|collapse"` | 0 | PASS |
| Range badges present | `grep -n "badge-error\|badge-warning\|badge-success\|badge-ghost"` | 6 badge variant lines confirmed | PASS |
| out_of_range_insights wired above behavioral_patterns | include line 104 < line 111 | Confirmed | PASS |
| const patterns before charts.js | line 207 < line 209 | Confirmed | PASS |
| Density filter in behavioral_patterns.html | `grep "bucket_start_minute % window_min == 0"` | line 44 | PASS |
| Hourly boundary filter in out_of_range_insights.html | `grep "bucket_start_minute % 60 == 0"` | line 15 | PASS |
| pct_out_of_range in behavioral_patterns.py | `grep -c "pct_out_of_range"` | 4 (field def, computation, dict key, constructor kwarg) | PASS |
| pct_out_of_range rendered in template | `grep -c "pct_out_of_range"` in out_of_range_insights.html | 2 (Above Range + Below Range cards) | PASS |
| % out of range text in template | `grep "% out of range"` | 2 matches | PASS |
| Test fixture updated | `grep "pct_out_of_range=0.25"` | line 287 in test file | PASS |

---

### Requirements Coverage

Phase 8 was designated as a UX improvement phase with no formal requirement IDs. Coverage is assessed solely against the 6 ROADMAP success criteria above. All 6 now verified.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | — |

No TODO/FIXME/placeholder comments, no empty return stubs, no hardcoded static data found in any modified file. All data flows from real session state. `pct_out_of_range` computes from live Polars filter on per-bucket readings — not a hardcoded value.

---

### Human Verification Required

#### 1. Time-of-Day Chart Renders on Upload

**Test:** Upload a Sugarmate Excel file (covering 7+ days), navigate to results page, scroll to Daily Patterns section.
**Expected:** Chart renders with colored line data — not a blank canvas.
**Why human:** Requires browser with real CGM data file; chart rendering cannot be verified by template parsing alone.

#### 2. Out-of-Range Section Appears Only When Applicable

**Test:** Upload a file where no 60-min hourly-boundary patterns fall outside 70–180 mg/dL.
**Expected:** No "Time Windows to Focus On" card appears — page goes directly from Daily Patterns chart to Behavioral Patterns tabs.
**Why human:** Requires a specific test file with in-range-only patterns to confirm the two-pass guard suppresses the card.

#### 3. Weekday/Weekend Split and % Out of Range Visible With Sufficient Data

**Test:** Upload a file with 14+ days of data (sufficient weekdays and weekend days), navigate to out_of_range_insights and behavioral_patterns components.
**Expected:** "WD 145 · WE 162" style split visible inline in behavioral_patterns rows; "Weekdays: 152 mg/dL · Weekends: 171 mg/dL" and "63% out of range" (or similar) visible in out-of-range insights cards.
**Why human:** Requires data with sufficient weekday and weekend coverage to trigger the WD/WE split conditional (`>= 5 days` threshold). The `% out of range` rendering is confirmed structurally but must be visually validated end-to-end.

---

## Gaps Summary

No gaps remain. All 6 ROADMAP Success Criteria are verified.

The one gap from the initial verification (SC-5: "% out of range" absent from out-of-range insights) was closed by plan 08-04:
- `BehavioralPattern.pct_out_of_range: float` field added (ge=0.0, le=1.0)
- Computed per bucket via Polars filter on raw glucose readings
- Wired through `analyze_behavioral_patterns` BehavioralPattern constructor
- Rendered in both Above Range and Below Range alert cards as "avg X mg/dL · Y% out of range"
- Test fixture `test_behavioral_pattern_is_immutable` updated with `pct_out_of_range=0.25`
- Full test suite: 252 passed, 0 failed

Three items require human browser testing before the phase can be marked fully complete: chart rendering with real data, conditional card suppression, and end-to-end WD/WE + pct_out_of_range display.

---

_Verified: 2026-06-12T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
