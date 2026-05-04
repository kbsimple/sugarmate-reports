"""Sugarmate CSV parser implementation."""

from datetime import datetime
from pathlib import Path

import polars as pl

from .parser import Parser, register_parser
from ..models import CGMReading


@register_parser
class SugarmateParser(Parser):
    """Parser for Sugarmate CSV exports.

    Handles the CSV format exported from Sugarmate with columns:
    - date: Date only (YYYY-MM-DD)
    - datetime: Full datetime (YYYY-MM-DD HH:MM)
    - time: Time only (HH:MM)
    - mg_dl: Glucose value in mg/dL
    - trend: Trend arrow (Unicode character)
    """

    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        """Return True only for Sugarmate CSV files (detected by header columns).

        Reads only the header row to confirm presence of the required
        'datetime' and 'mg_dl' columns that Sugarmate exports produce.
        """
        if Path(file_path).suffix.lower() != ".csv":
            return False
        try:
            header_df = pl.read_csv(file_path, n_rows=0)
            return "datetime" in header_df.columns and "mg_dl" in header_df.columns
        except Exception:
            return False

    def parse(
        self,
        file_path: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CGMReading]:
        """Parse Sugarmate CSV file.

        Args:
            file_path: Path to CSV file
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of CGMReading objects sorted by timestamp
        """
        # Read CSV with Polars
        df = pl.read_csv(file_path)

        # Validate required columns
        required_columns = ["datetime", "mg_dl"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Parse datetime column
        df = df.with_columns(
            pl.col("datetime")
            .str.to_datetime("%Y-%m-%d %H:%M")
            .alias("timestamp")
        )

        # Filter by date range if provided
        try:
            if start_date:
                df = df.filter(pl.col("timestamp") >= start_date)
            if end_date:
                df = df.filter(pl.col("timestamp") <= end_date)
        except Exception as e:
            raise ValueError(
                f"Date filter failed (check timezone consistency): {e}"
            ) from e

        # Filter out-of-range glucose values in Polars (vectorized, avoids Python loop overhead)
        original_count = len(df)
        df = df.filter(pl.col("mg_dl").cast(pl.Float64).is_between(40, 400))
        skipped_count = original_count - len(df)

        # Normalize trend arrows in Polars (vectorized)
        valid_trends = ["↑↑", "↑", "↗", "→", "↘", "↓", "↓↓"]
        if "trend" in df.columns:
            df = df.with_columns(
                pl.when(pl.col("trend").is_in(valid_trends))
                .then(pl.col("trend"))
                .otherwise(None)
                .alias("trend")
            )

        # Sort by timestamp
        df = df.sort("timestamp")

        # Build CGMReading objects — object construction requires Python loop
        readings = [
            CGMReading(
                timestamp=row["timestamp"],
                glucose_mg_dl=float(row["mg_dl"]),
                trend=row.get("trend") if "trend" in df.columns else None,
                source="sugarmate",
            )
            for row in df.iter_rows(named=True)
        ]

        if skipped_count:
            import logging
            logging.getLogger(__name__).warning(
                "Skipped %d reading(s) outside physiological range (40–400 mg/dL)",
                skipped_count,
            )

        return readings