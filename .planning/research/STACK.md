# Technology Stack

**Project:** CGM Insights
**Researched:** 2026-04-23 (v1.0), 2026-06-10 (v2.0 additions)
**Overall Confidence:** HIGH

## Recommended Stack

### Core Philosophy

**Simplicity over complexity.** This project has:
- File-based data imports (not real-time streams)
- Python analysis engine (must be reusable as library/CLI)
- Simple web frontend for visualization and interaction

The stack prioritizes **Python-first development** with minimal JavaScript, eliminating build tools and frontend framework complexity.

---

## Python Analysis Engine (v1.0)

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

## v2.0 Additions: Pattern Analysis (Anomaly, Sleep, Behavioral)

### New Dependencies for v2.0

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| **scikit-learn** | 1.6+ | Anomaly detection (IsolationForest) | Industry standard for unsupervised anomaly detection. Linear O(n) complexity, no distribution assumptions, handles multivariate data. Well-suited for CGM outlier detection after feature engineering. |
| **statsmodels** | 0.14+ | STL seasonal decomposition (optional) | Advanced trend/seasonal separation. Robust STL fitting automatically down-weights outliers. Useful for separating daily patterns from glucose trends. |

**Why IsolationForest for Anomaly Detection:**
- **Linear time complexity O(n)** — scales to millions of readings
- **No distribution assumptions** — CGM data is non-normal
- **Handles multivariate data naturally** — works with rolling features
- **Production-proven** — widely deployed for time-series anomaly detection
- **Minimal hyperparameters** — `contamination` is intuitive (expected anomaly rate)

**Why statsmodels STL (Optional):**
- For data with strong daily/weekly seasonality, STL separates:
  - Trend component (long-term glucose changes)
  - Seasonal component (daily patterns)
  - Residual component (anomalies)
- Robust fitting (`robust=True`) automatically down-weights outliers
- Low-weight observations in the `weights` attribute flag anomalies

### No New Libraries Needed

| Capability | Existing Solution | Notes |
|------------|-------------------|-------|
| Time bucketing | Polars `rolling()`, `rolling_mean_by()` | Polars 1.x has excellent time-series support with temporal windowing (e.g., `"30m"`, `"1h"`, `"2h"`). Supports `every` parameter for sliding windows. |
| Sleep window filtering | Polars `dt.hour()` filter | Simple time-based filtering for 10pm-6am window. No new library needed. |
| CGM metrics | GlucoStats (59 metrics) | Already integrated. Covers time-in-range, variability (MAGE, CV, GVP), glycemic risk indices. Use for sleep window metrics. |
| Sliding windows | Polars `group_by_dynamic()` | Native Polars capability for time-based groupings. Supports offset, closed interval options. |
| Weekday/weekend split | Polars `dt.weekday()` | Polars datetime expressions. No new library needed. |
| Cross-day consistency | SciPy `pearsonr`, `variation` | Already in ecosystem. Use for pattern correlation and coefficient of variation. |

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
│   │   ├── anomaly.py      # [v2.0] IsolationForest anomaly detection
│   │   ├── sleep.py        # [v2.0] Overnight pattern analysis
│   │   ├── behavioral.py   # [v2.0] Cross-day consistency
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

### Integration Pattern (v2.0 Additions)

```python
# src/cgm_engine/anomaly.py
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler
import polars as pl

def detect_anomalies(df: pl.DataFrame) -> pl.DataFrame:
    """Detect glucose anomalies using IsolationForest on engineered features."""

    # Feature engineering with Polars (existing pattern)
    df_features = df.with_columns([
        pl.col("glucose").rolling_mean_by("timestamp", window_size="2h").alias("rolling_mean_2h"),
        pl.col("glucose").rolling_std_by("timestamp", window_size="2h").alias("rolling_std_2h"),
        ((pl.col("glucose") - pl.col("rolling_mean_2h")) / pl.col("rolling_std_2h")).alias("z_score"),
        pl.col("glucose").shift(1).alias("glucose_lag_1"),      # 5-min lag
        pl.col("glucose").shift(12).alias("glucose_lag_1h"),    # 1-hour lag
    ])

    # IsolationForest detection
    clf = IsolationForest(
        n_estimators=200,
        contamination=0.01,  # ~3 anomalies/day expected
        random_state=42
    )

    # Use RobustScaler (resistant to outliers)
    features = df_features.select(["z_score", "rolling_std_2h", "glucose_lag_1h"]).to_numpy()
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(features)

    anomaly_scores = clf.fit_predict(X_scaled)
    return df_features.with_columns(pl.Series("is_anomaly", anomaly_scores))
```

