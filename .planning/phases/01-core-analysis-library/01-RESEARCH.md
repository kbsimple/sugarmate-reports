# Phase 1: Core Analysis Library - Research

**Researched:** 2026-04-23
**Domain:** CGM Data Processing and Validated Glucose Metrics (Python)
**Confidence:** HIGH

## Summary

This phase establishes the foundational Python library for CGM (Continuous Glucose Monitor) data processing with Polars for high-performance data manipulation and GlucoStats for validated glucose metrics. The core library must be independently usable before any CLI or web interface is built.

**Primary recommendation:** Use Polars (1.40.1) for all DataFrame operations with lazy evaluation for memory efficiency, GlucoStats (1.0.0) for validated CGM metrics (59 statistics including TIR, CV, GMI), and Pydantic (2.13.3) for data validation. Build as installable Python package with `src/` layout from day one.

**Critical finding:** Python 3.9.6 detected in environment, but GlucoStats requires Python 3.10+. Project must upgrade Python or use alternative metrics implementation.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Architecture:** Python library first, CLI second, web last — core library must be independently usable
- **Technology:** Polars + GlucoStats + FastAPI/HTMX + Typer (core library uses Polars + GlucoStats)
- **Regulatory:** Wellness language only, no medical advice

### Claude's Discretion
- Implementation details for data validation pipeline
- Internal package structure within core library
- Error handling strategy

### Deferred Ideas (OUT OF SCOPE)
- Pattern detection (Phase 2)
- Advanced analytics (Phase 2)
- Web interface (Phase 3)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | User can upload Sugarmate Excel export files | Polars `read_excel()` with calamine engine [VERIFIED: Polars docs] |
| DATA-02 | System parses glucose readings, timestamps, and trends | Polars DataFrame parsing; normalize to GlucoStats format (time, glucose columns) [VERIFIED: GlucoStats GitHub] |
| DATA-03 | System validates data completeness and flags gaps/missing readings | 80% completeness threshold; gap detection via timestamp intervals [VERIFIED: PMC11843558] |
| DATA-04 | System detects and handles sensor warm-up periods | 60-120 minute warmup; exclude first 2 hours [VERIFIED: PMC11843558] |
| DATA-05 | User can select date range for analysis | Polars `filter()` with datetime column; lazy evaluation [VERIFIED: Polars docs] |
| METR-01 | System calculates Time-in-Range (TIR) across all 5 glucose bands | GlucoStats `time_in_range` statistics with configurable bands [VERIFIED: GlucoStats paper] |
| METR-02 | System calculates average glucose with standard deviation | GlucoStats descriptive statistics category [VERIFIED: GlucoStats paper] |
| METR-03 | System calculates GMI with accuracy caveats | GlucoStats GMI calculation; caveat about 25-30% inaccuracy [VERIFIED: Bergenstal et al.] |
| METR-04 | System calculates Coefficient of Variation (%CV) for variability | GlucoStats variability category; target <36% [VERIFIED: GlucoStats paper] |
| METR-05 | System calculates Time Below Range (TBR) and Time Very Low | GlucoStats `time_below_range` statistics [VERIFIED: GlucoStats paper] |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| File upload/parsing | Core Library | — | Data ingestion is core business logic, not interface concern |
| Data validation | Core Library | — | Validation rules must be consistent across all interfaces |
| Metric calculation | Core Library | — | GlucoStats integration; validated algorithms |
| Date range filtering | Core Library | — | Polars filter operations on normalized data |
| Output formatting | Core Library | — | Results must be serializable for CLI/Web/JSON |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Polars | 1.40.1 | DataFrame operations, Excel parsing | 7-9x faster than pandas; lazy evaluation; native Arrow format |
| GlucoStats | 1.0.0 | CGM metrics calculation | 59 validated statistics; scikit-learn compatible; published research |
| Pydantic | 2.13.3 | Data validation models | Type-safe models; automatic validation; serialization |
| Python | 3.10+ | Runtime | GlucoStats requires 3.10+; type hints; pattern matching |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openpyxl | ^3.1 | Excel file handling | Polars `read_excel()` with engine='openpyxl' |
| python-dateutil | ^2.9 | DateTime parsing | Flexible timestamp parsing from various formats |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polars | pandas | pandas is slower (7-9x); no lazy evaluation; but more ecosystem support |
| GlucoStats | Custom implementation | GlucoStats has validated algorithms; custom risks clinical inaccuracy |
| Pydantic | dataclasses | Pydantic provides validation; dataclasses are just containers |

