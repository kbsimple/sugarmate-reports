"""Actionable suggestions from detected patterns.

This module generates wellness-focused suggestions from glucose patterns.
All suggestions use non-prescriptive language ("consider", "might explore")
and include a wellness disclaimer.

CRITICAL: This module contains NO medical advice. All suggestions are
informational and encourage consulting healthcare providers.
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

from cgm_insights.analytics.patterns import PatternResult, PatternType, PatternSeverity
from cgm_insights.analytics.behavioral_patterns import (
    BehavioralPattern,
    BehavioralAnalysisResult,
    ConsistencyLabel,
)
from cgm_insights.models import AnalysisResults


# Wellness language constants - NO medical advice
WELLNESS_PREFIXES = [
    "Consider",
    "You might consider",
    "A pattern of",
    "Your data shows",
    "Notice that",
]

WELLNESS_CONNECTORS = [
    "This may indicate",
    "This pattern suggests",
    "You might explore",
    "Consider discussing with your healthcare provider",
]

# MANDATORY disclaimer for all suggestions
WELLNESS_DISCLAIMER = (
    "This is for informational purposes only and is not medical advice. "
    "Always discuss glucose patterns with your healthcare provider."
)


class SuggestionCategory(str, Enum):
    """Category of suggestion for prioritization."""
    TIMING = "timing"
    VARIABILITY = "variability"
    CONTROL = "control"
    SAFETY = "safety"


class Suggestion(BaseModel):
    """Actionable suggestion tied to a detected pattern.

    All suggestions use wellness language and include disclaimer.

    Attributes:
        category: Suggestion category for prioritization
        pattern_reference: Description of the pattern this suggestion addresses
        title: Short title for the suggestion
        description: Human-readable description of the pattern
        action: Suggested action using wellness language
        priority: Priority level (1=highest, 5=lowest)
        wellness_disclaimer: Whether to show disclaimer with this suggestion
    """

    category: SuggestionCategory = Field(
        ...,
        description="Category of suggestion"
    )
    pattern_reference: str = Field(
        ...,
        description="Description of the pattern this addresses"
    )
    title: str = Field(
        ...,
        description="Short title for the suggestion"
    )
    description: str = Field(
        ...,
        description="Description of the pattern in wellness language"
    )
    action: str = Field(
        ...,
        description="Suggested action using wellness language"
    )
    priority: int = Field(
        ...,
        ge=1,
        le=5,
        description="Priority level (1=highest, 5=lowest)"
    )
    wellness_disclaimer: bool = Field(
        True,
        description="Whether to show wellness disclaimer"
    )

    model_config = ConfigDict(frozen=True)


# Suggestion templates for each pattern type
# All use wellness language - NO medical advice
SUGGESTION_TEMPLATES = {
    "time_of_day_high": {
        "title": "Elevated glucose period detected",
        "description": "Your glucose tends to be higher during {time_period}.",
        "action": "Consider activities that may help, such as a short walk or movement during this time.",
        "category": SuggestionCategory.TIMING,
        "priority": 2,
    },
    "time_of_day_low": {
        "title": "Lower glucose period detected",
        "description": "Your glucose tends to be lower during {time_period}.",
        "action": "Be mindful of this pattern and consider having glucose sources available.",
        "category": SuggestionCategory.SAFETY,
        "priority": 2,
    },
    "time_of_day_variability": {
        "title": "High glucose variability detected",
        "description": "Your glucose varies more during {time_period}.",
        "action": "Consider tracking what might contribute to this variability.",
        "category": SuggestionCategory.VARIABILITY,
        "priority": 3,
    },
    "weekend_higher": {
        "title": "Weekend glucose pattern",
        "description": "Your weekend glucose tends to be higher than weekdays.",
        "action": "Consider exploring weekend routines that might influence glucose.",
        "category": SuggestionCategory.CONTROL,
        "priority": 3,
    },
    "weekend_lower": {
        "title": "Weekend glucose pattern",
        "description": "Your weekend glucose tends to be lower than weekdays.",
        "action": "Be aware of this pattern and consider how weekend activities might contribute.",
        "category": SuggestionCategory.CONTROL,
        "priority": 3,
    },
    "weekend_variability": {
        "title": "Weekend variability pattern",
        "description": "Your glucose variability is higher on weekends.",
        "action": "Consider maintaining consistent routines through the weekend.",
        "category": SuggestionCategory.VARIABILITY,
        "priority": 3,
    },
    "specific_day_high": {
        "title": "Day-specific glucose pattern",
        "description": "Your glucose on {day} tends to be higher than other days.",
        "action": "Consider what might be different about {day} in your routine.",
        "category": SuggestionCategory.CONTROL,
        "priority": 3,
    },
    "specific_day_low": {
        "title": "Day-specific glucose pattern",
        "description": "Your glucose on {day} tends to be lower than other days.",
        "action": "Be mindful of this pattern and what might contribute to it.",
        "category": SuggestionCategory.CONTROL,
        "priority": 3,
    },
    "behavioral_consistent": {
        "title": "Consistent period detected",
        "description": "Your glucose during {bucket_label} is particularly consistent across days.",
        "action": (
            "This period may be a useful anchor for your routine — "
            "consider noting what contributes to this consistency."
        ),
        "category": SuggestionCategory.TIMING,
        "priority": 3,
    },
    "behavioral_variable": {
        "title": "Variable period detected",
        "description": "Your glucose during {bucket_label} tends to vary more across days.",
        "action": "Consider exploring what differs on days when this period looks higher or lower.",
        "category": SuggestionCategory.VARIABILITY,
        "priority": 3,
    },
    "behavioral_weekday_weekend_diff": {
        "title": "Weekday vs weekend difference",
        "description": (
            "During {bucket_label}, your weekday glucose ({weekday_avg:.0f} mg/dL) "
            "and weekend glucose ({weekend_avg:.0f} mg/dL) follow different patterns."
        ),
        "action": "Consider whether routines during this time differ between weekdays and weekends.",
        "category": SuggestionCategory.CONTROL,
        "priority": 4,
    },
}


def generate_suggestions(
    patterns: list[PatternResult],
    results: AnalysisResults | None = None
) -> list[Suggestion]:
    """Generate actionable suggestions from detected patterns.

    Uses wellness language throughout. No medical advice.
    All suggestions encourage consulting healthcare provider.

    Args:
        patterns: List of detected patterns
        results: Optional analysis results for additional context

    Returns:
        List of actionable suggestions sorted by priority (safety first)
    """
    if not patterns:
        return []

    suggestions = []

    for pattern in patterns:
        suggestion = _pattern_to_suggestion(pattern)
        if suggestion:
            suggestions.append(suggestion)

    # Sort by priority (1 = highest priority, comes first)
    suggestions.sort(key=lambda s: s.priority)

    return suggestions


def generate_behavioral_suggestions(
    behavioral_result: BehavioralAnalysisResult,
) -> list[Suggestion]:
    """Generate actionable suggestions from behavioral pattern analysis.

    Selects notable patterns (Consistent and Variable labels) and generates
    one suggestion per notable pattern. All suggestions use wellness language.
    Weekday/weekend difference suggestions are generated when both averages
    are available and differ by more than 10 mg/dL.

    Args:
        behavioral_result: Result from analyze_behavioral_patterns().

    Returns:
        List of Suggestion objects sorted by priority (1=highest).
    """
    if not behavioral_result.patterns:
        return []

    suggestions: list[Suggestion] = []
    # Limit to top 3 consistent and top 3 variable patterns to avoid suggestion flood
    consistent_patterns = [
        p for p in behavioral_result.patterns
        if p.consistency_label == ConsistencyLabel.CONSISTENT
    ][:3]
    variable_patterns = [
        p for p in behavioral_result.patterns
        if p.consistency_label == ConsistencyLabel.VARIABLE
    ][:3]

    for pattern in consistent_patterns:
        template = SUGGESTION_TEMPLATES["behavioral_consistent"]
        suggestions.append(Suggestion(
            category=template["category"],
            pattern_reference=f"Consistent period: {pattern.bucket_label}",
            title=template["title"],
            description=template["description"].format(bucket_label=pattern.bucket_label),
            action=template["action"],
            priority=template["priority"],
            wellness_disclaimer=True,
        ))

    for pattern in variable_patterns:
        template = SUGGESTION_TEMPLATES["behavioral_variable"]
        suggestions.append(Suggestion(
            category=template["category"],
            pattern_reference=f"Variable period: {pattern.bucket_label}",
            title=template["title"],
            description=template["description"].format(bucket_label=pattern.bucket_label),
            action=template["action"],
            priority=template["priority"],
            wellness_disclaimer=True,
        ))

    # Weekday/weekend diff: only for patterns where both averages exist and differ > 10 mg/dL
    for pattern in behavioral_result.patterns:
        if (
            pattern.weekday_avg_glucose is not None
            and pattern.weekend_avg_glucose is not None
            and abs(pattern.weekday_avg_glucose - pattern.weekend_avg_glucose) > 10.0
        ):
            template = SUGGESTION_TEMPLATES["behavioral_weekday_weekend_diff"]
            suggestions.append(Suggestion(
                category=template["category"],
                pattern_reference=f"Weekday/weekend diff: {pattern.bucket_label}",
                title=template["title"],
                description=template["description"].format(
                    bucket_label=pattern.bucket_label,
                    weekday_avg=pattern.weekday_avg_glucose,
                    weekend_avg=pattern.weekend_avg_glucose,
                ),
                action=template["action"],
                priority=template["priority"],
                wellness_disclaimer=True,
            ))
            break  # One weekday/weekend diff suggestion is enough

    suggestions.sort(key=lambda s: s.priority)
    return suggestions


def _pattern_to_suggestion(pattern: PatternResult) -> Suggestion | None:
    """Convert a pattern to a suggestion.

    Args:
        pattern: Detected pattern

    Returns:
        Suggestion or None if pattern cannot be mapped
    """
    # Determine template key based on pattern
    template_key = _get_template_key(pattern)
    if not template_key:
        return None

    template = SUGGESTION_TEMPLATES.get(template_key)
    if not template:
        return None

    # Fill in template placeholders
    time_period = pattern.details.get("period_label", pattern.time_period)
    day = pattern.time_period  # For day-of-week patterns

    description = template["description"].format(
        time_period=time_period,
        day=day
    )
    action = template["action"].format(
        time_period=time_period,
        day=day
    )

    # Adjust priority based on severity
    priority = template["priority"]
    if pattern.severity == PatternSeverity.SIGNIFICANT:
        priority = max(1, priority - 1)  # Increase priority for significant patterns
    elif pattern.severity == PatternSeverity.INFO:
        priority = min(5, priority + 1)  # Decrease priority for info-level patterns

    return Suggestion(
        category=template["category"],
        pattern_reference=pattern.description,
        title=template["title"],
        description=description,
        action=action,
        priority=priority,
        wellness_disclaimer=True,
    )


def _get_template_key(pattern: PatternResult) -> str | None:
    """Get the template key for a pattern.

    Args:
        pattern: Detected pattern

    Returns:
        Template key or None
    """
    if pattern.pattern_type == PatternType.TIME_OF_DAY:
        # Check description for pattern type
        desc_lower = pattern.description.lower()

        if "higher" in desc_lower or "elevated" in desc_lower:
            return "time_of_day_high"
        elif "lower" in desc_lower:
            return "time_of_day_low"
        elif "variability" in desc_lower:
            return "time_of_day_variability"

    elif pattern.pattern_type == PatternType.DAY_OF_WEEK:
        desc_lower = pattern.description.lower()
        time_period = pattern.time_period.lower()

        if "weekend" in time_period or "weekend" in desc_lower:
            if "variability" in desc_lower:
                return "weekend_variability"
            elif "higher" in desc_lower:
                return "weekend_higher"
            elif "lower" in desc_lower:
                return "weekend_lower"
        else:
            # Specific day pattern
            if "higher" in desc_lower:
                return "specific_day_high"
            elif "lower" in desc_lower:
                return "specific_day_low"

    return None


def format_suggestions(suggestions: list[Suggestion]) -> str:
    """Format suggestions as human-readable text.

    Args:
        suggestions: List of suggestions to format

    Returns:
        Formatted string with all suggestions and wellness disclaimer
    """
    if not suggestions:
        return "No significant patterns detected.\n\n" + WELLNESS_DISCLAIMER

    lines = []
    lines.append("=" * 60)
    lines.append("INSIGHTS & SUGGESTIONS")
    lines.append("=" * 60)
    lines.append("")

    for i, suggestion in enumerate(suggestions, 1):
        lines.append(f"{i}. {suggestion.title}")
        lines.append(f"   {suggestion.description}")
        lines.append(f"   {suggestion.action}")
        lines.append("")

    # Add wellness disclaimer
    lines.append("-" * 60)
    lines.append(WELLNESS_DISCLAIMER)

    return "\n".join(lines)


def format_suggestions_rich(suggestions: list[Suggestion], console) -> None:
    """Format suggestions using Rich console for colored output.

    Args:
        suggestions: List of suggestions to format
        console: Rich Console object
    """
    from rich.table import Table
    from rich.text import Text

    if not suggestions:
        console.print("\n[yellow]No significant patterns detected.[/yellow]")
        console.print(f"\n[dim]{WELLNESS_DISCLAIMER}[/dim]")
        return

    console.print("\n[bold cyan]Insights & Suggestions[/bold cyan]\n")

    # Create table for suggestions
    table = Table(show_header=True, header_style="bold", expand=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Category", style="cyan", width=10)
    table.add_column("Pattern", style="white")
    table.add_column("Suggestion", style="green")

    # Category colors
    category_styles = {
        SuggestionCategory.SAFETY: "red",
        SuggestionCategory.CONTROL: "yellow",
        SuggestionCategory.TIMING: "blue",
        SuggestionCategory.VARIABILITY: "magenta",
    }

    for i, suggestion in enumerate(suggestions, 1):
        style = category_styles.get(suggestion.category, "white")
        table.add_row(
            str(i),
            f"[{style}]{suggestion.category.value}[/{style}]",
            suggestion.description,
            suggestion.action,
        )

    console.print(table)

    # Add wellness disclaimer
    console.print(f"\n[dim]Note: {WELLNESS_DISCLAIMER}[/dim]")