```python
# src/cgm_engine/sleep.py
import polars as pl
from glucostats import ExtractGlucoStats

def analyze_sleep_patterns(df: pl.DataFrame) -> dict:
    """Analyze overnight glucose patterns from inferred 10pm-6am window."""

    # Filter to sleep window
    sleep_df = df.filter(
        (pl.col("timestamp").dt.hour() >= 22) | (pl.col("timestamp").dt.hour() < 6)
    )

    # Convert to pandas for GlucoStats
    sleep_pandas = sleep_df.to_pandas()

    # Compute sleep-specific metrics
    stats_extractor = ExtractGlucoStats([
        "mean", "CV", "TIR_70_180", "TBR_54_70", "TBR_below_54",
        "MAGE", "min_lbgi"
    ])

    sleep_metrics = stats_extractor.transform(sleep_pandas)

    return {
        "mean_glucose": sleep_metrics["mean"].iloc[0],
        "time_in_range": sleep_metrics["TIR_70_180"].iloc[0],
        "variability_cv": sleep_metrics["CV"].iloc[0],
        "mage": sleep_metrics["MAGE"].iloc[0],
    }
```

```python
# src/cgm_engine/behavioral.py
from scipy.stats import pearsonr
from scipy.stats.mstats import variation
import polars as pl
import numpy as np

def compute_pattern_consistency(df: pl.DataFrame, time_bucket: str = "1h") -> dict:
    """Analyze cross-day consistency of time-bucketed patterns."""

    # Create time buckets and weekday/weekend labels
    bucketed = df.with_columns([
        pl.col("timestamp").dt.truncate(time_bucket).alias("bucket"),
        pl.col("timestamp").dt.weekday().alias("day_of_week"),
    ]).with_columns(
        (pl.col("day_of_week") < 5).alias("is_weekday")  # Mon-Fri
    )

    # Compute mean glucose per bucket per day
    daily_patterns = bucketed.group_by(["day_of_week", "bucket"]).agg(
        pl.col("glucose").mean().alias("mean_glucose")
    )

    # Weekday vs weekend comparison
    weekday_patterns = daily_patterns.filter(pl.col("is_weekday"))
    weekend_patterns = daily_patterns.filter(~pl.col("is_weekday"))

    # Compute coefficient of variation for consistency
    # Lower CV = more consistent behavior across days
    def compute_cv(group):
        values = group["mean_glucose"].to_numpy()
        if len(values) < 2:
            return None
        return float(variation(values))  # std/mean

    weekday_cv = compute_cv(weekday_patterns)
    weekend_cv = compute_cv(weekend_patterns)

    # Correlation between weekday patterns (same bucket across days)
    # High correlation = consistent timing of glucose patterns
    pivot = daily_patterns.pivot(
        values="mean_glucose",
        index="bucket",
        columns="day_of_week"
    )
    # Drop null columns for correlation
    pivot_clean = pivot.drop_nulls()

    if pivot_clean.height >= 3:  # Need enough data for correlation
        corr, p_value = pearsonr(
            pivot_clean["Monday"].to_numpy(),
            pivot_clean["Tuesday"].to_numpy()
        )
    else:
        corr, p_value = None, None

    return {
        "weekday_cv": weekday_cv,
        "weekend_cv": weekend_cv,
        "pattern_correlation": corr,
        "correlation_p_value": p_value,
        "interpretation": "consistent" if weekday_cv < 0.15 else "variable"
    }
```

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

