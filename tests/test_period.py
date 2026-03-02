"""Tests for the period expression parser."""

from datetime import date
from unittest.mock import patch

import pytest

from amazon_invoice_dl.period import DateRange, PeriodParseError, parse_period


class TestFullYear:
    def test_single_year(self):
        r = parse_period("2024")
        assert r == DateRange(date(2024, 1, 1), date(2024, 12, 31))

    def test_year_2020(self):
        r = parse_period("2020")
        assert r == DateRange(date(2020, 1, 1), date(2020, 12, 31))

    def test_year_with_whitespace(self):
        r = parse_period("  2024  ")
        assert r == DateRange(date(2024, 1, 1), date(2024, 12, 31))


class TestMonth:
    def test_month_november(self):
        r = parse_period("2024-11")
        assert r == DateRange(date(2024, 11, 1), date(2024, 11, 30))

    def test_month_january(self):
        r = parse_period("2024-01")
        assert r == DateRange(date(2024, 1, 1), date(2024, 1, 31))

    def test_month_february_non_leap(self):
        r = parse_period("2023-02")
        assert r == DateRange(date(2023, 2, 1), date(2023, 2, 28))

    def test_month_february_leap(self):
        r = parse_period("2024-02")
        assert r == DateRange(date(2024, 2, 1), date(2024, 2, 29))

    def test_month_single_digit(self):
        r = parse_period("2024-3")
        assert r == DateRange(date(2024, 3, 1), date(2024, 3, 31))

    def test_month_december(self):
        r = parse_period("2024-12")
        assert r == DateRange(date(2024, 12, 1), date(2024, 12, 31))

    def test_month_invalid_zero(self):
        with pytest.raises(PeriodParseError, match="Invalid month"):
            parse_period("2024-00")

    def test_month_invalid_thirteen(self):
        with pytest.raises(PeriodParseError, match="Invalid month"):
            parse_period("2024-13")


class TestQuarter:
    def test_q1(self):
        r = parse_period("2024Q1")
        assert r == DateRange(date(2024, 1, 1), date(2024, 3, 31))

    def test_q2(self):
        r = parse_period("2024Q2")
        assert r == DateRange(date(2024, 4, 1), date(2024, 6, 30))

    def test_q3(self):
        r = parse_period("2024Q3")
        assert r == DateRange(date(2024, 7, 1), date(2024, 9, 30))

    def test_q4(self):
        r = parse_period("2024Q4")
        assert r == DateRange(date(2024, 10, 1), date(2024, 12, 31))

    def test_lowercase_q(self):
        r = parse_period("2024q3")
        assert r == DateRange(date(2024, 7, 1), date(2024, 9, 30))


class TestHalfYear:
    def test_h1(self):
        r = parse_period("2024H1")
        assert r == DateRange(date(2024, 1, 1), date(2024, 6, 30))

    def test_h2(self):
        r = parse_period("2024H2")
        assert r == DateRange(date(2024, 7, 1), date(2024, 12, 31))

    def test_lowercase_h(self):
        r = parse_period("2024h1")
        assert r == DateRange(date(2024, 1, 1), date(2024, 6, 30))


class TestRange:
    def test_year_range(self):
        r = parse_period("2023..2025")
        assert r == DateRange(date(2023, 1, 1), date(2025, 12, 31))

    def test_month_range(self):
        r = parse_period("2024-06..2024-12")
        assert r == DateRange(date(2024, 6, 1), date(2024, 12, 31))

    def test_mixed_range_year_to_month(self):
        r = parse_period("2023..2024-06")
        assert r == DateRange(date(2023, 1, 1), date(2024, 6, 30))

    def test_mixed_range_month_to_year(self):
        r = parse_period("2023-06..2025")
        assert r == DateRange(date(2023, 6, 1), date(2025, 12, 31))

    def test_same_year_range(self):
        r = parse_period("2024..2024")
        assert r == DateRange(date(2024, 1, 1), date(2024, 12, 31))

    def test_same_month_range(self):
        r = parse_period("2024-06..2024-06")
        assert r == DateRange(date(2024, 6, 1), date(2024, 6, 30))

    def test_range_with_spaces(self):
        r = parse_period(" 2023 .. 2025 ")
        assert r == DateRange(date(2023, 1, 1), date(2025, 12, 31))

    def test_reversed_range_error(self):
        with pytest.raises(PeriodParseError, match="after end date"):
            parse_period("2025..2023")

    def test_empty_start_error(self):
        with pytest.raises(PeriodParseError, match="Invalid range"):
            parse_period("..2024")

    def test_empty_end_error(self):
        with pytest.raises(PeriodParseError, match="Invalid range"):
            parse_period("2024..")


class TestDefault:
    @patch("amazon_invoice_dl.period.date")
    def test_none_returns_current_year(self, mock_date):
        mock_date.today.return_value = date(2026, 3, 2)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        r = parse_period(None)
        assert r == DateRange(date(2026, 1, 1), date(2026, 12, 31))

    @patch("amazon_invoice_dl.period.date")
    def test_empty_string_returns_current_year(self, mock_date):
        mock_date.today.return_value = date(2026, 3, 2)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        r = parse_period("")
        assert r == DateRange(date(2026, 1, 1), date(2026, 12, 31))

    @patch("amazon_invoice_dl.period.date")
    def test_whitespace_only_returns_current_year(self, mock_date):
        mock_date.today.return_value = date(2026, 3, 2)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        r = parse_period("   ")
        assert r == DateRange(date(2026, 1, 1), date(2026, 12, 31))


class TestInvalidExpressions:
    def test_garbage(self):
        with pytest.raises(PeriodParseError):
            parse_period("foobar")

    def test_partial_date(self):
        with pytest.raises(PeriodParseError):
            parse_period("202")

    def test_five_digit_year(self):
        with pytest.raises(PeriodParseError):
            parse_period("20245")

    def test_invalid_quarter(self):
        with pytest.raises(PeriodParseError):
            parse_period("2024Q5")

    def test_invalid_half(self):
        with pytest.raises(PeriodParseError):
            parse_period("2024H3")

    def test_full_date_not_supported(self):
        with pytest.raises(PeriodParseError):
            parse_period("2024-01-15")


class TestDateRangeYears:
    def test_single_year_years(self):
        r = parse_period("2024")
        assert r.years == [2024]

    def test_multi_year_years(self):
        r = parse_period("2022..2025")
        assert r.years == [2022, 2023, 2024, 2025]

    def test_single_month_years(self):
        r = parse_period("2024-06")
        assert r.years == [2024]

    def test_cross_year_month_range(self):
        r = parse_period("2023-11..2024-02")
        assert r.years == [2023, 2024]
