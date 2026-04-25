"""CLI entry point for CGM Insights using Typer.

This module provides the command-line interface for analyzing CGM data.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cgm_insights import analyze_file, format_summary, format_quality_flags, GMI_CAVEAT
from cgm_insights.ingestion import get_parser, exclude_warmup_period
from cgm_insights.output.visualization import (
    render_trend_graph,
    render_daily_table,
    render_comparison,
    render_zone_legend,
)
from cgm_insights.analytics.patterns import (
    detect_time_of_day_patterns,
    detect_day_of_week_patterns,
)
from cgm_insights.output.suggestions import (
    generate_suggestions,
    format_suggestions_rich,
    WELLNESS_DISCLAIMER,
)

app = typer.Typer(
    name="cgm-insights",
    help="Analyze CGM (Continuous Glucose Monitor) data for glucose insights.",
)


@app.command()
def analyze(
    file_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to CGM data file (CSV format supported)",
    ),
    start_date: Optional[str] = typer.Option(
        None,
        "--start",
        "-s",
        help="Start date filter (ISO format: YYYY-MM-DD)",
    ),
    end_date: Optional[str] = typer.Option(
        None,
        "--end",
        "-e",
        help="End date filter (ISO format: YYYY-MM-DD)",
    ),
    exclude_warmup: bool = typer.Option(
        True,
        "--exclude-warmup/--include-warmup",
        help="Exclude sensor warmup period (first 2 hours) from analysis",
    ),
    visualize: bool = typer.Option(
        True,
        "--viz/--no-viz",
        help="Show trend visualization",
    ),
    compare: bool = typer.Option(
        False,
        "--compare",
        "-c",
        help="Compare with previous period of same duration",
    ),
    insights: bool = typer.Option(
        True,
        "--insights/--no-insights",
        help="Show time-of-day and day-of-week patterns with suggestions",
    ),
) -> None:
    """Analyze CGM data from file and display metrics.

    This command reads CGM data from a file, calculates glucose metrics
    including time-in-range, average glucose, GMI, and variability metrics,
    then displays the results with optional trend visualization.

    Examples:
        cgm-insights analyze readings.csv
        cgm-insights analyze readings.csv --start 2024-01-01 --end 2024-01-31
        cgm-insights analyze readings.csv --include-warmup
        cgm-insights analyze readings.csv --no-viz
        cgm-insights analyze readings.csv --compare
    """
    console = Console()

    try:
        # Parse dates if provided
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        # Run analysis using the core library
        results = analyze_file(
            str(file_path),
            start_date=start_date,
            end_date=end_date,
            exclude_warmup=exclude_warmup,
        )

        # Get readings for visualization or insights if needed
        readings = None
        if visualize or compare or insights:
            parser = get_parser(str(file_path))
            readings = parser.parse(str(file_path), start_date=start, end_date=end)
            if exclude_warmup and readings:
                readings = exclude_warmup_period(readings)

        # Display trend visualization if requested
        if visualize and readings:
            try:
                render_trend_graph(readings, console)
            except Exception as e:
                console.print(f"[yellow]Could not render trend graph: {e}[/yellow]")

        # Display daily summary table
        render_daily_table(results, console)

        # Display quality flags if present
        if results.data_quality_flags:
            console.print("\n[bold]Quality Flags:[/bold]")
            formatted_flags = format_quality_flags(results.data_quality_flags)
            for flag_info in formatted_flags:
                console.print(f"  - {flag_info['message']}")

        # Display period comparison if requested
        if compare:
            try:
                # Calculate previous period dates
                current_start = results.date_range_start
                current_end = results.date_range_end
                duration = current_end - current_start

                previous_end = current_start - timedelta(seconds=1)
                previous_start = previous_end - duration

                # Parse previous period
                parser = get_parser(str(file_path))
                previous_readings = parser.parse(
                    str(file_path),
                    start_date=previous_start,
                    end_date=previous_end,
                )

                if previous_readings and exclude_warmup:
                    previous_readings = exclude_warmup_period(previous_readings)

                if previous_readings:
                    from cgm_insights.analytics import calculate_metrics
                    from cgm_insights.ingestion import validate_completeness

                    previous_validation = validate_completeness(previous_readings)
                    previous_results = calculate_metrics(previous_readings, previous_validation)

                    # Render comparison
                    render_comparison(results, previous_results, console)
                else:
                    console.print("\n[yellow]No data available for previous period comparison.[/yellow]")

            except Exception as e:
                console.print(f"\n[yellow]Could not compare periods: {e}[/yellow]")

        # Display insights if requested
        if insights and readings:
            try:
                # Detect patterns
                time_patterns = detect_time_of_day_patterns(readings)
                day_patterns = detect_day_of_week_patterns(readings)
                all_patterns = time_patterns + day_patterns

                if all_patterns:
                    # Generate suggestions from patterns
                    suggestions = generate_suggestions(all_patterns, results)
                    format_suggestions_rich(suggestions, console)
                else:
                    console.print("\n[cyan]No significant patterns detected in your data.[/cyan]")
                    console.print(f"\n[dim]{WELLNESS_DISCLAIMER}[/dim]")

            except Exception as e:
                console.print(f"\n[yellow]Could not generate insights: {e}[/yellow]")
        elif insights and not readings:
            console.print("\n[yellow]Insights require data. No readings available.[/yellow]")

        # Display GMI caveat
        console.print(f"\n[dim]Note: {GMI_CAVEAT}[/dim]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()