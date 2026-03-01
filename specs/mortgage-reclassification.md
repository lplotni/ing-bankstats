# Mortgage Reclassification to Savings Bucket

## Rationale

Mortgage payments build equity (the homeowner's net worth increases with each payment), so they should count toward the **20% savings** bucket rather than the **50% needs** bucket in the 50/30/20 budget rule.

## Changes Made

### `src/ing_bankstats/assets/categories.yaml`

Changed the mortgage category's `budget_bucket` from `needs` to `savings`. The `type: investment` field was already correctly set and remained unchanged.

```yaml
mortgage:
  color: "#8e44ad"
  type: investment
  budget_bucket: savings  # was: needs
  keywords:
    - tilgung
    - sondertilgung
    - baufinanzierung
```

## Verification

- All 90 tests passed (`pytest`) — no test hardcodes mortgage's budget bucket.

## Commit

`18c1bb3` — Reclassify mortgage as savings in 50/30/20 budget
