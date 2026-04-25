# Architecture Patterns

**Domain:** CGM Analytics Application
**Researched:** 2026-04-23

## Recommended Architecture

The architecture follows a **layered separation pattern** with the Python analysis engine at the core, wrapped by thin interface adapters (CLI and Web API). This enables the analysis engine to be used independently as a library, via command line, or through a web interface.

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACES                               │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Web Frontend  │   CLI Tool      │   Direct Import             │
│   (HTML/JS)     │   (Typer/Click) │   (Python library)          │
└────────┬────────┴────────┬────────┴─────────────────────────────┘
         │                 │
         ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     WEB API LAYER                               │
│                     (FastAPI)                                   │
│  - REST endpoints for upload, analysis, results                 │
│  - Request/response validation (Pydantic)                       │
│  - File handling and storage coordination                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CORE ANALYSIS ENGINE                          │
│                   (Python Package)                              │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Ingestion     │   Analytics     │   Output                    │
│   - Parsers     │   - Metrics     │   - Formatters              │
│   - Validators  │   - Patterns    │   - Visualizations          │
│   - Loaders     │   - Anomalies   │   - Reports                 │
│   - Models      │   - Insights    │   - Suggestions             │
└─────────────────┴─────────────────┴─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                  │
│   - File storage (uploaded exports)                             │
│   - Session data (analysis results cache)                       │
│   - Optional: SQLite for persistence                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Web Frontend** | User interface, file upload, results display | Web API (HTTP) |
| **CLI Tool** | Command-line interface for analysis | Core Engine (direct import) |
| **Web API** | REST endpoints, file handling, orchestration | Core Engine (direct import), Data Layer |
| **Core Engine - Ingestion** | Parse, validate, normalize CGM data files | Called by API/CLI, outputs to Analytics |
| **Core Engine - Analytics** | Calculate metrics, detect patterns, find anomalies | Called by API/CLI, uses Ingestion output |
| **Core Engine - Output** | Format results, generate visualizations, create suggestions | Called by API/CLI, uses Analytics output |
| **Data Layer** | Store uploaded files, cache results | Web API only |

### Key Principle: Thin Interfaces

Interface layers (CLI, Web API) should contain **no business logic**. They only:
1. Parse input and validate request format
2. Call core engine functions
3. Format and return results

This ensures the core engine remains framework-agnostic and testable in isolation.

---

## Data Flow

### Upload and Analysis Flow

```
1. User uploads file → Web Frontend
2. Frontend POSTs file → Web API (/upload endpoint)
3. Web API stores file, creates session → Data Layer
4. Web API calls core.ingestion.parse() → Core Engine
5. Core Engine returns validated CGM readings
6. Web API calls core.analytics.analyze() → Core Engine
7. Core Engine returns metrics, patterns, anomalies
8. Web API calls core.output.format() → Core Engine
9. Core Engine returns formatted results + suggestions
10. Web API caches results → Data Layer
11. Web API returns results → Frontend
12. Frontend displays results
```

### Subsequent Request Flow (Results Already Cached)

```
1. User requests results → Web Frontend
2. Frontend GETs /results/{session_id} → Web API
3. Web API retrieves cached results → Data Layer
4. Web API returns results → Frontend
```

---

## Core Engine Structure

The Python package structure enables independent use and clear separation of concerns:

```
cgm_insights/
├── __init__.py              # Public API exports
├── models/
│   ├── __init__.py
│   ├── reading.py           # CGM reading data model
│   ├── session.py           # Analysis session model
│   └── results.py           # Analysis results model
├── ingestion/
│   ├── __init__.py
│   ├── parser.py            # Generic parser interface
│   ├── sugarmate.py         # Sugarmate Excel parser
│   ├── validator.py         # Data validation rules
│   └── normalizer.py        # Standardize to common format
├── analytics/
│   ├── __init__.py
│   ├── metrics.py           # Time-in-range, variability, etc.
│   ├── patterns.py          # Time-of-day, day-of-week patterns
│   ├── anomalies.py         # Unexplained highs/lows detection
│   └── events.py            # Hypo/hyperglycemic episode detection
├── output/
│   ├── __init__.py
│   ├── formatter.py         # Structure results for display
│   ├── suggestions.py       # Generate actionable suggestions
│   └── visualization.py     # Plotly chart specifications
└── cli.py                   # CLI entry point (thin wrapper)
```

