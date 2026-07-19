"""File upload routes for CGM Insights web application.

Provides endpoints for uploading CGM data files and triggering analysis.
"""

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..services.session import create_session, session_store
from cgm_insights import analyze_file
from cgm_insights.analytics import detect_day_of_week_patterns, detect_time_of_day_patterns
from cgm_insights.analytics.anomaly_detection import analyze_anomalies
from cgm_insights.analytics.behavioral_patterns import analyze_behavioral_patterns
from cgm_insights.analytics.overnight_patterns import analyze_overnight_patterns
from cgm_insights.ingestion import exclude_warmup_period, get_parser

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

_CONTENT_TYPE_EXTS: dict[str, str] = {
    "text/csv": ".csv",
    "application/csv": ".csv",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


def validate_upload(file: UploadFile) -> None:
    """Validate uploaded file extension.

    Raises:
        HTTPException: If the extension is not in ALLOWED_EXTENSIONS.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )


def _ext_from_response(url: str, headers: httpx.Headers) -> str:
    """Infer file extension from URL path, Content-Disposition, or Content-Type."""
    path_ext = Path(urlparse(url).path).suffix.lower()
    if path_ext in ALLOWED_EXTENSIONS:
        return path_ext

    cd = headers.get("content-disposition", "")
    if cd:
        m = re.search(r'filename[^;=\n]*=\s*[\'"]?([^\'";\n]+)', cd, re.IGNORECASE)
        if m:
            cd_ext = Path(m.group(1).strip()).suffix.lower()
            if cd_ext in ALLOWED_EXTENSIONS:
                return cd_ext

    ct = headers.get("content-type", "").split(";")[0].strip().lower()
    if ct in _CONTENT_TYPE_EXTS:
        return _CONTENT_TYPE_EXTS[ct]

    # Sugarmate and most CGM exports default to Excel when no type is declared.
    return ".xlsx"


def _downsample_to_5min(readings) -> list[dict]:
    """Bucket readings into 5-minute slots and return one averaged point per slot.

    High-frequency CGMs (e.g. 1-minute or 2-minute intervals) produce far more
    readings than 5-minute devices. Without downsampling, the 30-day window for a
    1-minute CGM has 43 000+ readings, which would be silently truncated and cause
    the chart to show only the first 10–15 days. Bucketing to 5-minute resolution
    keeps at most 288 points per day (8 640 for 30 days) regardless of sensor rate.
    """
    from collections import defaultdict

    buckets: dict = defaultdict(list)
    for r in readings:
        ts = r.timestamp
        # Round down to the nearest 5-minute boundary
        bucket_ts = ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
        buckets[bucket_ts].append(r.glucose_mg_dl)

    return [
        {
            "timestamp": ts.isoformat(),
            "glucose": round(sum(vals) / len(vals), 1),
        }
        for ts, vals in sorted(buckets.items())
    ]


async def _analyze_and_store(
    contents: bytes,
    filename_hint: str,
    start_date: Optional[str],
    end_date: Optional[str],
    exclude_warmup: bool,
) -> str:
    """Run analysis pipeline on raw file bytes and return a new session_id.

    Raises:
        HTTPException: On validation or analysis failure.
    """
    suffix = Path(filename_hint).suffix.lower() or ".csv"

    with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        parser = get_parser(tmp_path)
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        readings = parser.parse(tmp_path, start_date=start, end_date=end)

        if exclude_warmup:
            readings = exclude_warmup_period(readings)

        results = analyze_file(
            tmp_path,
            start_date=start_date,
            end_date=end_date,
            exclude_warmup=exclude_warmup,
        )

        time_patterns = detect_time_of_day_patterns(readings)
        day_patterns = detect_day_of_week_patterns(readings)
        all_patterns = time_patterns + day_patterns

        behavioral_result = analyze_behavioral_patterns(readings)
        overnight_result = analyze_overnight_patterns(readings)
        anomaly_result = analyze_anomalies(readings)

        raw_readings = _downsample_to_5min(readings)

        session_id = create_session()
        session_store.store(
            session_id,
            results,
            patterns=all_patterns,
            raw_readings=raw_readings,
            behavioral_patterns=behavioral_result.model_dump(),
            overnight_patterns=overnight_result.model_dump(),
            anomaly_detection=anomaly_result.model_dump(),
        )
        return session_id

    except ValueError as e:
        error_msg = str(e)
        if "insufficient" in error_msg.lower():
            raise HTTPException(
                status_code=422,
                detail="Insufficient data for analysis. Please upload a file with more glucose readings.",
            )
        raise HTTPException(status_code=400, detail=f"Could not process file: {error_msg}")

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, url: Optional[str] = Query(None)):
    return templates.TemplateResponse(
        request, "upload.html", {"prefill_url": url or ""}
    )


@router.post("/upload", response_class=JSONResponse)
async def upload_file(
    file: UploadFile = File(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    exclude_warmup: bool = Form(True),
):
    """Handle multipart file upload and analysis."""
    validate_upload(file)

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB")

    try:
        session_id = await _analyze_and_store(
            contents,
            file.filename or "data.csv",
            start_date,
            end_date,
            exclude_warmup,
        )
        return JSONResponse({"session_id": session_id, "redirect": f"/results/{session_id}"})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your file. Please try again.",
        )


@router.post("/upload/url", response_class=JSONResponse)
async def upload_from_url(
    url: str = Form(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    exclude_warmup: bool = Form(True),
):
    """Fetch a CGM data file from a URL and analyse it."""
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Only HTTPS URLs are supported.")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL.")

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
        ) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not fetch URL (HTTP {response.status_code}).",
                    )
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes(8192):
                    total += len(chunk)
                    if total > MAX_FILE_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail="Downloaded file too large. Maximum size is 10MB.",
                        )
                    chunks.append(chunk)

                contents = b"".join(chunks)
                ext = _ext_from_response(url, response.headers)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    try:
        session_id = await _analyze_and_store(
            contents, f"data{ext}", start_date, end_date, exclude_warmup
        )
        # Store the source URL so the results page can offer a share link
        session = session_store.get(session_id)
        if session is not None:
            session.source_url = url
        return JSONResponse({"session_id": session_id, "redirect": f"/results/{session_id}"})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing the file. Please try again.",
        )
