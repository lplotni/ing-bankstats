"""Assemble the self-contained HTML report."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import plotly.offline
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from . import aggregator, charts

_ASSETS_DIR = Path(__file__).parent / "assets"


@dataclass
class TabData:
    """Data for a single report tab."""

    label: str
    tab_id: str
    stats: dict = field(default_factory=dict)
    chart_income_expenses: str = ""
    chart_spending_by_category: str = ""
    chart_category_pie: str = ""
    chart_savings: str = ""
    other_transactions: list[dict] = field(default_factory=list)
    avg_expense_categories: list[dict] = field(default_factory=list)
    avg_income_categories: list[dict] = field(default_factory=list)
    avg_years: list[str] = field(default_factory=list)
    category_transactions: list[dict] = field(default_factory=list)
    benchmarks: dict = field(default_factory=dict)
    has_data: bool = False


def _fmt_eur(value: float) -> str:
    return f"€{value:,.2f}"


def _filter_to_month(
    df: pd.DataFrame, year: int, month: int,
) -> pd.DataFrame:
    """Return rows matching the given year/month."""
    return df[(df["date"].dt.year == year) & (df["date"].dt.month == month)].copy()


def _build_tab_data(
    df: pd.DataFrame,
    config: dict[str, Any],
    colors: dict[str, str],
    label: str,
    tab_id: str,
) -> TabData:
    """Build a TabData from *df*, guarding against empty DataFrames."""
    tab = TabData(label=label, tab_id=tab_id)

    if df.empty:
        return tab

    tab.has_data = True

    result = aggregator.aggregate(df, config)

    # ── Build chart HTML divs ──────────────────────────────────────────
    tab.chart_income_expenses = charts.income_vs_expenses_bar(result.monthly_summary)

    if not result.monthly_by_category.empty:
        tab.chart_spending_by_category = charts.spending_by_category_bar(
            result.monthly_by_category, colors,
        )
    else:
        tab.chart_spending_by_category = "<p>No expense data available.</p>"

    if not result.category_totals.empty:
        tab.chart_category_pie = charts.category_pie(result.category_totals, colors)
    else:
        tab.chart_category_pie = "<p>No expense data available.</p>"

    tab.chart_savings = charts.savings_line(result.monthly_summary)

    # ── Format scalar stats ────────────────────────────────────────────
    stats = result.stats
    stats["total_income_fmt"] = _fmt_eur(stats["total_income"])
    stats["total_expenses_fmt"] = _fmt_eur(stats["total_expenses"])
    stats["net_fmt"] = _fmt_eur(stats["net"])
    stats["avg_monthly_income_fmt"] = _fmt_eur(stats["avg_monthly_income"])
    stats["avg_monthly_expenses_fmt"] = _fmt_eur(stats["avg_monthly_expenses"])
    stats["total_consumption_fmt"] = _fmt_eur(stats["total_consumption"])
    stats["total_investment_fmt"] = _fmt_eur(stats["total_investment"])
    stats["avg_monthly_consumption_fmt"] = _fmt_eur(stats["avg_monthly_consumption"])
    stats["avg_monthly_investment_fmt"] = _fmt_eur(stats["avg_monthly_investment"])
    tab.stats = stats

    # ── Build "other" transactions table ───────────────────────────────
    other_df = df[df["category"] == "other"].copy()
    tab.other_transactions = [
        {
            "date": row["date"].strftime("%d.%m.%Y"),
            "merchant": row.get("merchant", ""),
            "reference": row.get("reference", ""),
            "amount": _fmt_eur(abs(row["amount"])),
            "negative": row["amount"] < 0,
        }
        for _, row in other_df.iterrows()
    ]

    # ── Transactions by category ──────────────────────────────────────
    cat_order = list(config.get("categories", {}).keys())
    for cat_name in cat_order:
        if cat_name in ("income", "other"):
            continue
        cat_df = df[df["category"] == cat_name].copy()
        if cat_df.empty:
            continue
        cat_df = cat_df.sort_values("date", ascending=False)
        total = float(cat_df["amount"].sum())
        rows = [
            {
                "date": row["date"].strftime("%d.%m.%Y"),
                "merchant": row.get("merchant", ""),
                "reference": row.get("reference", ""),
                "amount": _fmt_eur(abs(row["amount"])),
                "negative": row["amount"] < 0,
            }
            for _, row in cat_df.iterrows()
        ]
        tab.category_transactions.append({
            "name": cat_name,
            "color": colors.get(cat_name, "#95a5a6"),
            "count": len(rows),
            "total": _fmt_eur(abs(total)),
            "total_negative": total < 0,
            "transactions": rows,
        })

    # ── Category averages tables ───────────────────────────────────────
    cat_types = {
        name: cfg.get("type", "consumption")
        for name, cfg in config.get("categories", {}).items()
    }
    avg_expense_rows, avg_income_rows, all_avg_years = aggregator.prepare_avg_table_rows(
        result.avg_expenses, result.avg_income, colors, cat_types,
    )
    tab.avg_expense_categories = avg_expense_rows
    tab.avg_income_categories = avg_income_rows
    tab.avg_years = [str(y) for y in all_avg_years]

    # ── Financial health benchmarks ─────────────────────────────────────
    tab.benchmarks = result.benchmarks or {}

    return tab


def generate_report(
    df: pd.DataFrame,
    output_path: str | Path,
    config: dict[str, Any],
) -> None:
    """Render and write the HTML report to *output_path*.

    Parameters
    ----------
    df:
        Categorised transactions DataFrame.
    output_path:
        Destination ``.html`` file path.
    config:
        Parsed categories YAML config dict.
    """
    colors: dict[str, str] = {
        cat: cfg.get("color", "#95a5a6")
        for cat, cfg in config.get("categories", {}).items()
    }

    # ── Build tab data ─────────────────────────────────────────────────
    # Monthly tabs first (most recent first), "All Transactions" last
    tabs: list[TabData] = []

    latest = df["date"].max()
    for i in range(12):
        month = latest.month - i
        year = latest.year
        while month <= 0:
            month += 12
            year -= 1
        label = f"{year}-{month:02d}"
        tab_id = f"m-{year}-{month:02d}"
        month_df = _filter_to_month(df, year, month)
        tabs.append(
            _build_tab_data(month_df, config, colors, label, tab_id),
        )

    tabs.append(
        _build_tab_data(df, config, colors, "All Transactions", "all"),
    )

    # ── Render Jinja2 template ─────────────────────────────────────────
    env = Environment(
        loader=FileSystemLoader(str(_ASSETS_DIR)),
        autoescape=True,
    )
    template = env.get_template("report.html.j2")
    html = template.render(
        plotly_js=plotly.offline.get_plotlyjs(),
        tabs=tabs,
    )

    Path(output_path).write_text(html, encoding="utf-8")
