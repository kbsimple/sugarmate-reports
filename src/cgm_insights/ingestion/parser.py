"""Abstract base class for CGM data parsers."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Type

from ..models import CGMReading


class Parser(ABC):
    """Abstract base class for CGM data parsers.

    Parsers transform various CGM export formats into a normalized
    list of CGMReading objects. Subclasses implement format-specific
    parsing logic.
    """

    @classmethod
    @abstractmethod
    def can_parse(cls, file_path: str) -> bool:
        """Return True if this parser handles the given file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if this parser can handle the file format
        """
        pass

    @abstractmethod
    def parse(
        self,
        file_path: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[CGMReading]:
        """Parse file and return normalized CGM readings.

        Args:
            file_path: Path to the file to parse
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)

        Returns:
            List of CGMReading objects in chronological order

        Raises:
            ValueError: If file cannot be parsed or data is invalid
        """
        pass


# Registry of available parsers
PARSERS: list[Type[Parser]] = []


def register_parser(parser_cls: Type[Parser]) -> Type[Parser]:
    """Register a parser class for auto-discovery.

    Args:
        parser_cls: Parser class to register

    Returns:
        The same parser class (for use as decorator)
    """
    PARSERS.append(parser_cls)
    return parser_cls


def get_parser(file_path: str) -> Parser:
    """Get appropriate parser for file type.

    Args:
        file_path: Path to the file

    Returns:
        Parser instance for the file type

    Raises:
        ValueError: If no parser found for file type
    """
    for parser_cls in PARSERS:
        if parser_cls.can_parse(file_path):
            return parser_cls()
    raise ValueError(f"No parser found for {file_path}")