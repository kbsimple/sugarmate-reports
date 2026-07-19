"""FastAPI application entry point for CGM Insights web interface.

This module provides the main FastAPI application with:
- Jinja2 template rendering
- Static file serving
- CORS middleware for development
- Router inclusion for upload and results routes
"""

import os
import resource
import subprocess
import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager
from importlib.metadata import version as _pkg_version, PackageNotFoundError

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Template and static file paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: Initialize any resources
    yield
    # Shutdown: Clean up any resources


_BOOT_TIME = time.time()

app = FastAPI(
    title="CGM Insights",
    description="Web interface for CGM data analysis",
    version="0.1.0",
    lifespan=lifespan,
)

_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
_allowed_origins: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Template configuration
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Import and include routers after app is created to avoid circular imports
from .routes import upload, results, export  # noqa: E402

app.include_router(upload.router, tags=["upload"])
app.include_router(results.router, tags=["results"])
app.include_router(export.router, tags=["export"])


def _git(cmd: str) -> str | None:
    try:
        return subprocess.check_output(
            cmd.split(), cwd=BASE_DIR, stderr=subprocess.DEVNULL
        ).decode().strip() or None
    except Exception:
        return None


def _dep_version(name: str) -> str:
    try:
        return _pkg_version(name)
    except PackageNotFoundError:
        return "unknown"


def _memory_mb() -> str:
    try:
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS ru_maxrss is bytes; Linux is kilobytes
        mb = rss / 1024 / 1024 if sys.platform == "darwin" else rss / 1024
        return f"{mb:.1f} MB"
    except Exception:
        return "unavailable"


def _uptime(boot: float) -> str:
    total = int(time.time() - boot)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"


@app.get("/statusz")
async def statusz(request: Request):
    from .services.session import session_store

    commit = os.environ.get("COMMIT_REF") or _git("git rev-parse HEAD") or "unknown"
    raw_branch = _git("git rev-parse --abbrev-ref HEAD")
    if raw_branch == "HEAD":
        raw_branch = None
    branch = os.environ.get("BRANCH") or os.environ.get("HEAD") or raw_branch or "unknown"
    release_date = (
        os.environ.get("RELEASE_DATE")
        or _git("git log -1 --format=%ci")
        or "unknown"
    )

    sessions = list(session_store._sessions.values())
    total_readings = sum(len(s.raw_readings) for s in sessions)

    return templates.TemplateResponse(request, "statusz.html", {"info": {
        "service": "cgm-insights",
        "status": "ok",
        "version": _dep_version("cgm-insights"),
        "release_date": release_date,
        "commit": commit,
        "commit_short": commit[:8] if commit != "unknown" else "unknown",
        "branch": branch,
        "context": os.environ.get("CONTEXT", "local"),
        "python": sys.version.split()[0],
        "pid": os.getpid(),
        "uptime": _uptime(_BOOT_TIME),
        "memory": _memory_mb(),
        "session_count": len(sessions),
        "total_readings": total_readings,
        "features": {
            "Behavioral pattern analysis": True,
            "Overnight pattern analysis": True,
            "Anomaly detection": True,
            "AGP PDF export": True,
            "URL-based upload": True,
            "Daily TIR chart with gap-fill": True,
        },
        "deps": {
            "fastapi": _dep_version("fastapi"),
            "polars": _dep_version("polars"),
            "pydantic": _dep_version("pydantic"),
            "uvicorn": _dep_version("uvicorn"),
            "jinja2": _dep_version("jinja2"),
        },
    }})


@app.get("/")
async def root():
    """Redirect root to upload page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/upload")