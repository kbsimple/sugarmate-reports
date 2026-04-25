"""Output module - formatting, visualization, and suggestions."""

from .formatter import format_results, format_quality_flags, format_summary
from .visualization import (
    classify_glucose_zone,
    render_trend_graph,
    render_daily_table,
    render_comparison,
    render_zone_legend,
    calculate_delta,
)
from .suggestions import (
    generate_suggestions,
    format_suggestions,
    format_suggestions_rich,
    Suggestion,
    SuggestionCategory,
    WELLNESS_DISCLAIMER,
)

__all__ = [
    # Formatting
    "format_results",
    "format_quality_flags",
    "format_summary",
    # Visualization
    "classify_glucose_zone",
    "render_trend_graph",
    "render_daily_table",
    "render_comparison",
    "render_zone_legend",
    "calculate_delta",
    # Suggestions
    "generate_suggestions",
    "format_suggestions",
    "format_suggestions_rich",
    "Suggestion",
    "SuggestionCategory",
    "WELLNESS_DISCLAIMER",
]