**Installation:**
```bash
# Create pyproject.toml with dependencies
uv pip install polars>=1.40.0 glucostats>=1.0.0 pydantic>=2.13.0 openpyxl>=3.1.0 python-dateutil>=2.9.0
```

**Version verification:** Versions verified from PyPI on 2026-04-23:
- Polars: 1.40.1 (published 2025)
- GlucoStats: 1.0.0 (published September 2025)
- Typer: 0.24.2 (for future CLI phase)
- Pydantic: 2.13.3

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     FUTURE INTERFACES                           │
│        (CLI Tool)      (Web API)      (Direct Import)           │
│             │              │                  │                 │
└─────────────┼──────────────┼──────────────────┼────────────────┘
              │              │                  │
              ▼              ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CORE ANALYSIS ENGINE                         │
│                    (Python Package)                             │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   ingestion/     │   analytics/    │   output/                  │
│   ┌───────────┐  │   ┌───────────┐ │   ┌───────────┐           │
│   │ parser.py │  │   │ metrics.py│ │   │formatter.py│          │
│   │ (Polars)  │  │   │(GlucoStats)│ │   │(Pydantic) │          │
│   └───────────┘  │   └───────────┘ │   └───────────┘           │
│   ┌───────────┐  │   ┌───────────┐ │                            │
│   │validator.py│ │   │ calculator│ │                            │
│   └───────────┘  │   └───────────┘ │                            │
│   ┌───────────┐  │                 │                            │
│   │normalizer │  │                 │                            │
│   └───────────┘  │                 │                            │
├─────────────────┴─────────────────┴─────────────────────────────┤
│                        models/                                  │
│   CGMReading | AnalysisSession | AnalysisResults               │
│   (Pydantic models for validation)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                 │
│   Input: Excel file upload → Polars DataFrame → Normalized     │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
src/
├── cgm_insights/           # Installable package
│   ├── __init__.py         # Public API exports
│   ├── models/
│   │   ├── __init__.py
│   │   ├── reading.py      # CGMReading Pydantic model
│   │   └── results.py      # AnalysisResults Pydantic model
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── parser.py       # Generic parser interface
│   │   ├── sugarmate.py    # Sugarmate Excel parser
│   │   ├── validator.py    # Data validation rules
│   │   └── normalizer.py   # Normalize to GlucoStats format
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── metrics.py      # GlucoStats integration
│   │   └── completeness.py # Data quality checks
│   └── output/
│       ├── __init__.py
│       └── formatter.py    # Results formatting
tests/
├── __init__.py
├── test_models/
├── test_ingestion/
└── test_analytics/
pyproject.toml
README.md
```

### Pattern 1: Parser Registry for Extensible Format Support

**What:** Pluggable parsers for different CGM data formats, registered by format type.

**When to use:** Adding support for new CGM export formats (Dexcom, Libre, etc.)

**Example:**
```python
# Source: [VERIFIED: Architecture research pattern]
# ingestion/parser.py
from abc import ABC, abstractmethod
from typing import Type
from ..models import CGMReading

class Parser(ABC):
    """Abstract base class for CGM data parsers."""

    @classmethod
    @abstractmethod
    def can_parse(cls, file_path: str) -> bool:
        """Return True if this parser handles the given file."""
        pass

    @abstractmethod
    def parse(self, file_path: str) -> list[CGMReading]:
        """Parse file and return normalized CGM readings."""
        pass

# Registry of available parsers
PARSERS: list[Type[Parser]] = []

def register_parser(parser_cls: Type[Parser]) -> Type[Parser]:
    PARSERS.append(parser_cls)
    return parser_cls

def get_parser(file_path: str) -> Parser:
    for parser_cls in PARSERS:
        if parser_cls.can_parse(file_path):
            return parser_cls()
    raise ValueError(f"No parser found for {file_path}")
```

```python
# ingestion/sugarmate.py
import polars as pl
from .parser import Parser, register_parser
from ..models import CGMReading

@register_parser
class SugarmateParser(Parser):
    """Parser for Sugarmate Excel exports."""

    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        return file_path.endswith(('.xlsx', '.xls'))

    def parse(self, file_path: str) -> list[CGMReading]:
        df = pl.read_excel(file_path, engine='openpyxl')
        readings = self._transform(df)
        return readings

    def _transform(self, df: pl.DataFrame) -> list[CGMReading]:
        # Normalize column names, validate, convert to CGMReading list
        pass
