"""CLI entry point for CGM Insights using Typer.

This module provides the command-line interface for analyzing CGM data.
"""

import tempfile
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer
from rich.console import Console

from cgm_insights import analyze_file, format_quality_flags, GMI_CAVEAT
from cgm_insights.ingestion import get_parser, exclude_warmup_period
from cgm_insights.output.visualization import (
    render_trend_graph,
    render_daily_table,
    render_comparison,
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


def _run_analysis(
    file_path: Path,
    start_date: Optional[str],
    end_date: Optional[str],
    exclude_warmup: bool,
    visualize: bool,
    compare: bool,
    insights: bool,
    console: Console,
) -> None:
    """Run analysis on a local file and print results to console."""
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    results = analyze_file(
        str(file_path),
        start_date=start_date,
        end_date=end_date,
        exclude_warmup=exclude_warmup,
    )

    readings = None
    if visualize or compare or insights:
        parser = get_parser(str(file_path))
        readings = parser.parse(str(file_path), start_date=start, end_date=end)
        if exclude_warmup and readings:
            readings = exclude_warmup_period(readings)

    if visualize and readings:
        try:
            render_trend_graph(readings, console)
        except Exception as e:
            console.print(f"[yellow]Could not render trend graph: {e}[/yellow]")

    render_daily_table(results, console)

    if results.data_quality_flags:
        console.print("\n[bold]Quality Flags:[/bold]")
        for flag_info in format_quality_flags(results.data_quality_flags):
            console.print(f"  - {flag_info['message']}")

    if compare:
        try:
            duration = results.date_range_end - results.date_range_start
            previous_end = results.date_range_start - timedelta(seconds=1)
            previous_start = previous_end - duration

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

                previous_results = calculate_metrics(
                    previous_readings, validate_completeness(previous_readings)
                )
                render_comparison(results, previous_results, console)
            else:
                console.print("\n[yellow]No data available for previous period comparison.[/yellow]")
        except Exception as e:
            console.print(f"\n[yellow]Could not compare periods: {e}[/yellow]")

    if insights and readings:
        try:
            all_patterns = detect_time_of_day_patterns(readings) + detect_day_of_week_patterns(readings)
            if all_patterns:
                format_suggestions_rich(generate_suggestions(all_patterns, results), console)
            else:
                console.print("\n[cyan]No significant patterns detected in your data.[/cyan]")
                console.print(f"\n[dim]{WELLNESS_DISCLAIMER}[/dim]")
        except Exception as e:
            console.print(f"\n[yellow]Could not generate insights: {e}[/yellow]")
    elif insights and not readings:
        console.print("\n[yellow]Insights require data. No readings available.[/yellow]")

    console.print(f"\n[dim]Note: {GMI_CAVEAT}[/dim]")


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
        None, "--start", "-s", help="Start date filter (ISO format: YYYY-MM-DD)",
    ),
    end_date: Optional[str] = typer.Option(
        None, "--end", "-e", help="End date filter (ISO format: YYYY-MM-DD)",
    ),
    exclude_warmup: bool = typer.Option(
        True,
        "--exclude-warmup/--include-warmup",
        help="Exclude sensor warmup period (first 2 hours) from analysis",
    ),
    visualize: bool = typer.Option(True, "--viz/--no-viz", help="Show trend visualization"),
    compare: bool = typer.Option(
        False, "--compare", "-c", help="Compare with previous period of same duration",
    ),
    insights: bool = typer.Option(
        True, "--insights/--no-insights", help="Show time-of-day and day-of-week patterns",
    ),
) -> None:
    """Analyze CGM data from a local file and display metrics.

    Examples:
        cgm-insights analyze readings.csv
        cgm-insights analyze readings.csv --start 2024-01-01 --end 2024-01-31
        cgm-insights analyze readings.csv --include-warmup --no-viz --compare
    """
    console = Console()
    try:
        _run_analysis(file_path, start_date, end_date, exclude_warmup, visualize, compare, insights, console)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def download_and_analyze(
    url: str = typer.Argument(..., help="URL of the CGM data file to download and analyze"),
    start_date: Optional[str] = typer.Option(
        None, "--start", "-s", help="Start date filter (ISO format: YYYY-MM-DD)",
    ),
    end_date: Optional[str] = typer.Option(
        None, "--end", "-e", help="End date filter (ISO format: YYYY-MM-DD)",
    ),
    exclude_warmup: bool = typer.Option(
        True,
        "--exclude-warmup/--include-warmup",
        help="Exclude sensor warmup period (first 2 hours) from analysis",
    ),
    visualize: bool = typer.Option(True, "--viz/--no-viz", help="Show trend visualization"),
    compare: bool = typer.Option(
        False, "--compare", "-c", help="Compare with previous period of same duration",
    ),
    insights: bool = typer.Option(
        True, "--insights/--no-insights", help="Show time-of-day and day-of-week patterns",
    ),
) -> None:
    """Download a CGM data file from a URL and analyze it.

    Examples:
        cgm-insights download-and-analyze https://example.com/readings.csv
        cgm-insights download-and-analyze https://example.com/readings.csv --start 2024-01-01
    """
    console = Console()
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            console.print("[red]Error: URL must start with http:// or https://[/red]")
            raise typer.Exit(1)

        suffix = Path(parsed.path).suffix or ".csv"
        console.print(f"[cyan]Downloading {url}...[/cyan]")

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            urllib.request.urlretrieve(url, tmp_path)
            console.print("[green]Download complete.[/green]\n")
            _run_analysis(tmp_path, start_date, end_date, exclude_warmup, visualize, compare, insights, console)
        finally:
            tmp_path.unlink(missing_ok=True)

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except urllib.error.URLError as e:
        console.print(f"[red]Download failed: {e.reason}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()