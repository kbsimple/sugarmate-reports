# Technology Stack

**Project:** CGM Insights
**Researched:** 2026-04-23
**Overall Confidence:** HIGH

## Recommended Stack

### Core Philosophy

**Simplicity over complexity.** This project has:
- File-based data imports (not real-time streams)
- Python analysis engine (must be reusable as library/CLI)
- Simple web frontend for visualization and interaction

The stack prioritizes **Python-first development** with minimal JavaScript, eliminating build tools and frontend framework complexity.

---

## Python Analysis Engine

The core analysis engine is a standalone Python package that can be used as:
1. A library imported by the web app
2. A CLI tool for local analysis
3. A foundation for future integrations

### Data Processing

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **Polars** | 1.40.0 | Primary data processing | 7-9x faster than pandas for file I/O and joins; lazy evaluation for memory efficiency; native Parquet/Arrow support; ideal for CGM time-series data (~8,600 readings/month) |
| **Pandas** | 3.0.2 | ML/scikit-learn compatibility | GlucoStats and other libraries may require pandas DataFrames; conversion is trivial: `polars_df.to_pandas()` |
| **NumPy** | 2.4.4 | Numerical operations | Foundation for scientific computing; required by scipy and glucostats |
| **openpyxl** | 3.1.3 | Excel file parsing | Sugarmate exports are Excel format; use `read_only=True` mode for large files |

**Rationale for Polars over Pandas:**
- CGM data is time-series with ~288 readings/day
- Polars' lazy evaluation prevents loading entire dataset into memory
- Streaming support for files larger than RAM
- Cleaner API for filtering, grouping, and time-based operations
- **Verdict:** Use Polars for ETL, convert to pandas only when required by downstream libraries

### CGM-Specific Analysis

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **GlucoStats** | 1.0.0 | CGM metrics extraction | Purpose-built for CGM data; 59 validated statistics including TIR, MAGE, GMI; scikit-learn compatible; published research (BMC Bioinformatics Sept 2025) |
| **SciPy** | 1.17.1 | Statistical analysis | Required by GlucoStats; signal processing, statistical tests, interpolation for missing CGM readings |

**Why GlucoStats:**
This is a **purpose-built library for CGM analysis**. It extracts 59 statistics across 6 categories:
- Time in Ranges (TIR, TAR, TBR)
- Descriptive Statistics (mean, min, max, AUC)
- Glucose Risks (LBGI, GRADE)
- Glycemic Control (GMI, J-Index)
- Glucose Variability (MAGE, GVP)
- Supports window-based analysis (time-of-day, day-of-week patterns)

**This eliminates the need to implement CGM metrics from scratch.**

### CLI Framework

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **Typer** | 0.24.2 | CLI interface | Created by FastAPI author; type-hint based; automatic `--help` generation; integrates with Rich for beautiful output |

---

## Web Frontend Stack

### Backend Framework

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **FastAPI** | 0.136.0 | Web framework | Async-first; automatic OpenAPI docs; Pydantic validation; 38% of Python developers use it (2026); standard for Python web APIs |
| **Uvicorn** | 0.34.0 | ASGI server | Standard FastAPI server; production-ready with uvloop for performance |
| **Jinja2** | 3.1.6 | HTML templating | Server-side rendering; FastAPI native support; eliminates need for React/Vue |

### Frontend Interactivity

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **HTMX** | 2.0.4 | Dynamic interactions | 14KB library; enables AJAX, CSS transitions, WebSockets via HTML attributes; no build step; no JavaScript framework needed |
| **Alpine.js** | 3.14.3 | Client-side state | For minimal client-side interactivity (dropdowns, modals); 15KB; complements HTMX for pure client state |

**Why HTMX + Alpine.js instead of React/Vue:**
- **5x faster initial page loads** (300-500ms vs 1500-3000ms)
- **95% reduction in page weight** (50-100KB vs 1.5-3MB)
- **No build tools** - no npm, webpack, or node_modules
- **Python developers stay productive** - all logic in Python
- **Server-side rendering** - better SEO and accessibility

### Styling

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **Tailwind CSS** | 4.1.4 | Utility-first CSS | Industry standard; rapid prototyping; no custom CSS needed |
| **DaisyUI** | 5.0.0 | Component library | Pre-built components; semantic class names; works with Tailwind |

