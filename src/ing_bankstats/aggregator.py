"""Monthly and category aggregations over categorised transactions."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class AggregationResult:
    """All aggregation outputs needed for the report."""

    monthly_summary: pd.DataFrame
    monthly_by_category: pd.DataFrame
    category_totals: pd.Series
    stats: dict
    avg_expenses: pd.DataFrame
    avg_income: pd.DataFrame
    benchmarks: dict = None


def _category_types(config: dict | None) -> dict[str, str]:
    """Return a mapping of category name to type ("consumption" or "investment")."""
    if not config:
        return {}
    return {
        name: cfg.get("type", "consumption")
        for name, cfg in config.get("categories", {}).items()
    }


def _excluded_categories(config: dict | None) -> set[str]:
    """Return category names that have ``exclude: true`` in the config."""
    if not config:
        return set()
    return {
        name
        for name, cfg in config.get("categories", {}).items()
        if cfg.get("exclude", False)
    }


def _category_averages(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute average monthly spend/income per category, overall and per year.

    Returns (avg_expenses, avg_income) DataFrames with columns for each year
    and an ``overall`` column, indexed by category name, sorted by overall
    descending.
    """
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M")
    df["year"] = df["date"].dt.year

    results = []
    for sign, label in [("neg", "expenses"), ("pos", "income")]:
        subset = df[df["amount"] < 0] if sign == "neg" else df[df["amount"] > 0]
        if subset.empty:
            results.append(pd.DataFrame(columns=["category", "overall"]))
            continue

        amounts = subset.copy()
        amounts["abs_amount"] = amounts["amount"].abs()

        # Per-year averages
        year_totals = amounts.groupby(["year", "category"])["abs_amount"].sum()
        months_per_year = amounts.groupby("year")["month"].nunique()
        year_avg = year_totals.div(months_per_year, level="year").unstack(level="year", fill_value=0)

        # Overall averages
        total_by_cat = amounts.groupby("category")["abs_amount"].sum()
        total_months = amounts["month"].nunique()
        overall = total_by_cat / total_months

        result = year_avg.copy()
        result.columns = [int(c) for c in result.columns]
        result["overall"] = overall
        result = result.fillna(0).sort_values("overall", ascending=False)
        result = result.reset_index()
        results.append(result)

    return results[0], results[1]


def _budget_buckets(config: dict | None) -> dict[str, str]:
    """Return a mapping of category name to budget bucket (needs/wants/savings)."""
    if not config:
        return {}
    return {
        name: cfg["budget_bucket"]
        for name, cfg in config.get("categories", {}).items()
        if "budget_bucket" in cfg
    }


def _make_metric(
    value: float | None,
    formatted: str,
    rating: str,
    benchmark: str,
) -> dict:
    return {
        "value": value,
        "formatted": formatted,
        "rating": rating,
        "benchmark": benchmark,
    }


def _na_metric(benchmark: str) -> dict:
    return _make_metric(None, "N/A", "neutral", benchmark)


