"""Tests für die Form der Rechtematrix (#87, #139, `docs/rechtematrix.md`).

S1, S2 und S4 verweisen auf die Szenarien im Issue #87 (Kommentar „Szenarien für die Umsetzung,
23.10.2026“). S3 prüfen die Protokolltests, die die Kennungen PR-02 und PR-04 nennen. Die Rechte
selbst prüfen die Tests, die eine gebaute Kennung nennt; diese hier prüfen nur, dass die Matrix
vollständig ist und jede gebaute Kennung auf echte Tests zeigt. Die Tests in der Mitte kommen aus
den Korrekturen nach dem externen Review (#136), die am Ende aus dem Umbau ins Raster (#139).
"""

import re

import pytest
from django.apps import apps
from django.db import models

from tests.rechtematrix import (
    FORBIDDEN_START,
    LEAD_SENTENCE,
    MATRIX,
    REQUIREMENTS,
    SCOPE_WORDS,
    bad_cells,
    bad_forbidden_items,
    broken_test_references,
    dangling_references,
    duplicate_ids,
    forbidden_ids,
    grid_rows,
    ids_without_entry,
    invalid_ids,
    matrix_text,
    missing_tables,
    requirement_ids,
    row_ids,
    rows,
    sections_without_entries,
    sections_without_lead_sentence,
    stray_path_words,
    unknown_sections,
    unknown_tables,
    unplaced_ids,
)

SECTIONS = [
    "Eigenes Profil",
    "Personen mit Konto",
    "Verwaltete Personen",
    "Einheiten",
    "Leitungen und Rollen",
    "Veranstaltungen und Anmeldungen",
    "Kreise",
    "Gesundheitsangaben",
    "Support-Zugang der Admins",
    "Protokolle",
    "Technische Daten des Logins",
    "Tabellen in der Datenbank",
]

HEADER = "| Kennung | Was genau | Quelle | Stand |\n| --- | --- | --- | --- |\n"
TESTS_HEADER = "| Kennung | Tests |\n| --- | --- |\n"


def headings(text: str) -> list[str]:
    return re.findall(r"^## (.+)$", text, flags=re.MULTILINE)


def test_matrix_hat_inhaltsverzeichnis_und_jeden_abschnitt():
    text = matrix_text()
    found = headings(text)

    assert found[:1] == ["Inhalt"]
    for section in SECTIONS:
        assert section in found, section
    contents = text.split("## Inhalt", 1)[1].split("\n## ", 1)[0]
    for section in found[1:]:
        assert f"[{section}]" in contents, section


def test_jeder_eintrag_nennt_alle_vier_angaben():
    found = rows(matrix_text())

    assert found
    for cells in found:
        assert len(cells) == 4, cells
        assert all(cells), cells
        assert cells[3].startswith(("geplant", "gebaut")), cells


def test_jeder_abschnitt_mit_rechten_hat_eintraege():
    assert sections_without_entries(matrix_text()) == []


def test_jede_tabelle_hat_einen_vorgesehenen_kopf():
    assert unknown_tables(matrix_text()) == []


GRID_LINE = "| Recht | GL | StL | RL | BL | Mitgl. | o. Zuord. | VL | DPV-VT | Admin | Kennungen |"
EVENT_GRID_LINE = "| Recht | GL | StL | RL | BL | Mitgl. | o. Zuord. | VL | DPV-VT | Admin | Veranst.-Ltg. | Ansprechp. | Kennungen |"


def replace_in_section(text: str, title: str, old: str, new: str) -> str:
    """`old` im Abschnitt `title` einmal durch `new` ersetzt; der Rest der Matrix bleibt."""
    before, _, rest = text.partition(f"## {title}\n")
    section, sep, after = rest.partition("\n## ")
    assert old in section, (title, old)
    return before + f"## {title}\n" + section.replace(old, new, 1) + sep + after


