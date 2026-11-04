"""Tests für den Helfer der Vorschau (`tests/vorschau.py`, Skill `vorschau`, #249).

Die Vorschau ist eine einzelne HTML-Datei aus den echten Vorlagen mit erfundenen Daten, die
Sebastian ohne Server im Browser öffnet. Der Helfer bettet Gestaltung und Skript ein, sperrt Links
und Formulare und zeigt jeden Fall in PC- und in Handybreite. Ändert `core/templates/base.html`,
welche Dateien eine Seite lädt, soll die Vorschau nicht still ungestaltet bleiben, sondern laut
scheitern. Alle Seiten und Daten sind erfunden.
"""

import html
import re
import subprocess
from pathlib import Path

import pytest
from django.test import Client

from tests import vorschau
from tests.vorschau import schreibe_vorschau

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC = BASE_DIR / "core" / "static" / "core"

pytestmark = pytest.mark.django_db

# Kleinste Seite, die die Vorschau annimmt: Sie lädt ein echtes Stylesheet, aber kein Skript.
GESTALTET = '<link rel="stylesheet" href="/static/core/app.css">'


def _seite(inhalt):
    return f"<html><head>{GESTALTET}</head><body>{inhalt}</body></html>"


def _login_seite():
    antwort = Client().get("/anmelden/")
    assert antwort.status_code == 200
    return antwort.content.decode()


def _vorschau(tmp_path, faelle, name="vorschau-1.html"):
    ziel = tmp_path / "lokal" / name
    ergebnis = schreibe_vorschau(faelle, ziel)
    assert Path(ergebnis) == ziel
    assert ziel.is_file(), "Es wurde keine Datei geschrieben"
    return ziel.read_text(encoding="utf-8")


def test_vorschau_verweist_nicht_auf_static_und_bettet_gestaltung_und_skript_ein(tmp_path):
    text = _vorschau(tmp_path, [("Login", _login_seite())])

    assert "/static/" not in text
    assert (STATIC / "app.css").read_text(encoding="utf-8").strip() in html.unescape(text)
    assert (STATIC / "bootstrap" / "bootstrap.min.css").read_text(encoding="utf-8").strip() in html.unescape(text)
    skript = (STATIC / "app.js").read_text(encoding="utf-8").strip().replace("</", "<\\/")
    assert skript in html.unescape(text)


def test_vorschau_zeigt_den_inhalt_der_echten_seite(tmp_path):
    text = html.unescape(_vorschau(tmp_path, [("Login", _login_seite())]))

    assert "Mit DPV-Konto anmelden" in text


def test_jeder_fall_erscheint_in_pc_und_in_handybreite(tmp_path):
    seite = _login_seite()
    text = _vorschau(tmp_path, [("Erster Fall", seite), ("Zweiter Fall", seite), ("Dritter Fall", seite)])

    for name in ["Erster Fall", "Zweiter Fall", "Dritter Fall"]:
        assert name in text, name
    assert len(re.findall(r"<iframe\b", text)) == 6, "je Fall ein Rahmen für PC und einer für das Handy"
    assert len(re.findall(r'<iframe\b[^>]*\bwidth="390"', text)) == 3, "je Fall ein Rahmen in Handybreite"
    assert "Handy" in text and "PC" in text
    assert len(re.findall(r'<nav>.*?</nav>', text, re.S)) == 1
    assert len(re.findall(r'<button type="button">', text.split("</nav>")[0])) == 3, "je Fall ein Knopf zum Umschalten"
    assert 'addEventListener("click", function () { zeige(n); })' in text, "Die Knöpfe schalten nicht um"


def test_vorschau_zeigt_nicht_mehr_als_die_genannten_faelle(tmp_path):
    text = _vorschau(tmp_path, [("Nur einer", _seite("<p>Hallo</p>"))])

    assert len(re.findall(r"<iframe\b", text)) == 2


def test_vorschau_sperrt_links_und_formulare_in_jeder_seite(tmp_path):
    text = html.unescape(_vorschau(tmp_path, [("Fall", _seite("Hallo"))]))

    # Die Seite lädt kein Skript: Was hier steht, kommt allein aus der Sperre des Helfers.
    assert text.count(vorschau._SPERRE) == 2, "je Rahmen einmal"
    assert 'a[href]' in vorschau._SPERRE
    assert re.search(r"addEventListener\(\s*[\"']submit[\"']", vorschau._SPERRE), "Formulare sind nicht gesperrt"


def test_sperre_haelt_das_schliessen_eines_dialogs_auf():
    """`app.js` lädt beim Schließen von `dialog[data-dialog]` eine neue Adresse; im Rahmen führte das ins Leere."""
    assert re.search(r"addEventListener\(\s*[\"']cancel[\"']", vorschau._SPERRE), "Escape am Dialog ist nicht gesperrt"
    assert "dialog[data-dialog]" in vorschau._SPERRE, "Klicks neben den Dialog sind nicht gesperrt"
    assert "stopPropagation" in vorschau._SPERRE, "Das Ereignis erreicht sonst `app.js`"


def test_vorschau_legt_einen_fehlenden_ordner_lokal_an(tmp_path):
    ziel = tmp_path / "gibt-es-noch-nicht" / "lokal" / "vorschau-7.html"
    assert not ziel.parent.exists()

    schreibe_vorschau([("Fall", _seite("Hallo"))], ziel)

    assert ziel.is_file()


