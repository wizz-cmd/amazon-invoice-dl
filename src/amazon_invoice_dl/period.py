"""
Period expression parser inspired by hledger.

Supported formats:
    YYYY          → full year (Jan 1 to Dec 31)
    YYYY-MM       → single month (first to last day)
    YYYYQN        → quarter (N=1-4)
    YYYYHN        → half year (N=1-2)
    FROM..TO      → range (both inclusive, each can be YYYY or YYYY-MM)
    (empty)       → current year
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DateRange:
    """Inclusive date range."""

    start: date
    end: date

    @property
    def years(self) -> list[int]:
        """Return list of years covered by this range."""
        return list(range(self.start.year, self.end.year + 1))


class PeriodParseError(ValueError):
    """Raised when a period expression cannot be parsed."""


def _last_day_of_month(year: int, month: int) -> int:
    """Return the last day of the given month."""
    return calendar.monthrange(year, month)[1]


def _parse_single(expr: str) -> DateRange:
    """Parse a single period expression (not a range)."""
    expr = expr.strip()

    # YYYY — full year
    m = re.fullmatch(r"(\d{4})", expr)
    if m:
        year = int(m.group(1))
        return DateRange(date(year, 1, 1), date(year, 12, 31))

    # YYYY-MM — single month
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", expr)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if not 1 <= month <= 12:
            raise PeriodParseError(f"Invalid month: {month}")
        last_day = _last_day_of_month(year, month)
        return DateRange(date(year, month, 1), date(year, month, last_day))

    # YYYYQN — quarter
    m = re.fullmatch(r"(\d{4})[Qq]([1-4])", expr)
    if m:
        year, q = int(m.group(1)), int(m.group(2))
        start_month = (q - 1) * 3 + 1
        end_month = start_month + 2
        last_day = _last_day_of_month(year, end_month)
        return DateRange(date(year, start_month, 1), date(year, end_month, last_day))

    # YYYYHN — half year
    m = re.fullmatch(r"(\d{4})[Hh]([1-2])", expr)
    if m:
        year, h = int(m.group(1)), int(m.group(2))
        if h == 1:
            return DateRange(date(year, 1, 1), date(year, 6, 30))
        else:
            return DateRange(date(year, 7, 1), date(year, 12, 31))

    raise PeriodParseError(
        f"Cannot parse period expression: {expr!r}\n"
        "Expected: YYYY, YYYY-MM, YYYYQN, YYYYHN, or FROM..TO"
    )


def parse_period(expr: str | None) -> DateRange:
    """Parse a period expression and return an inclusive DateRange.

    Args:
        expr: Period expression string, or None for current year.

    Returns:
        DateRange with start and end dates.

    Raises:
        PeriodParseError: If the expression cannot be parsed.
    """
    if not expr or not expr.strip():
        year = date.today().year
        return DateRange(date(year, 1, 1), date(year, 12, 31))

    expr = expr.strip()

    # Range: FROM..TO
    if ".." in expr:
        parts = expr.split("..", 1)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise PeriodParseError(
                f"Invalid range expression: {expr!r}\n"
                "Expected: FROM..TO (e.g. 2023..2025 or 2024-06..2024-12)"
            )
        start_range = _parse_single(parts[0])
        end_range = _parse_single(parts[1])
        if start_range.start > end_range.end:
            raise PeriodParseError(
                f"Start date {start_range.start} is after end date {end_range.end}"
            )
        return DateRange(start_range.start, end_range.end)

    return _parse_single(expr)
