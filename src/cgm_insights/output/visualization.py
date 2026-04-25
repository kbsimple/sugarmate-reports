"""Terminal-based visualization for CGM glucose data.

This module provides visualization functions for displaying glucose trends,
daily summaries, and period comparisons in the terminal using Rich and asciichartpy.
"""

from rich.console import Console
from rich.table import Table
from rich.text import Text

import asciichartpy

from cgm_insights.models import CGMReading, AnalysisResults
from cgm_insights.analytics.metrics import GLUCOSE_THRESHOLDS


# Zone colors for glucose visualization
ZONE_COLORS = {
    "very_low": "red",
    "low": "bright_red",
    "target": "green",
    "high": "yellow",
    "very_high": "bright_yellow",
}


def classify_glucose_zone(glucose_mg_dl: float) -> str:
    """Classify glucose value into a zone.

    Args:
        glucose_mg_dl: Glucose value in mg/dL

    Returns:
        Zone name: 'very_low', 'low', 'target', 'high', or 'very_high'
    """
    if glucose_mg_dl < 54:
        return "very_low"
    elif glucose_mg_dl < 70:
        return "low"
    elif glucose_mg_dl <= 180:
        return "target"
    elif glucose_mg_dl <= 250:
        return "high"
    else:
        return "very_high"


def render_zone_legend(console: Console) -> None:
    """Display legend for glucose zones with colors.

    Args:
        console: Rich console for output
    """
    zones = [
        ("Very Low", "<54 mg/dL", "red"),
        ("Low", "54-70 mg/dL", "bright_red"),
        ("Target", "70-180 mg/dL", "green"),
        ("High", "180-250 mg/dL", "yellow"),
        ("Very High", ">250 mg/dL", "bright_yellow"),
    ]

    console.print("\n[bold]Glucose Zones:[/bold]")
    for name, range_str, color in zones:
        console.print(f"  [{color}]█[/{color}] {name}: {range_str}")


def render_trend_graph(readings: list[CGMReading], console: Console | None = None) -> None:
    """Render glucose trend graph with color-coded zones using asciichart.

    Args:
        readings: List of CGM readings sorted by timestamp
        console: Rich console for output (creates new if None)
    """
    if console is None:
        console = Console()

    if not readings:
        console.print("[yellow]No readings available to display.[/yellow]")
        return

    if len(readings) == 1:
        reading = readings[0]
        zone = classify_glucose_zone(reading.glucose_mg_dl)
        color = ZONE_COLORS.get(zone, "white")
        console.print(f"\n[bold]Glucose Trend[/bold]")
        console.print(f"Single reading: [{color}]{reading.glucose_mg_dl:.0f} mg/dL[/{color}]")
        console.print(f"Time: {reading.timestamp}")
        render_zone_legend(console)
        return

    # Extract glucose values and timestamps
    glucose_values = [r.glucose_mg_dl for r in readings]
    timestamps = [r.timestamp for r in readings]

    # Limit display to reasonable number of points for terminal
    max_points = 100
    if len(glucose_values) > max_points:
        # Sample evenly
        step = len(glucose_values) // max_points
        glucose_values = glucose_values[::step]
        timestamps = timestamps[::step]

    # Render graph header
    console.print("\n[bold]Glucose Trend[/bold]")
    console.print(f"Period: {timestamps[0].strftime('%Y-%m-%d %H:%M')} to {timestamps[-1].strftime('%Y-%m-%d %H:%M')}")

    # Calculate statistics for context
    avg_glucose = sum(glucose_values) / len(glucose_values)
    min_glucose = min(glucose_values)
    max_glucose = max(glucose_values)

    # Create asciichartpy configuration
    # Set height and add colors for different ranges
    config = {
        'height': 15,
        'colors': [asciichartpy.green],  # Base color
    }

    # Display the ASCII chart
    try:
        chart_output = asciichartpy.plot([glucose_values], config)
        console.print(chart_output)
    except Exception as e:
        console.print(f"[yellow]Could not render trend graph: {e}[/yellow]")

    # Display summary stats
    console.print(f"\n[cyan]Statistics:[/cyan]")
    console.print(f"  Average: {avg_glucose:.0f} mg/dL")
    console.print(f"  Range: {min_glucose:.0f} - {max_glucose:.0f} mg/dL")

    # Display zone legend
    render_zone_legend(console)


