"""Tests for ing_bankstats.aggregator."""

import pandas as pd
import pytest

from ing_bankstats.aggregator import aggregate


@pytest.fixture
def categorised_df():
    """Small two-month categorised DataFrame for aggregation tests."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2025-01-05",
                    "2025-01-10",
                    "2025-01-15",
                    "2025-01-20",
                    "2025-02-05",
                    "2025-02-08",
                    "2025-02-12",
                ]
            ),
            "merchant": [
                "Arbeitgeber",
                "REWE",
                "Netflix",
                "Telekom",
                "Arbeitgeber",
                "EDEKA",
                "Zahnarzt",
            ],
            "reference": ["Gehalt", "Einkauf", "Abo", "Rechnung", "Gehalt", "Einkauf", "Behandlung"],
            "amount": [2500.0, -50.0, -14.50, -40.0, 2500.0, -50.0, -100.0],
            "category": ["income", "food", "entertainment", "utilities", "income", "food", "health"],
        }
    )


class TestAggregate:
    def test_returns_four_values(self, categorised_df):
        result = aggregate(categorised_df)
        assert len(result) == 4

    def test_monthly_summary_columns(self, categorised_df):
        monthly_summary, _, _, _ = aggregate(categorised_df)
        assert set(monthly_summary.columns) == {"income", "expenses", "savings"}

    def test_monthly_summary_two_months(self, categorised_df):
        monthly_summary, _, _, _ = aggregate(categorised_df)
        assert len(monthly_summary) == 2

    def test_january_income(self, categorised_df):
        monthly_summary, _, _, _ = aggregate(categorised_df)
        jan = monthly_summary.loc[pd.Period("2025-01", "M")]
        assert jan["income"] == pytest.approx(2500.0)

    def test_january_expenses(self, categorised_df):
        monthly_summary, _, _, _ = aggregate(categorised_df)
        jan = monthly_summary.loc[pd.Period("2025-01", "M")]
        assert jan["expenses"] == pytest.approx(104.50)

    def test_savings_is_income_minus_expenses(self, categorised_df):
        monthly_summary, _, _, _ = aggregate(categorised_df)
        for _, row in monthly_summary.iterrows():
            assert row["savings"] == pytest.approx(row["income"] - row["expenses"])

    def test_monthly_by_category_is_dataframe(self, categorised_df):
        _, monthly_by_category, _, _ = aggregate(categorised_df)
        assert isinstance(monthly_by_category, pd.DataFrame)

    def test_monthly_by_category_has_expense_categories(self, categorised_df):
        _, monthly_by_category, _, _ = aggregate(categorised_df)
        assert "food" in monthly_by_category.columns

    def test_monthly_by_category_positive_values(self, categorised_df):
        _, monthly_by_category, _, _ = aggregate(categorised_df)
        assert (monthly_by_category >= 0).all().all()

    def test_category_totals_is_series(self, categorised_df):
        _, _, category_totals, _ = aggregate(categorised_df)
        assert isinstance(category_totals, pd.Series)

    def test_category_totals_food(self, categorised_df):
        _, _, category_totals, _ = aggregate(categorised_df)
        assert category_totals.get("food", 0) == pytest.approx(100.0)

    def test_stats_keys(self, categorised_df):
        _, _, _, stats = aggregate(categorised_df)
        for key in (
            "date_from", "date_to", "months_count", "transaction_count",
            "total_income", "total_expenses", "net", "avg_monthly_income",
            "avg_monthly_expenses", "uncategorised_count",
        ):
            assert key in stats, f"Missing stats key: {key}"

    def test_stats_total_income(self, categorised_df):
        _, _, _, stats = aggregate(categorised_df)
        assert stats["total_income"] == pytest.approx(5000.0)

    def test_stats_total_expenses(self, categorised_df):
        _, _, _, stats = aggregate(categorised_df)
        assert stats["total_expenses"] == pytest.approx(254.50)

    def test_stats_net(self, categorised_df):
        _, _, _, stats = aggregate(categorised_df)
        assert stats["net"] == pytest.approx(5000.0 - 254.50)

    def test_stats_months_count(self, categorised_df):
        _, _, _, stats = aggregate(categorised_df)
        assert stats["months_count"] == 2

    def test_stats_uncategorised_count(self, categorised_df):
        _, _, _, stats = aggregate(categorised_df)
        assert stats["uncategorised_count"] == 0
