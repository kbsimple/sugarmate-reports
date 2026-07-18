"""Results display routes for CGM Insights web application.

Provides endpoints for displaying analysis results.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..services.session import session_store
from cgm_insights import format_results, format_quality_flags
from cgm_insights.analytics.behavioral_patterns import BehavioralAnalysisResult
from cgm_insights.analytics.overnight_patterns import OvernightAnalysisResult
from cgm_insights.analytics.anomaly_detection import AnomalyDetectionResult
from cgm_insights.output.suggestions import (
    generate_suggestions,
    generate_behavioral_suggestions,
    generate_overnight_suggestions,
    generate_anomaly_suggestions,
)

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
    session_data = session_store.get(session_id)

    if session_data is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload your file again."
        )

    results = session_data.results
    patterns = session_data.patterns
    raw_readings = session_data.raw_readings

    # Extract behavioral patterns from session
    behavioral_patterns_data = session_data.behavioral_patterns  # dict or None

    # Extract overnight patterns from session (Phase 5)
    overnight_patterns_data = session_data.overnight_patterns  # dict or None

    # Format results for display
    formatted = format_results(results)

    # Format quality flags
    quality_warnings = format_quality_flags(results.data_quality_flags)

    # Generate suggestions from patterns
    suggestions = generate_suggestions(patterns, results)

    # Add behavioral suggestions if analysis succeeded
    if behavioral_patterns_data and not behavioral_patterns_data.get("insufficient_data", True):
        behavioral_result = BehavioralAnalysisResult.model_validate(behavioral_patterns_data)
        suggestions = suggestions + generate_behavioral_suggestions(behavioral_result)
        suggestions.sort(key=lambda s: s.priority)

    # Add overnight suggestions if analysis succeeded
    if overnight_patterns_data and not overnight_patterns_data.get("insufficient_data", True):
        overnight_result = OvernightAnalysisResult.model_validate(overnight_patterns_data)
        suggestions = suggestions + generate_overnight_suggestions(overnight_result)
        suggestions.sort(key=lambda s: s.priority)

    # Extract anomaly detection from session (Phase 6)
    anomaly_detection_data = session_data.anomaly_detection  # dict or None

    # Add anomaly suggestions if analysis succeeded
    if anomaly_detection_data and not anomaly_detection_data.get("insufficient_data", True):
        anomaly_result = AnomalyDetectionResult.model_validate(anomaly_detection_data)
        suggestions = suggestions + generate_anomaly_suggestions(anomaly_result)
        suggestions.sort(key=lambda s: s.priority)

    # Format patterns for template
    formatted_patterns = [
        {
            "type": p.pattern_type.value,
            "description": p.description,
            "time_period": p.time_period,
            "severity": p.severity.value,
            "avg_glucose": round(p.avg_glucose, 1),
            "reading_count": p.reading_count,
            "confidence": round(p.confidence, 2),
        }
        for p in patterns
    ]

    # Format suggestions for template
    formatted_suggestions = [
        {
            "category": s.category.value,
            "title": s.title,
            "description": s.description,
            "action": s.action,
            "priority": s.priority,
        }
        for s in suggestions
    ]

    # Prepare TIR chart data
    tir_data = {
        "very_low": formatted["time_in_range"]["very_low_pct"],
        "low": formatted["time_in_range"]["low_pct"],
        "target": formatted["time_in_range"]["target_pct"],
        "high": formatted["time_in_range"]["high_pct"],
        "very_high": formatted["time_in_range"]["very_high_pct"],
    }

    return templates.TemplateResponse(
        request,
        "results.html",
        {
            "session_id": session_id,
            "results": results,
            "formatted": formatted,
            "quality_warnings": quality_warnings,
            "patterns": formatted_patterns,
            "suggestions": formatted_suggestions,
            "tir_data": tir_data,
            "glucose_readings": raw_readings,
            "behavioral_patterns": behavioral_patterns_data,
            "overnight_patterns": overnight_patterns_data,
            "anomaly_detection": anomaly_detection_data,
            "source_url": session_data.source_url,
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
    session_data = session_store.get(session_id)

    if session_data is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return {
        "results": session_data.results.model_dump(),
        "patterns": [
            {
                "type": p.pattern_type.value,
                "description": p.description,
                "time_period": p.time_period,
                "severity": p.severity.value,
                "avg_glucose": p.avg_glucose,
                "reading_count": p.reading_count,
                "confidence": p.confidence,
            }
            for p in session_data.patterns
        ],
        "glucose_readings": session_data.raw_readings,
        "behavioral_patterns": session_data.behavioral_patterns,
        "overnight_patterns": session_data.overnight_patterns,
        "anomaly_detection": session_data.anomaly_detection,
    }