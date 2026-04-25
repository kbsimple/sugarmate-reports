"""Data ingestion module - parsers, validators, normalizers."""

from .parser import Parser, PARSERS, register_parser, get_parser
from .sugarmate import SugarmateParser

__all__ = [
    "Parser",
    "PARSERS",
    "register_parser",
    "get_parser",
    "SugarmateParser",
]