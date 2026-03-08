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


def spending_by_category_heatmap(
    monthly_by_category: pd.DataFrame,
) -> str:
    """Heatmap of monthly spending by category."""
    months = _months_str(monthly_by_category.index)
    categories = [c.capitalize() for c in monthly_by_category.columns]
    values = monthly_by_category.values.T  # categories × months

    # Build hover text with euro formatting
    hover = []
    for i, cat in enumerate(categories):
        row = []
        for j, month in enumerate(months):
            row.append(f"{cat}<br>{month}<br>€{values[i][j]:,.2f}")
        hover.append(row)

    fig = go.Figure(
        go.Heatmap(
            z=values,
            x=months,
            y=categories,
            colorscale=[
                [0, "rgba(74,158,255,0)"],
                [0.25, "rgba(74,158,255,0.25)"],
                [0.5, "rgba(74,158,255,0.5)"],
                [0.75, "rgba(74,158,255,0.75)"],
                [1, "rgba(74,158,255,1)"],
            ],
            hovertext=hover,
            hovertemplate="%{hovertext}<extra></extra>",
            colorbar=dict(
                title="EUR",
                tickformat=",",
            ),
        )
    )
    fig.update_layout(
        **{**_LAYOUT_DEFAULTS, "margin": dict(l=120, r=20, t=50, b=40)},
        title="Monthly Spending by Category",
        yaxis=dict(autorange="reversed"),
    )
    return fig.to_html(**_TO_HTML_KWARGS)


def spending_by_category_bar(
    monthly_by_category: pd.DataFrame,
    colors: dict[str, str] | None = None,
) -> str:
    """Horizontal bar chart of spending by category for a single month."""
    colors = colors or {}
    # Sum across months (typically just one) and sort ascending so largest is at top
    totals = monthly_by_category.sum().sort_values(ascending=True)
    categories = [c.capitalize() for c in totals.index]
    bar_colors = [colors.get(c, "#95a5a6") for c in totals.index]

    fig = go.Figure(
        go.Bar(
            x=totals.values,
            y=categories,
            orientation="h",
            marker_color=bar_colors,
            hovertemplate="%{y}<br>€%{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title="Spending by Category",
        xaxis_title="Amount (EUR)",
        yaxis=dict(tickmode="linear"),
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
