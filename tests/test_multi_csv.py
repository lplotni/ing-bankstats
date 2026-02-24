"""Tests for multi-CSV merge and transfer cancellation."""

import pandas as pd

from ing_bankstats.parser import parse_csv


class TestMultiCsvMerge:
    def test_concat_two_csvs(self, sample_csv_path, savings_csv_path):
        df1 = parse_csv(sample_csv_path)
        df2 = parse_csv(savings_csv_path)
        merged = pd.concat([df1, df2], ignore_index=True)
        assert len(merged) == len(df1) + len(df2)

    def test_savings_transfers_cancel_out(self, sample_csv_path, savings_csv_path):
        """Matching transfers between checking and savings should sum to zero."""
        df1 = parse_csv(sample_csv_path)
        df2 = parse_csv(savings_csv_path)
        merged = pd.concat([df1, df2], ignore_index=True)

        # Filter to savings-related transactions (keyword: "Sparen")
        savings_mask = merged["reference"].str.contains("Sparen", case=False, na=False)
        savings_total = merged.loc[savings_mask, "amount"].sum()
        assert savings_total == pytest.approx(0.0), (
            f"Savings transfers should cancel out across accounts, got {savings_total}"
        )


import pytest
