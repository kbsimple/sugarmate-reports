"""CLI entry point for CGM Insights using Typer.

This module provides the command-line interface for analyzing CGM data.
"""

import tempfile
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

_XLSX_MAGIC = b"PK\x03\x04"


def _detect_suffix(downloaded: Path, url_path: str) -> str:
    """Return the real file extension based on magic bytes, falling back to URL path."""
    try:
        with downloaded.open("rb") as f:
            if f.read(4) == _XLSX_MAGIC:
                return ".xlsx"
    except OSError:
        pass
    return Path(url_path).suffix or ".csv"

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
from cgm_insights.analytics.behavioral_patterns import (
    analyze_behavioral_patterns,
    ConsistencyLabel,
)
from cgm_insights.analytics.overnight_patterns import analyze_overnight_patterns
from cgm_insights.analytics.anomaly_detection import analyze_anomalies
from cgm_insights.output.suggestions import (
    generate_suggestions,
    format_suggestions_rich,
    WELLNESS_DISCLAIMER,
)

app = typer.Typer(
    name="cgm-insights",
    help="Analyze CGM (Continuous Glucose Monitor) data for glucose insights.",
)


def _render_behavioral_patterns(
    result,
    console: Console,
) -> None:
    """Render behavioral patterns as a Rich table per window size.

    Shows bucket label, consistency label, average glucose, and CV score
    for Consistent and Variable buckets (Moderate omitted to reduce noise).

    Args:
        result: BehavioralAnalysisResult from analyze_behavioral_patterns().
        console: Rich Console for output.
    """
    from rich.table import Table

    console.print("\n[bold cyan]Behavioral Patterns[/bold cyan]")
    console.print(f"[dim]({result.total_days} days of data)[/dim]\n")

    for window_min in result.window_sizes:
        window_patterns = [
            p for p in result.patterns
            if p.window_size_min == window_min
        ]
        notable = [
            p for p in window_patterns
            if p.consistency_label in (ConsistencyLabel.CONSISTENT, ConsistencyLabel.VARIABLE)
        ]
        if not notable:
            continue

        table = Table(
            title=f"{window_min}-Minute Windows — Notable Periods",
            show_header=True,
            header_style="bold",
        )
        table.add_column("Time", style="white", width=14)
        table.add_column("Consistency", style="cyan", width=12)
        table.add_column("Avg Glucose", style="white", width=12)
        table.add_column("CV Score", style="dim", width=10)

        for pattern in notable:
            label_style = (
                "green" if pattern.consistency_label == ConsistencyLabel.CONSISTENT
                else "yellow"
            )
            table.add_row(
                pattern.bucket_label,
                f"[{label_style}]{pattern.consistency_label.value}[/{label_style}]",
                f"{pattern.avg_glucose:.0f} mg/dL",
                f"{pattern.cv_score:.1f}%",
            )

        console.print(table)
        console.print()


