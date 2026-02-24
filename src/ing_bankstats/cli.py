"""CLI entry point — ``visualise`` command."""

from __future__ import annotations

import webbrowser
from pathlib import Path

import click

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
    "--open",
    "open_browser",
    is_flag=True,
    default=False,
    help="Open the report in the default browser after generating.",
)
def visualise(csv_files: tuple[str, ...], output: str | None, config_path: str | None, open_browser: bool) -> None:
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

    # ── Parse CSV(s) ───────────────────────────────────────────────────────
    import pandas as pd

    dfs = []
    for csv_file in csv_files:
        csv_path = Path(csv_file)
        click.echo(f"Parsing {csv_path.name} …")
        df = parser.parse_csv(str(csv_path))
        click.echo(f"  {len(df)} transactions")
        dfs.append(df)
    df = pd.concat(dfs, ignore_index=True)
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
