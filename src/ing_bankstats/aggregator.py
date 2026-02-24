"""Monthly and category aggregations over categorised transactions."""

from __future__ import annotations

import pandas as pd


def _excluded_categories(config: dict | None) -> set[str]:
    """Return category names that have ``exclude: true`` in the config."""
    if not config:
        return set()
    return {
        name
        for name, cfg in config.get("categories", {}).items()
        if cfg.get("exclude", False)
    }


def aggregate(
    df: pd.DataFrame,
    config: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, dict]:
    """Compute all aggregations needed for the report.

    Parameters
    ----------
    df:
        Categorised transactions DataFrame (must have ``date``, ``amount``,
        ``category`` columns).
    config:
        Parsed categories YAML config dict.  Categories with
        ``exclude: true`` are filtered out before computing totals
        (internal transfers that aren't real income/expenses).

    Returns
    -------
    monthly_summary:
        DataFrame indexed by ``Period[M]`` with columns
        ``income``, ``expenses``, ``savings``.
    monthly_by_category:
        DataFrame indexed by ``Period[M]``; columns are category names;
        values are **positive** expense totals.
    category_totals:
        Series mapping each category to its total (positive) expense.
    stats:
        Scalar statistics dict for the summary bar.
    """
    excluded = _excluded_categories(config)

    df = df.copy()
    df["month"] = df["date"].dt.to_period("M")

    # Count excluded before filtering
    excluded_count = int(df["category"].isin(excluded).sum()) if excluded else 0

    # Filter out excluded categories (e.g. internal savings transfers)
    if excluded:
        df = df[~df["category"].isin(excluded)]

    income_df = df[df["amount"] > 0]
    expense_df = df[df["amount"] < 0]

    # ── Monthly summary ────────────────────────────────────────────────────
    monthly_income = income_df.groupby("month")["amount"].sum()
    monthly_expenses = expense_df.groupby("month")["amount"].sum().abs()

    monthly_summary = pd.DataFrame(
        {"income": monthly_income, "expenses": monthly_expenses}
    ).fillna(0)
    monthly_summary["savings"] = (
        monthly_summary["income"] - monthly_summary["expenses"]
    )
    monthly_summary = monthly_summary.sort_index()

    # ── Monthly by category (expenses only) ────────────────────────────────
    if not expense_df.empty:
        monthly_by_category = (
            expense_df.groupby(["month", "category"])["amount"]
            .sum()
            .abs()
            .unstack(fill_value=0)
        )
        monthly_by_category = monthly_by_category.sort_index()
    else:
        monthly_by_category = pd.DataFrame(index=monthly_summary.index)

    # ── Category totals ─────────────────────────────────────────────────────
    category_totals = expense_df.groupby("category")["amount"].sum().abs()

    # ── Scalar stats ────────────────────────────────────────────────────────
    total_income = float(income_df["amount"].sum())
    total_expenses = float(abs(expense_df["amount"].sum()) if not expense_df.empty else 0)
    net = total_income - total_expenses

    avg_monthly_income = float(
        income_df.groupby("month")["amount"].sum().mean()
        if not income_df.empty else 0
    )
    avg_monthly_expenses = float(
        expense_df.groupby("month")["amount"].sum().abs().mean()
        if not expense_df.empty else 0
    )

    stats = {
        "date_from": df["date"].min().strftime("%d.%m.%Y"),
        "date_to": df["date"].max().strftime("%d.%m.%Y"),
        "months_count": int(df["month"].nunique()),
        "transaction_count": int(len(df)),
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net": net,
        "avg_monthly_income": avg_monthly_income,
        "avg_monthly_expenses": avg_monthly_expenses,
        "uncategorised_count": int((df["category"] == "other").sum()),
        "excluded_count": excluded_count,
    }

    return monthly_summary, monthly_by_category, category_totals, stats
