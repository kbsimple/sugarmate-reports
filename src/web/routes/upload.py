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
            # Analyze file using core library
            results = analyze_file(
                tmp_path,
                start_date=start_date,
                end_date=end_date,
                exclude_warmup=exclude_warmup,
            )

            # Create session and store results
            session_id = create_session()
            session_store.store(session_id, results)

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