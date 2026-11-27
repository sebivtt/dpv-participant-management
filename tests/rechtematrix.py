"""Liest die Rechtematrix (`docs/rechtematrix.md`) für die Tests in `tests/test_rechtematrix.py`.

Die Matrix ist für Menschen geschrieben; gelesen wird nur, was die Tests brauchen. Seit #139 hat
jeder Abschnitt mit Rechten bis zu vier Teile:

- das **Raster**: Tabelle mit dem Kopf „Recht“, je Rolle eine Spalte, zuletzt „Kennungen“;
- den Block **„Was niemand darf“**: Punkte der Form `- VP-13 (im Tool): …`;
- die **Einträge**: Tabelle mit dem Kopf „Kennung | Was genau | Quelle | Stand“, je Kennung eine Zeile;
- die **Tests je Kennung**: Tabelle mit dem Kopf „Kennung | Tests“ in einem aufklappbaren Block.

Dazu die Liste der Tabellen in der Datenbank. Die Tests laufen mit `./pruefen.sh`; der Rundumtest
(`tests/test_rundumtest.py`) liest die Kennungen über `row_ids`.
"""

import ast
import re
from collections import Counter
from pathlib import Path

from django.conf import settings

MATRIX = Path(settings.BASE_DIR) / "docs" / "rechtematrix.md"
REQUIREMENTS = Path(settings.BASE_DIR) / "docs" / "anforderungen.md"
TABLES_SECTION = "Tabellen in der Datenbank"
# Abschnitte ohne Rechte: Sie haben weder Raster noch Einträge.
NO_RIGHTS_SECTIONS = ("Inhalt", "So liest man die Matrix", TABLES_SECTION)

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

# Die Spalten jedes Rasters, immer alle und in dieser Folge (#139); die Lesehilfe erklärt sie.
GRID_HEAD = ["Recht", "GL", "StL", "RL", "BL", "Mitgl.", "o. Zuord.", "VL", "DPV-VT", "Admin", "Kennungen"]
# In diesen Abschnitten kommen Veranstaltungsleitung und Ansprechperson dazu.
EVENT_SECTIONS = ("Veranstaltungen und Anmeldungen", "Gesundheitsangaben")
EVENT_GRID_HEAD = GRID_HEAD[:-1] + ["Veranst.-Ltg.", "Ansprechp.", "Kennungen"]
ENTRY_HEAD = ["Kennung", "Was genau", "Quelle", "Stand"]
TESTS_HEAD = ["Kennung", "Tests"]
TABLES_HEAD = ["Tabelle", "Inhalt", "Abschnitt"]

# Die Wörter, mit denen eine Zelle des Rasters beginnt (#139); die Lesehilfe erklärt jedes.
SCOPE_WORDS = (
    "eigene Einheit",
    "Bereich",
    "eine Ebene tiefer",
    "Kette nach oben",
    "eigener Bund",
    "alle Bünde",
    "Verbandsebene",
    "eigene Veranstaltung",
    "eigene Anmeldung",
    # Kreise (#381)
    "Mitglied im Kreis",
    "Verwaltende im Kreis",
    "eigene Einladung",
    "nur sich selbst",
    "ja",
    "–",
)
# Hinter dem Wort: höchstens eine Hochzahl, die auf einen Eintrag verweist, dann eine kurze Grenze.
CELL = re.compile(r"^(" + "|".join(re.escape(word) for word in SCOPE_WORDS) + r")[¹²³⁴⁵⁶⁷⁸⁹]?(, \S.*)?$")
# Satz über jedem Raster (#139): einspringende Leitung und Admin im Support-Zugang.
LEAD_SENTENCE = (
    "Fehlt einer Einheit eine Leitung mit Konto, hat die Leitung darüber dort die Rechte aus der Spalte "
    "dieser Einheit (EH-18). Ein Admin im Support-Zugang hat in der gewählten Einheit die Rechte ihrer "
    "Leitung (SZ-03), gibt sich aber selbst keine Rolle (SZ-05)."
)
FORBIDDEN_START = "**Was niemand darf:**"
# Ein Punkt im Block „Was niemand darf“: Kennungen, Geltung in Klammern, Doppelpunkt, Text.
FORBIDDEN_ITEM = re.compile(r"^- ((?:[A-Z]{2}-\d{2})(?:, [A-Z]{2}-\d{2})*) \(([^()]+)\): \S")


