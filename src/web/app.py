"""FastAPI application entry point for CGM Insights web interface.

This module provides the main FastAPI application with:
- Jinja2 template rendering
- Static file serving
- CORS middleware for development
- Router inclusion for upload and results routes
"""

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
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


app = FastAPI(
    title="CGM Insights",
    description="Web interface for CGM data analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Template configuration
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Import and include routers after app is created to avoid circular imports
from .routes import upload, results  # noqa: E402

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(results.router, prefix="/api", tags=["results"])


@app.get("/")
async def root():
    """Redirect root to upload page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/upload")