### Visualization

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **Chart.js** | 4.4.2 | Interactive charts | Lightweight; good documentation; time-series support; HTMX-compatible |
| **Altair** | 5.5.0 | Statistical visualizations | Python-native; generates Vega-Lite JSON; excellent for glucose pattern analysis |

**Alternative:** Plotly.py for interactive visualizations, but Chart.js is lighter for this use case.

---

## Integration Architecture

### Project Structure

```
cgm-insights/
├── pyproject.toml          # uv project config
├── uv.lock                 # Locked dependencies
├── src/
│   ├── cgm_engine/         # Analysis engine (library)
│   │   ├── __init__.py
│   │   ├── parser.py       # Sugarmate Excel parsing
│   │   ├── analysis.py     # GlucoStats integration
│   │   ├── patterns.py     # Time-of-day, day-of-week analysis
│   │   └── insights.py     # Actionable suggestions generation
│   └── web/                # FastAPI application
│       ├── __init__.py
│       ├── main.py         # FastAPI app
│       ├── routers/
│       │   ├── upload.py   # File upload endpoint
│       │   └── insights.py # Analysis endpoints
│       ├── templates/      # Jinja2 templates
│       │   ├── base.html
│       │   ├── index.html
│       │   └── results.html
│       └── static/
│           ├── css/
│           └── js/
├── cli.py                  # Typer CLI entry point
└── tests/
```

### Integration Pattern

```python
# src/web/main.py
from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from cgm_engine import analyze_file, get_insights

app = FastAPI()
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
templates = Jinja2Templates(directory="src/web/templates")

@app.post("/analyze")
async def analyze(file: UploadFile):
    # Engine is a library - just import and call
    data = await file.read()
    result = analyze_file(data)  # Polars-based processing
    insights = get_insights(result)  # GlucoStats + custom logic
    return {"statistics": result, "insights": insights}

@app.get("/results/{session_id}", response_class=HTMLResponse)
async def results(request: Request, session_id: str):
    # HTMX partials for progressive enhancement
    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={"data": get_cached_results(session_id)}
    )
```

### CLI Usage

```python
# cli.py
import typer
from cgm_engine import analyze_file, generate_report

app = typer.Typer()

@app.command()
def analyze(path: str, output: str = "report.html"):
    """Analyze CGM data from file."""
    result = analyze_file(path)
    generate_report(result, output)
    typer.echo(f"Report saved to {output}")

if __name__ == "__main__":
    app()
```

---

## Package Management

| Tool | Purpose | Why |
|------|---------|-----|
| **uv** | Package manager, venv, Python version | 10-100x faster than pip; replaces pip + virtualenv + pyenv + pip-tools; lockfile reproducibility; 2026 standard |

### pyproject.toml

```toml
[project]
name = "cgm-insights"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    # Core
    "fastapi>=0.136.0",
    "uvicorn[standard]>=0.34.0",
    "jinja2>=3.1.6",

    # Data Processing
    "polars>=1.40.0",
    "pandas>=3.0.2",
    "numpy>=2.4.4",
    "scipy>=1.17.1",
    "openpyxl>=3.1.3",

    # CGM Analysis
    "glucostats>=1.0.0",

    # CLI
    "typer>=0.24.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.11.0",
]

[project.scripts]
cgm-cli = "cli:app"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "ruff>=0.11.0",
]
```

---

## Deployment

### Recommended Platform: Railway or SnapDeploy

| Platform | Free Tier | Best For |
|----------|-----------|----------|
| **Railway** | Limited free hours | Flexibility, database add-ons |
| **SnapDeploy** | 100 free hours | Simplicity, auto-detection |
| **Out Plane** | $20 free credit | Production monitoring |

**Why not containers initially:**
- Single-file upload app doesn't need complex orchestration
- Platform-managed deployment is simpler
- Add Docker later if scaling requires it

### Minimal Production Setup

