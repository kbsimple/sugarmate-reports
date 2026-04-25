"""CLI entry point for CGM Insights using Typer.

This module provides the command-line interface for analyzing CGM data.
"""

from pathlib import Path
from typing import Optional

import typer

from cgm_insights import analyze_file, format_summary, format_quality_flags, GMI_CAVEAT

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
) -> None:
    """Analyze CGM data from file and display metrics.

    This command reads CGM data from a file, calculates glucose metrics
    including time-in-range, average glucose, GMI, and variability metrics,
    then displays the results as formatted text output.

    Examples:
        cgm-insights analyze readings.csv
        cgm-insights analyze readings.csv --start 2024-01-01 --end 2024-01-31
        cgm-insights analyze readings.csv --include-warmup
    """
    try:
        # Run analysis using the core library
        results = analyze_file(
            str(file_path),
            start_date=start_date,
            end_date=end_date,
            exclude_warmup=exclude_warmup,
        )

        # Format and display results
        summary = format_summary(results)
        typer.echo(summary)

        # Display quality flags if present
        if results.data_quality_flags:
            typer.echo("")
            typer.echo("Quality Flags:")
            formatted_flags = format_quality_flags(results.data_quality_flags)
            for flag_info in formatted_flags:
                typer.echo(f"  - {flag_info['message']}")

        # Display GMI caveat
        typer.echo("")
        typer.echo(f"Note: {GMI_CAVEAT}")

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()