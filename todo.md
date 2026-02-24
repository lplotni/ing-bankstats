# TODO

## Multiple CSV / multiple bank accounts

Add support for passing multiple CSV files to `visualise` so transactions from different bank accounts (e.g. joint account, personal account, savings account) can be merged into a single report.

Considerations:
- Accept multiple file arguments: `visualise account1.csv account2.csv`
- Or accept a directory: `visualise --dir data/`
- Deduplicate transactions that might appear in both exports (e.g. transfers between own accounts)
- Track which account each transaction came from (add an `account` column)
- Potentially allow per-account filtering in the report
