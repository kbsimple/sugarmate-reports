# Phase 2: CLI Tool + Insights - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous execution)

<domain>
## Phase Boundary

CLI Tool + Insights builds a command-line interface for the Core Analysis Library (Phase 1) and adds pattern detection for actionable insights. Users can run analysis from terminal, view glucose trends, and receive time-of-day pattern suggestions.

**Dependencies:** Phase 1 (Core Analysis Library) must be complete.

**Delivers:**
- Typer-based CLI with file path and date range arguments
- Glucose trend visualization (terminal-based graphs)
- Daily summary statistics
- Period comparison (current vs previous)
- Time-of-day and day-of-week pattern detection
- Actionable suggestions using wellness language

</domain>

<decisions>
## Implementation Decisions

### CLI Framework
- **Typer** — Already specified in tech stack. Modern async-friendly CLI framework with rich terminal output support.
- **Output format** — Rich tables for metrics, asciichart for trends (terminal-compatible).
- **Entry point** — `cgm-insights analyze <file>` command.

### Visualization Approach
- **Terminal graphs** — Use asciichart or rich-pixels for glucose trend visualization. No external dependencies (matplotlib, plotly) to keep CLI lightweight.
- **Color-coded zones** — Use Rich library colors for low (red), target (green), high (yellow) zones.
- **Daily summary** — Table format with date, average, TIR, readings count.

### Pattern Detection
- **Time-of-day patterns** — Group readings by hour, calculate average per hour, identify patterns (spikes at specific times).
- **Day-of-week patterns** — Group readings by day name, compare weekday vs weekend.
- **Actionable suggestions** — Template-based with wellness language ("Consider [action] after [time]" rather than medical advice).

### Comparison Feature
- **Side-by-side** — Two columns for current vs previous period in terminal output.
- **Delta highlighting** — Show percentage change with color indicators (improved/worsened).

### Claude's Discretion
- CLI argument structure and help text formatting
- Exact pattern detection algorithm implementation
- Insight template wording

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Core Library (Phase 1)** — `cgm_insights` package with `analyze_file()`, `format_results()`, models
- **CGMReading** — Validated data model with timestamp, glucose_mg_dl, trend, source
- **AnalysisResults** — Contains TimeInRange (5 bands), avg_glucose, std_glucose, gmi, cv_pct, completeness, quality_flags
- **SugarmateParser** — CSV parsing ready for CLI use
- **Validator** — Completeness validation, sensor warmup detection

### Established Patterns
- **Pydantic v2** — ConfigDict pattern for model configuration
- **Glucose validation** — 40-400 mg/dL physiologically plausible range
- **5-band TIR** — very_low/low/target/high/very_high structure
- **Wellness language** — GMI_CAVEAT constant for disclaimers

### Integration Points
- `cgm_insights.analyze_file()` — Main entry point for CLI
- `cgm_insights.format_results()` — Output formatting for display
- CLI will call core library functions directly

</code_context>

<specifics>
## Specific Ideas

- CLI command: `cgm-insights analyze <file> [--start DATE] [--end DATE] [--compare]`
- Default output: Summary table + trend graph + insights list
- Comparison output: Side-by-side tables with delta indicators
- Pattern output: "Afternoon spike detected (avg 180 mg/dL at 3pm). Consider a short walk after lunch."

</specifics>

<deferred>
## Deferred Ideas

- Real-time CGM connection (v2+ requirement)
- Post-meal analysis (requires meal logging)
- Anomaly detection (v2+ requirement)
- Advanced pattern ML models

</deferred>