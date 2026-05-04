"""Sugarmate Excel workbook parser.

Handles the multi-sheet .xlsx format exported by Sugarmate, where each sheet
is a single day with a header row followed by timestamped glucose readings.
"""

import logging
from datetime import datetime
from pathlib import Path

import polars as pl

from .parser import Parser, register_parser
from ..models import CGMReading

logger = logging.getLogger(__name__)

# xlsx uses two non-standard heavy arrows; normalize them to the same symbols
# used by the CSV export so the rest of the pipeline sees a uniform set.
_TREND_NORMALIZE = {
    "➚": "↗",  # HEAVY NORTH EAST ARROW → ↗
    "➘": "↘",  # HEAVY SOUTH EAST ARROW → ↘
}
_VALID_TRENDS = {"↑↑", "↑", "↗", "→", "↘", "↓", "↓↓"}


def _parse_timestamp(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@register_parser
class SugarmateXlsxParser(Parser):
    """Parser for Sugarmate multi-sheet Excel exports.

    Each non-Summary sheet is a single day. The header row contains
    'time', 'mg/dL', 'trend', ... and data rows follow immediately after.
    """

    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        if Path(file_path).suffix.lower() != ".xlsx":
            return False
        try:
            import fastexcel  # lazy: only needed for xlsx
            wb = fastexcel.read_excel(file_path)
            return "Summary" in wb.sheet_names and len(wb.sheet_names) > 1
        except Exception:
            return False

    def parse(
        self,
        file_path: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CGMReading]:
        import fastexcel

        wb = fastexcel.read_excel(file_path)
        daily_sheets = [s for s in wb.sheet_names if s != "Summary"]

        readings: list[CGMReading] = []
        skipped_count = 0

        for sheet_name in daily_sheets:
            sheet = wb.load_sheet(sheet_name, header_row=None)
            df = pl.from_arrow(sheet.to_arrow())

            # Locate the header row (col 0 == "time", col 1 == "mg/dL")
            header_idx = None
            for i, row in enumerate(df.iter_rows()):
                if row[0] == "time" and row[1] == "mg/dL":
                    header_idx = i
                    break

            if header_idx is None:
                logger.warning("Sheet '%s': no header row found, skipping", sheet_name)
                continue

            for row in df.slice(header_idx + 1).iter_rows():
                if not row[0] or not row[1]:
                    continue

                ts = _parse_timestamp(str(row[0]))
                if ts is None:
                    logger.warning("Could not parse timestamp: %s", row[0])
                    continue

                try:
                    glucose = float(row[1])
                except (ValueError, TypeError):
                    continue

                if glucose < 40 or glucose > 400:
                    skipped_count += 1
                    continue

                if start_date and ts < start_date:
                    continue
                if end_date and ts > end_date:
                    continue

                raw_trend = str(row[2]) if len(row) > 2 and row[2] else None
                trend: str | None = None
                if raw_trend:
                    normalized = _TREND_NORMALIZE.get(raw_trend, raw_trend)
                    trend = normalized if normalized in _VALID_TRENDS else None

                readings.append(
                    CGMReading(
                        timestamp=ts,
                        glucose_mg_dl=glucose,
                        trend=trend,
                        source="sugarmate",
                    )
                )

        if skipped_count:
            logger.warning(
                "Skipped %d reading(s) outside physiological range (40-400 mg/dL)",
                skipped_count,
            )

        return sorted(readings, key=lambda r: r.timestamp)
