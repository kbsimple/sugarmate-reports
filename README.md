# CGM Insights

**Quick Start: [Analyze Your CGM Data →](https://sugarmate-reports.onrender.com)**

Analyze your Continuous Glucose Monitor data and understand your glucose patterns. Upload a Sugarmate CSV export and get time-in-range metrics, behavioral patterns, overnight analysis, and unusual reading detection — all in wellness language, no medical advice.

Available as a CLI tool, Python library, and web dashboard.

---

## Installation

```bash
git clone https://github.com/kbsimple/sugarmate-reports.git
cd sugarmate-reports
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

**Requires:** Python 3.10+, a [Sugarmate](https://sugarmate.io) CSV export.

---

## CLI

```bash
# Full analysis (all features on by default)
cgm-insights analyze readings.csv

# Limit to a date range
cgm-insights analyze readings.csv --start 2024-01-01 --end 2024-01-31

# Compare current period against the previous one
cgm-insights analyze readings.csv --compare

# Download from a URL and analyze
cgm-insights download-and-analyze https://example.com/readings.csv
```

**All flags** (each has a `--no-*` counterpart to disable):

| Flag | What it shows |
|------|--------------|
| `--viz` | ASCII trend graph with color-coded zones |
| `--compare` | Side-by-side comparison with prior period |
| `--insights` | Time-of-day and day-of-week pattern highlights |
| `--behavioral` | 30/60/120-min sliding-window consistency scores |
| `--overnight` | 10pm–6am window metrics (mean, TIR, CV, stability) |
| `--anomaly` | Unusual readings vs. personal baseline, by week |
| `--exclude-warmup` | Drop first 2 hours of sensor data (default: on) |

---

## Web Interface

```bash
uvicorn web.app:app --reload
# Open http://localhost:8000
```

Upload a CSV, explore an interactive Chart.js dashboard, and download an AGP (Ambulatory Glucose Profile) PDF for your healthcare provider.

---

## Python Library

```python
from cgm_insights import (
    analyze_file,
    analyze_behavioral_patterns,
    analyze_overnight_patterns,
    analyze_anomalies,
)

results = analyze_file("readings.csv")
print(f"Time in Range: {results.time_in_range.target_pct:.1f}%")
print(f"Average Glucose: {results.avg_glucose:.0f} mg/dL")
print(f"GMI: {results.gmi:.1f}%")

behavioral = analyze_behavioral_patterns(results.readings)
overnight  = analyze_overnight_patterns(results.readings)
anomalies  = analyze_anomalies(results.readings)
```

---

## Features

**Core metrics**
- Time-in-Range across five glucose bands (very low / low / target / high / very high)
- Average glucose, standard deviation, GMI with accuracy caveat
- Data completeness percentage and gap detection

**Behavioral patterns** *(v2.0)*
- Sliding-window analysis at 30, 60, and 120-minute granularities
- Weekday vs. weekend segmentation for every time period
- Cross-day consistency scores — surface your most and least predictable windows

**Overnight analysis** *(v2.0)*
- Dedicated 10pm–6am window with mean glucose, TIR, CV, and time below range
- Overnight stability score (higher = more consistent night-to-night)
- Weekday vs. weekend overnight comparison
- Sustained excursion detection (≥3 consecutive readings outside threshold)

**Unusual pattern detection** *(v2.0)*
- Personal baseline built from your own time-of-day/day-of-week history
- PISA artifact filtering (pressure-induced sensor drops removed before analysis)
- Severity tiers: mild (2–3×), moderate (3–4×), significant (4×+) from baseline
- Weekly aggregate summaries — no individual reading alerts

**Reports**
- AGP PDF export with glucose profile, daily glucose, and data statistics
- All insights use wellness language — no medical advice, no treatment suggestions

---

## Deploy on Render

The repo includes a `render.yaml` that pre-configures everything. The only manual step is entering three fields in the Render dashboard.

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect the `sugarmate-reports` GitHub repo
3. Fill in:

| Field | Value |
|-------|-------|
| **Build command** | `pip install -e .` |
| **Start command** | `uvicorn web.app:app --host 0.0.0.0 --port $PORT` |

4. Add environment variables:

| Key | Value |
|-----|-------|
| `PYTHONPATH` | `src` |
| `ALLOWED_ORIGINS` | *(leave blank on first deploy; set to your `https://your-app.onrender.com` URL after)* |

5. Click **Create Web Service**.

> **Note:** The free tier spins down after 15 minutes of inactivity — the first request after idle takes ~30 seconds. Upgrade to the $7/month Starter tier to keep it warm.

---

## Development

```bash
# Run tests
.venv/bin/python -m pytest

# Run with coverage
.venv/bin/python -m pytest --cov=src --cov-report=html

# Type check
.venv/bin/python -m mypy src
```

**Stack:** Polars · Pydantic v2 · Typer + Rich · FastAPI + HTMX · Chart.js · ReportLab

---

## Disclaimer

This tool provides wellness insights and pattern analysis only. It does not provide medical advice, insulin recommendations, or treatment suggestions. Always consult your healthcare provider for medical decisions.