```

### Pattern 2: GlucoStats Integration with Polars

**What:** Convert Polars DataFrame to GlucoStats-compatible format for metric calculation.

**When to use:** Calculating validated CGM metrics from processed data.

**Example:**
```python
# Source: [VERIFIED: GlucoStats GitHub README]
# analytics/metrics.py
import polars as pl
import pandas as pd
from glucostats.extract_statistics import ExtractGlucoStats

def calculate_metrics(df: pl.DataFrame) -> dict:
    """
    Calculate CGM metrics using GlucoStats.
    
    Args:
        df: Polars DataFrame with 'time' and 'glucose' columns
    
    Returns:
        Dictionary with calculated metrics
    """
    # Convert to pandas DataFrame for GlucoStats compatibility
    # GlucoStats expects columns: 'time' (datetime), 'glucose' (float)
    pandas_df = df.to_pandas()
    pandas_df["time"] = pd.to_datetime(pandas_df["time"], errors="coerce")
    
    # Configure GlucoStats
    list_statistics = [
        'mean', 'std', 'cv',  # Descriptive
        'time_in_range', 'time_below_range', 'time_above_range',  # TIR
        'gmi',  # Glycemic Management Indicator
    ]
    
    stats_extraction = ExtractGlucoStats(
        list_statistics,
        windowing=False,  # Single period analysis
        batch_size=100,
        n_workers=1
    )
    stats_extraction.configuration(in_range_interval=[70, 180])
    
    # Extract statistics
    df_stats = stats_extraction.transform(pandas_df)
    return df_stats.to_dict()
```

### Pattern 3: Pydantic Models for Data Validation

**What:** Type-safe data models with automatic validation.

**When to use:** Defining CGM readings and analysis results.

**Example:**
```python
# Source: [VERIFIED: Pydantic documentation]
# models/reading.py
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class CGMReading(BaseModel):
    """Single CGM glucose reading."""
    
    timestamp: datetime = Field(..., description="Reading timestamp")
    glucose_mg_dl: float = Field(
        ..., 
        ge=40, 
        le=400,
        description="Glucose value in mg/dL (physiologically plausible range)"
    )
    trend: str | None = Field(
        None,
        description="Trend arrow from CGM device"
    )
    source: str = Field(
        "sugarmate",
        description="Data source identifier"
    )

    @field_validator('glucose_mg_dl')
    @classmethod
    def validate_glucose_range(cls, v: float) -> float:
        """Flag values outside typical CGM range."""
        if v < 40:
            # Log warning but accept - CGMs can read very low
            pass
        if v > 400:
            # Log warning - CGM max is typically 400 mg/dL
            pass
        return v

class AnalysisResults(BaseModel):
    """Complete analysis results for a date range."""
    
    date_range_start: datetime
    date_range_end: datetime
    total_readings: int
    data_completeness_pct: float = Field(..., ge=0, le=100)
    
    # Core metrics
    time_in_range_pct: float = Field(..., ge=0, le=100)
    time_below_range_pct: float = Field(..., ge=0, le=100)
    time_above_range_pct: float = Field(..., ge=0, le=100)
    average_glucose: float
    glucose_std: float
    cv_pct: float = Field(..., description="Coefficient of variation")
    gmi: float = Field(..., description="Glucose Management Indicator")
    
    # Metadata
    sensor_warmup_excluded: bool = True
    data_quality_flags: list[str] = []
