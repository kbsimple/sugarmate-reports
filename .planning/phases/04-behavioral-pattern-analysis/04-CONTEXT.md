# Phase 4: Behavioral Pattern Analysis - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Behavioral Pattern Analysis delivers time-bucketed glucose analysis using sliding windows (30, 60, and 120-minute windows with 5-minute slide intervals), weekday/weekend segmentation, cross-day consistency scoring, and actionable wellness-framed insights.

**Dependencies:** v1.0 complete (Phases 1–3).

**Delivers:**
- New `behavioral_patterns` analysis module in the core library
- Time-bucketed pattern data for all three window sizes (30/60/120 min)
- Weekday vs weekend breakdown per time bucket
- Cross-day consistency score per time period (Pearson correlation)
- Identification of high-consistency and high-variability periods
- Wellness-framed actionable insights from behavioral patterns
- Web and CLI surfaces for the new analysis

</domain>

<decisions>
## Implementation Decisions

### Window Size Display
- **D-01:** Show all three window sizes (30/60/120-min) to the user — not just one default.
- **D-02:** Layout is Claude's discretion — tabs (30/60/120) or stacked sections, whichever fits best in the existing HTMX/Jinja2 web dashboard. Tabs are likely the right call given the existing page structure.

### Existing Pattern Detection
- **D-03:** No backward-compatibility constraint — Phase 4 is free to change what patterns are surfaced in both CLI and web output.
- **D-04:** Fate of existing code is Claude's discretion. Upgrade-in-place is the natural choice: Phase 4 replaces or supersedes `detect_time_of_day_patterns()` and `detect_day_of_week_patterns()` as the primary pattern view. Keeping dead code around is not required.

### Consistency Score Display
- **D-05:** Show a qualitative label by default — `Consistent`, `Moderate`, or `Variable`.
- **D-06:** Raw correlation coefficient is accessible via an expandable detail section (not a tooltip). This works on both desktop and mobile, and fits the HTMX pattern.

### Consistency Threshold (High vs Variable)
- **D-07:** Use relative thresholds — flag top/bottom quartile of the user's own time periods as "high consistency" / "high variability" respectively. This ensures meaningful output for all users regardless of overall glucose control level.
- **D-08:** Middle 50% of periods receive the "Moderate" consistency label.

### Wellness Language
- **D-09:** All insights follow BHVR-06 / INSG-04 — wellness framing throughout. No prescriptive language. Example: "Your noon readings on weekdays are particularly consistent — this period may be a useful anchor for routine." Not: "Your noon routine is fine, don't change it."

### Claude's Discretion
- Layout choice for all-three window size display (tabs vs stacked)
- Exact correlation metric used for consistency (Pearson r is standard; Spearman acceptable if implementation is simpler given pandas/polars)
- Minimum days required for a consistency score to be considered valid (suggest 5+ days of data for that time slot)
- Model structure: whether `PatternResult` is extended or a new `BehavioralPattern` model is created
- Whether behavioral pattern results are added to `AnalysisResults` directly or returned as a separate result object

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Behavioral Patterns — BHVR-01 through BHVR-06 (the 6 requirements this phase implements)
- `.planning/ROADMAP.md` §Phase 4 — Success criteria and dependency notes

### Existing Code to Understand Before Planning
- `src/cgm_insights/analytics/patterns.py` — Existing pattern detection (time-of-day 2-hr blocks, day-of-week); Phase 4 builds on or supersedes this
- `src/cgm_insights/models/results.py` — `AnalysisResults` and `PatternResult` models; integration point for new analysis results
- `src/cgm_insights/__init__.py` — Public API surface; new behavioral analysis functions must be exposed here
- `src/cgm_insights/analytics/metrics.py` — Existing metrics calculation pattern to follow
- `src/web/routes/results.py` — Web results page; where behavioral patterns will be rendered
- `src/cgm_insights/output/suggestions.py` — Wellness language suggestion templates; new insights should follow this pattern

### Prior Phase Context
- `.planning/phases/02-cli-tool-insights/02-CONTEXT.md` — Phase 2 decisions (CLI framework, pattern detection approach)
- `.planning/phases/03-web-interface-reports/03-CONTEXT.md` — Phase 3 decisions (web architecture: thin adapters, stateless, HTMX)

No external specs — requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PatternResult` (patterns.py)**: Existing model with type, description, time_period, severity, avg_glucose, reading_count, confidence, details — likely reusable or extendable for behavioral patterns
- **`PatternType` / `PatternSeverity` enums**: Existing severity/type classification; may need `BEHAVIORAL` type added
- **`_group_by_time_period()`**: Existing helper groups by fixed N-hour blocks — Phase 4 needs sliding window variant
- **`_group_by_day_of_week()`**: Existing day grouping — Phase 4 needs weekday/weekend split per time bucket
- **`_calculate_day_metrics()`**: Returns avg, std, cv, tir, count — reusable as building block for bucket metrics
- **Wellness suggestion templates (`suggestions.py`)**: Template-based system for generating wellness-framed text — Phase 4 insights should use same approach

### Established Patterns
- **Pydantic v2 ConfigDict**: All models use `model_config = ConfigDict(frozen=True)` or similar
- **Confidence scoring**: `min(1.0, count / (MIN_READINGS * N))` pattern for clamped confidence
- **Percent-from-baseline**: 20% deviation threshold used for existing patterns — Phase 4 uses correlation-based consistency instead, but the baseline comparison remains useful for insight text
- **Wellness language**: GMI_CAVEAT constant pattern; new insights must follow the same non-prescriptive framing

### Integration Points
- `analyze_file()` in `__init__.py` — Main entry point; behavioral analysis likely added as optional parameter or returned alongside `AnalysisResults`
- `src/web/routes/results.py` + Jinja2 templates — Web rendering; new behavioral patterns section added here
- `src/cgm_insights/cli.py` — CLI output; new `--behavioral` or integrated into default output

</code_context>

<specifics>
## Specific Ideas

- Consistency label mapping: top 25% of user's time periods → "Consistent", bottom 25% → "Variable", middle 50% → "Moderate"
- Expandable detail section: `<details><summary>Consistent (r=0.82)</summary>...</details>` HTML pattern works cleanly with HTMX/Jinja2, no JS required
- All three window views (30/60/120) shown; tabs likely best since the web dashboard uses a tabbed layout for existing sections

</specifics>

<deferred>
## Deferred Ideas

- Inferred sleep window detection from glucose stability patterns (ENHC-01) — future v2.1+
- Pattern similarity using dynamic time warping (ENHC-02) — future v2.1+
- Personalized threshold tuning based on user feedback (ENHC-03) — future v2.1+
- Custom sleep window for shift workers (ENHC-04) — future v2.1+

None of the above belong in Phase 4 scope.

</deferred>

---

*Phase: 04-behavioral-pattern-analysis*
*Context gathered: 2026-06-11*
