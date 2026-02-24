"""Tests for ing_bankstats.parser."""

import pandas as pd
import pytest

from ing_bankstats.parser import parse_csv, _find_header_row


class TestFindHeaderRow:
    def test_finds_row_with_preamble(self, sample_csv_path):
        skip = _find_header_row(sample_csv_path)
        assert skip == 4  # fixture has 4 preamble lines (indices 0-3), header at 4

    def test_raises_on_invalid_file(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_bytes(b"not;an;ing;file\n")
        with pytest.raises(ValueError, match="Buchung"):
            _find_header_row(str(bad))


class TestParseCsv:
    def test_returns_dataframe(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        assert isinstance(df, pd.DataFrame)

    def test_expected_columns(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        for col in ("date", "merchant", "reference", "amount"):
            assert col in df.columns, f"Missing column: {col}"

    def test_currency_columns_dropped(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        assert not any("hrung" in c for c in df.columns), \
            "Währung columns should be dropped"

    def test_date_is_datetime(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_amount_is_float(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        assert pd.api.types.is_float_dtype(df["amount"])

    def test_german_number_parsing(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        # The fixture has a 2500.00 salary entry
        assert 2500.0 in df["amount"].values

    def test_negative_amounts(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        assert (df["amount"] < 0).any(), "Should have negative (expense) rows"

    def test_positive_amounts(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        assert (df["amount"] > 0).any(), "Should have positive (income) rows"

    def test_row_count(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        # Fixture has 12 data rows (2 income + 8 expenses + 2 savings transfers)
        assert len(df) == 12

    def test_no_nan_in_critical_columns(self, sample_csv_path):
        df = parse_csv(sample_csv_path)
        assert df["date"].notna().all()
        assert df["amount"].notna().all()

    def test_template_csv_no_preamble(self):
        """The template CSV at the repo root has no preamble rows."""
        import os
        template = os.path.join(
            os.path.dirname(__file__), "..", "data", "umsatzanzeige.template.csv"
        )
        if not os.path.exists(template):
            pytest.skip("Template CSV not present")
        df = parse_csv(template)
        assert len(df) > 0
