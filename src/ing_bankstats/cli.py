"""CLI entry point — ``visualise`` command."""

from __future__ import annotations

import webbrowser
from pathlib import Path

import click
import pandas as pd

from . import categorizer, parser, report


@click.command()
@click.argument("csv_files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output HTML file path. Defaults to <input>.html (single file) or report.html (multiple).",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    default=None,
    type=click.Path(exists=True),
    help="Custom categories YAML file. Defaults to the bundled categories.",
)
@click.option(
    "--own-accounts",
    "-a",
    multiple=True,
    help="Merchant name(s) to treat as own-account transfers (repeatable). Merged with config file values.",
)
@click.option(
    "--open",
    "open_browser",
    is_flag=True,
    default=False,
    help="Open the report in the default browser after generating.",
)
def visualise(
    csv_files: tuple[str, ...],
    output: str | None,
    config_path: str | None,
    own_accounts: tuple[str, ...],
    open_browser: bool,
) -> None:
    """Parse one or more ING Bank Germany CSV exports and generate an interactive HTML report."""
    # ── Resolve output path ────────────────────────────────────────────────
    if output:
        out_path = Path(output)
    elif len(csv_files) == 1:
        out_path = Path(csv_files[0]).with_suffix(".html")
    else:
        out_path = Path("report.html")

    # ── Load config ────────────────────────────────────────────────────────
    click.echo(f"Loading config …")
    config = categorizer.load_config(config_path)

    # ── Merge CLI own-accounts into config ──────────────────────────────────
    if own_accounts:
        existing = config.get("own_accounts", [])
        merged = list(dict.fromkeys(existing + list(own_accounts)))
        config["own_accounts"] = merged

    # ── Parse CSV(s) ───────────────────────────────────────────────────────
    dfs = []
    for csv_file in csv_files:
        csv_path = Path(csv_file)
        click.echo(f"Parsing {csv_path.name} …")
        df = parser.parse_csv(csv_path)
        click.echo(f"  {len(df)} transactions")
        dfs.append(df)
    df = pd.concat(dfs, ignore_index=True)

    # ── Deduplicate transactions ───────────────────────────────────────────
    before = len(df)
    df = df.drop_duplicates(
        subset=["date", "merchant", "amount", "reference"],
        keep="first",
        ignore_index=True,
    )
    dupes = before - len(df)
    if dupes:
        click.echo(f"  Removed {dupes} duplicate transaction(s)")
    click.echo(f"  {len(df)} transactions total")

    # ── Categorise ─────────────────────────────────────────────────────────
    click.echo("Categorising transactions …")
    df = categorizer.categorise(df, config)
    other_count = (df["category"] == "other").sum()
    if other_count:
        click.echo(
            f"  {other_count} transaction(s) landed in 'other' — "
            "check the Uncategorised section in the report to add keywords."
        )

    # ── Generate report ────────────────────────────────────────────────────
    click.echo(f"Generating report → {out_path} …")
    report.generate_report(df, out_path, config)
    click.echo(click.style(f"Done! Report written to {out_path}", fg="green"))

    if open_browser:
        webbrowser.open(out_path.resolve().as_uri())