## Package Management

| Tool | Purpose | Why |
|------|---------|-----|
| **uv** | Package manager, venv, Python version | 10-100x faster than pip; replaces pip + virtualenv + pyenv + pip-tools; lockfile reproducibility; 2026 standard |

### pyproject.toml (Updated for v2.0)

```toml
[project]
name = "cgm-insights"
version = "0.2.0"
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

    # [v2.0] Pattern Analysis
    "scikit-learn>=1.6.0",
    "statsmodels>=0.14.0",  # Optional for STL decomposition

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

## v2.0 Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| IsolationForest | Local Outlier Factor (LOF) | Small datasets (<10k rows), when anomalies are in locally sparse regions near dense clusters |
| IsolationForest | isotree (Extended IF) | Multimodal distributions, mixed numerical/categorical data, when density-based scoring needed |
| IsolationForest | LSTM Autoencoder | Deep learning preferred, complex temporal patterns, very large datasets with GPU |
| scikit-learn | anomaly-pipeline | Production ensemble needed, want multiple detection methods combined automatically |
| RobustScaler | StandardScaler | NOT recommended - StandardScaler is sensitive to outliers, defeats anomaly detection purpose |
| STL decomposition | MSTL (multiple seasonality) | When both daily AND weekly seasonality need separation (e.g., hourly data with 24 and 168 periods) |

---

## What NOT to Use (v2.0)

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Deep learning (LSTM, Transformers) | Overkill for CGM anomaly detection. Requires GPU, large training data, complex deployment. | IsolationForest with engineered features |
| Prophet for CGM patterns | Designed for forecasting, not anomaly detection. Heavy dependency. | STL decomposition (if needed) + IsolationForest |
| TensorFlow/PyTorch | Adds ML infrastructure complexity for simple outlier detection. | scikit-learn (NumPy-based, no GPU needed) |
| DBSCAN clustering | O(n^2) complexity, poor for large CGM datasets (~288 readings/day). | IsolationForest O(n) complexity |
| Commercial CGM analytics SDKs | Vendor lock-in, limited customization, often require device pairing. | Open-source stack (Polars + GlucoStats + scikit-learn) |

---

## v2.0 Implementation Notes

### 1. Feature Engineering is Critical for IsolationForest

IsolationForest has no temporal awareness. Must engineer rolling features:

```python
# Required features for CGM anomaly detection
features = [
    "z_score",           # (glucose - rolling_mean) / rolling_std
    "rolling_std_2h",    # 2-hour volatility
    "glucose_lag_1h",    # 1-hour change rate proxy
    "hour_of_day",       # Time context (sin/cos encoded)
]
```

### 2. Use RobustScaler, Not StandardScaler

StandardScaler uses mean/std which are influenced by outliers. RobustScaler uses median/IQR, which are outlier-resistant. This is critical for anomaly detection where outliers should NOT influence the scaling.

### 3. Contamination Parameter Tuning

Set `contamination` based on expected anomaly rate. For CGM:
- 1% contamination ~= 3 anomalies/day (288 readings)
- 0.5% contamination ~= 1-2 anomalies/day
- Start conservative, tune based on user feedback

### 4. Polars Time Bucketing for Behavioral Analysis

```python
# 30-minute buckets, sliding every 5 minutes
df.group_by_dynamic(
    "timestamp",
    every="5m",        # Step size for sliding
    period="30m",      # Window duration
).agg([
    pl.col("glucose").mean().alias("mean_glucose"),
    pl.col("glucose").std().alias("std_glucose"),
])
```

### 5. STL for Seasonal Baseline (Optional, Advanced)

```python
from statsmodels.tsa.seasonal import STL

# For daily glucose patterns with hourly data
hourly = df.group_by_dynamic("timestamp", every="1h").agg(pl.col("glucose").mean())

# Decompose: trend + seasonal (daily) + residual
stl = STL(hourly["glucose"], period=24, robust=True)  # 24 = daily cycle
res = stl.fit()

