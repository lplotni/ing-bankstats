"""Assemble the self-contained HTML report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import plotly.offline
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from . import aggregator, charts

_ASSETS_DIR = Path(__file__).parent / "assets"


def _fmt_eur(value: float) -> str:
    return f"€{value:,.2f}"


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
    monthly_summary, monthly_by_category, category_totals, stats = aggregator.aggregate(df, config)

    colors: dict[str, str] = {
        cat: cfg.get("color", "#95a5a6")
        for cat, cfg in config.get("categories", {}).items()
    }

    # ── Build chart HTML divs ──────────────────────────────────────────────
    chart_income_expenses = charts.income_vs_expenses_bar(monthly_summary)

    if not monthly_by_category.empty:
        chart_spending_by_category = charts.spending_by_category_bar(
            monthly_by_category, colors
        )
    else:
        chart_spending_by_category = "<p>No expense data available.</p>"

    if not category_totals.empty:
        chart_category_pie = charts.category_pie(category_totals, colors)
    else:
        chart_category_pie = "<p>No expense data available.</p>"

    chart_savings = charts.savings_line(monthly_summary)

    # ── Format scalar stats ────────────────────────────────────────────────
    stats["total_income_fmt"] = _fmt_eur(stats["total_income"])
    stats["total_expenses_fmt"] = _fmt_eur(stats["total_expenses"])
    stats["net_fmt"] = _fmt_eur(stats["net"])
    stats["avg_monthly_income_fmt"] = _fmt_eur(stats["avg_monthly_income"])
    stats["avg_monthly_expenses_fmt"] = _fmt_eur(stats["avg_monthly_expenses"])

    # ── Build "other" transactions table ──────────────────────────────────
    other_df = df[df["category"] == "other"].copy()
    other_transactions = [
        {
            "date": row["date"].strftime("%d.%m.%Y"),
            "merchant": row.get("merchant", ""),
            "reference": row.get("reference", ""),
            "amount": _fmt_eur(abs(row["amount"])),
            "negative": row["amount"] < 0,
        }
        for _, row in other_df.iterrows()
    ]

    # ── Render Jinja2 template ─────────────────────────────────────────────
    env = Environment(
        loader=FileSystemLoader(str(_ASSETS_DIR)),
        autoescape=False,
    )
    template = env.get_template("report.html.j2")
    html = template.render(
        plotly_js=plotly.offline.get_plotlyjs(),
        stats=stats,
        chart_income_expenses=chart_income_expenses,
        chart_spending_by_category=chart_spending_by_category,
        chart_category_pie=chart_category_pie,
        chart_savings=chart_savings,
        other_transactions=other_transactions,
    )

    Path(output_path).write_text(html, encoding="utf-8")