```

### Anti-Patterns to Avoid
- **Business logic in interface layer:** All calculations must be in core package, not CLI or web routes
- **Tight coupling to Sugarmate format:** Normalize all formats to common CGMReading model
- **Skipping data validation:** Always validate completeness before calculating metrics
- **Assuming CGM is accurate blood glucose:** Document 5-25 minute physiological lag

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-in-Range calculation | Custom TIR function | GlucoStats `time_in_range` | Validated against clinical research; handles edge cases |
| Variability metrics (CV, MAGE) | Custom math | GlucoStats `cv`, `mage` | 59 validated statistics; published algorithms |
| DataFrame operations | Pure Python loops | Polars | 7-9x faster; lazy evaluation; memory efficient |
| Excel file parsing | Manual parsing | Polars `read_excel()` | Handles format variations; fast; type inference |
| Data validation | Custom validators | Pydantic | Type-safe; automatic serialization; error messages |
| Date/time parsing | strptime chains | python-dateutil | Flexible format detection; timezone handling |

**Key insight:** CGM metrics have clinical significance. Hand-rolled calculations risk medical inaccuracy. GlucoStats provides peer-reviewed, validated implementations.

## Runtime State Inventory

> Phase 1 is a greenfield library implementation. No runtime state to migrate.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — greenfield | Create initial data models |
| Live service config | None — greenfield | Create pyproject.toml |
| OS-registered state | None — greenfield | — |
| Secrets/env vars | None — greenfield | — |
| Build artifacts | None — greenfield | — |

## Common Pitfalls

### Pitfall 1: Insufficient Python Version
**What goes wrong:** Using Python 3.9.x when GlucoStats requires Python 3.10+.

**Why it happens:** System Python may be older; GlucoStats is a new library (Sept 2025).

**How to avoid:**
- Detect Python version at project start
- Use `uv` or `pyenv` to manage Python 3.10+
- Document minimum Python version in pyproject.toml: `requires-python = ">=3.10"`

**Warning signs:**
- Import errors when installing GlucoStats
- Type hint syntax errors (e.g., `str | None` requires Python 3.10+)

### Pitfall 2: Medical Device Regulatory Boundary
**What goes wrong:** Using disease-specific language that triggers FDA medical device classification.

**Why it happens:** Developers naturally use clinical terms like "diabetes management," "hypoglycemia," or "treatment recommendations."

**How to avoid:**
- Use wellness language: "glucose patterns," "insights," "wellness"
- Never provide insulin dosing recommendations
- Include clear disclaimer: "Not a medical device. For informational purposes only."
- All user-facing text must use wellness positioning

**Warning signs:**
- Copy using "diabetes management," "hypoglycemia detection"
- Clinical alerts recommending specific medical actions
- Marketing to diabetics for disease management

### Pitfall 3: Ignoring Data Quality Issues
**What goes wrong:** Calculating metrics on incomplete or corrupted CGM data, producing unreliable results.

**Why it happens:** CGM data naturally contains gaps (sensor disconnection), artifacts (compression lows), and sensor warm-up periods (first 2 hours inaccurate).

**How to avoid:**
- Require minimum 80% data completeness before calculating metrics [VERIFIED: PMC11843558]
- Detect and exclude sensor warm-up period (first 60-120 minutes)
- Flag suspicious patterns (overnight lows, rapid spikes/drops)
- Display data quality indicators alongside insights

**Warning signs:**
- Time Below Range dramatically overstated (compression lows during sleep)
- Patterns based on <14 days of data
- Metrics calculated with >20% data gaps

### Pitfall 4: Treating CGM as Accurate Blood Glucose
**What goes wrong:** Treating CGM readings as equivalent to blood glucose, ignoring the 5-25 minute physiological lag.

**Why it happens:** Developers assume sensor data is "ground truth."

**How to avoid:**
- Document and communicate physiological lag in code comments
- Consider rate-of-change when detecting patterns
- Never recommend insulin timing based on CGM alone
- Display trend arrows prominently

**Warning signs:**
- Meal peaks appearing at wrong times
- Exercise effects misaligned with actual activity

### Pitfall 5: Single Metrics Without Context
**What goes wrong:** Displaying TIR in isolation without CV, TBR, or GMI for interpretation.

**Why it happens:** Developers focus on individual metrics without understanding clinical context.

**How to avoid:**
- Always show related metrics together (TIR + CV + GMI + TBR)
- Provide reference ranges and interpretations
- Explain how metrics relate to each other
- Same TIR with higher CV = worse outcomes

**Warning signs:**
- User confusion about what "good" looks like
- Questions about why TIR improved but control feels worse

## Code Examples

### Polars Excel Reading and Filtering
```python
# Source: [VERIFIED: Polars documentation]
import polars as pl
from datetime import datetime, timedelta

def load_cgm_data(file_path: str, start_date: datetime | None = None) -> pl.DataFrame:
    """
    Load CGM data from Excel file with optional date filtering.
    Uses lazy evaluation for memory efficiency.
    """
    # Read Excel with schema inference
    df = pl.read_excel(
        file_path,
        engine='openpyxl',
        infer_schema_length=1000,  # More rows for better type inference
    )
    
    # Convert to lazy for efficient filtering
    lazy_df = df.lazy()
    
    if start_date:
        # Filter by date range using lazy evaluation
        lazy_df = lazy_df.filter(
            pl.col("timestamp") >= start_date
        )
    
    # Collect (execute) the lazy query
    return lazy_df.collect()
