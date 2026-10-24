"""Liest die Rechtematrix (`docs/rechtematrix.md`) für die Tests in `tests/test_rechtematrix.py`.

Die Matrix ist für Menschen geschrieben; gelesen wird nur, was die Tests brauchen: Zeilen mit
Kennung, die Liste der Tabellen und die Tests, die eine gebaute Zeile nennt. Die Tests laufen
mit `./pruefen.sh`; #90 baut darauf auf.
"""

import ast
import re
from collections import Counter
from pathlib import Path

from django.conf import settings

MATRIX = Path(settings.BASE_DIR) / "docs" / "rechtematrix.md"
REQUIREMENTS = Path(settings.BASE_DIR) / "docs" / "anforderungen.md"
TABLES_SECTION = "Tabellen in der Datenbank"

# Zwei Großbuchstaben, Bindestrich, zwei Ziffern, z. B. VP-02.
ROW_ID = re.compile(r"^[A-Z]{2}-\d{2}$")
# Verweise auf Zeilen (VP-02) und Anforderungen (BER-01, DSG-09) im Fließtext.
REFERENCE = re.compile(r"\b[A-Z]{2,4}-\d{2}\b")
# Jedes Wort, das „Pfad“ enthält; erlaubt ist nur der Begriff „Leitungspfad“ (#136, A1).
PATH_WORD = re.compile(r"\w*[Pp]fad\w*")
ALLOWED_PATH_WORDS = {"Leitungspfad", "Leitungspfads", "Leitungspfades"}
TEST_REFERENCE = re.compile(r"`([^`]+\.py)::(test_\w+)`")
# Verweise auf Tests in Klassen (datei.py::Klasse::test_x) erkennt die Prüfung nicht; sie meldet
# sie als fehlenden Test. Die Tests dieses Repos stehen nicht in Klassen.


def matrix_text() -> str:
    """Der Text der Rechtematrix, wie er im Repo steht."""
    return MATRIX.read_text(encoding="utf-8")


def _cells(line: str) -> list[str]:
    # Ein senkrechter Strich in einer Zelle wäre als \| geschrieben; die Matrix nutzt keinen.
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def rows(text: str) -> list[list[str]]:
    """Alle Datenzeilen der Tabellen, deren Kopf mit „Kennung“ beginnt, je als Liste ihrer Zellen.

    Gezählt wird jede Zeile solcher Tabellen, auch eine mit falsch geschriebener Kennung, damit
    sie nicht still aus den Prüfungen herausfällt; `invalid_ids` meldet sie.
    """
    found = []
    in_matrix_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            in_matrix_table = False
            continue
        cells = _cells(line)
        if cells[0] == "Kennung":
            in_matrix_table = True
        elif in_matrix_table and not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            found.append(cells)
    return found


def invalid_ids(text: str) -> list[str]:
    """Kennungen, die nicht die Form „zwei Großbuchstaben, Bindestrich, zwei Ziffern“ haben."""
    return [cells[0] for cells in rows(text) if not ROW_ID.match(cells[0])]


def duplicate_ids(text: str) -> list[str]:
    """Kennungen, die mehr als einmal vorkommen."""
    counts = Counter(cells[0] for cells in rows(text))
    return sorted(row_id for row_id, count in counts.items() if count > 1)


def row_ids(text: str) -> set[str]:
    """Alle Kennungen der Matrix."""
    return {cells[0] for cells in rows(text)}


def requirement_ids(text: str) -> set[str]:
    """Alle Anforderungs-IDs aus `docs/anforderungen.md` (erste Spalte der Tabellen)."""
    return set(re.findall(r"^\| ([A-Z]{2,4}-\d{2}) \|", text, flags=re.MULTILINE))


def dangling_references(text: str, known: set[str]) -> list[str]:
    """Verweise auf Kennungen oder Anforderungen, die es weder in der Matrix noch in `known` gibt."""
    found = set(REFERENCE.findall(text))
    return sorted(found - row_ids(text) - known)


def stray_path_words(text: str) -> list[str]:
    """Wörter mit „Pfad“, die nicht der Begriff „Leitungspfad“ sind.

    „Pfad“ allein stand früher für zwei Dinge (#136, A1); jetzt heißt es „Kette nach oben“ für
    das Sehen und „Leitungspfad“ dafür, wo jemand Leitung sein darf.
    """
    return sorted({word for word in PATH_WORD.findall(text) if word not in ALLOWED_PATH_WORDS})


def _section(text: str, title: str) -> str:
    parts = re.split(r"^## ", text, flags=re.MULTILINE)
    for part in parts:
        if part.startswith(title + "\n"):
            return part
    return ""


def unknown_sections(text: str) -> list[str]:
    """Abschnitte in der Tabellenliste, die es als Überschrift nicht gibt."""
    headings = set(re.findall(r"^## (.+)$", text, flags=re.MULTILINE))
    unknown = []
    for line in _section(text, TABLES_SECTION).splitlines():
        if line.startswith("| `"):
            for section in _cells(line)[-1].split(";"):
                name = re.sub(r"\s*\(.*\)$", "", section.strip())
                if name not in headings:
                    unknown.append(name)
    return unknown


def missing_tables(text: str, models) -> list[str]:
    """Datenmodelle, die im Abschnitt „Tabellen in der Datenbank“ fehlen.

    Gezählt wird jedes Modell, das Django kennt, auch die der fertigen Bausteine (Login,
    Sitzungen). Reine Verbindungstabellen, die Django selbst zu einem Modell anlegt, gehören zu
    diesem Modell und fehlen deshalb in `models` (`apps.get_models()` ohne `include_auto_created`).
    """
    table_rows = [line for line in _section(text, TABLES_SECTION).splitlines() if line.startswith("| `")]
    listed = {_cells(line)[0].strip("`") for line in table_rows}
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
        # Getrennt wird am Wort „verboten“ nach einem Strichpunkt, nicht an einem Testnamen,
        # der das Wort enthält.
        allowed, _, forbidden = stand.partition("; verboten ")
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
