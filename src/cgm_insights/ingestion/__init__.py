"""Data ingestion module - parsers, validators, normalizers."""

from .parser import Parser, PARSERS, register_parser, get_parser
from .sugarmate import SugarmateParser
from .sugarmate_xlsx import SugarmateXlsxParser
from .validator import (
    validate_completeness,
    detect_sensor_warmup,
    filter_by_date_range,
    exclude_warmup_period,
    MIN_COMPLETENESS_PCT,
    STANDARD_INTERVAL_MINUTES,
    GAP_THRESHOLD_MINUTES,
    SENSOR_WARMUP_HOURS,
)
from .normalizer import normalize_for_glucostats, to_glucostats_dataframe

__all__ = [
    # Parser
    "Parser",
    "PARSERS",
    "register_parser",
    "get_parser",
    "SugarmateParser",
    "SugarmateXlsxParser",
    # Validator
    "validate_completeness",
    "detect_sensor_warmup",
    "filter_by_date_range",
    "exclude_warmup_period",
    "MIN_COMPLETENESS_PCT",
    "STANDARD_INTERVAL_MINUTES",
    "GAP_THRESHOLD_MINUTES",
    "SENSOR_WARMUP_HOURS",
    # Normalizer
    "normalize_for_glucostats",
    "to_glucostats_dataframe",
]