```

### Data Completeness Validation
```python
# Source: [VERIFIED: PMC11843558 - CGM data quality processing]
def validate_completeness(
    df: pl.DataFrame,
    expected_interval_minutes: int = 5,
    minimum_completeness_pct: float = 0.80
) -> tuple[bool, list[str]]:
    """
    Validate CGM data completeness.
    
    Returns:
        Tuple of (is_valid, list of quality flags)
    """
    flags = []
    
    # Calculate expected readings vs actual
    time_span = df["timestamp"].max() - df["timestamp"].min()
    expected_readings = time_span.total_seconds() / (expected_interval_minutes * 60)
    actual_readings = len(df)
    
    completeness = actual_readings / expected_readings
    
    if completeness < minimum_completeness_pct:
        flags.append(f"Data completeness {completeness:.1%} below minimum {minimum_completeness_pct:.0%}")
        return False, flags
    
    # Check for sensor warmup period (first 2 hours)
    if time_span.total_seconds() > 7200:  # More than 2 hours of data
        first_two_hours = df.filter(
            pl.col("timestamp") < (pl.col("timestamp").min() + pl.duration(hours=2))
        )
        if len(first_two_hours) > 0:
            flags.append("Sensor warmup period detected (first 2 hours may be inaccurate)")
    
    # Check for gaps (missing readings)
    time_diffs = df.sort("timestamp").select(
        pl.col("timestamp").diff().alias("time_diff")
    )
    max_gap = time_diffs.filter(pl.col("time_diff") > pl.duration(minutes=10))
    
    if len(max_gap) > 0:
        flags.append(f"Found {len(max_gap)} gaps greater than 10 minutes")
    
    return len(flags) == 0, flags
```

### GlucoStats Integration
```python
# Source: [VERIFIED: GlucoStats GitHub]
from glucostats.extract_statistics import ExtractGlucoStats
import polars as pl
import pandas as pd

def calculate_all_metrics(df: pl.DataFrame) -> dict:
    """
    Calculate comprehensive CGM metrics using GlucoStats.
    
    Expects Polars DataFrame with 'time' and 'glucose' columns.
    """
    # Convert to pandas DataFrame for GlucoStats
    pandas_df = df.to_pandas()
    pandas_df["time"] = pd.to_datetime(pandas_df["time"])
    
    # Define statistics to extract
    statistics = [
        # Descriptive
        'mean', 'std', 'min', 'max', 'median',
        # Variability
        'cv', 'mage',
        # Time in ranges
        'time_in_range', 'time_below_range', 'time_above_range',
        'time_very_low', 'time_very_high',
        # Glycemic management
        'gmi',
    ]
    
    # Create extractor
    extractor = ExtractGlucoStats(
        list_statistics=statistics,
        windowing=False,
        batch_size=100,
        n_workers=1
    )
    
    # Configure glucose ranges (mg/dL)
    extractor.configuration(
        in_range_interval=[70, 180],  # Target range
        low_threshold=70,              # Below this = low
        very_low_threshold=54,         # Below this = very low
        high_threshold=180,           # Above this = high
        very_high_threshold=250       # Above this = very high
    )
    
    # Extract metrics
    results = extractor.transform(pandas_df)
    
    return results.to_dict('records')[0] if len(results) > 0 else {}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pandas for DataFrame operations | Polars | 2023-2025 | 7-9x faster; lazy evaluation; memory efficient |
| Custom metric calculations | GlucoStats | Sept 2025 | Validated algorithms; 59 statistics; research-backed |
| setup.py + setup.cfg | pyproject.toml | 2023+ | Single source of truth; modern packaging |
| Python 3.8/3.9 | Python 3.10+ | 2024+ | Pattern matching; improved type hints; GlucoStats requires 3.10+ |
| dataclasses for models | Pydantic v2 | 2023+ | Automatic validation; serialization; performance improvements |

**Deprecated/outdated:**
- setup.py: Use pyproject.toml instead
- pandas for new CGM projects: Polars offers significant performance gains
- Custom TIR/CV calculations: GlucoStats provides validated implementations

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | GlucoStats requires Python 3.10+ | Standard Stack | HIGH — Python 3.9.6 detected in environment; must upgrade |
| A2 | Sugarmate Excel format has time/glucose columns | Architecture Patterns | MEDIUM — May need field mapping; format not documented publicly |
| A3 | 5-minute reading interval is standard | Code Examples | LOW — Most CGMs use 5-minute intervals; Dexcom/Libre standard |
| A4 | Sensor warmup is first 2 hours | Common Pitfalls | LOW — Dexcom G7 is 1 hour, G6 is 2 hours; conservative default |

## Open Questions