### Core Engine Public API

The `__init__.py` exposes a clean public interface:

```python
# cgm_insights/__init__.py
from .models import CGMReading, AnalysisSession, AnalysisResults
from .ingestion import parse_file, validate_readings
from .analytics import analyze, calculate_metrics, detect_patterns
from .output import format_results, generate_suggestions

__all__ = [
    "CGMReading",
    "AnalysisSession",
    "AnalysisResults",
    "parse_file",
    "validate_readings",
    "analyze",
    "calculate_metrics",
    "detect_patterns",
    "format_results",
    "generate_suggestions",
]
```

### Usage Examples

**As a Python library:**
```python
from cgm_insights import parse_file, analyze, format_results

readings = parse_file("sugarmate_export.xlsx")
results = analyze(readings)
formatted = format_results(results)
print(formatted.summary)
```

**Via CLI:**
```bash
cgm-insights analyze sugarmate_export.xlsx --output results.json
cgm-insights metrics sugarmate_export.xlsx --format table
```

**Via Web API:**
```bash
curl -X POST -F "file=@sugarmate_export.xlsx" http://localhost:8000/api/analyze
```

---

## Patterns to Follow

### Pattern 1: Parser Registry

**What:** Pluggable parsers for different CGM data formats, registered by format type.

**When:** Adding support for new CGM export formats (Dexcom, Libre, etc.)

**Example:**
```python
# ingestion/parser.py
from abc import ABC, abstractmethod
from typing import Type
from .models import CGMReading

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
import pandas as pd
from .parser import Parser, register_parser
from .models import CGMReading

@register_parser
class SugarmateParser(Parser):
    """Parser for Sugarmate Excel exports."""

    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        return file_path.endswith(('.xlsx', '.xls'))

    def parse(self, file_path: str) -> list[CGMReading]:
        df = pd.read_excel(file_path)
        readings = self._transform(df)
        return readings
```

### Pattern 2: Metrics Calculator Pipeline

**What:** Composable metric calculations that run in sequence on normalized data.

**When:** Calculating all CGM metrics from validated readings.

**Example:**
```python
# analytics/metrics.py
from dataclasses import dataclass
from typing import Callable
import numpy as np

@dataclass
class MetricResult:
    name: str
    value: float
    unit: str
    interpretation: str | None = None

MetricCalculator = Callable[[list[float]], MetricResult]

def time_in_range(readings: list[float], low: float = 70, high: float = 180) -> MetricResult:
    in_range = sum(1 for g in readings if low <= g <= high)
    percentage = (in_range / len(readings)) * 100

    interpretation = "on target" if percentage >= 70 else "below target"

    return MetricResult(
        name="Time in Range",
        value=round(percentage, 1),
        unit="%",
        interpretation=interpretation
    )

def coefficient_of_variation(readings: list[float]) -> MetricResult:
    cv = (np.std(readings) / np.mean(readings)) * 100

    interpretation = "low variability" if cv < 36 else "high variability"

    return MetricResult(
        name="Coefficient of Variation",
        value=round(cv, 1),
        unit="%",
        interpretation=interpretation
    )

# Pipeline of all metrics
METRIC_CALCULATORS: list[MetricCalculator] = [
    time_in_range,
    coefficient_of_variation,
    # ... more metrics
]

def calculate_all_metrics(readings: list[float]) -> list[MetricResult]:
    return [calc(readings) for calc in METRIC_CALCULATORS]
```

### Pattern 3: Suggestion Generator