def render_daily_table(results: AnalysisResults, console: Console | None = None) -> None:
    """Render daily glucose summary as Rich table.

    Args:
        results: Analysis results with metrics
        console: Rich console for output
    """
    if console is None:
        console = Console()

    # Create table
    table = Table(title="Glucose Summary")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", justify="right")
    table.add_column("Target Range", style="dim")

    # Date range
    date_range = f"{results.date_range_start.date()} to {results.date_range_end.date()}"

    # Helper to color-code values
    def color_value(value: float, is_good: bool, unit: str = "") -> str:
        """Return colored value string."""
        color = "green" if is_good else "yellow"
        return f"[{color}]{value:.1f}{unit}[/{color}]"

    # Average glucose
    avg_in_target = 70 <= results.average_glucose <= 180
    table.add_row(
        "Average Glucose",
        color_value(results.average_glucose, avg_in_target, " mg/dL"),
        "70-180 mg/dL",
    )

    # Standard deviation
    table.add_row(
        "Standard Deviation",
        f"{results.glucose_std:.1f} mg/dL",
        "Lower is better",
    )

    # CV (Coefficient of Variation)
    cv_good = results.cv_pct < 36
    table.add_row(
        "CV",
        color_value(results.cv_pct, cv_good, "%"),
        "<36%",
    )

    # GMI
    gmi_good = results.gmi < 7.0
    table.add_row(
        "GMI",
        color_value(results.gmi, gmi_good, "%"),
        "<7%",
    )

    # Time in Target Range
    tir_good = results.time_in_range.target_pct >= 70
    table.add_row(
        "Time in Target",
        color_value(results.time_in_range.target_pct, tir_good, "%"),
        ">70%",
    )

    # Time Below Range
    tbr_good = (results.time_in_range.very_low_pct + results.time_in_range.low_pct) < 4
    below_pct = results.time_in_range.very_low_pct + results.time_in_range.low_pct
    table.add_row(
        "Time Below Range",
        color_value(below_pct, tbr_good, "%"),
        "<4%",
    )

    # Time Above Range
    tar_good = (results.time_in_range.high_pct + results.time_in_range.very_high_pct) < 25
    above_pct = results.time_in_range.high_pct + results.time_in_range.very_high_pct
    table.add_row(
        "Time Above Range",
        color_value(above_pct, tar_good, "%"),
        "<25%",
    )

    # Display table
    console.print(f"\n[cyan]Analysis Period:[/cyan] {date_range}")
    console.print(f"[cyan]Readings:[/cyan] {results.total_readings} ({results.completeness_pct:.0f}% complete)")
    console.print(table)


def calculate_delta(
    current: float,
    previous: float,
    lower_is_better: bool = False
) -> tuple[float, str]:
    """Calculate percentage change and direction indicator.

    Args:
        current: Current value
        previous: Previous value
        lower_is_better: Whether lower values are better (e.g., for glucose average)

    Returns:
        Tuple of (delta percentage, direction indicator string)
    """
    if previous == 0:
        return (0.0, "")

    delta_pct = ((current - previous) / previous) * 100

    # Determine direction
    if abs(delta_pct) < 0.1:
        direction = "↔"  # Left-right arrow (no change)
    elif lower_is_better:
        # For metrics where lower is better
        if current < previous:
            direction = "↓"  # Down arrow (improvement)
        else:
            direction = "↑"  # Up arrow (worsening)
    else:
        # For metrics where higher is better
        if current > previous:
            direction = "↑"  # Up arrow (improvement)
        else:
            direction = "↓"  # Down arrow (worsening)

    return (delta_pct, direction)