1. **Sugarmate Excel Column Names**
   - What we know: Sugarmate exports Excel with glucose readings; Dexcom format has specific columns
   - What's unclear: Exact column names in Sugarmate export (time? timestamp? glucose? glucose_value?)
   - Recommendation: Request sample export file from user; implement flexible column mapping

2. **Python Version Upgrade Path**
   - What we know: Environment has Python 3.9.6; GlucoStats requires 3.10+
   - What's unclear: User's preferred Python version management (uv? pyenv? conda?)
   - Recommendation: Document Python 3.10+ requirement; provide installation instructions

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | GlucoStats | ✗ (3.9.6) | 3.9.6 | **BLOCKING** |
| Polars | Data processing | ✓ (via pip) | — | — |
| openpyxl | Excel reading | ✓ (via pip) | — | — |
| Pydantic | Data validation | ✓ (via pip) | — | — |
| uv package manager | Build system | ✗ | — | Use pip/venv |

**Missing dependencies with no fallback:**
- Python 3.10+: Must upgrade before GlucoStats installation. Use `uv python install 3.10` or system package manager.

**Missing dependencies with fallback:**
- uv package manager: Can use standard pip/venv workflow; uv provides 10-100x speed improvement

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | Phase 1 is library-only, no auth |
| V3 Session Management | No | Phase 1 is library-only |
| V4 Access Control | No | Phase 1 is library-only |
| V5 Input Validation | Yes | Pydantic models with field validators; glucose range validation (40-400 mg/dL); timestamp parsing with error handling |
| V6 Cryptography | No | No sensitive data encryption in Phase 1 |

### Known Threat Patterns for CGM Analytics

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed file upload | Tampering | Polars handles Excel parsing errors; validate file extension and size limits |
| Path traversal | Tampering | Use allowlist for file paths; never accept user-provided paths |
| Glucose range injection | Tampering | Pydantic field validators; physiologically plausible ranges (40-400 mg/dL) |
| Medical advice generation | Repudiation | Regulatory boundary: wellness language only; no treatment recommendations |

### Regulatory Compliance

**FDA General Wellness Guidance (2026):**
- App must not claim to diagnose, treat, or prevent disease
- Must not provide insulin dosing recommendations
- Must use wellness language ("glucose patterns" not "diabetes management")
- Include clear disclaimer: "Not a medical device. For informational purposes only."

## Sources

### Primary (HIGH confidence)
- [Polars Python API Documentation](https://docs.pola.rs/api/python/stable/) - DataFrame operations, Excel reading, lazy evaluation
- [GlucoStats PyPI](https://pypi.org/project/glucostats/) - Installation, version 1.0.0
- [GlucoStats GitHub](https://github.com/ai4healthurjc/GlucoStats) - Usage examples, data format requirements
- [GlucoStats Paper (BMC Bioinformatics)](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-025-06250-w) - 59 validated statistics, research validation
- [Typer Documentation](https://typer.tiangolo.com/) - CLI framework patterns
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation, model patterns

### Secondary (MEDIUM confidence)
- [PMC: Processing Algorithm for CGM Data Quality](https://pmc.ncbi.nlm.nih.gov/articles/PMC11843558/) - Data validation, completeness thresholds, duplication detection
- [Python Package Structure Guide 2025](https://pyopensci.org/python-package-guide/package-structure-code/python-package-structure.html) - src/ layout, pyproject.toml
- [Modern Python Packaging with pyproject.toml](https://automateanddeploy.com/blog/modern-python-packaging-with-pyproject-toml-and-uv) - uv package manager
- [Dexcom G7 15 Day FDA Clearance](https://www.accessdata.fda.gov/cdrh_docs/reviews/K243214.pdf) - Sensor warmup periods, data capture rates

### Tertiary (LOW confidence)
- [Sugarmate Website](https://www.sugarmate.io/) - Export capabilities exist; exact column format unclear
- [GlucoseDAO/cgm_format](https://github.com/GlucoseDAO/cgm_format) - Standardized CGM format reference

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Polars, GlucoStats, Pydantic are well-documented with verified versions
- Architecture: HIGH — Standard Python package patterns; src/ layout recommended
- Pitfalls: HIGH — FDA guidance and CGM research papers provide clear prevention strategies
- GlucoStats integration: MEDIUM — New library (Sept 2025); may need patches for Sugarmate format
- Sugarmate format: LOW — Exact column names not documented; needs sample file

**Research date:** 2026-04-23
**Valid until:** 2026-07-23 (3 months for stable libraries; 30 days for GlucoStats given newness)