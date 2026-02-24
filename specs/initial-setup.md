# Initial Setup Summary

## What we built

A CLI tool (`visualise`) that reads ING Bank Germany CSV transaction exports, categorises each transaction by keyword rules, and generates a self-contained interactive HTML report.

## Tech stack

- **Python 3.11+** with Click (CLI), pandas (data), Plotly (charts), PyYAML (config), Jinja2 (templating)
- Packaged via `pyproject.toml` + setuptools; `pip install -e ".[dev]"` wires the `visualise` command

## Project structure

```
src/ing_bankstats/
  cli.py            Click entry point
  parser.py         CSV ingestion (latin-1, German locale numbers, preamble detection)
  categorizer.py    Keyword matching against merchant + reference text
  aggregator.py     Monthly/category aggregations with exclude support
  charts.py         4 Plotly charts (income vs expenses, spending by category, pie, savings line)
  report.py         Jinja2 HTML assembly with embedded Plotly JS (fully offline)
  assets/
    report.html.j2  Dark-themed responsive HTML template
    categories.yaml Bundled default categories
config/
  categories.yaml   User-editable copy (canonical source for tuning)
tests/              43 unit tests covering parser, categorizer, aggregator
```

## ING CSV quirks handled

- **Encoding**: latin-1 (not UTF-8)
- **Preamble rows**: scans for line starting with "Buchung" to find the actual header
- **German number format**: thousands `.`, decimal `,` — parsed manually via string replacement to avoid pandas misinterpreting date columns (e.g. `05.01.2025` as `5012025`)
- **Duplicate currency columns**: both dropped (always EUR)

## Categories config

- 16 categories: income, mortgage, housing, food, transport, car, health, shopping, entertainment, utilities, insurance, investment, savings, childcare, cash, other
- Categories higher in the YAML file take priority on multi-match
- `exclude: true` flag filters a category out of all charts/totals (used for savings transfers and CA Consumer Finance — money that moves between own accounts)
- Keywords are case-insensitive and regex-escaped

## Categories tuning (from training data)

Started at 21.1% categorised with the initial generic config. After analysing ~6,200 real transactions from `data/training.data.csv`:

- Added keywords for high-volume merchants (BUDNI, Sannmann, Plugsurfing, Telefonica, Konditorei Junge, E-CENTER, etc.)
- Fixed misclassifications: removed `"gas"` from utilities (matched "Gastronomie"), replaced standalone `"lohn"` with `"lohn/gehalt"` (prevented ATM withdrawal misclassification)
- Split drugstores (DM, Rossmann, Budni) from food into shopping
- Added new categories: mortgage, housing, insurance, childcare, cash, savings, car
- Split housing into mortgage (equity-building debt repayment) and housing (running costs)

Final result: **63.6% categorised** (3,964 / 6,232 transactions).

## HTML report contents

- Summary stats bar (date range, totals, averages, uncategorised count)
- Monthly income vs expenses (grouped bar)
- Monthly spending by category (stacked bar)
- Category breakdown (donut chart)
- Monthly net savings (line chart)
- Collapsible uncategorised transactions table

All charts interactive (hover, zoom, legend toggle). Fully self-contained HTML — no network requests.