@pytest.mark.parametrize(
    ("title", "old", "new"),
    [
        ("Eigenes Profil", "| Kennung | Was genau |", "| Kenung | Was genau |"),
        ("Verwaltete Personen", GRID_LINE, GRID_LINE.removesuffix(" Kennungen |")),
        ("Verwaltete Personen", "| Kennung | Tests |", "| Kennung | Test |"),
        ("Gesundheitsangaben", EVENT_GRID_LINE, GRID_LINE),
    ],
    ids=["eintraege", "raster_ohne_kennungen", "tests_je_kennung", "raster_ohne_veranstaltungsspalten"],
)
def test_vertippter_tabellenkopf_ist_rot(title, old, new):
    """Gegenprobe: Eine Tabelle, die nicht als Teil der Matrix erkannt wird, fällt auf."""
    broken = replace_in_section(matrix_text(), title, old, new)

    assert unknown_tables(broken) != []


def test_eintraege_mit_vertipptem_kopf_fehlen_dem_abschnitt():
    """Gegenprobe: Ohne erkannte Einträge meldet die Prüfung den Abschnitt."""
    text = replace_in_section(matrix_text(), "Eigenes Profil", "| Kennung | Was genau |", "| Kenung | Was genau |")

    assert sections_without_entries(text) == ["Eigenes Profil"]


def test_jede_kennung_hat_die_vorgesehene_form():
    assert invalid_ids(matrix_text()) == []


@pytest.mark.parametrize("row_id", ["VP-2", "VP-100", "vp-02", "**VP-02**", "", "-"])
def test_falsch_geschriebene_kennung_faellt_nicht_still_heraus(row_id):
    """Gegenprobe: Ein solcher Eintrag zählt mit und wird gemeldet."""
    text = HEADER + f"| {row_id} | Beispiel | BER-01 | gebaut |\n"

    assert invalid_ids(text) == [row_id]
    assert broken_test_references(text, MATRIX.parent.parent) != []


# S1: Jede Art von Daten in der Datenbank steht in der Matrix


def test_jede_tabelle_der_datenbank_steht_in_der_matrix():
    assert missing_tables(matrix_text(), apps.get_models()) == []


@pytest.fixture
def unlisted_model():
    """Ein absichtlich nicht eingetragenes Datenmodell, nur für die Dauer des Tests angemeldet."""
    meta = type("Meta", (), {"app_label": "units"})
    model = type("Unlisted", (models.Model,), {"__module__": "units.models", "Meta": meta})
    yield model
    del apps.all_models["units"]["unlisted"]
    apps.clear_cache()


def test_nicht_eingetragene_tabelle_macht_die_pruefung_rot(unlisted_model):
    """S1, Gegenprobe."""
    assert missing_tables(matrix_text(), apps.get_models()) == ["units.Unlisted"]


def test_tabellenliste_nennt_nur_vorhandene_abschnitte():
    assert unknown_sections(matrix_text()) == []


def test_tabellenliste_mit_unbekanntem_abschnitt_ist_rot():
    """Gegenprobe."""
    text = matrix_text().replace("| `units.Unit` | Einheiten, zufällige Kennung für Adressen | Einheiten |", "| `units.Unit` | Einheiten, zufällige Kennung für Adressen | Organisationen |")

    assert unknown_sections(text) == ["Organisationen"]


# S2: Jede gebaute Kennung zeigt auf Tests, die es gibt und die ihre Kennung tragen


def test_gebaute_zeilen_nennen_tests_mit_ihrer_kennung():
    text = matrix_text()

    assert any(cells[3].startswith("gebaut") for cells in rows(text))
    assert broken_test_references(text, MATRIX.parent.parent) == []


