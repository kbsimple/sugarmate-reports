# Phase 3: Web Interface + Reports - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous execution)

<domain>
## Phase Boundary

Web Interface + Reports provides browser-based file upload, interactive dashboard, and AGP report export. Builds on the Core Analysis Library (Phase 1) and CLI (Phase 2).

**Dependencies:** Phase 1 (Core Analysis Library) and Phase 2 (CLI Tool + Insights) must be complete.

**Delivers:**
- FastAPI web server with HTMX frontend
- File upload for CGM data
- Interactive dashboard with metrics, graphs, and insights
- AGP (Ambulatory Glucose Profile) report export for healthcare sharing

</domain>

<decisions>
## Implementation Decisions

### Framework
- **FastAPI** — Modern async Python web framework, already in tech stack
- **HTMX** — Lightweight interactivity without heavy JS framework
- **Jinja2** — Template rendering for HTML

### UI Structure
- **Single-page dashboard** — Upload, results, and export in one flow
- **File upload** — Drag-and-drop or file selection for CSV files
- **Results display** — Reuse visualization components from Phase 2 (trend graph, tables)
- **AGP export** — PDF generation with standard AGP format

### Architecture
- **Thin adapter** — Web layer calls core library, minimal logic in web code
- **Stateless** — No user accounts or persistence (file upload → analysis → results)
- **Static assets** — CSS, minimal JS for HTMX interactions

### Claude's Discretion
- Exact page layout and styling
- AGP report template format
- Error handling and user feedback flow

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets from Phase 1 & 2
- **Core library** — `cgm_insights.analyze_file()`, `format_results()`, models
- **Visualization** — `render_trend_graph()`, `render_daily_table()`, `render_comparison()`
- **Pattern detection** — `detect_time_patterns()`, `detect_day_patterns()`
- **Suggestions** — `generate_suggestions()` with wellness language
- **CLI entry point** — `cgm_insights.cli` module structure

### Integration Points
- `analyze_file(file_path, start_date, end_date)` — Main analysis entry
- `AnalysisResults` — Contains all metrics, TimeInRange, patterns, suggestions
- `ValidationResult` — Data quality flags

</code_context>

<specifics>
## Specific Ideas

- Upload page with drag-drop zone
- Results page with tabs: Overview, Trends, Patterns
- AGP report button with PDF download
- Responsive design for mobile viewing

</specifics>

<deferred>
## Deferred Ideas

- User accounts and data persistence (v2+)
- Real-time CGM connection (v2+)
- Multiple file comparison (v2+)
- Advanced export formats (v2+)

</deferred>