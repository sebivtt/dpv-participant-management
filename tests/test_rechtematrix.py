"""Tests für die Form der Rechtematrix (#87, `docs/rechtematrix.md`).

S1, S2 und S4 verweisen auf die Szenarien im Issue #87 (Kommentar „Szenarien für die Umsetzung,
23.10.2026“). S3 prüfen die Protokolltests, die die Zeilen PR-02 und PR-04 nennen. Die Rechte
selbst prüfen die Tests, die eine gebaute Zeile nennt; diese hier prüfen nur, dass die Matrix
vollständig ist und jede gebaute Zeile auf echte Tests zeigt.
"""

import re

import pytest
from django.apps import apps
from django.db import models

from tests.rechtematrix import (
    MATRIX,
    broken_test_references,
    duplicate_ids,
    invalid_ids,
    matrix_text,
    missing_tables,
    rows,
    unknown_sections,
)

SECTIONS = [
    "Eigenes Profil",
    "Personen mit Konto",
    "Verwaltete Personen",
    "Einheiten",
    "Leitungen und Rollen",
    "Veranstaltungen und Anmeldungen",
    "Gesundheitsangaben",
    "Protokolle",
    "Tabellen in der Datenbank",
]

HEADER = "| Kennung | Wer | Daten | Aktion | Ergebnis | Quelle | Stand |\n| --- | --- | --- | --- | --- | --- | --- |\n"


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


def test_jede_zeile_nennt_alle_sieben_angaben():
    found = rows(matrix_text())

    assert found
    for cells in found:
        assert len(cells) == 7, cells
        assert all(cells), cells
        assert cells[4].startswith(("erlaubt", "verboten")), cells
        assert cells[6].startswith(("geplant", "gebaut")), cells


def test_jede_kennung_hat_die_vorgesehene_form():
    assert invalid_ids(matrix_text()) == []


@pytest.mark.parametrize("row_id", ["VP-2", "VP-100", "vp-02", "**VP-02**"])
def test_falsch_geschriebene_kennung_faellt_nicht_still_heraus(row_id):
    """Gegenprobe: Eine solche Zeile zählt mit und wird gemeldet."""
    text = HEADER + f"| {row_id} | Stammesleitung | Beispiel | ansehen | erlaubt | BER-01 | gebaut: erlaubt `tests/x.py::test_a` |\n"

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
    text = matrix_text().replace("| `units.Unit` | Einheiten | Einheiten |", "| `units.Unit` | Einheiten | Organisationen |")

    assert unknown_sections(text) == ["Organisationen"]


# S2: Jede gebaute Zeile zeigt auf Tests, die es gibt und die ihre Kennung tragen


def test_gebaute_zeilen_nennen_tests_mit_ihrer_kennung():
    text = matrix_text()

    assert any(cells[6].startswith("gebaut") for cells in rows(text))
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
    return HEADER + f"| XY-01 | Stammesleitung | Beispiel | ansehen | erlaubt | BER-01 | {stand} |\n"


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


# S4: Jede Kennung kommt nur einmal vor


def test_jede_kennung_kommt_nur_einmal_vor():
    assert duplicate_ids(matrix_text()) == []


def test_doppelte_kennung_macht_die_pruefung_rot():
    """S4, Gegenprobe."""
    row = "| XY-01 | Stammesleitung | Beispiel | ansehen | erlaubt | BER-01 | geplant (#90) |\n"
    other = "| XY-02 | Gruppenleitung | Beispiel | ansehen | verboten | BER-01 | geplant (#90) |\n"

    assert duplicate_ids(HEADER + row + other + "\n## Weiter\n\n" + HEADER + row) == ["XY-01"]