def compute_benchmarks(
    stats: dict,
    expense_df: pd.DataFrame,
    monthly_summary: pd.DataFrame,
    config: dict | None,
) -> dict:
    """Compute financial health benchmark metrics.

    Returns a dict of metric_key -> {value, formatted, rating, benchmark}.
    """
    income = stats.get("total_income", 0.0)
    benchmarks: dict = {}

    # ── Savings Rate ────────────────────────────────────────────────────
    if income <= 0:
        benchmarks["savings_rate"] = _na_metric("20%+ healthy")
    else:
        val = stats["net"] / income * 100
        if val >= 20:
            rating = "healthy"
        elif val >= 10:
            rating = "adequate"
        else:
            rating = "at_risk"
        benchmarks["savings_rate"] = _make_metric(
            val, f"{val:.1f}%", rating, "20%+ healthy",
        )

    # ── Housing Cost Ratio ──────────────────────────────────────────────
    if income <= 0:
        benchmarks["housing_ratio"] = _na_metric("<28% comfortable")
    else:
        housing_cats = {"mortgage", "housing"}
        housing_total = float(
            expense_df[expense_df["category"].isin(housing_cats)]["amount"].sum().item()
            if not expense_df.empty
            else 0
        )
        housing_total = abs(housing_total)
        val = housing_total / income * 100
        if val < 28:
            rating = "comfortable"
        elif val <= 33:
            rating = "acceptable"
        else:
            rating = "stretched"
        benchmarks["housing_ratio"] = _make_metric(
            val, f"{val:.1f}%", rating, "<28% comfortable",
        )

    # ── Investment Rate ─────────────────────────────────────────────────
    if income <= 0:
        benchmarks["investment_rate"] = _na_metric("15%+ excellent")
    else:
        inv = stats.get("total_investment", 0.0)
        val = inv / income * 100
        if val >= 15:
            rating = "excellent"
        elif val >= 10:
            rating = "good"
        else:
            rating = "low"
        benchmarks["investment_rate"] = _make_metric(
            val, f"{val:.1f}%", rating, "15%+ excellent",
        )

    # ── Engel's Coefficient ─────────────────────────────────────────────
    if income <= 0:
        benchmarks["engel"] = _na_metric("<15% comfortable")
    else:
        food_cats = {"groceries", "dining"}
        food_total = float(
            abs(expense_df[expense_df["category"].isin(food_cats)]["amount"].sum().item())
            if not expense_df.empty
            else 0
        )
        val = food_total / income * 100
        if val < 15:
            rating = "comfortable"
        elif val <= 25:
            rating = "moderate"
        else:
            rating = "high"
        benchmarks["engel"] = _make_metric(
            val, f"{val:.1f}%", rating, "<15% comfortable",
        )

    # ── 50/30/20 Rule ───────────────────────────────────────────────────
    buckets = _budget_buckets(config)
    if income <= 0:
        benchmarks["needs_pct"] = _na_metric("≤50%")
        benchmarks["wants_pct"] = _na_metric("≤30%")
        benchmarks["savings_bucket_pct"] = _na_metric("≥20%")
    else:
        bucket_totals: dict[str, float] = {"needs": 0.0, "wants": 0.0, "savings": 0.0}
        if not expense_df.empty:
            for cat, bucket in buckets.items():
                cat_total = abs(float(
                    expense_df[expense_df["category"] == cat]["amount"].sum().item()
                ))
                bucket_totals[bucket] += cat_total

        needs_val = bucket_totals["needs"] / income * 100
        wants_val = bucket_totals["wants"] / income * 100
        savings_val = bucket_totals["savings"] / income * 100

        benchmarks["needs_pct"] = _make_metric(
            needs_val, f"{needs_val:.1f}%",
            "on_target" if needs_val <= 50 else "over",
            "≤50%",
        )
        benchmarks["wants_pct"] = _make_metric(
            wants_val, f"{wants_val:.1f}%",
            "on_target" if wants_val <= 30 else "over",
            "≤30%",
        )
        benchmarks["savings_bucket_pct"] = _make_metric(
            savings_val, f"{savings_val:.1f}%",
            "on_target" if savings_val >= 20 else "under",
            "≥20%",
        )

    # ── Expense Trend ───────────────────────────────────────────────────
    if len(monthly_summary) >= 6:
        recent_3 = monthly_summary["expenses"].iloc[-3:].mean()
        prior_3 = monthly_summary["expenses"].iloc[-6:-3].mean()
        if prior_3 > 0:
            val = (recent_3 - prior_3) / prior_3 * 100
            if abs(val) < 5:
                rating = "stable"
            elif val > 0:
                rating = "increasing"
            else:
                rating = "decreasing"
            benchmarks["expense_trend"] = _make_metric(
                val, f"{val:+.1f}%", rating, "±5% stable",
            )
        else:
            benchmarks["expense_trend"] = _na_metric("±5% stable")
    else:
        benchmarks["expense_trend"] = _na_metric("±5% stable")

    return benchmarks