def matrix_text() -> str:
    """Der Text der Rechtematrix, wie er im Repo steht."""
    return MATRIX.read_text(encoding="utf-8")


def _cells(line: str) -> list[str]:
    # Ein senkrechter Strich in einer Zelle wäre als \| geschrieben; die Matrix nutzt keinen.
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Alle Tabellen als (Kopf, Datenzeilen), jede Zeile als Liste ihrer Zellen."""
    found = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            current = None
            continue
        cells = _cells(line)
        if current is None:
            current = (cells, [])
            found.append(current)
        elif not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            current[1].append(cells)
    return found


def sections(text: str) -> dict[str, str]:
    """Die Abschnitte der Matrix (Überschrift `## `), Titel und Text."""
    found = {}
    for part in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        title, _, body = part.partition("\n")
        found[title] = body
    return found


def rights_sections(text: str) -> dict[str, str]:
    return {title: body for title, body in sections(text).items() if title not in NO_RIGHTS_SECTIONS}


def rows(text: str) -> list[list[str]]:
    """Alle Einträge (Tabellen mit dem Kopf „Kennung | Was genau | Quelle | Stand“), je als Liste ihrer Zellen.

    Gezählt wird jeder Eintrag, auch einer mit falsch geschriebener Kennung, damit er nicht still
    aus den Prüfungen herausfällt; `invalid_ids` meldet ihn.
    """
    return [cells for head, body in _tables(text) if head == ENTRY_HEAD for cells in body]


def invalid_ids(text: str) -> list[str]:
    """Kennungen, die nicht die Form „zwei Großbuchstaben, Bindestrich, zwei Ziffern“ haben."""
    return [cells[0] for cells in rows(text) if not ROW_ID.match(cells[0])]


def duplicate_ids(text: str) -> list[str]:
    """Kennungen mit mehr als einem Eintrag oder mehr als einer Zeile unter „Tests je Kennung“."""
    entries = Counter(cells[0] for cells in rows(text))
    tests = Counter(cells[0] for head, body in _tables(text) if head == TESTS_HEAD for cells in body)
    return sorted({row_id for counts in (entries, tests) for row_id, count in counts.items() if count > 1})


def row_ids(text: str) -> set[str]:
    """Alle Kennungen der Matrix, also alle mit einem Eintrag."""
    return {cells[0] for cells in rows(text)}


def unknown_tables(text: str) -> list[str]:
    """Tabellen in Abschnitten mit Rechten, deren Kopf keiner der vorgesehenen ist, etwa vertippt."""
    problems = []
    for title, body in rights_sections(text).items():
        grid_head = EVENT_GRID_HEAD if title in EVENT_SECTIONS else GRID_HEAD
        for head, _ in _tables(body):
            if head not in (grid_head, ENTRY_HEAD, TESTS_HEAD):
                problems.append(f"{title}: {' | '.join(head)}")
    return problems


def sections_without_entries(text: str) -> list[str]:
    """Abschnitte mit Rechten, in denen kein Eintrag gefunden wird."""
    return [title for title, body in rights_sections(text).items() if not rows(body)]


def grid_rows(text: str) -> list[tuple[str, list[str], list[str]]]:
    """Alle Zeilen der Raster als (Abschnitt, Kopf, Zellen)."""
    found = []
    for title, body in rights_sections(text).items():
        for head, table in _tables(body):
            if head[0] == "Recht":
                found += [(title, head, cells) for cells in table]
    return found


def grid_ids(text: str) -> set[str]:
    """Kennungen, die in der letzten Spalte eines Rasters stehen."""
    return {row_id for _, _, cells in grid_rows(text) for row_id in REFERENCE.findall(cells[-1])}


def bad_cells(text: str) -> list[str]:
    """Zellen eines Rasters, die nicht mit einem Wort der Liste beginnen, und Zeilen mit falscher Zahl an Zellen."""
    problems = []
    for title, head, cells in grid_rows(text):
        if len(cells) != len(head):
            problems.append(f"{title}: {cells[0]}: {len(cells)} statt {len(head)} Zellen")
            continue
        for role, cell in zip(head[1:-1], cells[1:-1], strict=True):
            if not CELL.match(cell):
                problems.append(f"{title}: {cells[0]}: {role}: {cell}")
        if not cells[-1] or any(not ROW_ID.match(part) for part in cells[-1].split(", ")):
            problems.append(f"{title}: {cells[0]}: Kennungen: {cells[-1]}")
    return problems


def _forbidden_lines(text: str) -> list[str]:
    """Die Punkte aller Blöcke „Was niemand darf“: die Zeilen mit „- “ direkt unter der Überschrift."""
    found = []
    for body in rights_sections(text).values():
        lines = body.splitlines()
        for number, line in enumerate(lines):
            if line.strip() == FORBIDDEN_START:
                rest = lines[number + 1 :]
                while rest and not rest[0].strip():
                    rest = rest[1:]
                while rest and rest[0].startswith("- "):
                    found.append(rest[0])
                    rest = rest[1:]
    return found


def forbidden_ids(text: str) -> set[str]:
    """Kennungen, die einen Punkt im Block „Was niemand darf“ beginnen."""
    ids = set()
    for line in _forbidden_lines(text):
        match = FORBIDDEN_ITEM.match(line)
        if match:
            ids |= set(match.group(1).split(", "))
    return ids


def bad_forbidden_items(text: str) -> list[str]:
    """Punkte im Block „Was niemand darf“ ohne Kennung am Anfang oder ohne Geltung in Klammern."""
    return [line for line in _forbidden_lines(text) if not FORBIDDEN_ITEM.match(line)]


def unplaced_ids(text: str) -> list[str]:
    """Kennungen mit Eintrag, die in keinem Raster und keinem Block „Was niemand darf“ stehen."""
    return sorted(row_ids(text) - grid_ids(text) - forbidden_ids(text))


def ids_without_entry(text: str) -> list[str]:
    """Kennungen in Rastern, Blöcken „Was niemand darf“ oder Tests je Kennung ohne eigenen Eintrag."""
    placed = grid_ids(text) | forbidden_ids(text) | set(tests_by_id(text))
    return sorted(placed - row_ids(text))


def sections_without_lead_sentence(text: str) -> list[str]:
    """Abschnitte mit Raster, über deren Raster der Satz zur einspringenden Leitung fehlt."""
    missing = []
    for title, body in rights_sections(text).items():
        if any(head[0] == "Recht" for head, _ in _tables(body)):
            before_grid = body.split("\n| Recht |", 1)[0]
            if LEAD_SENTENCE not in before_grid:
                missing.append(title)
    return missing


def tests_by_id(text: str) -> dict[str, str]:
    """Die Tests je Kennung (Tabellen mit dem Kopf „Kennung | Tests“), Kennung und Text."""
    return {cells[0]: cells[-1] for head, body in _tables(text) if head == TESTS_HEAD for cells in body}


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


def unknown_sections(text: str) -> list[str]:
    """Abschnitte in der Tabellenliste, die es als Überschrift nicht gibt."""
    headings = set(sections(text))
    unknown = []
    for head, body in _tables(sections(text).get(TABLES_SECTION, "")):
        if head == TABLES_HEAD:
            for cells in body:
                for section in cells[-1].split(";"):
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
    listed = set()
    for head, body in _tables(sections(text).get(TABLES_SECTION, "")):
        if head == TABLES_HEAD:
            listed |= {cells[0].strip("`") for cells in body}
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
    """Gebaute Kennungen, deren Tests fehlen oder die Kennung nicht tragen.

    Eine Kennung, deren Eintrag in der Spalte „Stand“ mit „gebaut“ beginnt, hat eine Zeile unter
    „Tests je Kennung“. Diese nennt hinter „erlaubt“ und hinter „verboten“ je mindestens einen
    Test als `datei.py::test_name`. Jeder genannte Test muss es geben, und er trägt die Kennung
    als `@pytest.mark.rechtematrix("XY-01")`.
    """
    problems = []
    tests = tests_by_id(text)
    for cells in rows(text):
        row_id, stand = cells[0], cells[-1]
        if not stand.startswith("gebaut"):
            continue
        if row_id not in tests:
            problems.append(f"{row_id}: keine Zeile unter „Tests je Kennung“")
            continue
        # Getrennt wird am Wort „verboten“ nach einem Strichpunkt, nicht an einem Testnamen,
        # der das Wort enthält.
        allowed, _, forbidden = tests[row_id].partition("; verboten ")
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