**What:** Rule-based system that generates actionable suggestions from analysis results.

**When:** Converting metrics and patterns into user-facing recommendations.

**Example:**
```python
# output/suggestions.py
from dataclasses import dataclass
from typing import Protocol

@dataclass
class Suggestion:
    category: str  # "timing", "variability", "anomaly"
    priority: int  # 1 = highest
    title: str
    description: str
    action: str    # What user should do

class SuggestionRule(Protocol):
    def evaluate(self, results: AnalysisResults) -> Suggestion | None:
        ...

class LowTimeInRangeRule:
    def evaluate(self, results: AnalysisResults) -> Suggestion | None:
        if results.metrics.time_in_range < 50:
            return Suggestion(
                category="control",
                priority=1,
                title="Low Time in Range",
                description=f"Only {results.metrics.time_in_range}% of readings are in range.",
                action="Review your highest glucose periods and identify potential causes."
            )
        return None

def generate_suggestions(results: AnalysisResults) -> list[Suggestion]:
    rules: list[SuggestionRule] = [
        LowTimeInRangeRule(),
        HighVariabilityRule(),
        DawnPhenomenonRule(),
        PostMealSpikeRule(),
        # ... more rules
    ]

    suggestions = []
    for rule in rules:
        suggestion = rule.evaluate(results)
        if suggestion:
            suggestions.append(suggestion)

    return sorted(suggestions, key=lambda s: s.priority)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Business Logic in Interface Layer

**What goes wrong:** Putting metric calculations or analysis logic in the Web API routes or CLI commands.

**Why it happens:** Developers add logic incrementally without refactoring to core library.

**Consequences:**
- Logic cannot be reused between CLI and Web
- Testing requires spinning up full API server
- Core library provides no value

**Instead:** Keep interfaces thin. All logic goes in the core package. Interface layers only orchestrate calls.

```python
# WRONG: Logic in API route
@app.post("/analyze")
def analyze(file: UploadFile):
    df = pd.read_excel(file)
    # DON'T do calculations here
    tir = df[df['glucose'].between(70, 180)].count() / len(df) * 100
    return {"time_in_range": tir}

# CORRECT: API route delegates to core
@app.post("/analyze")
def analyze(file: UploadFile):
    readings = parse_file(file.path)           # Core library
    results = analyze(readings)                # Core library
    return format_results(results).to_dict()   # Core library
