"""Parse ING Bank Germany CSV transaction exports."""

from __future__ import annotations

import pandas as pd


_COLUMN_RENAMES = {
    "Buchung": "date",
    "Valuta": "value_date",
    "Auftraggeber/Empf\xe4nger": "merchant",  # latin-1 ä
    "Buchungstext": "transaction_type",
    "Verwendungszweck": "reference",
    "Saldo": "balance",
    "Betrag": "amount",
}


def _find_header_row(file_path: str) -> int:
    """Return the zero-based line index of the CSV header row.

    ING prepends several account-metadata lines before the actual header.
    The header always starts with the German word ``Buchung``.
    """
    with open(file_path, encoding="latin-1") as fh:
        for i, line in enumerate(fh):
            if line.startswith("Buchung"):
                return i
    raise ValueError(
        f"Could not find header row starting with 'Buchung' in {file_path!r}. "
        "Is this a valid ING Bank CSV export?"
    )


def parse_csv(file_path: str) -> pd.DataFrame:
    """Read an ING Bank Germany CSV export and return a clean DataFrame.

    Handles:
    - Latin-1 encoding with German umlauts
    - Preamble rows before the actual header
    - German number format (thousands ```.```, decimal ```,```)
    - Duplicate currency columns (dropped)
    - Date parsing from ``DD.MM.YYYY``
    """
    skip = _find_header_row(file_path)

    # Read everything as strings to avoid the German thousands separator "."
    # being mistakenly applied to date columns (e.g. 05.01.2025 → 5012025).
    df = pd.read_csv(
        file_path,
        sep=";",
        encoding="latin-1",
        skiprows=skip,
        dtype=str,
    )

    # Convert German-locale number columns (thousands='.', decimal=',') manually.
    for col in ("Saldo", "Betrag"):
        if col in df.columns:
            df[col] = (
                df[col]
                .str.strip()
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop the two currency columns (always EUR, not interesting)
    df = df.drop(
        columns=[c for c in df.columns if c.startswith("W\xe4hrung")],
        errors="ignore",
    )

    df = df.rename(columns=_COLUMN_RENAMES)

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y", errors="coerce")
    if "value_date" in df.columns:
        df["value_date"] = pd.to_datetime(
            df["value_date"], format="%d.%m.%Y", errors="coerce"
        )

    # Drop rows without a date or amount (e.g. trailing empty lines)
    df = df.dropna(subset=["date", "amount"])

    # Ensure amount is float
    df["amount"] = df["amount"].astype(float)

    # Fill text fields with empty string so str operations are safe
    for col in ("merchant", "reference", "transaction_type"):
        if col in df.columns:
            df[col] = df[col].fillna("")

    return df.reset_index(drop=True)
