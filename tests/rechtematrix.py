"""Liest die Rechtematrix (`docs/rechtematrix.md`) für die Tests in `tests/test_rechtematrix.py`.

Gerüst für #87; die Funktionen finden noch nichts.
"""

from pathlib import Path

from django.conf import settings

MATRIX = Path(settings.BASE_DIR) / "docs" / "rechtematrix.md"


def matrix_text() -> str:
    """Der Text der Rechtematrix, wie er im Repo steht."""
    return MATRIX.read_text(encoding="utf-8")


def rows(text: str) -> list[list[str]]:
    """Alle Zeilen der Matrix mit Kennung, je als Liste ihrer Zellen."""
    return []


def duplicate_ids(text: str) -> list[str]:
    """Kennungen, die mehr als einmal vorkommen."""
    return []


def missing_tables(text: str, models) -> list[str]:
    """Datenmodelle, die im Abschnitt „Tabellen in der Datenbank“ fehlen."""
    return []


def broken_test_references(text: str, root: Path) -> list[str]:
    """Gebaute Zeilen, deren Tests fehlen oder die Kennung der Zeile nicht tragen."""
    return []
