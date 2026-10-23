"""Liest die Rechtematrix (`docs/rechtematrix.md`) für die Tests in `tests/test_rechtematrix.py`.

Die Matrix ist für Menschen geschrieben; gelesen wird nur, was die Tests brauchen: Zeilen mit
Kennung, die Liste der Tabellen und die Tests, die eine gebaute Zeile nennt. Ab #90 nutzt
`./pruefen.sh` dieselben Funktionen.
"""

import ast
import re
from collections import Counter
from pathlib import Path

from django.conf import settings

MATRIX = Path(settings.BASE_DIR) / "docs" / "rechtematrix.md"
TABLES_SECTION = "Tabellen in der Datenbank"

# Zwei Großbuchstaben, Bindestrich, zwei Ziffern, z. B. VP-02.
ROW_ID = re.compile(r"^[A-Z]{2}-\d{2}$")
TEST_REFERENCE = re.compile(r"`([^`]+\.py)::(test_\w+)`")


def matrix_text() -> str:
    """Der Text der Rechtematrix, wie er im Repo steht."""
    return MATRIX.read_text(encoding="utf-8")


def _cells(line: str) -> list[str]:
    # Ein senkrechter Strich in einer Zelle wäre als \| geschrieben; die Matrix nutzt keinen.
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def rows(text: str) -> list[list[str]]:
    """Alle Zeilen der Matrix mit Kennung, je als Liste ihrer Zellen."""
    found = []
    for line in text.splitlines():
        if line.startswith("|"):
            cells = _cells(line)
            if ROW_ID.match(cells[0]):
                found.append(cells)
    return found


def duplicate_ids(text: str) -> list[str]:
    """Kennungen, die mehr als einmal vorkommen."""
    counts = Counter(cells[0] for cells in rows(text))
    return sorted(row_id for row_id, count in counts.items() if count > 1)


def _section(text: str, title: str) -> str:
    parts = re.split(r"^## ", text, flags=re.MULTILINE)
    for part in parts:
        if part.startswith(title + "\n"):
            return part
    return ""


def missing_tables(text: str, models) -> list[str]:
    """Datenmodelle, die im Abschnitt „Tabellen in der Datenbank“ fehlen.

    Gezählt wird jedes Modell, das Django kennt, auch die der fertigen Bausteine (Login,
    Sitzungen). Reine Verbindungstabellen, die Django selbst zu einem Modell anlegt, gehören zu
    diesem Modell und fehlen deshalb in `models` (`apps.get_models()` ohne `include_auto_created`).
    """
    listed = set(re.findall(r"`(\w+\.\w+)`", _section(text, TABLES_SECTION)))
    return sorted(model._meta.label for model in models if model._meta.label not in listed)


def _marked_ids(path: Path, name: str) -> set[str] | None:
    """Kennungen am Test `name` in `path`, None wenn es den Test nicht gibt."""
    if not path.is_file():
        return None
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            ids = set()
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and ast.unparse(decorator.func) == "pytest.mark.rechtematrix":
                    ids |= {arg.value for arg in decorator.args if isinstance(arg, ast.Constant)}
            return ids
    return None


def broken_test_references(text: str, root: Path) -> list[str]:
    """Gebaute Zeilen, deren Tests fehlen oder die Kennung der Zeile nicht tragen.

    Eine gebaute Zeile nennt hinter „erlaubt“ und hinter „verboten“ je mindestens einen Test
    als `datei.py::test_name`. Jeder genannte Test muss es geben, und er trägt die Kennung der
    Zeile als `@pytest.mark.rechtematrix("XY-01")`.
    """
    problems = []
    for cells in rows(text):
        row_id, stand = cells[0], cells[-1]
        if not stand.startswith("gebaut"):
            continue
        allowed, _, forbidden = stand.partition("verboten")
        for case, part in (("erlaubt", allowed), ("verboten", forbidden)):
            references = TEST_REFERENCE.findall(part)
            if not references:
                problems.append(f"{row_id}: kein Test für den Fall „{case}“")
            for file, name in references:
                ids = _marked_ids(root / file, name)
                if ids is None:
                    problems.append(f"{row_id}: Test {file}::{name} gibt es nicht")
                elif row_id not in ids:
                    problems.append(f"{row_id}: Test {file}::{name} trägt die Kennung nicht")
    return problems