```dockerfile
# Only if Docker needed later
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
CMD ["uv", "run", "uvicorn", "src.web.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Data Processing | **Polars** | Pandas only | 7-9x slower on I/O; memory-intensive for larger datasets |
| Data Processing | **Polars** | DuckDB | SQL-centric; Polars has better pandas interop for GlucoStats |
| Web Framework | **FastAPI** | Django | Overkill for simple app; ORM not needed for file-based |
| Web Framework | **FastAPI** | Flask | No async; no automatic OpenAPI; older patterns |
| Frontend | **HTMX + Jinja2** | React/Next.js | Overkill for simple dashboard; adds build complexity |
| Frontend | **HTMX + Jinja2** | Reflex | Interesting pure-Python option but less mature ecosystem |
| Package Manager | **uv** | Poetry | 10x slower dependency resolution; uv is 2026 standard |
| Deployment | **Railway** | AWS/AWS | Unnecessary complexity for MVP |

---

## What NOT to Use

| Avoid | Why |
|-------|-----|
| **React/Vue/Svelte** | Requires JavaScript build pipeline; Python developers less productive |
| **Django** | ORM, admin panel, auth - all unnecessary for file-upload analytics app |
| **Poetry** | Slower than uv; uv is now the 2026 standard |
| **SQLite/PostgreSQL** | Not needed for MVP - file-based uploads; can add later for session storage |
| **Celery/Redis** | No async job queues needed initially - analysis is fast enough synchronously |
| **GraphQL** | REST is simpler for this use case; no complex client requirements |

---

## Installation Commands

```bash
# Initialize project
uv init cgm-insights
cd cgm-insights

# Set Python version
uv python pin 3.12

# Add dependencies
uv add fastapi "uvicorn[standard]" jinja2
uv add polars pandas numpy scipy openpyxl
uv add glucostats
uv add typer

# Add dev dependencies
uv add --dev pytest ruff

# Run development server
uv run uvicorn src.web.main:app --reload

# Run CLI
uv run cgm-cli analyze data.xlsx
```

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Data Processing** | HIGH | Polars is proven for this data size; GlucoStats is purpose-built for CGM |
| **Web Framework** | HIGH | FastAPI is the 2026 standard; well-documented; active ecosystem |
| **Frontend** | HIGH | HTMX+Jinja2 pattern well-established; eliminates JavaScript complexity |
| **GlucoStats** | MEDIUM | New library (Sept 2025); well-documented but may need patches for Sugarmate format |
| **Integration** | HIGH | Standard FastAPI library import pattern |
| **Deployment** | HIGH | Railway/SnapDeploy auto-detect FastAPI |

---

## Sources

### Data Processing
- [Polars vs Pandas 2026](https://www.analyticsinsight.net/programming/polars-vs-pandas-in-2026-should-you-make-the-switch) - Performance benchmarks, when to use each
- [Polars 1.40.0 Release](https://github.com/pola-rs/polars/releases/tag/py-1.40.0) - Current version
- [Pandas 3.0.2 Release](https://github.com/pandas-dev/pandas/releases/tag/v3.0.2) - Current stable
- [NumPy 2.4.4 Release](https://github.com/numpy/numpy/releases) - Current stable
- [SciPy 1.17.1 Release](https://github.com/scipy/scipy/releases) - Current stable

### CGM Analysis
- [GlucoStats Documentation](https://glucostats.readthedocs.io/en/latest/) - Official docs
- [GlucoStats Paper](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-025-06250-w) - BMC Bioinformatics publication

### Web Framework
- [FastAPI Latest](https://github.com/fastapi/fastapi/releases/tag/0.136.0) - Current version
- [FastAPI 2026 Guide](https://www.programming-helper.com/tech/fastapi-2026-python-async-api-framework-ml-deployment) - Ecosystem overview

### Frontend
- [FastAPI + HTMX Dashboards](https://medium.com/codex/building-real-time-dashboards-with-fastapi-and-htmx-01ea458673cb) - Real-world pattern
- [HTMX + FastAPI Starter](https://github.com/kszongic/htmx-fastapi-starter) - Production template
- [No-Build Full-Stack](https://blakecrosley.com/guides/fastapi-htmx) - Production patterns

### Package Management
- [uv Guide 2026](https://www.heyuan110.com/posts/python/2026-04-10-uv-python-package-manager/) - Comprehensive best practices
- [Package Managers Compared](https://scopir.com/posts/best-python-package-managers-2026/) - uv vs Poetry vs pip

### Deployment
- [Railway FastAPI Guide](https://docs.railway.com/guides/fastapi) - Official deployment
- [SnapDeploy FastAPI](https://snapdeploy.dev/blog/deploy-fastapi-60-seconds) - Simple hosting

### CLI
- [Typer Documentation](https://typer.tiangolo.com/) - Official docs
- [Typer 0.24.2 Release](https://pypi.org/project/typer/) - Current version