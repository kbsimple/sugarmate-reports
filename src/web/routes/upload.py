"""File upload routes for CGM Insights web application.

Provides endpoints for uploading CGM data files and triggering analysis.
"""

import tempfile
import os
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from ..services.session import session_store, create_session
from cgm_insights import analyze_file
from cgm_insights.ingestion import get_parser, exclude_warmup_period
from cgm_insights.analytics import detect_time_of_day_patterns, detect_day_of_week_patterns
from cgm_insights.analytics.behavioral_patterns import analyze_behavioral_patterns
from cgm_insights.analytics.overnight_patterns import analyze_overnight_patterns
from cgm_insights.analytics.anomaly_detection import analyze_anomalies

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")

# Allowed file extensions
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_upload(file: UploadFile) -> None:
    """Validate uploaded file.

    Args:
        file: Uploaded file

    Raises:
        HTTPException: If file is invalid
    """
    # Check file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Render upload page with file upload form.

    Args:
        request: FastAPI request object

    Returns:
        HTML page with upload form
    """
    return templates.TemplateResponse(
        "upload.html",
        {"request": request}
    )


@router.post("/upload", response_class=JSONResponse)
async def upload_file(
    file: UploadFile = File(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    exclude_warmup: bool = Form(True),
):
    """Handle file upload and analysis.

    Args:
        file: Uploaded CGM data file
        start_date: Optional start date filter (ISO format)
        end_date: Optional end date filter (ISO format)
        exclude_warmup: Whether to exclude sensor warmup period

    Returns:
        JSON response with session_id for results retrieval

    Raises:
        HTTPException: On upload or analysis errors
    """
    # Validate file
    validate_upload(file)

    # Check file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10MB"
        )

    # Create temp file for analysis
    try:
        # Write to temp file
        suffix = Path(file.filename or "data.csv").suffix
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix,
            delete=False
        ) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            # Parse file to get readings for pattern detection
            parser = get_parser(tmp_path)
            from datetime import datetime
            start = datetime.fromisoformat(start_date) if start_date else None
            end = datetime.fromisoformat(end_date) if end_date else None
            readings = parser.parse(tmp_path, start_date=start, end_date=end)

            # Exclude warmup if requested
            if exclude_warmup:
                readings = exclude_warmup_period(readings)

            # Analyze file using core library
            results = analyze_file(
                tmp_path,
                start_date=start_date,
                end_date=end_date,
                exclude_warmup=exclude_warmup,
            )

            # Detect patterns
            time_patterns = detect_time_of_day_patterns(readings)
            day_patterns = detect_day_of_week_patterns(readings)
            all_patterns = time_patterns + day_patterns

            # Behavioral pattern analysis (Phase 4)
            behavioral_result = analyze_behavioral_patterns(readings)
            behavioral_patterns_dict = behavioral_result.model_dump()

            # Overnight pattern analysis (Phase 5)
            overnight_result = analyze_overnight_patterns(readings)
            overnight_patterns_dict = overnight_result.model_dump()

            # Anomaly detection (Phase 6)
            anomaly_result = analyze_anomalies(readings)
            anomaly_detection_dict = anomaly_result.model_dump()

            # Convert readings to chart format (limit for web display)
            raw_readings = [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "glucose": r.glucose_mg_dl
                }
                for r in readings[:2000]  # Limit to 2000 points for web
            ]

            # Create session and store results with patterns
            session_id = create_session()
            session_store.store(
                session_id,
                results,
                patterns=all_patterns,
                raw_readings=raw_readings,
                behavioral_patterns=behavioral_patterns_dict,
                overnight_patterns=overnight_patterns_dict,
                anomaly_detection=anomaly_detection_dict,
            )

            return JSONResponse({
                "session_id": session_id,
                "redirect": f"/results/{session_id}"
            })

        except ValueError as e:
            # Handle insufficient data or parsing errors
            error_msg = str(e)
            if "insufficient" in error_msg.lower():
                raise HTTPException(
                    status_code=422,
                    detail="Insufficient data for analysis. Please upload a file with more glucose readings."
                )
            raise HTTPException(
                status_code=400,
                detail=f"Could not process file: {error_msg}"
            )

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    except HTTPException:
        raise
    except Exception as e:
        # Generic error - don't expose internal details
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your file. Please try again."
        )