# CGM Insights

A Python tool for analyzing Continuous Glucose Monitor (CGM) data and generating actionable wellness insights.

## Overview

Upload your CGM data and get:

- **Time-in-Range metrics** — Percentage breakdown across glucose bands (very low, low, target, high, very high)
- **Glucose statistics** — Average glucose, standard deviation, GMI (Glucose Management Indicator)
- **Pattern detection** — Time-of-day and day-of-week glucose patterns
- **Wellness suggestions** — Actionable insights using wellness language (no medical advice)
- **AGP reports** — Export Ambulatory Glucose Profile reports for healthcare sharing

## Installation

```bash
# Clone the repository
git clone https://github.com/kbsimple/sugarmate-reports.git
cd sugarmate-reports

# Create virtual environment and install
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Usage

### Command Line Interface

```bash
# Basic analysis
cgm-insights analyze data.csv

# With date range
cgm-insights analyze data.csv --start 2024-01-01 --end 2024-01-31

# Compare with previous period
cgm-insights analyze data.csv --compare

# Exclude sensor warmup period (default: excluded)
cgm-insights analyze data.csv --include-warmup
```

**Options:**
- `--start DATE` — Start date filter (YYYY-MM-DD)
- `--end DATE` — End date filter (YYYY-MM-DD)
- `--viz/--no-viz` — Show trend visualization (default: on)
- `--compare` — Compare with previous period of same duration
- `--insights/--no-insights` — Show pattern insights (default: on)
- `--exclude-warmup/--include-warmup` — Exclude sensor warmup period (default: exclude)

### Web Interface

```bash
# Start the web server
uvicorn web.app:app --reload

# Open browser to http://localhost:8000
```

The web interface provides:
- Drag-and-drop file upload
- Interactive dashboard with Chart.js visualizations
- AGP report PDF export

### Python Library

```python
from cgm_insights import analyze_file, format_summary

# Run analysis
results = analyze_file("data.csv")

# Access metrics
print(f"Time in Range: {results.time_in_range.target_pct:.1f}%")
print(f"Average Glucose: {results.avg_glucose:.0f} mg/dL")
print(f"GMI: {results.gmi:.1f}%")

# Format output
summary = format_summary(results)
print(summary)
```

## Supported Data Formats

- **Sugarmate CSV exports** — Standard format from the Sugarmate app

## Project Structure

```
src/
├── cgm_insights/        # Core analysis library
│   ├── ingestion/       # Data parsing and validation
│   ├── analytics/       # Metrics and pattern detection
│   ├── output/          # Visualization and suggestions
│   └── cli.py           # CLI entry point
└── web/                 # FastAPI web interface
    ├── routes/          # API endpoints
    ├── services/        # Business logic
    ├── templates/       # Jinja2 templates
    └── static/          # CSS and JavaScript
```

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html

# Lint code
ruff check src tests
```

## Technology Stack

- **Python 3.10+** — Core language
- **Polars** — High-performance data processing
- **GlucoStats** — Validated CGM metrics calculations
- **Pydantic** — Data validation
- **Typer + Rich** — CLI with beautiful terminal output
- **FastAPI + HTMX** — Web interface
- **Chart.js** — Interactive visualizations
- **ReportLab** — PDF report generation

## Disclaimer

This tool provides wellness insights and pattern analysis only. It does not provide medical advice, insulin recommendations, or treatment suggestions. Always consult your healthcare provider for medical decisions.

## License

MIT License — see [LICENSE](LICENSE) for details.