def _render_overnight_patterns(
    result,
    console: Console,
) -> None:
    """Render overnight glucose patterns as a Rich table.

    Shows per-metric summary row, stability score, and weekday/weekend split
    if available. Never uses "sleep" or clinical metric names.

    Args:
        result: OvernightAnalysisResult from analyze_overnight_patterns().
        console: Rich Console for output.
    """
    from rich.table import Table

    console.print("\n[bold cyan]Overnight Patterns (10pm–6am)[/bold cyan]")
    console.print(f"[dim]({result.nights_with_data} nights of data)[/dim]\n")

    table = Table(
        title="Overnight Window Metrics",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Metric", style="white", width=22)
    table.add_column("Value", style="cyan", width=16)

    if result.mean_glucose is not None:
        table.add_row("Mean Glucose", f"{result.mean_glucose:.0f} mg/dL")
    if result.tir_pct is not None:
        table.add_row("Time in Range (70–180)", f"{result.tir_pct:.1f}%")
    if result.cv is not None:
        table.add_row("Variability (CV)", f"{result.cv:.1f}%")
    if result.tbr_pct is not None:
        table.add_row("Time Below Range (<70)", f"{result.tbr_pct:.1f}%")
    if result.stability_score is not None:
        score_pct = result.stability_score * 100
        table.add_row(
            "Overnight Stability Score",
            f"{score_pct:.0f}% — {result.stability_label}",
        )

    console.print(table)

    if result.weekday_mean_glucose is not None and result.weekend_mean_glucose is not None:
        console.print(
            f"\n[dim]Weekday nights avg:[/dim] {result.weekday_mean_glucose:.0f} mg/dL  "
            f"[dim]Weekend nights avg:[/dim] {result.weekend_mean_glucose:.0f} mg/dL"
        )

    exc = result.excursion_summary
    if exc.get("total_excursion_nights", 0) > 0:
        console.print("\n[yellow]Overnight patterns of note:[/yellow]")
        if exc.get("sustained_low_nights", 0) > 0:
            console.print(
                f"  {exc['sustained_low_nights']} of {exc['total_nights']} nights: "
                "sustained low glucose periods"
            )
        if exc.get("sustained_high_nights", 0) > 0:
            console.print(
                f"  {exc['sustained_high_nights']} of {exc['total_nights']} nights: "
                "sustained elevated glucose periods"
            )

    console.print(f"\n[dim]Window: {result.window_label}[/dim]")


def _render_anomaly_detection(
    result,
    console: Console,
) -> None:
    """Render anomaly detection summary as Rich output.

    Shows weekly summary counts using badge-style text styling.
    Never uses "alert", "alarm", "abnormal", or clinical diagnosis terms.

    Args:
        result: AnomalyDetectionResult from analyze_anomalies().
        console: Rich Console for output.
    """
    from rich.table import Table

    console.print("\n[bold cyan]Unusual Glucose Patterns[/bold cyan]")
    console.print(
        f"[dim]({result.days_analyzed} days analyzed, "
        f"{result.total_anomalies} unusual readings detected)[/dim]\n"
    )

    if result.total_anomalies == 0:
        console.print("[dim]No unusual patterns detected in your data.[/dim]")
        return

    table = Table(
        title="Unusual Pattern Summary",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Tier", style="white", width=16)
    table.add_column("Count", style="cyan", width=10)
    table.add_column("Description", style="dim", width=30)

    if result.severe_total > 0:
        table.add_row(
            "[red]Significant[/red]",
            str(result.severe_total),
            "4x+ from personal baseline",
        )
    if result.moderate_total > 0:
        table.add_row(
            "[yellow]Moderate[/yellow]",
            str(result.moderate_total),
            "3-4x from personal baseline",
        )
    if result.mild_total > 0:
        table.add_row(
            "[blue]Mild[/blue]",
            str(result.mild_total),
            "2-3x from personal baseline",
        )
    console.print(table)

    if result.pisa_artifacts_filtered > 0:
        console.print(
            f"\n[dim]{result.pisa_artifacts_filtered} sensor artifact "
            f"reading(s) excluded from analysis.[/dim]"
        )

    if result.weekly_summaries:
        console.print("\n[bold]Weekly Breakdown:[/bold]")
        for week in result.weekly_summaries[:4]:
            parts = []
            if week.severe_count:
                parts.append(f"[red]{week.severe_count} significant[/red]")
            if week.moderate_count:
                parts.append(f"[yellow]{week.moderate_count} moderate[/yellow]")
            if week.mild_count:
                parts.append(f"[blue]{week.mild_count} mild[/blue]")
            summary = ", ".join(parts) if parts else "none"
            console.print(f"  {week.week_label}: {summary}")


def _run_analysis(
    file_path: Path,
    start_date: Optional[str],
    end_date: Optional[str],
    exclude_warmup: bool,
    visualize: bool,
    compare: bool,
    insights: bool,
    behavioral: bool,
    overnight: bool,
    anomaly: bool,
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
    if visualize or compare or insights or behavioral or overnight or anomaly:
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

    if behavioral and readings:
        try:
            behavioral_result = analyze_behavioral_patterns(readings)
            if behavioral_result.insufficient_data:
                console.print(
                    "\n[yellow]Behavioral patterns require at least 5 days of data.[/yellow]"
                )
            else:
                _render_behavioral_patterns(behavioral_result, console)
        except Exception as e:
            console.print(f"\n[yellow]Could not generate behavioral patterns: {e}[/yellow]")
    elif behavioral and not readings:
        console.print("\n[yellow]Behavioral patterns require data. No readings available.[/yellow]")

    if overnight and readings:
        try:
            overnight_result = analyze_overnight_patterns(readings)
            if overnight_result.insufficient_data:
                console.print(
                    "\n[yellow]Overnight patterns require at least 5 nights of data "
                    "in the 10pm–6am window.[/yellow]"
                )
            else:
                _render_overnight_patterns(overnight_result, console)
        except Exception as e:
            console.print(
                f"\n[yellow]Could not generate overnight patterns: {e}[/yellow]"
            )
    elif overnight and not readings:
        console.print(
            "\n[yellow]Overnight patterns require data. No readings available.[/yellow]"
        )

    if anomaly and readings:
        try:
            anomaly_result = analyze_anomalies(readings)
            if anomaly_result.insufficient_data:
                console.print(
                    "\n[yellow]Unusual pattern detection requires at least 5 days "
                    "of data to establish a personal baseline.[/yellow]"
                )
            else:
                _render_anomaly_detection(anomaly_result, console)
        except Exception as e:
            console.print(
                f"\n[yellow]Could not generate unusual pattern analysis: {e}[/yellow]"
            )
    elif anomaly and not readings:
        console.print(
            "\n[yellow]Unusual pattern detection requires data. "
            "No readings available.[/yellow]"
        )

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
    behavioral: bool = typer.Option(
        True,
        "--behavioral/--no-behavioral",
        help="Show time-bucketed behavioral patterns (30/60/120 min windows)",
    ),
    overnight: bool = typer.Option(
        True,
        "--overnight/--no-overnight",
        help="Show overnight glucose patterns (10pm–6am window)",
    ),
    anomaly: bool = typer.Option(
        True,
        "--anomaly/--no-anomaly",
        help="Show unusual glucose pattern detection summary",
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
        _run_analysis(file_path, start_date, end_date, exclude_warmup, visualize, compare, insights, behavioral, overnight, anomaly, console)
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
    behavioral: bool = typer.Option(
        True,
        "--behavioral/--no-behavioral",
        help="Show time-bucketed behavioral patterns (30/60/120 min windows)",
    ),
    overnight: bool = typer.Option(
        True,
        "--overnight/--no-overnight",
        help="Show overnight glucose patterns (10pm–6am window)",
    ),
    anomaly: bool = typer.Option(
        True,
        "--anomaly/--no-anomaly",
        help="Show unusual glucose pattern detection summary",
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

        console.print(f"[cyan]Downloading {url}...[/cyan]")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            raw_path = Path(tmp.name)

        tmp_path = raw_path
        try:
            urllib.request.urlretrieve(url, raw_path)
            suffix = _detect_suffix(raw_path, parsed.path)
            tmp_path = raw_path.with_name(raw_path.name + suffix)
            raw_path.rename(tmp_path)
            console.print("[green]Download complete.[/green]\n")
            _run_analysis(tmp_path, start_date, end_date, exclude_warmup, visualize, compare, insights, behavioral, overnight, anomaly, console)
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