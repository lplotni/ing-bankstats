"""Tests for ing_bankstats.report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ing_bankstats.report import (
    TabData,
    _filter_to_month,
    _build_tab_data,
    generate_report,
)


@pytest.fixture
def two_month_df():
    """DataFrame spanning January and February 2025."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime([
                "2025-01-05", "2025-01-15", "2025-01-20",
                "2025-02-05", "2025-02-12",
            ]),
            "merchant": ["Employer", "REWE", "Netflix", "Employer", "EDEKA"],
            "reference": ["Salary", "Shopping", "Sub", "Salary", "Shopping"],
            "amount": [2500.0, -50.0, -14.50, 2500.0, -50.0],
            "category": ["income", "groceries", "entertainment", "income", "groceries"],
        }
    )


@pytest.fixture
def config():
    return {
        "categories": {
            "income": {"color": "#2ecc71"},
            "groceries": {"color": "#e67e22", "budget_bucket": "needs"},
            "entertainment": {"color": "#f39c12", "budget_bucket": "wants"},
        }
    }


@pytest.fixture
def colors(config):
    return {
        cat: cfg.get("color", "#95a5a6")
        for cat, cfg in config["categories"].items()
    }


class TestFilterToMonth:
    def test_returns_correct_subset(self, two_month_df):
        jan = _filter_to_month(two_month_df, 2025, 1)
        assert len(jan) == 3
        assert all(jan["date"].dt.month == 1)

    def test_returns_empty_for_missing_month(self, two_month_df):
        result = _filter_to_month(two_month_df, 2025, 12)
        assert result.empty

    def test_returns_copy(self, two_month_df):
        jan = _filter_to_month(two_month_df, 2025, 1)
        jan["amount"] = 0
        # Original should be unchanged
        assert two_month_df["amount"].iloc[0] == 2500.0


class TestBuildTabData:
    def test_empty_df_returns_no_data(self, config, colors):
        empty_df = pd.DataFrame(columns=["date", "amount", "category", "merchant", "reference"])
        tab = _build_tab_data(empty_df, config, colors, "Empty", "empty")
        assert tab.has_data is False
        assert tab.label == "Empty"
        assert tab.tab_id == "empty"

    def test_valid_df_returns_has_data(self, two_month_df, config, colors):
        tab = _build_tab_data(two_month_df, config, colors, "All", "all")
        assert tab.has_data is True
        assert tab.stats["total_income"] == pytest.approx(5000.0)

    def test_charts_are_non_empty(self, two_month_df, config, colors):
        tab = _build_tab_data(two_month_df, config, colors, "All", "all")
        assert len(tab.chart_income_expenses) > 0
        assert len(tab.chart_savings) > 0

    def test_tab_data_fields(self, two_month_df, config, colors):
        tab = _build_tab_data(two_month_df, config, colors, "Test", "test")
        assert isinstance(tab, TabData)
        assert tab.label == "Test"
        assert tab.tab_id == "test"


class TestGenerateReport:
    def test_html_contains_all_plus_monthly_tabs(self, two_month_df, config, tmp_path):
        out = tmp_path / "report.html"
        generate_report(two_month_df, out, config)
        html = out.read_text(encoding="utf-8")
        # "All" tab + 12 monthly tabs = 13 tab buttons
        assert html.count("tab-btn") >= 13

    def test_html_contains_tab_content_divs(self, two_month_df, config, tmp_path):
        out = tmp_path / "report.html"
        generate_report(two_month_df, out, config)
        html = out.read_text(encoding="utf-8")
        assert 'id="tab-all"' in html
        # Monthly tabs use m-YYYY-MM format
        assert 'id="tab-m-2025-02"' in html
        assert 'id="tab-m-2025-01"' in html

    def test_html_contains_switch_tab_js(self, two_month_df, config, tmp_path):
        out = tmp_path / "report.html"
        generate_report(two_month_df, out, config)
        html = out.read_text(encoding="utf-8")
        assert "switchTab" in html

    def test_html_contains_financial_health_section(self, two_month_df, config, tmp_path):
        out = tmp_path / "report.html"
        generate_report(two_month_df, out, config)
        html = out.read_text(encoding="utf-8")
        assert "Financial Health" in html
        assert "Savings Rate" in html
        assert "fh-section" in html

    def test_benchmarks_on_tab_data(self, two_month_df, config, colors):
        tab = _build_tab_data(two_month_df, config, colors, "All", "all")
        assert tab.benchmarks
        assert "savings_rate" in tab.benchmarks
        assert "needs_pct" in tab.benchmarks

    def test_empty_month_shows_no_data_message(self, config, tmp_path):
        # Only January data — other monthly tabs should show "No transactions"
        df = pd.DataFrame({
            "date": pd.to_datetime(["2025-01-05", "2025-01-15"]),
            "merchant": ["Employer", "REWE"],
            "reference": ["Salary", "Shopping"],
            "amount": [2500.0, -50.0],
            "category": ["income", "groceries"],
        })
        out = tmp_path / "report.html"
        generate_report(df, out, config)
        html = out.read_text(encoding="utf-8")
        assert "No transactions found for this period" in html
