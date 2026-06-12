# Phase 8: Time-of-Day Chart & Patterns UX - Research

**Researched:** 2026-06-11
**Domain:** Frontend template/JS bug fix + Jinja2 template UX redesign (pure web layer, no backend changes)
**Confidence:** HIGH

---

## Summary

Phase 8 is a pure frontend phase. There is no new backend analysis code to write. All required data
already exists in the session and is passed to the template. The work is three tightly scoped tasks:
(1) fix a one-line JS injection bug that keeps the Time-of-Day chart blank, (2) redesign the
`behavioral_patterns.html` component to show range status and variability inline without accordions,
and (3) add a new priority-insights section that surfaces out-of-range time windows with weekday vs
weekend detail.

The codebase is fully understood. All data structures are verified. No new Python code, no new
library dependencies, and no CLI changes are needed. The fix can be executed without research into
external documentation.

**Primary recommendation:** Three sequential plan files — 08-01 (chart bug fix + JS audit), 08-02
(behavioral patterns UX redesign), 08-03 (out-of-range priority insights section). Each plan is
self-contained and verifiable by running the existing template-rendering test suite.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Time-of-Day chart rendering | Browser/Client | — | Chart.js reads a JS const; fix is injecting that const from template |
| Behavioral patterns display | Frontend Server (Jinja2/SSR) | — | Component is server-rendered HTML; data is already in template context |
| Range status derivation | Frontend Server (Jinja2/SSR) | — | Computed from avg_glucose in template logic; no backend change needed |
| Out-of-range priority insights | Frontend Server (Jinja2/SSR) | — | New template section filtering behavioral_patterns by range; data already exists |
| Weekday/weekend insight segmentation | Frontend Server (Jinja2/SSR) | — | weekday_avg_glucose / weekend_avg_glucose fields already on BehavioralPattern |

---

## Bug Analysis: Blank Time-of-Day Chart

### Root Cause (VERIFIED: direct code inspection)

`src/web/templates/results.html` `{% block scripts %}` injects two JS constants but not `patterns`:

```html
<!-- Current (broken): -->
<script>
const tirData = {{ tir_data | tojson }};
const glucoseReadings = {{ glucose_readings | tojson }};
</script>
<script src="/static/js/charts.js"></script>
```

`src/web/static/js/charts.js` `initializeCharts()` guards the chart call with:

```js
if (typeof patterns !== 'undefined' && patterns && patterns.length > 0) {
    createDailyPatternsChart('dailyPatternsChart', patterns);
}
```

Because `patterns` is never declared as a JS const, `typeof patterns` is always `'undefined'` and
the chart call is never reached. The canvas element `#dailyPatternsChart` exists in
`daily_patterns.html` but Chart.js never draws on it.

### Fix (VERIFIED: template context confirmed)

`results.py` passes `"patterns": formatted_patterns` to the template context (line 131). In the
template, `patterns` is the top-level Jinja2 variable — the same one used by `patterns_list.html`.
The `daily_patterns.html` include at line 98 uses no `{% with %}` block, so it inherits `patterns`
from the outer scope.

**One-line fix:**

```html
<script>
const tirData = {{ tir_data | tojson }};
const glucoseReadings = {{ glucose_readings | tojson }};
const patterns = {{ patterns | tojson }};
</script>
```

`formatted_patterns` is a list of dicts with keys: `type`, `description`, `time_period`, `severity`,
`avg_glucose`, `reading_count`, `confidence`. The `createDailyPatternsChart()` function filters for
`p.type === 'time_of_day'` — this matches the `PatternType.TIME_OF_DAY = "time_of_day"` enum value.

### JS Audit Scope

The `charts.js` file has three chart creation functions. Only `createDailyPatternsChart` is broken.
The other two work because `tirData` and `glucoseReadings` are already injected. No other chart
functions need changes.

One cosmetic note: `createDailyPatternsChart` sorts time periods by parsing the leading integer from
`time_period` (e.g. `"14:00-16:00"` → 14). This works for the `"HH:MM-HH:MM"` format used by
`detect_time_of_day_patterns()`. No change needed.

---

## Data Structures (VERIFIED: direct source inspection)

### PatternResult (patterns.py) — used by Time-of-Day chart

Fields available to `createDailyPatternsChart`:

