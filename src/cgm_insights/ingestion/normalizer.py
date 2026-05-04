"""Data normalization for GlucoStats integration."""

from datetime import datetime

import polars as pl

from ..models import CGMReading


def normalize_for_glucostats(
    readings: list[CGMReading],
    exclude_warmup: bool = True,
) -> pl.DataFrame:
    """Convert CGM readings to GlucoStats-compatible format.

    GlucoStats expects a pandas DataFrame with columns:
    - time: datetime
    - glucose: float (mg/dL)

    Args:
        readings: List of CGMReading objects
        exclude_warmup: Whether to exclude sensor warmup period

    Returns:
        Polars DataFrame with normalized data
    """
    if not readings:
        return pl.DataFrame({"time": [], "glucose": []})

    # Convert to Polars DataFrame
    data = {
        "time": [r.timestamp for r in readings],
        "glucose": [r.glucose_mg_dl for r in readings],
    }
    df = pl.DataFrame(data)

    # Sort by time
    df = df.sort("time")

    return df


def to_glucostats_dataframe(df: pl.DataFrame) -> "pd.DataFrame":
    """Convert Polars DataFrame to pandas for GlucoStats.

    GlucoStats requires pandas DataFrame with specific column names.
    pandas is imported lazily so it is only required when this function
    is actually called (optional dependency).

    Args:
        df: Polars DataFrame with 'time' and 'glucose' columns

    Returns:
        pandas DataFrame compatible with GlucoStats
    """
    import pandas as pd  # Lazy import: only required if GlucoStats is used

    pandas_df = df.to_pandas()

    # Ensure time column is datetime
    if "time" in pandas_df.columns:
        pandas_df["time"] = pd.to_datetime(pandas_df["time"], errors="coerce")

    # Ensure glucose column is float
    if "glucose" in pandas_df.columns:
        pandas_df["glucose"] = pandas_df["glucose"].astype(float)

    return pandas_df