def aggregate(
    df: pd.DataFrame,
    config: dict | None = None,
) -> AggregationResult:
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
    avg_expenses:
        Average monthly expenses per category (overall + per year).
    avg_income:
        Average monthly income per category (overall + per year).
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

    # ── Consumption vs investment split ───────────────────────────────────
    cat_types = _category_types(config)
    if not expense_df.empty:
        expense_cats = expense_df.copy()
        expense_cats["cat_type"] = expense_cats["category"].map(
            lambda c: cat_types.get(c, "consumption")
        )
        consumption_total = float(abs(expense_cats.loc[expense_cats["cat_type"] == "consumption", "amount"].sum()))
        investment_total = float(abs(expense_cats.loc[expense_cats["cat_type"] == "investment", "amount"].sum()))

        consumption_monthly = expense_cats[expense_cats["cat_type"] == "consumption"].groupby("month")["amount"].sum().abs()
        investment_monthly = expense_cats[expense_cats["cat_type"] == "investment"].groupby("month")["amount"].sum().abs()
        avg_monthly_consumption = float(consumption_monthly.mean()) if not consumption_monthly.empty else 0.0
        avg_monthly_investment = float(investment_monthly.mean()) if not investment_monthly.empty else 0.0
    else:
        consumption_total = 0.0
        investment_total = 0.0
        avg_monthly_consumption = 0.0
        avg_monthly_investment = 0.0

    stats["total_consumption"] = consumption_total
    stats["total_investment"] = investment_total
    stats["avg_monthly_consumption"] = avg_monthly_consumption
    stats["avg_monthly_investment"] = avg_monthly_investment

    # ── Category averages (per year + overall) ────────────────────────────
    avg_expenses, avg_income = _category_averages(df)

    # ── Financial health benchmarks ─────────────────────────────────────
    benchmarks = compute_benchmarks(stats, expense_df, monthly_summary, config)

    return AggregationResult(
        monthly_summary=monthly_summary,
        monthly_by_category=monthly_by_category,
        category_totals=category_totals,
        stats=stats,
        avg_expenses=avg_expenses,
        avg_income=avg_income,
        benchmarks=benchmarks,
    )


def _fmt_eur(value: float) -> str:
    return f"€{value:,.2f}"


def _avg_to_rows(
    avg_df: pd.DataFrame,
    colors: dict[str, str],
) -> tuple[list[dict], list[int]]:
    """Convert an averages DataFrame to template-ready row dicts."""
    if avg_df.empty or "category" not in avg_df.columns:
        return [], []
    year_cols = sorted(c for c in avg_df.columns if isinstance(c, int))
    rows = []
    for _, r in avg_df.iterrows():
        row: dict = {
            "category": r["category"],
            "color": colors.get(r["category"], "#95a5a6"),
        }
        for y in year_cols:
            row[str(y)] = _fmt_eur(r[y])
        row["overall"] = _fmt_eur(r["overall"])
        rows.append(row)
    return rows, year_cols


def prepare_avg_table_rows(
    avg_expenses: pd.DataFrame,
    avg_income: pd.DataFrame,
    colors: dict[str, str],
    cat_types: dict[str, str],
) -> tuple[list[dict], list[dict], list[int]]:
    """Build template-ready rows for the average-expenses and income tables.

    Returns ``(grouped_expense_rows, avg_income_rows, all_avg_years)``.
    """
    avg_expense_rows, avg_years = _avg_to_rows(avg_expenses, colors)
    avg_income_rows, avg_income_years = _avg_to_rows(avg_income, colors)
    all_avg_years = sorted(set(avg_years) | set(avg_income_years))

    # Split expenses into consumption / investment with subtotals
    consumption_rows = [r for r in avg_expense_rows if cat_types.get(r["category"], "consumption") == "consumption"]
    investment_rows = [r for r in avg_expense_rows if cat_types.get(r["category"], "consumption") == "investment"]

    def _subtotal_row(label: str, categories: list[str]) -> dict:
        subset = avg_expenses[avg_expenses["category"].isin(categories)]
        row: dict = {"category": label, "color": "", "is_subtotal": True}
        for y in avg_years:
            row[str(y)] = _fmt_eur(float(subset[y].sum())) if y in subset.columns else _fmt_eur(0)
        row["overall"] = _fmt_eur(float(subset["overall"].sum())) if not subset.empty else _fmt_eur(0)
        return row

    grouped_expense_rows: list[dict] = []
    if consumption_rows:
        grouped_expense_rows.extend(consumption_rows)
        grouped_expense_rows.append(_subtotal_row("Consumption Subtotal", [r["category"] for r in consumption_rows]))
    if investment_rows:
        grouped_expense_rows.extend(investment_rows)
        grouped_expense_rows.append(_subtotal_row("Investment Subtotal", [r["category"] for r in investment_rows]))

    if grouped_expense_rows:
        avg_expense_rows = grouped_expense_rows

    return avg_expense_rows, avg_income_rows, all_avg_years
