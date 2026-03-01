# Financial Health Benchmarking Spec

Proposed financial health metrics calculable from existing category data.

## Primary Metrics

### 50/30/20 Rule

Split total spending into Needs / Wants / Savings based on category mappings.

| Bucket   | Benchmark | Category mapping (examples)                          |
|----------|-----------|------------------------------------------------------|
| Needs    | 50%       | `mortgage`, `utilities`, `insurance`, `food`, `health`, `transport` |
| Wants    | 30%       | `entertainment`, `shopping`, `travel`, `dining`       |
| Savings  | 20%       | `investment`, `savings`                               |

**Calculation:** Assign each category to a bucket via config (`budget_bucket: needs|wants|savings`). Compute `bucket_total / income * 100` for each bucket.

### Savings Rate

```
savings_rate = net / income * 100
```

- **Benchmark:** 20%+ is healthy, 10-20% is adequate, <10% is at risk.
- Already computable from `stats["net"]` and `stats["total_income"]`.

### Housing Cost Ratio

```
housing_ratio = (mortgage + housing_costs) / income * 100
```

- **Benchmark:** <28% is comfortable, 28-33% is acceptable, >33% is stretched.
- Requires categories: `mortgage`, `rent`, or a general `housing` category.

### Investment Rate

```
investment_rate = investment / income * 100
```

- **Benchmark:** 10-15% is good, 15%+ is excellent.
- Already computable from `stats["total_investment"]` and `stats["total_income"]`.

## Secondary Metrics

### Expense Trend Direction

Compare average monthly expenses over the last 3 months vs the 3 months before that. Report as "increasing", "stable", or "decreasing".

```
recent_avg = mean(expenses[-3:])
prior_avg  = mean(expenses[-6:-3])
trend = (recent_avg - prior_avg) / prior_avg * 100
```

- **Stable:** |trend| < 5%
- **Increasing/Decreasing:** otherwise

### Food-to-Income Ratio (Engel's Coefficient)

```
engel = food_spending / income * 100
```

- **Benchmark:** <15% is comfortable, 15-25% is moderate, >25% is high.

## Implementation Notes

- Metrics should be computed in `aggregator.py` alongside existing stats.
- The report template can display these as a "Financial Health" card or section.
- Category-to-bucket mapping can be added to `categories.yaml` as a new optional field per category.
- All metrics require at least 1 month of data; trend metrics require at least 6 months.
- When income is zero, ratios should display "N/A" rather than dividing by zero.
