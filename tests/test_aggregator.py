"""Tests for ing_bankstats.aggregator."""

import pandas as pd
import pytest

from ing_bankstats.aggregator import aggregate, _category_types, AggregationResult


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
                    "2025-01-25",
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
                "Trade Republic",
                "Arbeitgeber",
                "EDEKA",
                "Zahnarzt",
            ],
            "reference": ["Gehalt", "Einkauf", "Abo", "Rechnung", "Sparplan", "Gehalt", "Einkauf", "Behandlung"],
            "amount": [2500.0, -50.0, -14.50, -40.0, -200.0, 2500.0, -50.0, -100.0],
            "category": ["income", "food", "entertainment", "utilities", "investment", "income", "food", "health"],
        }
    )


@pytest.fixture
def config_with_types():
    """Config with investment type annotations."""
    return {
        "categories": {
            "income": {"color": "#2ecc71"},
            "food": {"color": "#e67e22"},
            "entertainment": {"color": "#f39c12"},
            "utilities": {"color": "#1abc9c"},
            "health": {"color": "#e74c3c"},
            "investment": {"color": "#2980b9", "type": "investment"},
            "mortgage": {"color": "#8e44ad", "type": "investment"},
            "savings": {"color": "#00b894", "type": "investment"},
        }
    }


class TestAggregate:
    def test_returns_aggregation_result(self, categorised_df):
        result = aggregate(categorised_df)
        assert isinstance(result, AggregationResult)

    def test_monthly_summary_columns(self, categorised_df):
        result = aggregate(categorised_df)
        assert set(result.monthly_summary.columns) == {"income", "expenses", "savings"}

    def test_monthly_summary_two_months(self, categorised_df):
        result = aggregate(categorised_df)
        assert len(result.monthly_summary) == 2

    def test_january_income(self, categorised_df):
        result = aggregate(categorised_df)
        jan = result.monthly_summary.loc[pd.Period("2025-01", "M")]
        assert jan["income"] == pytest.approx(2500.0)

    def test_january_expenses(self, categorised_df):
        result = aggregate(categorised_df)
        jan = result.monthly_summary.loc[pd.Period("2025-01", "M")]
        assert jan["expenses"] == pytest.approx(304.50)

    def test_savings_is_income_minus_expenses(self, categorised_df):
        result = aggregate(categorised_df)
        for _, row in result.monthly_summary.iterrows():
            assert row["savings"] == pytest.approx(row["income"] - row["expenses"])

    def test_monthly_by_category_is_dataframe(self, categorised_df):
        result = aggregate(categorised_df)
        assert isinstance(result.monthly_by_category, pd.DataFrame)

    def test_monthly_by_category_has_expense_categories(self, categorised_df):
        result = aggregate(categorised_df)
        assert "food" in result.monthly_by_category.columns

    def test_monthly_by_category_positive_values(self, categorised_df):
        result = aggregate(categorised_df)
        assert (result.monthly_by_category >= 0).all().all()

    def test_category_totals_is_series(self, categorised_df):
        result = aggregate(categorised_df)
        assert isinstance(result.category_totals, pd.Series)

    def test_category_totals_food(self, categorised_df):
        result = aggregate(categorised_df)
        assert result.category_totals.get("food", 0) == pytest.approx(100.0)

    def test_stats_keys(self, categorised_df):
        result = aggregate(categorised_df)
        for key in (
            "date_from", "date_to", "months_count", "transaction_count",
            "total_income", "total_expenses", "net", "avg_monthly_income",
            "avg_monthly_expenses", "uncategorised_count",
        ):
            assert key in result.stats, f"Missing stats key: {key}"

    def test_stats_total_income(self, categorised_df):
        result = aggregate(categorised_df)
        assert result.stats["total_income"] == pytest.approx(5000.0)

    def test_stats_total_expenses(self, categorised_df):
        result = aggregate(categorised_df)
        assert result.stats["total_expenses"] == pytest.approx(454.50)

    def test_stats_net(self, categorised_df):
        result = aggregate(categorised_df)
        assert result.stats["net"] == pytest.approx(5000.0 - 454.50)

    def test_stats_months_count(self, categorised_df):
        result = aggregate(categorised_df)
        assert result.stats["months_count"] == 2

    def test_stats_uncategorised_count(self, categorised_df):
        result = aggregate(categorised_df)
        assert result.stats["uncategorised_count"] == 0