def render_comparison(
    current: AnalysisResults,
    previous: AnalysisResults,
    console: Console | None = None
) -> None:
    """Render side-by-side comparison of two analysis periods.

    Args:
        current: Current period results
        previous: Previous period results
        console: Rich console for output
    """
    if console is None:
        console = Console()

    # Create table
    table = Table(title="Period Comparison")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Current", justify="right")
    table.add_column("Previous", justify="right")
    table.add_column("Change", justify="right")

    # Helper to format change with color
    def format_change(delta: float, direction: str, is_improvement: bool) -> str:
        """Format delta with color based on improvement."""
        color = "green" if is_improvement else "red"
        if abs(delta) < 0.1:
            return f"[dim]{delta:+.1f}%[/dim]"
        return f"[{color}]{delta:+.1f}% {direction}[/{color}]"

    # Average glucose comparison
    avg_delta, avg_dir = calculate_delta(
        current.average_glucose, previous.average_glucose, lower_is_better=True
    )
    avg_improvement = current.average_glucose < previous.average_glucose
    table.add_row(
        "Average Glucose",
        f"{current.average_glucose:.0f} mg/dL",
        f"{previous.average_glucose:.0f} mg/dL",
        format_change(avg_delta, avg_dir, avg_improvement)
    )

    # CV comparison
    cv_delta, cv_dir = calculate_delta(
        current.cv_pct, previous.cv_pct, lower_is_better=True
    )
    cv_improvement = current.cv_pct < previous.cv_pct
    table.add_row(
        "CV",
        f"{current.cv_pct:.1f}%",
        f"{previous.cv_pct:.1f}%",
        format_change(cv_delta, cv_dir, cv_improvement)
    )

    # GMI comparison
    gmi_delta, gmi_dir = calculate_delta(
        current.gmi, previous.gmi, lower_is_better=True
    )
    gmi_improvement = current.gmi < previous.gmi
    table.add_row(
        "GMI",
        f"{current.gmi:.1f}%",
        f"{previous.gmi:.1f}%",
        format_change(gmi_delta, gmi_dir, gmi_improvement)
    )

    # Time in Target comparison
    tir_delta, tir_dir = calculate_delta(
        current.time_in_range.target_pct, previous.time_in_range.target_pct, lower_is_better=False
    )
    tir_improvement = current.time_in_range.target_pct > previous.time_in_range.target_pct
    table.add_row(
        "Time in Target",
        f"{current.time_in_range.target_pct:.1f}%",
        f"{previous.time_in_range.target_pct:.1f}%",
        format_change(tir_delta, tir_dir, tir_improvement)
    )

    # Time Below Range comparison
    curr_below = current.time_in_range.very_low_pct + current.time_in_range.low_pct
    prev_below = previous.time_in_range.very_low_pct + previous.time_in_range.low_pct
    below_delta, below_dir = calculate_delta(curr_below, prev_below, lower_is_better=True)
    below_improvement = curr_below < prev_below
    table.add_row(
        "Time Below Range",
        f"{curr_below:.1f}%",
        f"{prev_below:.1f}%",
        format_change(below_delta, below_dir, below_improvement)
    )

    # Time Above Range comparison
    curr_above = current.time_in_range.high_pct + current.time_in_range.very_high_pct
    prev_above = previous.time_in_range.high_pct + previous.time_in_range.very_high_pct
    above_delta, above_dir = calculate_delta(curr_above, prev_above, lower_is_better=True)
    above_improvement = curr_above < prev_above
    table.add_row(
        "Time Above Range",
        f"{curr_above:.1f}%",
        f"{prev_above:.1f}%",
        format_change(above_delta, above_dir, above_improvement)
    )

    # Display comparison
    console.print(f"\n[bold]Comparing Periods[/bold]")
    console.print(f"  Current:  {current.date_range_start.date()} to {current.date_range_end.date()}")
    console.print(f"  Previous: {previous.date_range_start.date()} to {previous.date_range_end.date()}")
    console.print(table)