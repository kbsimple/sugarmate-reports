"""Results display routes for CGM Insights web application.

Provides endpoints for displaying analysis results.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..services.session import session_store

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/results/{session_id}", response_class=HTMLResponse)
async def get_results(request: Request, session_id: str):
    """Display analysis results for a session.

    Args:
        request: FastAPI request object
        session_id: Unique session identifier

    Returns:
        HTML page with analysis results

    Raises:
        HTTPException: 404 if session not found
    """
    results = session_store.get(session_id)

    if results is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload your file again."
        )

    # Format results for template display
    from cgm_insights import format_results
    formatted = format_results(results)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "session_id": session_id,
            "results": results,
            "formatted": formatted,
        }
    )


@router.get("/results/{session_id}/data")
async def get_results_data(session_id: str):
    """Get analysis results as JSON for a session.

    Args:
        session_id: Unique session identifier

    Returns:
        JSON representation of analysis results

    Raises:
        HTTPException: 404 if session not found
    """
    results = session_store.get(session_id)

    if results is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return results.model_dump()