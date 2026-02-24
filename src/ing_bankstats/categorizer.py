"""Keyword-based transaction categorisation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


_DEFAULT_CONFIG = Path(__file__).parent / "assets" / "categories.yaml"


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load the categories YAML config.

    Falls back to the bundled default when *config_path* is ``None``.
    """
    path = Path(config_path) if config_path else _DEFAULT_CONFIG
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def categorise(df, config: dict[str, Any]):
    """Return *df* with a new ``category`` column.

    Matching strategy
    -----------------
    1. Default every row to ``"other"``.
    2. Build a ``search_text`` column from merchant + reference (lower-cased).
    3. Iterate categories in **reverse** YAML order (bottom → top), so that
       categories higher in the file take precedence (they are applied last
       and therefore overwrite lower-priority matches).
    4. For each category apply a vectorised ``str.contains`` regex over the
       combined keywords; skip categories with no keywords.
    """
    import pandas as pd  # local import keeps module light if only config used

    df = df.copy()
    df["search_text"] = (
        df.get("merchant", pd.Series("", index=df.index)).fillna("").str.lower()
        + " "
        + df.get("reference", pd.Series("", index=df.index)).fillna("").str.lower()
    )

    df["category"] = "other"

    categories: dict[str, Any] = config.get("categories", {})

    for cat_name, cat_cfg in reversed(list(categories.items())):
        keywords: list[str] = cat_cfg.get("keywords", []) or []
        if not keywords:
            continue
        pattern = "|".join(re.escape(str(kw)) for kw in keywords)
        mask = df["search_text"].str.contains(pattern, case=False, na=False)
        df.loc[mask, "category"] = cat_name

    return df.drop(columns=["search_text"])
