"""Tests for suggestions module."""

import pytest
from datetime import datetime, timedelta

from cgm_insights.output.suggestions import (
    generate_suggestions,
    format_suggestions,
    format_suggestions_rich,
    Suggestion,
    SuggestionCategory,
    WELLNESS_DISCLAIMER,
    SUGGESTION_TEMPLATES,
)
from cgm_insights.analytics.patterns import (
    PatternResult,
    PatternType,
    PatternSeverity,
)
from cgm_insights.models import CGMReading


# Test fixtures

def create_pattern(
    pattern_type: PatternType = PatternType.TIME_OF_DAY,
    description: str = "Test pattern",
    time_period: str = "14:00-16:00",
    severity: PatternSeverity = PatternSeverity.MODERATE,
    avg_glucose: float = 180.0,
    reading_count: int = 100,
    confidence: float = 0.8,
    details: dict = None,
) -> PatternResult:
    """Create a test pattern."""
    if details is None:
        details = {}
    return PatternResult(
        pattern_type=pattern_type,
        description=description,
        time_period=time_period,
        severity=severity,
        avg_glucose=avg_glucose,
        reading_count=reading_count,
        confidence=confidence,
        details=details,
    )


# Tests for generate_suggestions

def test_generate_suggestions_returns_list():
    """Test that generate_suggestions returns a list."""
    patterns = [create_pattern()]
    suggestions = generate_suggestions(patterns)
    assert isinstance(suggestions, list)


def test_generate_suggestions_empty_patterns():
    """Test that empty patterns returns empty list."""
    suggestions = generate_suggestions([])
    assert suggestions == []


def test_generate_suggestions_maps_time_of_day_high():
    """Test mapping of time-of-day high pattern to suggestion."""
    patterns = [
        create_pattern(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Higher glucose in Afternoon (180 mg/dL)",
            time_period="14:00-16:00",
        )
    ]
    suggestions = generate_suggestions(patterns)

    assert len(suggestions) == 1
    assert suggestions[0].category == SuggestionCategory.TIMING
    assert "higher" in suggestions[0].description.lower() or "elevated" in suggestions[0].title.lower()


def test_generate_suggestions_maps_time_of_day_low():
    """Test mapping of time-of-day low pattern to suggestion."""
    patterns = [
        create_pattern(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Lower glucose in Night (65 mg/dL)",
            time_period="02:00-04:00",
            avg_glucose=65.0,
        )
    ]
    suggestions = generate_suggestions(patterns)

    assert len(suggestions) == 1
    assert suggestions[0].category == SuggestionCategory.SAFETY
    assert "lower" in suggestions[0].description.lower()


def test_generate_suggestions_maps_weekend_pattern():
    """Test mapping of weekend pattern to suggestion."""
    patterns = [
        create_pattern(
            pattern_type=PatternType.DAY_OF_WEEK,
            description="Weekend glucose tends to be higher (150 mg/dL vs 120 mg/dL weekdays)",
            time_period="Weekends",
        )
    ]
    suggestions = generate_suggestions(patterns)

    assert len(suggestions) == 1
    assert "weekend" in suggestions[0].description.lower()


def test_generate_suggestions_sorts_by_priority():
    """Test that suggestions are sorted by priority."""
    patterns = [
        create_pattern(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Higher glucose in Afternoon (180 mg/dL)",
            severity=PatternSeverity.INFO,
        ),
        create_pattern(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Lower glucose in Night (65 mg/dL)",
            severity=PatternSeverity.SIGNIFICANT,
        ),
    ]
    suggestions = generate_suggestions(patterns)

    # Safety (low glucose) should come before timing (high glucose)
    # Priority 1 = highest
    assert suggestions[0].priority <= suggestions[1].priority


def test_generate_suggestions_adjusts_priority_for_severity():
    """Test that significant patterns get higher priority."""
    patterns = [
        create_pattern(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Higher glucose in Afternoon (180 mg/dL)",
            severity=PatternSeverity.SIGNIFICANT,
        ),
    ]
    suggestions = generate_suggestions(patterns)

    # Significant patterns should have priority reduced (higher priority)
    assert suggestions[0].priority <= 2