```

### Anti-Pattern 2: Tight Coupling to Specific Format

**What goes wrong:** Hardcoding Sugarmate-specific field names throughout the codebase.

**Why it happens:** Starting with one format and not abstracting early.

**Consequences:**
- Adding new formats requires changes across codebase
- Cannot test analytics with synthetic data easily
- Parser changes break downstream code

**Instead:** Use the normalizer to transform all formats to a common `CGMReading` model. Analytics code only works with the normalized model.

### Anti-Pattern 3: Large Result Objects

**What goes wrong:** Returning massive nested objects with all possible data.

**Why it happens:** Trying to provide "everything the frontend might need."

**Consequences:**
- Slow API responses
- Memory issues with large datasets
- Frontend receives data it doesn't use

**Instead:** Layer results from summary to detailed. Frontend requests what it needs.

```python
# Layered results structure
results = {
    "summary": {...},           # Always returned
    "metrics": {...},           # Always returned
    "patterns": {...},          # Returned on request
    "anomalies": {...},         # Returned on request
    "raw_readings": [...],      # Only returned if explicitly requested
}
```

---

## Scalability Considerations

| Concern | At 1 user | At 100 users | At 10K users |
|---------|-----------|--------------|--------------|
| File storage | Local filesystem | Local filesystem with cleanup | S3/object storage |
| Analysis caching | In-memory dict | SQLite per session | Redis or PostgreSQL |
| Concurrent uploads | Single-threaded FastAPI | Multi-worker FastAPI | Containerized workers |
| Large files | Process in memory | Stream processing | Background job queue |
| Session data | File-based | SQLite | Database with TTL |

**For MVP (Phase 1):** Local filesystem + in-memory caching is sufficient. Design interfaces to allow swapping implementations later.

---

## Build Order (Dependencies Between Components)

Based on the architecture, here is the recommended build order:

### Phase 1: Core Library Foundation
1. **Data Models** (`models/`)
   - CGMReading, AnalysisSession, AnalysisResults
   - Pydantic models for validation
   - No dependencies - build first

2. **Ingestion - Sugarmate Parser** (`ingestion/sugarmate.py`, `ingestion/parser.py`)
   - Parser interface
   - Sugarmate Excel parser
   - Validator and normalizer
   - Depends on: Data Models

3. **Analytics - Basic Metrics** (`analytics/metrics.py`)
   - Time-in-range, average, variability metrics
   - Depends on: Data Models

4. **Output - Basic Formatter** (`output/formatter.py`)
   - Structure results for display
   - Depends on: Data Models, Analytics

### Phase 2: CLI Interface (Validates Core)
5. **CLI Tool** (`cli.py`)
   - Typer/Click commands
   - File input, JSON output
   - Depends on: All of Phase 1
   - **Checkpoint:** Core library is now independently usable and tested

### Phase 3: Web API Layer
6. **Web API - Upload Endpoint** (`api/upload.py`)
   - File upload handling
   - Session creation
   - Depends on: Core Library

7. **Web API - Analysis Endpoint** (`api/analyze.py`)
   - Trigger analysis
   - Return results
   - Depends on: Core Library, Upload

### Phase 4: Enhanced Analytics
8. **Analytics - Pattern Detection** (`analytics/patterns.py`)
   - Time-of-day, day-of-week patterns
   - Depends on: Data Models

9. **Analytics - Anomaly Detection** (`analytics/anomalies.py`)
   - Unexplained highs/lows
   - Depends on: Data Models, Patterns

10. **Output - Suggestions** (`output/suggestions.py`)
    - Rule-based suggestion engine
    - Depends on: Analytics

### Phase 5: Web Frontend
11. **Web Frontend - Upload UI**
    - File dropzone
    - Progress indication
    - Depends on: Web API

12. **Web Frontend - Results Display**
    - Summary dashboard
    - Detailed metrics
    - Depends on: Web API

---

## Technology Choices (Architecture Implications)

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Core Library | Pure Python + Pandas + NumPy | No framework lock-in, works everywhere |
| CLI | Typer | Modern, type-hint friendly, thin wrapper |
| Web API | FastAPI | Async, Pydantic integration, automatic OpenAPI |
| Frontend | Simple HTML/JS or React | Depends on complexity needs |
| Storage (MVP) | Local filesystem | Simple, no infrastructure |
| Visualization | Plotly (Python) | JSON specs, works in both CLI and Web |

---

## Sources

- [Glucose360 Open-Source Platform](https://github.com/vurhd2/Glucose360) - Reference architecture for CGM analysis library + web app
- [GlucoStats Python Library](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-025-06250-w) - 59 glucose metrics with scikit-learn compatibility
- [iglu R Package](https://irinagain.github.io/iglu) - 40+ validated CGM metrics, architecture reference
- [cgmquantify](https://github.com/brinnaebent/cgmquantify) - Python CGM metrics library
- [agp_tool](https://github.com/daedalus/agp_tool) - AGP visualization implementation
- [FastAPI Best Practices](https://fastlaunchapi.dev/blog/fastapi-best-practices-production-2026) - Web API architecture patterns
- [Python Library Architecture (Stack Overflow)](https://stackoverflow.com/questions/56008212/how-to-efficiently-provide-a-web-cli-api-interface-in-python) - Multi-interface design patterns
- [Meal Event Detection Algorithms](https://pmc.ncbi.nlm.nih.gov/articles/PMC10709931/) - Pattern detection methods for glucose data