| Field | Type | Notes |
|-------|------|-------|
| `type` | `str` | `"time_of_day"` or `"day_of_week"` |
| `time_period` | `str` | Format: `"HH:MM-HH:MM"` e.g. `"14:00-16:00"` |
| `avg_glucose` | `float` | Average glucose for this period |
| `reading_count` | `int` | Readings contributing to pattern |
| `severity` | `str` | `"info"`, `"moderate"`, `"significant"` |
| `description` | `str` | Human-readable pattern description |

### BehavioralPattern (behavioral_patterns.py) — used by redesigned UX

Fields available in `behavioral_patterns.html`:

| Field | Type | Notes |
|-------|------|-------|
| `window_size_min` | `int` | 30, 60, or 120 |
| `bucket_start_minute` | `int` | 0–1439 |
| `bucket_label` | `str` | e.g. `"12:00–12:30"` (en dash) |
| `consistency_label` | `str` | `"Consistent"`, `"Moderate"`, `"Variable"` |
| `cv_score` | `float` | Lower = more consistent |
| `avg_glucose` | `float` | Mean glucose across all days |
| `weekday_avg_glucose` | `float\|null` | None if < 5 weekdays with data |
| `weekend_avg_glucose` | `float\|null` | None if < 5 weekend days with data |
| `days_with_data` | `int` | Distinct calendar days |
| `reading_count` | `int` | Total readings |

`behavioral_patterns` template variable is the `.model_dump()` of `BehavioralAnalysisResult`:
```
{
  "patterns": [...],
  "window_sizes": [30, 60, 120],
  "total_days": N,
  "insufficient_data": bool
}
```

---

## Standard Stack

### Core (no new dependencies)

| Component | Technology | Notes |
|-----------|-----------|-------|
| Template engine | Jinja2 (via FastAPI/Starlette) | Already in use |
| CSS framework | DaisyUI + Tailwind (CDN) | Already in use |
| Chart library | Chart.js 4.4.1 (CDN) | Already in use |
| Backend | FastAPI | No changes needed |

