"""Export routes for CGM Insights web application.

Provides endpoints for exporting analysis results in various formats,
including AGP (Ambulatory Glucose Profile) report PDFs.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..services.session import session_store
from ..services.agp_generator import generate_agp_report

router = APIRouter()


@router.get("/export/{session_id}/agp")
async def export_agp_report(session_id: str):
    """Export AGP report as PDF download.

    Generates a standardized Ambulatory Glucose Profile report
    suitable for healthcare provider sharing.

    Args:
        session_id: Unique session identifier

    Returns:
        StreamingResponse with PDF file download

    Raises:
        HTTPException: 404 if session not found
        HTTPException: 500 if PDF generation fails
    """
    # Retrieve session data
    session_data = session_store.get(session_id)

    if session_data is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload your file again."
        )

    try:
        # Generate PDF
        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=session_data.results,
            patterns=session_data.patterns,
            generated_date=datetime.utcnow(),
        )

        # Create filename with date
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"agp-report-{date_str}.pdf"

        # Return as streaming response
        from io import BytesIO

        def iterfile():
            yield from BytesIO(pdf_bytes)

        return StreamingResponse(
            iterfile(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate AGP report: {str(e)}"
        )


@router.get("/export/{session_id}/preview")
async def preview_agp_report(session_id: str):
    """Preview AGP report as HTML.

    Returns HTML preview of the AGP report for checking
    content before downloading PDF.

    Args:
        session_id: Unique session identifier

    Returns:
        HTML content of the report preview

    Raises:
        HTTPException: 404 if session not found
    """
    from ..services.agp_generator import generate_agp_preview
    from fastapi.responses import HTMLResponse

    # Retrieve session data
    session_data = session_store.get(session_id)

    if session_data is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload your file again."
        )

    try:
        # Generate HTML preview
        html_content = generate_agp_preview(
            session_id=session_id,
            results=session_data.results,
            patterns=session_data.patterns,
            generated_date=datetime.utcnow(),
        )

        return HTMLResponse(content=html_content)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate preview: {str(e)}"
        )