@pytest.fixture
def repo(tmp_path):
    """Ein kleines Repo mit einer Testdatei: ein Test mit Kennung, einer ohne."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_beispiel.py").write_text(
        "import pytest\n\n\n"
        '@pytest.mark.rechtematrix("XY-01")\n'
        "def test_mit_kennung():\n    pass\n\n\n"
        '@pytest.mark.rechtematrix("XY-01")\n'
        "def test_verboten_im_namen():\n    pass\n\n\n"
        "def test_ohne_kennung():\n    pass\n",
        encoding="utf-8",
    )
    return tmp_path


def matrix_with(stand: str) -> str:
    """Ein Eintrag XY-01, gebaut, und seine Zeile unter „Tests je Kennung“."""
    return HEADER + "| XY-01 | Beispiel | BER-01 | gebaut |\n\n" + TESTS_HEADER + f"| XY-01 | {stand} |\n"


def test_gegenprobe_mit_vorhandenen_tests_ist_gruen(repo):
    stand = "gebaut: erlaubt `tests/test_beispiel.py::test_mit_kennung`; verboten `tests/test_beispiel.py::test_mit_kennung`"

    assert broken_test_references(matrix_with(stand), repo) == []


@pytest.mark.parametrize(
    "stand",
    [
        "gebaut: erlaubt `tests/test_beispiel.py::test_gibt_es_nicht`; verboten `tests/test_beispiel.py::test_mit_kennung`",
        "gebaut: erlaubt `tests/test_fehlt.py::test_mit_kennung`; verboten `tests/test_beispiel.py::test_mit_kennung`",
        "gebaut: erlaubt `tests/test_beispiel.py::test_mit_kennung`; verboten `tests/test_beispiel.py::test_ohne_kennung`",
        "gebaut: erlaubt `tests/test_beispiel.py::test_mit_kennung`",
        "gebaut: verboten `tests/test_beispiel.py::test_mit_kennung`",
        (
            "gebaut: erlaubt `tests/test_beispiel.py::test_mit_kennung`, `tests/test_beispiel.py::test_verboten_im_namen`, "
            "`tests/test_beispiel.py::test_mit_kennung`"
        ),
    ],
    ids=["test_fehlt", "datei_fehlt", "ohne_kennung", "verboten_fehlt", "erlaubt_fehlt", "verboten_nur_im_namen"],
)
def test_fehlender_oder_unmarkierter_test_macht_die_pruefung_rot(repo, stand):
    """S2, Gegenprobe."""
    problems = broken_test_references(matrix_with(stand), repo)

    assert len(problems) == 1
    assert "XY-01" in problems[0]


def test_gebaute_kennung_ohne_tests_je_kennung_ist_rot():
    """S2, Gegenprobe: Fehlt die Zeile unter „Tests je Kennung“, fällt die gebaute Kennung auf."""
    problems = broken_test_references(HEADER + "| XY-01 | Beispiel | BER-01 | gebaut (#90) |\n", MATRIX.parent.parent)

    assert problems == ["XY-01: keine Zeile unter „Tests je Kennung“"]


# S4: Jede Kennung hat genau einen Eintrag


def test_jede_kennung_kommt_nur_einmal_vor():
    assert duplicate_ids(matrix_text()) == []


def test_doppelte_kennung_macht_die_pruefung_rot():
    """S4, Gegenprobe: doppelter Eintrag, auch in einem anderen Abschnitt."""
    row = "| XY-01 | Beispiel | BER-01 | geplant (#90) |\n"
    other = "| XY-02 | Beispiel | BER-01 | geplant (#90) |\n"

    assert duplicate_ids(HEADER + row + other + "\n## Weiter\n\n" + HEADER + row) == ["XY-01"]


def test_doppelte_zeile_unter_tests_je_kennung_ist_rot():
    """Gegenprobe (#139, Befund der unabhängigen Prüfung): Eine zweite Zeile derselben Kennung
    unter „Tests je Kennung“ überschreibt die erste nicht still."""
    entry = HEADER + "| XY-01 | Beispiel | BER-01 | gebaut |\n\n"
    tests = TESTS_HEADER + "| XY-01 | gebaut: erlaubt `a`; verboten `b` |\n"

    assert duplicate_ids(entry + tests + "\n" + tests) == ["XY-01"]
    assert duplicate_ids(entry + tests) == []


# Korrekturen nach dem externen Review (#136)

# Zeilen je Kennung im ersten Entwurf vom 23.10.2026. Issues und Tests nennen diese Kennungen;
# fällt ein Recht weg, wird seine Zeile zum Verbot, statt zu verschwinden (#136).
FIRST_DRAFT = {"EP": 8, "PK": 23, "VP": 16, "EH": 21, "RO": 19, "VA": 4, "AN": 6, "GA": 5, "SZ": 6, "PR": 6, "TD": 1}


def missing_first_draft_ids(text: str) -> list[str]:
    expected = {f"{prefix}-{number:02d}" for prefix, count in FIRST_DRAFT.items() for number in range(1, count + 1)}
    return sorted(expected - row_ids(text))


def test_kennungen_des_ersten_entwurfs_bleiben_bestehen():
    assert missing_first_draft_ids(matrix_text()) == []


def test_entfernte_zeile_macht_die_pruefung_rot():
    """Gegenprobe."""
    text = "\n".join(line for line in matrix_text().splitlines() if not line.startswith("| RO-12 |"))

    assert missing_first_draft_ids(text) == ["RO-12"]


def test_entfallene_rechte_stehen_als_verbot():
    """Grundsatz 2 (RO-12, RO-16: niemand gibt sich selbst eine Rolle) und C2 (PK-11: keine
    Namenssuche nach Konten ohne Zuordnung). Seit #139 stehen sie im Block „Was niemand darf“."""
    assert {"RO-12", "RO-16", "PK-11"} <= forbidden_ids(matrix_text())


def test_entfallenes_recht_im_raster_ist_rot():
    """Gegenprobe: Steht PK-11 nicht mehr unter „Was niemand darf“, fällt das auf."""
    text = matrix_text()
    line = next(line for line in text.splitlines() if line.startswith("- PK-11"))

    assert "PK-11" not in forbidden_ids(text.replace(line, line.replace("- PK-11", "- PK-15", 1)))


def test_pfad_heisst_kette_nach_oben_oder_leitungspfad():
    """A1: „Pfad“ allein ist mehrdeutig; die Lesehilfe erklärt beide Begriffe."""
    text = matrix_text()
    reading = text.split("## So liest man die Matrix", 1)[1].split("\n## ", 1)[0]

    assert stray_path_words(text) == []
    assert "**Kette nach oben:**" in reading
    assert "**Leitungspfad" in reading


def test_mehrdeutiger_pfad_ist_rot():
    """Gegenprobe."""
    assert stray_path_words("Leitungen auf dem eigenen Pfad; Pfad-Regel; Leitungspfad") == ["Pfad"]


def test_verweise_zeigen_auf_vorhandene_zeilen_und_anforderungen():
    known = requirement_ids(REQUIREMENTS.read_text(encoding="utf-8"))

    assert {"BER-01", "ROL-02", "ORG-06"} <= known
    assert dangling_references(matrix_text(), known) == []


def test_verweis_ins_leere_ist_rot():
    """Gegenprobe: eine entfallene Kennung und vertippte Anforderungen, auch mit vier Buchstaben."""
    text = matrix_text().replace("(RO-01)", "(RO-99)", 1).replace("ORG-06", "ORG-66", 1).replace("TEAM-01", "TEAM-99", 1)
    known = requirement_ids(REQUIREMENTS.read_text(encoding="utf-8"))

    assert dangling_references(text, known) == ["ORG-66", "RO-99", "TEAM-99"]


# Folgekorrekturen nach PR #135 (#150)


def requirements_text() -> str:
    return REQUIREMENTS.read_text(encoding="utf-8")


def glossary(text: str) -> dict[str, str]:
    """Begriff und Bedeutung aus dem Glossar am Ende von `docs/anforderungen.md`."""
    part = text.split("\n## Glossar\n", 1)[1]
    found = {}
    for line in part.splitlines():
        if line.startswith("| "):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            found[cells[0]] = cells[1]
    return found


def visibility_table(text: str) -> dict[str, list[str]]:
    """Die Tabelle unter der Einleitung zu BER-01, je Zeile die Zellen nach „Wer“."""
    part = text.split("| Wer | Verwaltete Personen |", 1)[1].split("\n\n", 1)[0]
    found = {}
    for line in part.splitlines()[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        found[cells[0]] = cells[1:]
    return found


def requirement(text: str, requirement_id: str) -> str:
    return re.search(rf"^\| {requirement_id} \| (.+?) \|", text, flags=re.MULTILINE).group(1)


OWN_CIRCLE = re.compile(r"\beigene[nmrs]?\s+Kreis", flags=re.IGNORECASE)


def test_kette_nach_oben_steht_im_glossar():
    """Punkt 5 und C3: BER-01, Grund 3 nennt den Begriff; er beginnt auch bei der geleiteten Einheit."""
    meaning = glossary(requirements_text()).get("Kette nach oben", "")

    assert "Mitgliedschaft" in meaning
    assert "jede Einheit, die sie leitet" in meaning
    assert "RO-01" in meaning


def test_kette_nach_oben_beginnt_auch_bei_der_geleiteten_einheit():
    """C3: In der Lesehilfe der Matrix steht dieselbe Regel wie im Glossar, mit dem Beispiel Berta."""
    reading = matrix_text().split("**Kette nach oben:**", 1)[1].split("\n- **", 1)[0]

    assert "jede Einheit, die sie leitet" in reading
    assert "Berta" in reading
    assert "Ein Mitglied ohne Leitungsrolle, das direkt im Bund ist" in reading


def test_es_heisst_nur_noch_kreis():
    """Punkt 11: „Kreis“ statt „eigener Kreis“ (Entscheidung vom 24.10.2026, Nr. 10)."""
    assert OWN_CIRCLE.findall(requirements_text()) == []
    assert OWN_CIRCLE.findall(matrix_text()) == []


def test_eigener_kreis_ist_rot():
    """Gegenprobe."""
    assert len(OWN_CIRCLE.findall("eigene Kreise, eigenen Kreis, Eigener Kreis, Kreise")) == 3


def test_kreis_erstellen_nur_mit_zuordnung():
    """Punkt 4: GRP-01 folgt der Entscheidung vom 24.10.2026, Nr. 4."""
    assert requirement(requirements_text(), "GRP-01").startswith("Jede Person mit Zuordnung (BER-03)")


def test_tabelle_zu_ber_01_nennt_grund_3_und_4():
    """Punkte 1 und 2: Ausnahmen bei Personen fremder Einheiten, Veranstaltungen ausgeschrieben."""
    table = visibility_table(requirements_text())

    for who in ("Gruppenleitung", "Stammesleitung", "Ring-/Bundesleitung", "Verbandsleitung"):
        assert table[who][1] == "nein (außer BER-01, Grund 3 und 4)", who
    assert table["DPV-Veranstaltungsteam"][1] == "nein"
    for who, cells in table.items():
        if who != "Admin":
            assert cells[3] == "Veranstaltungen, in deren Teilnahmekreis sie sind (BER-04), und geleitete Veranstaltungen", who


# Umbau ins Raster (#139)


def test_jede_kennung_steht_in_einem_raster_oder_unter_was_niemand_darf():
    text = matrix_text()

    assert grid_rows(text)
    assert forbidden_ids(text)
    assert unplaced_ids(text) == []


def test_kennung_ausserhalb_von_raster_und_verboten_ist_rot():
    """Gegenprobe: VP-01 aus der Spalte „Kennungen“ genommen; der Eintrag bleibt."""
    text = matrix_text()
    line = next(line for line in text.splitlines() if line.startswith("| anlegen |") and "VP-01, " in line)

    assert unplaced_ids(text.replace(line, line.replace("VP-01, ", ""))) == ["VP-01"]


def test_jede_genannte_kennung_hat_einen_eintrag():
    assert ids_without_entry(matrix_text()) == []


def test_kennung_ohne_eintrag_ist_rot():
    """Gegenprobe: Der Eintrag zu VP-01 fehlt, das Raster nennt die Kennung weiter."""
    text = "\n".join(line for line in matrix_text().splitlines() if not line.startswith("| VP-01 | "))

    assert ids_without_entry(text) == ["VP-01"]


def test_jede_zelle_beginnt_mit_einem_wort_der_liste():
    assert bad_cells(matrix_text()) == []


def test_lesehilfe_erklaert_jedes_wort_der_liste():
    reading = matrix_text().split("## So liest man die Matrix", 1)[1].split("\n## ", 1)[0]

    for word in SCOPE_WORDS:
        assert f"**{word}:**" in reading or f"**„{word}“:**" in reading, word


@pytest.mark.parametrize(
    "cell",
    ["Stamm", "eigene Einheiten", "jaja", "Bereich ohne Komma", "eigene Einheit,", "eigene Einheit¹²", "x, Bereich"],
)
def test_zelle_ohne_wort_der_liste_ist_rot(cell):
    """Gegenprobe: eine Zelle mit anderem Wort, ohne Komma vor der Grenze oder mit leerer Grenze."""
    grid = "| Recht | GL | StL | RL | BL | Mitgl. | o. Zuord. | VL | DPV-VT | Admin | Kennungen |\n| --- |" + " --- |" * 10 + "\n"
    row = f"| anlegen | {cell} | Bereich | eine Ebene tiefer¹ | eigene Einheit, nur ohne Ringe | – | – | ja | – | – | XY-01 |\n"

    assert bad_cells("## Beispiel\n\n" + grid + row) == [f"Beispiel: anlegen: GL: {cell.strip()}"]


def test_zellen_mit_wort_hochzahl_und_grenze_sind_gruen():
    """Gegenprobe zur Gegenprobe."""
    grid = "| Recht | GL | StL | RL | BL | Mitgl. | o. Zuord. | VL | DPV-VT | Admin | Kennungen |\n| --- |" + " --- |" * 10 + "\n"
    row = "| anlegen | eigene Einheit | Bereich, nur auf dem Leitungspfad der Person | eine Ebene tiefer¹ | –² | nur sich selbst | ja | Verbandsebene | – | – | XY-01, XY-02 |\n"

    assert bad_cells("## Beispiel\n\n" + grid + row) == []


def test_rasterzeile_mit_fehlender_zelle_oder_ohne_kennung_ist_rot():
    grid = "| Recht | GL | StL | RL | BL | Mitgl. | o. Zuord. | VL | DPV-VT | Admin | Kennungen |\n| --- |" + " --- |" * 10 + "\n"
    short = "| anlegen | – | – | – | – | – | – | – | – | XY-01 |\n"
    without = "| löschen | – | – | – | – | – | – | – | – | – | Kennung fehlt |\n"

    assert len(bad_cells("## Beispiel\n\n" + grid + short + without)) == 2


def test_ueber_jedem_raster_steht_der_satz_zur_einspringenden_leitung():
    assert sections_without_lead_sentence(matrix_text()) == []


def test_raster_ohne_den_satz_ist_rot():
    """Gegenprobe: Im Abschnitt „Verwaltete Personen“ fehlt der Satz."""
    text = replace_in_section(matrix_text(), "Verwaltete Personen", LEAD_SENTENCE, "Siehe Lesehilfe.")

    assert sections_without_lead_sentence(text) == ["Verwaltete Personen"]


def test_lesehilfe_nennt_die_genaue_regel_zum_einspringen():
    reading = matrix_text().split("## So liest man die Matrix", 1)[1].split("\n## ", 1)[0]

    assert "höchstens bis zur Bundesleitung, nie die Verbandsleitung" in reading
    assert "angezeigte Leitungsrolle" in reading
    assert "gesperrt" in reading


def test_jeder_punkt_unter_was_niemand_darf_nennt_kennung_und_geltung():
    text = matrix_text()

    assert FORBIDDEN_START in text
    assert bad_forbidden_items(text) == []


@pytest.mark.parametrize(
    "item",
    ["- VP-13: Bestätigung ändern", "- Bestätigung ändern (im Tool): VP-13", "- VP-13 (): Bestätigung ändern", "- VP-13 (im Tool):"],
    ids=["ohne_geltung", "ohne_kennung_am_anfang", "leere_geltung", "ohne_text"],
)
def test_punkt_ohne_kennung_oder_geltung_ist_rot(item):
    """Gegenprobe."""
    text = f"## Beispiel\n\n{FORBIDDEN_START}\n\n- VP-12 (in P2): Bestätigung ansehen\n{item}\n"

    assert bad_forbidden_items(text) == [item]
    assert forbidden_ids(text) == {"VP-12"}