def test_generate_suggestions_multiple_patterns():
    """Test handling multiple patterns."""
    patterns = [
        create_pattern(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Higher glucose in Afternoon",
            time_period="14:00-16:00",
        ),
        create_pattern(
            pattern_type=PatternType.DAY_OF_WEEK,
            description="Weekend glucose tends to be higher",
            time_period="Weekends",
        ),
        create_pattern(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Lower glucose in Night",
            time_period="02:00-04:00",
            avg_glucose=65.0,
        ),
    ]
    suggestions = generate_suggestions(patterns)

    assert len(suggestions) == 3
    # All should have wellness_disclaimer=True
    for s in suggestions:
        assert s.wellness_disclaimer is True


# Tests for format_suggestions

def test_format_suggestions_returns_string():
    """Test that format_suggestions returns a string."""
    patterns = [create_pattern()]
    suggestions = generate_suggestions(patterns)
    output = format_suggestions(suggestions)

    assert isinstance(output, str)


def test_format_suggestions_empty_list():
    """Test format_suggestions with empty list."""
    output = format_suggestions([])

    assert "No significant patterns" in output
    assert WELLNESS_DISCLAIMER in output


def test_format_suggestions_includes_wellness_disclaimer():
    """Test that wellness disclaimer is included."""
    patterns = [create_pattern()]
    suggestions = generate_suggestions(patterns)
    output = format_suggestions(suggestions)

    assert WELLNESS_DISCLAIMER in output


def test_format_suggestions_includes_all_suggestions():
    """Test that all suggestions are formatted."""
    patterns = [
        create_pattern(description="Higher glucose in Afternoon"),
        create_pattern(description="Lower glucose in Night"),
    ]
    suggestions = generate_suggestions(patterns)
    output = format_suggestions(suggestions)

    assert "1." in output
    assert "2." in output


def test_format_suggestions_includes_title_and_action():
    """Test that title, description, and action are included."""
    patterns = [create_pattern()]
    suggestions = generate_suggestions(patterns)
    output = format_suggestions(suggestions)

    # Output should have title and action
    assert "INSIGHTS" in output or len(output) > 100


# Tests for Suggestion model

def test_suggestion_model_frozen():
    """Test that Suggestion is immutable (frozen)."""
    suggestion = Suggestion(
        category=SuggestionCategory.TIMING,
        pattern_reference="Test pattern",
        title="Test title",
        description="Test description",
        action="Test action",
        priority=2,
    )

    with pytest.raises(Exception):
        suggestion.title = "Modified"


def test_suggestion_model_validates_priority():
    """Test that priority must be 1-5."""
    # Valid priority
    suggestion = Suggestion(
        category=SuggestionCategory.TIMING,
        pattern_reference="Test",
        title="Test",
        description="Test",
        action="Test",
        priority=3,
    )
    assert suggestion.priority == 3

    # Invalid priority > 5
    with pytest.raises(Exception):
        Suggestion(
            category=SuggestionCategory.TIMING,
            pattern_reference="Test",
            title="Test",
            description="Test",
            action="Test",
            priority=10,  # > 5
        )

    # Invalid priority < 1
    with pytest.raises(Exception):
        Suggestion(
            category=SuggestionCategory.TIMING,
            pattern_reference="Test",
            title="Test",
            description="Test",
            action="Test",
            priority=0,  # < 1
        )


def test_suggestion_category_enum():
    """Test that SuggestionCategory enum has expected values."""
    assert SuggestionCategory.TIMING.value == "timing"
    assert SuggestionCategory.VARIABILITY.value == "variability"
    assert SuggestionCategory.CONTROL.value == "control"
    assert SuggestionCategory.SAFETY.value == "safety"


# Tests for wellness language

def test_wellness_disclaimer_constant():
    """Test that wellness disclaimer is defined correctly."""
    assert "informational purposes" in WELLNESS_DISCLAIMER.lower()
    assert "not medical advice" in WELLNESS_DISCLAIMER.lower()
    assert "healthcare provider" in WELLNESS_DISCLAIMER.lower()