def test_vorschau_wird_bei_einer_zweiten_runde_ueberschrieben(tmp_path):
    ziel = tmp_path / "lokal" / "vorschau-1.html"
    schreibe_vorschau([("Alt", _seite("Alt"))], ziel)
    schreibe_vorschau([("Neu", _seite("Neu"))], ziel)

    text = ziel.read_text(encoding="utf-8")
    assert "Neu" in text
    assert "Alt" not in text


@pytest.mark.parametrize(
    "einbindung",
    [
        '<link rel="stylesheet" href="/static/core/neu.css">',
        '<script src="/static/core/neu.js" defer></script>',
        '<img src="/static/core/logo.png" alt="">',
        '<link rel="stylesheet" href="/static/core/app.css"><link rel="icon" href="/static/core/favicon.ico">',
    ],
)
def test_wird_eine_statische_datei_nicht_eingebettet_scheitert_die_vorschau(tmp_path, einbindung):
    seite = f"<html><head>{einbindung}</head><body>Hallo</body></html>"
    ziel = tmp_path / "lokal" / "vorschau-1.html"

    with pytest.raises(ValueError, match="/static/core/"):
        schreibe_vorschau([("Fall", seite)], ziel)

    assert not ziel.exists(), "Eine halbe Vorschau darf nicht liegen bleiben"


@pytest.mark.parametrize(
    "seite",
    [
        "",
        "<html><body>Seite ohne Gestaltung</body></html>",
        '<html><head><link rel="stylesheet" href="https://example.test/fremd.css"></head><body>Hallo</body></html>',
    ],
    ids=["weiterleitung-ohne-inhalt", "ohne-stylesheet", "fremdes-stylesheet"],
)
def test_ungestaltete_seite_laesst_die_vorschau_scheitern(tmp_path, seite):
    ziel = tmp_path / "lokal" / "vorschau-1.html"

    with pytest.raises(ValueError, match="Fall"):
        schreibe_vorschau([("Fall", seite)], ziel)

    assert not ziel.exists(), "Eine ungestaltete Vorschau darf nicht liegen bleiben"


def test_ohne_faelle_entsteht_keine_vorschau(tmp_path):
    ziel = tmp_path / "lokal" / "vorschau-1.html"

    with pytest.raises(ValueError, match="keine Fälle"):
        schreibe_vorschau([], ziel)

    assert not ziel.exists()


def test_vorschau_folgt_einer_anderen_adresse_fuer_statische_dateien(tmp_path, settings):
    settings.STATIC_URL = "/dateien/"
    seite = '<html><head><link rel="stylesheet" href="/dateien/core/app.css"></head><body>Hallo</body></html>'

    text = html.unescape(_vorschau(tmp_path, [("Fall", seite)]))

    assert (STATIC / "app.css").read_text(encoding="utf-8").strip() in text
    assert "/dateien/" not in text


@pytest.mark.parametrize("ende", ["</style>", "</STYLE>"])
def test_stylesheet_mit_schlusszeichen_bleibt_im_stilblock(tmp_path, monkeypatch, ende):
    monkeypatch.setattr(vorschau, "_statische_datei", lambda pfad: f"/* {ende} */ body {{ color: red; }}")

    text = html.unescape(_vorschau(tmp_path, [("Fall", _seite("Hallo"))]))

    assert ende not in text.split("</style>", 1)[1].split("body { color: red; }")[0]


def test_skript_mit_schlusszeichen_bleibt_im_skriptblock(tmp_path, monkeypatch):
    monkeypatch.setattr(vorschau, "_statische_datei", lambda pfad: "var s = '</script>';")
    seite = _seite('<script src="/static/core/app.js"></script>')

    text = html.unescape(_vorschau(tmp_path, [("Fall", seite)]))

    assert "var s = '<\\/script>';" in text


def test_namen_der_faelle_werden_nicht_als_html_gelesen(tmp_path):
    text = _vorschau(tmp_path, [("<b>Fett</b> & mehr", _seite("Hallo"))])

    assert "<b>Fett</b>" not in text
    assert "&lt;b&gt;Fett&lt;/b&gt;" in text


def test_skript_der_seite_darf_den_umgebenden_rahmen_nicht_vorzeitig_beenden(tmp_path):
    seite = _seite("<script>var s = '</script>';</script>")
    text = _vorschau(tmp_path, [("Fall", seite)])

    assert len(re.findall(r"<iframe\b", text)) == 2
    assert text.count("</html>") == 1, "Die Seite des Falls muss im Rahmen eingeschlossen bleiben"


@pytest.mark.parametrize("pfad", ["tests/test_zz_vorschau_1.py", "tests/test_zz_vorschau_249.py", "lokal/vorschau-1.html"])
def test_git_ignoriert_voruebergehenden_test_und_vorschau_datei(pfad):
    befehl = ["git", "check-ignore", "-q", pfad]
    ergebnis = subprocess.run(befehl, cwd=BASE_DIR, check=False)  # noqa: S603 -- fester Befehl mit git

    assert ergebnis.returncode == 0, f"{pfad} wird von git nicht ignoriert"


def test_gitignore_erklaert_den_voruebergehenden_test():
    text = (BASE_DIR / ".gitignore").read_text(encoding="utf-8")

    assert "tests/test_zz_vorschau_*.py" in text
    assert "Vorübergehende Tests für die Vorschau (Skill `vorschau`), nie im Repo" in text