class TestCategoryAverages:
    def test_avg_expenses_has_categories(self, categorised_df):
        result = aggregate(categorised_df)
        assert len(result.avg_expenses) == 5  # food, investment, entertainment, utilities, health

    def test_avg_income_has_categories(self, categorised_df):
        result = aggregate(categorised_df)
        assert len(result.avg_income) == 1  # income

    def test_avg_expenses_overall_food(self, categorised_df):
        # food: total 100 over 2 months = 50/month
        result = aggregate(categorised_df)
        food_row = result.avg_expenses[result.avg_expenses["category"] == "food"].iloc[0]
        assert food_row["overall"] == pytest.approx(50.0)

    def test_avg_expenses_overall_entertainment(self, categorised_df):
        # entertainment: total 14.50 over 2 months = 7.25/month
        result = aggregate(categorised_df)
        ent_row = result.avg_expenses[result.avg_expenses["category"] == "entertainment"].iloc[0]
        assert ent_row["overall"] == pytest.approx(7.25)

    def test_avg_income_overall(self, categorised_df):
        # income: total 5000 over 2 months = 2500/month
        result = aggregate(categorised_df)
        inc_row = result.avg_income[result.avg_income["category"] == "income"].iloc[0]
        assert inc_row["overall"] == pytest.approx(2500.0)

    def test_avg_expenses_sorted_descending(self, categorised_df):
        result = aggregate(categorised_df)
        overall_vals = result.avg_expenses["overall"].tolist()
        assert overall_vals == sorted(overall_vals, reverse=True)

    def test_avg_expenses_year_column(self, categorised_df):
        result = aggregate(categorised_df)
        assert 2025 in result.avg_expenses.columns

    def test_multi_year_data(self):
        """Per-year averages are computed correctly with multi-year data."""
        df = pd.DataFrame({
            "date": pd.to_datetime([
                "2024-03-01", "2024-06-01",
                "2025-01-10", "2025-02-10", "2025-03-10",
            ]),
            "amount": [-120.0, -60.0, -90.0, -90.0, -90.0],
            "category": ["food", "food", "food", "food", "food"],
        })
        result = aggregate(df)
        food = result.avg_expenses[result.avg_expenses["category"] == "food"].iloc[0]
        # 2024: 180 total over 2 months = 90/month
        assert food[2024] == pytest.approx(90.0)
        # 2025: 270 total over 3 months = 90/month
        assert food[2025] == pytest.approx(90.0)
        # overall: 450 total over 5 months = 90/month
        assert food["overall"] == pytest.approx(90.0)


class TestCategoryTypes:
    def test_returns_types_from_config(self):
        config = {
            "categories": {
                "food": {"color": "#e67e22"},
                "mortgage": {"color": "#8e44ad", "type": "investment"},
                "savings": {"color": "#00b894", "type": "investment"},
            }
        }
        types = _category_types(config)
        assert types["food"] == "consumption"
        assert types["mortgage"] == "investment"
        assert types["savings"] == "investment"

    def test_returns_empty_dict_without_config(self):
        assert _category_types(None) == {}

    def test_defaults_to_consumption(self):
        config = {"categories": {"food": {"color": "#e67e22"}}}
        types = _category_types(config)
        assert types["food"] == "consumption"


class TestConsumptionInvestmentSplit:
    def test_stats_keys_exist(self, categorised_df, config_with_types):
        result = aggregate(categorised_df, config_with_types)
        for key in (
            "total_consumption", "total_investment",
            "avg_monthly_consumption", "avg_monthly_investment",
        ):
            assert key in result.stats, f"Missing stats key: {key}"

    def test_consumption_plus_investment_equals_total(self, categorised_df, config_with_types):
        result = aggregate(categorised_df, config_with_types)
        assert result.stats["total_consumption"] + result.stats["total_investment"] == pytest.approx(result.stats["total_expenses"])

    def test_total_consumption_value(self, categorised_df, config_with_types):
        # consumption: food(100) + entertainment(14.50) + utilities(40) + health(100) = 254.50
        result = aggregate(categorised_df, config_with_types)
        assert result.stats["total_consumption"] == pytest.approx(254.50)

    def test_total_investment_value(self, categorised_df, config_with_types):
        # investment: 200
        result = aggregate(categorised_df, config_with_types)
        assert result.stats["total_investment"] == pytest.approx(200.0)

    def test_avg_monthly_consumption(self, categorised_df, config_with_types):
        # Jan consumption: 50+14.50+40 = 104.50, Feb consumption: 50+100 = 150
        # avg = (104.50 + 150) / 2 = 127.25
        result = aggregate(categorised_df, config_with_types)
        assert result.stats["avg_monthly_consumption"] == pytest.approx(127.25)

    def test_avg_monthly_investment(self, categorised_df, config_with_types):
        # Jan investment: 200, Feb investment: 0 — but Feb has no investment transactions
        # so only 1 month with investment data, avg = 200/1 = 200
        result = aggregate(categorised_df, config_with_types)
        assert result.stats["avg_monthly_investment"] == pytest.approx(200.0)

    def test_defaults_to_consumption_without_config(self, categorised_df):
        # Without config, all categories default to consumption
        result = aggregate(categorised_df)
        assert result.stats["total_consumption"] == pytest.approx(result.stats["total_expenses"])
        assert result.stats["total_investment"] == pytest.approx(0.0)
