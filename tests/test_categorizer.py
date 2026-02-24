"""Tests for ing_bankstats.categorizer."""

import pandas as pd
import pytest

from ing_bankstats.categorizer import categorise, load_config


@pytest.fixture
def config():
    return load_config()  # bundled default


@pytest.fixture
def simple_df():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-10", "2025-01-15", "2025-01-20"]),
            "merchant": ["REWE Markt GmbH", "Netflix International", "Unknown Corp"],
            "reference": ["Einkauf", "Netflix Abo", "Diverse"],
            "amount": [-50.0, -14.50, -20.0],
        }
    )


class TestLoadConfig:
    def test_returns_dict(self, config):
        assert isinstance(config, dict)

    def test_has_categories_key(self, config):
        assert "categories" in config

    def test_income_category_present(self, config):
        assert "income" in config["categories"]

    def test_other_category_present(self, config):
        assert "other" in config["categories"]


class TestCategorise:
    def test_returns_dataframe_with_category_column(self, simple_df, config):
        result = categorise(simple_df, config)
        assert "category" in result.columns

    def test_rewe_categorised_as_food(self, simple_df, config):
        result = categorise(simple_df, config)
        rewe_row = result[result["merchant"].str.contains("REWE")]
        assert rewe_row["category"].iloc[0] == "food"

    def test_netflix_categorised_as_entertainment(self, simple_df, config):
        result = categorise(simple_df, config)
        netflix_row = result[result["merchant"].str.contains("Netflix")]
        assert netflix_row["category"].iloc[0] == "entertainment"

    def test_unknown_falls_back_to_other(self, simple_df, config):
        result = categorise(simple_df, config)
        unknown_row = result[result["merchant"] == "Unknown Corp"]
        assert unknown_row["category"].iloc[0] == "other"

    def test_income_keyword_in_reference(self, config):
        df = pd.DataFrame(
            {
                "merchant": ["Arbeitgeber GmbH"],
                "reference": ["Lohn/Gehalt Januar 2025"],
                "amount": [2500.0],
                "date": pd.to_datetime(["2025-01-05"]),
            }
        )
        result = categorise(df, config)
        assert result["category"].iloc[0] == "income"

    def test_case_insensitive_matching(self, config):
        df = pd.DataFrame(
            {
                "merchant": ["LIDL SAGT DANKE"],
                "reference": ["EINKAUF"],
                "amount": [-30.0],
                "date": pd.to_datetime(["2025-01-10"]),
            }
        )
        result = categorise(df, config)
        assert result["category"].iloc[0] == "food"

    def test_does_not_mutate_input(self, simple_df, config):
        original_cols = list(simple_df.columns)
        categorise(simple_df, config)
        assert list(simple_df.columns) == original_cols
        assert "category" not in simple_df.columns

    def test_search_text_column_removed(self, simple_df, config):
        result = categorise(simple_df, config)
        assert "search_text" not in result.columns

    def test_income_priority_over_other(self, config):
        """Income category should win because it sits at the top of the YAML."""
        df = pd.DataFrame(
            {
                "merchant": ["Finanzamt Hamburg"],
                "reference": ["Steuererstattung 2024"],
                "amount": [500.0],
                "date": pd.to_datetime(["2025-02-01"]),
            }
        )
        result = categorise(df, config)
        # "steuererstattung" is in income keywords
        assert result["category"].iloc[0] == "income"