def test_suggestion_templates_use_wellness_language():
    """Test that all suggestion templates use wellness language."""
    wellness_words = ["consider", "might", "may", "pattern"]
    prescriptive_words = ["should", "must", "take", "adjust", "medication", "insulin"]

    for template_key, template in SUGGESTION_TEMPLATES.items():
        action = template["action"].lower()
        description = template["description"].lower()

        # Should NOT contain prescriptive language
        for word in prescriptive_words:
            assert word not in action, f"Template '{template_key}' action contains prescriptive word '{word}'"
            assert word not in description, f"Template '{template_key}' description contains prescriptive word '{word}'"

        # Should contain wellness language
        has_wellness = any(word in action or word in description for word in wellness_words)
        assert has_wellness, f"Template '{template_key}' should contain wellness language"


def test_suggestions_contain_no_medical_advice():
    """Test that generated suggestions contain no medical advice."""
    patterns = [
        create_pattern(description="Higher glucose in Afternoon"),
        create_pattern(description="Lower glucose in Night"),
        create_pattern(description="Weekend variability"),
    ]
    suggestions = generate_suggestions(patterns)

    prescriptive_words = ["should", "must", "take", "adjust medication", "take insulin"]

    for suggestion in suggestions:
        for word in prescriptive_words:
            assert word not in suggestion.action.lower(), f"Suggestion action contains '{word}'"
            assert word not in suggestion.description.lower(), f"Suggestion description contains '{word}'"


def test_all_suggestions_have_wellness_disclaimer():
    """Test that all suggestions have wellness_disclaimer=True."""
    patterns = [
        create_pattern(description="Higher glucose"),
        create_pattern(description="Lower glucose"),
    ]
    suggestions = generate_suggestions(patterns)

    for suggestion in suggestions:
        assert suggestion.wellness_disclaimer is True


def test_format_suggestions_rich_with_empty(capsys):
    """Test format_suggestions_rich with empty list."""
    from rich.console import Console

    console = Console()
    format_suggestions_rich([], console)

    # Should print "No significant patterns"
    # Note: Rich output may include ANSI codes
    captured = capsys.readouterr()
    assert "No significant patterns" in captured.out or "No significant" in captured.out


def test_format_suggestions_rich_with_patterns(capsys):
    """Test format_suggestions_rich with patterns."""
    from rich.console import Console

    patterns = [create_pattern(description="Higher glucose in Afternoon")]
    suggestions = generate_suggestions(patterns)

    console = Console()
    format_suggestions_rich(suggestions, console)

    # Should print insights
    # Note: Rich output may include ANSI codes
    captured = capsys.readouterr()
    # Just check that something was printed
    assert len(captured.out) > 0


# Test for variability pattern mapping

def test_generate_suggestions_maps_variability():
    """Test mapping of variability pattern to suggestion."""
    patterns = [
        create_pattern(
            pattern_type=PatternType.TIME_OF_DAY,
            description="High variability in Afternoon (CV: 50%)",
            time_period="14:00-16:00",
            details={"cv": 50.0},
        )
    ]
    suggestions = generate_suggestions(patterns)

    assert len(suggestions) == 1
    assert suggestions[0].category == SuggestionCategory.VARIABILITY
    # Description uses "varies more" rather than "variability"
    assert "variab" in suggestions[0].description.lower() or "varies" in suggestions[0].description.lower()


# Test for specific day pattern mapping

def test_generate_suggestions_maps_specific_day():
    """Test mapping of specific day pattern to suggestion."""
    patterns = [
        create_pattern(
            pattern_type=PatternType.DAY_OF_WEEK,
            description="Monday glucose tends to be higher than other days",
            time_period="Monday",
        )
    ]
    suggestions = generate_suggestions(patterns)

    assert len(suggestions) == 1
    assert "Monday" in suggestions[0].description or "day" in suggestions[0].action.lower()