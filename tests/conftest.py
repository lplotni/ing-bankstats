"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_FIXTURE_CSV = _FIXTURE_DIR / "sample.csv"


def _write_latin1(src: Path, dest: Path) -> str:
    """Transcode a UTF-8 fixture CSV to latin-1 (as ING Bank exports)."""
    dest.write_bytes(src.read_text(encoding="utf-8").encode("latin-1"))
    return str(dest)


@pytest.fixture
def sample_csv_path(tmp_path: Path) -> str:
    """Write the UTF-8 fixture CSV re-encoded as latin-1 (as ING Bank exports).

    The fixture source file is stored as UTF-8 for readability; the parser
    always reads latin-1, so we transcode before handing the path to tests.
    """
    return _write_latin1(_FIXTURE_CSV, tmp_path / "sample.csv")


@pytest.fixture
def savings_csv_path(tmp_path: Path) -> str:
    """A second-account (savings) CSV fixture encoded as latin-1."""
    return _write_latin1(_FIXTURE_DIR / "savings.csv", tmp_path / "savings.csv")