# Anomalies in residuals or have low weights
residuals = res.resid
weights = res.weights  # Low weights = outliers
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

## Alternatives Considered (v1.0)

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

## What NOT to Use (v1.0)

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

# Add dependencies (v1.0)
uv add fastapi "uvicorn[standard]" jinja2
uv add polars pandas numpy scipy openpyxl
uv add glucostats
uv add typer

# Add v2.0 dependencies
uv add scikit-learn
uv add statsmodels  # Optional for STL

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
| **v2.0 Anomaly Detection** | HIGH | IsolationForest is production-proven; scikit-learn stable; feature engineering straightforward |
| **v2.0 Sleep Analysis** | HIGH | Time-filtering with Polars; GlucoStats for metrics; no new concepts |
| **v2.0 Behavioral Patterns** | MEDIUM | scipy.stats correlation/variation APIs stable; may need tuning for CGM-specific thresholds |

---

## Sources

### Data Processing
- [Polars vs Pandas 2026](https://www.analyticsinsight.net/programming/polars-vs-pandas-in-2026-should-you-make-the-switch) - Performance benchmarks, when to use each
- [Polars 1.40.0 Release](https://github.com/pola-rs/polars/releases/tag/py-1.40.0) - Current version
- [Polars Rolling Operations](https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.rolling.html) - Time-based rolling API
- [Pandas 3.0.2 Release](https://github.com/pandas-dev/pandas/releases/tag/v3.0.2) - Current stable
- [NumPy 2.4.4 Release](https://github.com/numpy/numpy/releases) - Current stable
- [SciPy 1.17.1 Release](https://github.com/scipy/scipy/releases) - Current stable

### CGM Analysis
- [GlucoStats Documentation](https://glucostats.readthedocs.io/en/latest/) - Official docs
- [GlucoStats Paper](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-025-06250-w) - BMC Bioinformatics publication
- [GlucoStats PyPI](https://pypi.org/project/glucostats/) - Version 1.0.0

### v2.0 Anomaly Detection
- [Context7] /websites/scikit-learn_stable - IsolationForest API, contamination parameter, RobustScaler (HIGH confidence)
- [PyData Bench: Time Series Anomaly Detection](https://pythondatabench.com/article/anomaly-detection-time-series-python-isolation-forest-lof-stl) - IsolationForest vs LOF comparison, production best practices (HIGH confidence)
- [dtaianomaly Documentation](https://dtaianomaly.readthedocs.io/en/0.4.1/api/anomaly_detection_algorithms/isolation_forest.html) - Time-series specific IsolationForest (MEDIUM confidence)
- [isotree Documentation](https://isotree.readthedocs.io/en/latest/) - Extended Isolation Forest variants (MEDIUM confidence)

### v2.0 Sleep & Behavioral Analysis
- [medRxiv: Sleep-CGM Study](https://www.medrxiv.org/content/10.64898/2026.03.04.26347496v1.full.pdf) - Sleep consistency and glycemic control in 227,860 nights (HIGH confidence)
- [JAMA Network: Sleep Duration and CGM](https://jamanetwork-com.libproxy.ajou.ac.kr/journals/jamanetworkopen/fullarticle/2831009) - Sleep timing and glycemic variability (HIGH confidence)
- [Context7] /websites/scipy_doc_scipy - pearsonr, spearmanr, variation (coefficient of variation) (HIGH confidence)
- [Retail Calendar Pattern Finder](https://github.com/AmirhosseinHonardoust/Retail-Calendar-Pattern-Finder) - Day-of-week analysis, hierarchical baselines (MEDIUM confidence)

### STL Decomposition
- [Context7] /websites/statsmodels_stable - STL, MSTL decomposition, robust fitting (HIGH confidence)
- [statsmodels STL API](https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.STL.html) - Official documentation (HIGH confidence)
- [statsmodels STL Notebook](https://www.statsmodels.org/devel/examples/notebooks/generated/stl_decomposition.html) - Usage examples (HIGH confidence)

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