"""Plotly chart builders — each returns an HTML div string."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

_LAYOUT_DEFAULTS = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"),
    margin=dict(l=40, r=20, t=50, b=40),
)

_TO_HTML_KWARGS = dict(full_html=False, include_plotlyjs=False, config={"responsive": True})


def _months_str(index: pd.PeriodIndex) -> list[str]:
    return [str(m) for m in index]


def income_vs_expenses_bar(monthly_summary: pd.DataFrame) -> str:
    """Grouped bar chart of monthly income vs expenses."""
    months = _months_str(monthly_summary.index)

    fig = go.Figure(
        [
            go.Bar(
                x=months,
                y=monthly_summary["income"],
                name="Income",
                marker_color="#2ecc71",
            ),
            go.Bar(
                x=months,
                y=monthly_summary["expenses"],
                name="Expenses",
                marker_color="#e74c3c",
            ),
        ]
    )
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title="Monthly Income vs Expenses",
        barmode="group",
        xaxis_title="Month",
        yaxis_title="Amount (EUR)",
        legend=dict(orientation="h", y=1.1),
    )
    return fig.to_html(**_TO_HTML_KWARGS)


def spending_by_category_bar(
    monthly_by_category: pd.DataFrame,
    colors: dict[str, str] | None = None,
) -> str:
    """Stacked bar chart of monthly spending broken down by category."""
    colors = colors or {}
    months = _months_str(monthly_by_category.index)

    traces = []
    for cat in monthly_by_category.columns:
        traces.append(
            go.Bar(
                x=months,
                y=monthly_by_category[cat],
                name=cat.capitalize(),
                marker_color=colors.get(cat, "#95a5a6"),
            )
        )

    fig = go.Figure(traces)
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title="Monthly Spending by Category",
        barmode="stack",
        xaxis_title="Month",
        yaxis_title="Amount (EUR)",
        legend=dict(orientation="h", y=-0.2, traceorder="normal"),
    )
    return fig.to_html(**_TO_HTML_KWARGS)


def category_pie(
    category_totals: pd.Series,
    colors: dict[str, str] | None = None,
) -> str:
    """Donut chart of total expense breakdown by category."""
    colors = colors or {}
    cats = category_totals.index.tolist()
    marker_colors = [colors.get(c, "#95a5a6") for c in cats]

    fig = go.Figure(
        go.Pie(
            labels=[c.capitalize() for c in cats],
            values=category_totals.values,
            hole=0.45,
            marker=dict(colors=marker_colors),
            textinfo="label+percent",
            hovertemplate="%{label}<br>€%{value:,.2f}<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title="Spending by Category",
        showlegend=False,
    )
    return fig.to_html(**_TO_HTML_KWARGS)


def savings_line(monthly_summary: pd.DataFrame) -> str:
    """Line chart of monthly net savings."""
    months = _months_str(monthly_summary.index)
    savings = monthly_summary["savings"]

    # Colour each point green/red based on sign
    colors_list = ["#2ecc71" if v >= 0 else "#e74c3c" for v in savings]

    fig = go.Figure(
        [
            go.Scatter(
                x=months,
                y=savings,
                mode="lines+markers",
                name="Net Savings",
                line=dict(color="#4a9eff", width=2),
                marker=dict(color=colors_list, size=8),
                hovertemplate="Month: %{x}<br>Savings: €%{y:,.2f}<extra></extra>",
            )
        ]
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#555", line_width=1)
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title="Monthly Net Savings",
        xaxis_title="Month",
        yaxis_title="Amount (EUR)",
    )
    return fig.to_html(**_TO_HTML_KWARGS)