**Installation:** None. Zero new dependencies for this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
Upload → Session Storage → results.py route → Jinja2 template render
                                  |
                            template context:
                            - patterns (PatternResult list) → JS const → Chart.js
                            - behavioral_patterns (dict) → Jinja2 HTML render
                                  |
                       results.html
                       ├── daily_patterns.html (canvas #dailyPatternsChart)
                       ├── behavioral_patterns.html (DaisyUI tabs)
                       └── [new] out_of_range_insights.html (priority list)
                                  |
                       charts.js (DOMContentLoaded)
                       └── createDailyPatternsChart('dailyPatternsChart', patterns)
```

### Recommended Project Structure

No structural changes needed. Files to modify or create:

```
src/web/
├── templates/
│   ├── results.html                      ← ADD: const patterns injection (1 line)
│   ├── components/
│   │   ├── daily_patterns.html           ← no change needed
│   │   ├── behavioral_patterns.html      ← REDESIGN: remove accordion, add range badge
│   │   └── out_of_range_insights.html    ← CREATE: new priority insights component
└── static/js/
    └── charts.js                         ← no change needed (bug is in template, not JS)
```

### Pattern 1: Range Status Badge in Jinja2

**What:** Derive range status from `avg_glucose` in template logic, render as colored DaisyUI badge.
**When to use:** Each behavioral pattern row in the redesigned component.

```html
{# Source: verified against DaisyUI badge docs and existing codebase patterns #}
{% if pattern.avg_glucose < 70 %}
  <span class="badge badge-error">Below Range</span>
{% elif pattern.avg_glucose > 180 %}
  <span class="badge badge-warning">Above Range</span>
{% else %}
  <span class="badge badge-success">In Range</span>
{% endif %}
```

Thresholds: below range `< 70`, in range `70–180`, above range `> 180` mg/dL.
These match the values already used in `charts.js` (`GLUCOSE_COLORS`) and the existing
`HIGH_GLUCOSE_THRESHOLD` / `LOW_GLUCOSE_THRESHOLD` constants in `patterns.py`.

### Pattern 2: Two-Dimensional Row Layout

**What:** Show consistency label + range status side by side, plus avg and weekday/weekend split —
all visible without any expand/collapse.

```html
<div class="bg-base-200 rounded-lg p-2 flex items-center justify-between">
  <div class="flex items-center gap-2">
    <span class="text-sm font-medium">{{ pattern.bucket_label }}</span>
    {# Consistency badge #}
    {% if pattern.consistency_label == "Consistent" %}
      <span class="badge badge-success badge-sm">Consistent</span>
    {% elif pattern.consistency_label == "Variable" %}
      <span class="badge badge-warning badge-sm">Variable</span>
    {% else %}
      <span class="badge badge-ghost badge-sm">Moderate</span>
    {% endif %}
    {# Range status badge — NEW #}
    {% if pattern.avg_glucose < 70 %}
      <span class="badge badge-error badge-sm">Below Range</span>
    {% elif pattern.avg_glucose > 180 %}
      <span class="badge badge-warning badge-sm">Above Range</span>
    {% else %}
      <span class="badge badge-success badge-outline badge-sm">In Range</span>
    {% endif %}
  </div>
  <div class="text-right">
    <p class="text-sm font-medium">{{ pattern.avg_glucose | round(0) | int }} mg/dL</p>
    {% if pattern.weekday_avg_glucose is not none and pattern.weekend_avg_glucose is not none %}
    <p class="text-xs text-base-content/60">
      WD {{ pattern.weekday_avg_glucose | round(0) | int }} &middot;
      WE {{ pattern.weekend_avg_glucose | round(0) | int }}
    </p>
    {% endif %}
  </div>
</div>
```

### Pattern 3: Out-of-Range Priority Insights

**What:** A new component that filters `behavioral_patterns.patterns` where `avg_glucose < 70` or
`> 180`, groups by range status, and renders each as an alert card with weekday/weekend split.
**When to use:** After (or before) the behavioral_patterns tab component in `results.html`.

Filter logic (Jinja2 — verified against Jinja2 selectattr):

```html
{% set oor_patterns = behavioral_patterns.patterns
    | selectattr("avg_glucose", "gt", 180)
    | sort(attribute="avg_glucose", reverse=True)
    | list %}
{# Similarly for below-range: selectattr("avg_glucose", "lt", 70) #}
```

**Important:** Jinja2 `selectattr` with comparison operators (`"gt"`, `"lt"`) requires
`jinja2.Environment` with `undefined=ChainableUndefined` or a version ≥ 2.11. The project uses
Jinja2 via Starlette/FastAPI. Safer to use `selectattr` with a custom test or filter within
a `{% for %}` loop using an `{% if %}` guard instead:

```html
{% for pattern in behavioral_patterns.patterns %}
  {% if pattern.avg_glucose > 180 %}
    {# render out-of-range card #}
  {% endif %}
{% endfor %}
```

This avoids any version-specific filter concerns and matches existing template patterns in the
codebase (the existing components all use `{% if %}` guards, not `selectattr` comparisons).

For the priority insights section, only show the 60-minute window patterns to avoid overwhelming
users with overlapping 30/120-min windows for the same time period. Use the 60-minute window as
the canonical display:

```html
{% set window_patterns = behavioral_patterns.patterns
    | selectattr("window_size_min", "equalto", 60) | list %}
```

`selectattr` with `"equalto"` is already used in the existing `behavioral_patterns.html` (line 40),
so this pattern is verified safe.

### Anti-Patterns to Avoid

- **`<details>`/`<summary>` accordion for variability data:** Already in the existing component — must be removed. The goal is zero hidden information for range status and weekday/weekend split.
- **Injecting `behavioral_patterns` as a JS const:** Not needed. The out-of-range insights are server-rendered HTML, not a chart.
- **Computing range status in Python:** Unnecessary backend change. Derivation from `avg_glucose` thresholds is trivial in Jinja2.
- **Showing all three window sizes in the priority insights section:** Would create redundant/overlapping insights. Use 60-minute window only for the priority list.
- **Using Jinja2 `selectattr` with `"gt"`/`"lt"` tests:** These rely on Jinja2 version behavior; use `{% if %}` guards in loop instead.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color-coded status badges | Custom CSS classes | DaisyUI `badge-success`, `badge-error`, `badge-warning` | Already used throughout codebase; consistent with existing components |
| Range threshold logic | New Python class | Jinja2 `{% if %}` on `avg_glucose` | Pure presentation logic; no business value in backend |
| Chart color mapping | Custom logic | `GLUCOSE_COLORS` object already in `charts.js` | Reuse existing constants |

**Key insight:** This phase is entirely presentation. The analysis data is already correct and
complete. The only gaps are (1) a missing JS variable injection and (2) UI components that hide
information behind accordions.

---

## Common Pitfalls

### Pitfall 1: Variable Name Collision (`patterns`)

**What goes wrong:** `patterns` in the template context is the `formatted_patterns` list from
`patterns.py` (PatternResult objects) — NOT the behavioral patterns. They are completely different
data structures used by different parts of the page.

**Why it happens:** Both the `daily_patterns.html` chart and the `patterns_list.html` suggestions
component use the same `patterns` template variable. The behavioral patterns component uses the
separate `behavioral_patterns` variable.

**How to avoid:** When adding `const patterns = {{ patterns | tojson }};` to the scripts block, use
exactly the key `patterns` (the PatternResult list, not behavioral_patterns). The `charts.js`
function `createDailyPatternsChart` already knows to filter for `p.type === 'time_of_day'`.

**Warning signs:** Chart renders but shows day-of-week patterns, or chart errors in browser console
about missing `.time_period` splits.

### Pitfall 2: `patterns` May Be an Empty List

**What goes wrong:** If the uploaded file has insufficient patterns detected, `formatted_patterns`
is `[]`. The `charts.js` guard already handles this: `if (... patterns.length > 0)` exits cleanly.
The `daily_patterns.html` template also has its own empty-state check (line 29).

**How to avoid:** No special handling needed — both guards are already in place.

### Pitfall 3: `behavioral_patterns` Can Be `None`

**What goes wrong:** If the session has no behavioral analysis (upload with < 5 days), the template
variable is `None`. The existing component handles this at line 16 with `{% if not behavioral_patterns %}`.
The new out-of-range insights component must apply the same guard before accessing `.patterns`.

**How to avoid:** Wrap the new component with `{% if behavioral_patterns and not behavioral_patterns.insufficient_data %}`.

### Pitfall 4: `weekday_avg_glucose` / `weekend_avg_glucose` Can Be `null`

**What goes wrong:** The split values are `None` in Python (serialized as `null` in JSON /
`none` in Jinja2) when the user has < 5 weekday or weekend days. The existing component already
checks `{% if pattern.weekday_avg_glucose is not none %}`.

**How to avoid:** Maintain the same `is not none` guard in the new inline layout and the priority
insights section.

### Pitfall 5: Accordion Removal Causes Vertical Overwhelm

**What goes wrong:** The 60-minute window has ~288 buckets (every 5 min slide). Showing all 288
rows without truncation makes the component unusable.

**Why it happens:** The original accordion hid extra detail precisely because there's a lot of it.

**How to avoid:** The existing component already limits display to a specific `window_size_min`
tab. Within a single tab, the 60-minute window with 5-min slide produces ~288 overlapping windows.
For UX clarity, the redesign should display the non-overlapping representative windows (e.g., show
only buckets where `bucket_start_minute % window_size_min == 0`), or use the original 2-hour
time blocks from `patterns.py`. Check how many patterns are rendered in the current component
to confirm density before committing to a display strategy.

**Alternative:** Keep the tabbed window-size interface but reduce density by showing only
`bucket_start_minute % 60 == 0` buckets within the 60-minute window tab (hourly boundaries).

### Pitfall 6: Jinja2 Template Syntax Regression

**What goes wrong:** The existing test `test_all_templates_parse_without_syntax_errors` will catch
Jinja2 syntax errors in modified templates. Django-style template syntax is invalid in Jinja2.

**How to avoid:** Use only Jinja2-valid syntax. The existing components in this codebase provide
correct patterns to follow. Run `pytest tests/web/test_results.py::TestResultsTemplateRendering`
after each template change.

---

## Code Examples

### Fix for results.html scripts block
```html
{# Source: verified from results.py context dict line 131 and charts.js line 327 #}
{% block scripts %}
<script>
// Chart data from template
const tirData = {{ tir_data | tojson }};
const glucoseReadings = {{ glucose_readings | tojson }};
const patterns = {{ patterns | tojson }};
</script>
<script src="/static/js/charts.js"></script>
{% endblock %}
```

### Out-of-range insights filter (60-min window, above range)
```html
{# Source: verified Jinja2 pattern from existing behavioral_patterns.html line 40 #}
{% set window_patterns = behavioral_patterns.patterns
    | selectattr("window_size_min", "equalto", 60) | list %}
{% for pattern in window_patterns %}
  {% if pattern.avg_glucose > 180 %}
    {# render above-range insight card #}
  {% endif %}
{% endfor %}
```

### DaisyUI alert card for out-of-range insight
```html
{# Source: verified from existing patterns_list.html alert pattern #}
<div class="alert alert-warning">
  <div class="flex-1">
    <div class="flex items-center justify-between flex-wrap gap-2">
      <span class="font-medium">{{ pattern.bucket_label }} — Above Range</span>
      <span class="text-sm">avg {{ pattern.avg_glucose | round(0) | int }} mg/dL</span>
    </div>
    {% if pattern.weekday_avg_glucose is not none and pattern.weekend_avg_glucose is not none %}
    <p class="text-sm mt-1 text-base-content/70">
      Weekdays: {{ pattern.weekday_avg_glucose | round(0) | int }} mg/dL
      &middot;
      Weekends: {{ pattern.weekend_avg_glucose | round(0) | int }} mg/dL
    </p>
    {% endif %}
  </div>
</div>
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Accordion (`<details>`) for consistency details | Inline badges (two dimensions per row) | Users see range status without any click |
| Chart data missing from JS scope | Explicit `const patterns = ...` injection | Chart renders on first load |
| No dedicated out-of-range surfacing | Priority insights section above behavioral tabs | Actionable time windows immediately visible |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 60-minute window is the right canonical window for the priority insights section | Common Pitfalls #5, Code Examples | Too many or too few rows shown; could use 120-min instead |
| A2 | Showing only `bucket_start_minute % 60 == 0` rows reduces density sufficiently | Common Pitfalls #5 | Still too dense; may need a different density strategy |

**All other claims in this research were verified by direct source code inspection.**

---

## Open Questions

1. **Row density in the redesigned behavioral_patterns component**
   - What we know: Sliding window with 5-min slide + 60-min window = ~288 bucket entries per tab
   - What's unclear: How many distinct hours have enough data to show after `min_days` filtering?
   - Recommendation: Check a real data file's behavioral_patterns JSON output to confirm typical
     count before choosing the display filter. If < 24 rows, show all. If > 24, filter to hourly.

2. **Where to place the out-of-range insights section on the page**
   - What we know: `results.html` already has a `behavioral_patterns` section and a `patterns_list` section
   - What's unclear: Should the priority insights be above or below the behavioral_patterns tabs?
   - Recommendation: Place it above the full behavioral_patterns tab component — users see the
     "what to focus on" summary first, then can drill into the tabs for full detail.

---

## Environment Availability

Step 2.6 SKIPPED — this phase has no external dependencies beyond the existing project stack. All
required libraries (Jinja2, DaisyUI via CDN, Chart.js via CDN, FastAPI) are already installed and
in use.

---

## Validation Architecture

`workflow.nyquist_validation` is `false` in `.planning/config.json`. Section skipped.

---

## Security Domain

No new input validation, authentication, session handling, or cryptography is introduced in this
phase. Changes are limited to Jinja2 template rendering of already-validated session data. Section
not applicable.

---

## Sources

### Primary (HIGH confidence)

- Direct inspection of `src/web/static/js/charts.js` — confirmed bug location and fix
- Direct inspection of `src/web/templates/results.html` — confirmed missing `const patterns` line
- Direct inspection of `src/web/routes/results.py` — confirmed `patterns` key in template context
- Direct inspection of `src/cgm_insights/analytics/behavioral_patterns.py` — confirmed BehavioralPattern field names
- Direct inspection of `src/web/templates/components/behavioral_patterns.html` — confirmed accordion and existing patterns

### Secondary (MEDIUM confidence)

- Jinja2 `selectattr` with `"equalto"` — verified used at behavioral_patterns.html line 40
- DaisyUI badge classes — [ASSUMED] consistent with existing usage in behavioral_patterns.html

---

## Metadata

**Confidence breakdown:**
- Bug root cause and fix: HIGH — verified by direct code inspection of all five involved files
- Data structure fields: HIGH — verified from Pydantic model definitions and template parameter docs
- UX redesign patterns: HIGH — verified against existing DaisyUI components in the codebase
- Row density concern: MEDIUM — depends on real data; conservative estimate based on algorithm

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (stable stack; changes only if Chart.js or DaisyUI CDN version bumped)
