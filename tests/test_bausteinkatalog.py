"""Tests für den Bausteinkatalog unter /bausteine/ (#176, docs/gestaltung.md, NFA-03).

Die Nummern verweisen auf Sebastians Szenarien zu #176 vom 27.10.2026
(https://github.com/sebivtt/dpv-participant-management/issues/176). Der Katalog zeigt nur
entschiedene Bausteine, jeden über dasselbe Vorlagenstück wie die echten Seiten. Szenario 9
(Barrierefreiheit am PC und am Handy) prüft der Rauchtest in rauchtests/test_rauchtest.py.
Alle Daten sind erfunden.
"""

import re
from pathlib import Path

import pytest
from django.test import Client

from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree
from tests.test_rechte_ohne_seite import org  # noqa: F401 -- Fixture mit Personen in allen Rollen
from tests.test_rundumtest import ALL, PUBLIC, _example_address
from tests.test_rollen import build_org

pytestmark = pytest.mark.django_db

ADDRESS = "/bausteine/"
ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "core" / "templates" / "core" / "bausteine.html"
LAYOUT = ROOT / "core" / "templatetags" / "layout.py"


def _client_for(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _section(root, heading_id: str):
    return _one(_by_tag(root, "section", aria_labelledby=heading_id))


# ---------- Szenario 1: angemeldet auf dem eigenen Rechner oder in der Testumgebung ----------


@pytest.mark.parametrize("environment", ["eigener Rechner", "Testumgebung"])
def test_angemeldet_zeigt_der_katalog_jeden_baustein_mit_zweck_und_issue(settings, environment):
    settings.BUILDING_BLOCKS_VISIBLE = True
    settings.TEST_ENVIRONMENT = environment == "Testumgebung"
    people = build_org()

    root = _tree(_client_for(people.erika).get(ADDRESS))

    entries = _all(root, lambda e: e.name == "section" and "a-baustein" in _classes(e))
    assert len(entries) >= 7
    for entry in entries:
        name = _text(_one(_by_tag(entry, "h2")))
        purpose = _one(_all(entry, lambda e: "a-baustein-zweck" in _classes(e)))
        assert _text(purpose).endswith("."), f"„{name}“ ohne Satz zum Zweck"
        decided = _one(_all(entry, lambda e: "a-baustein-herkunft" in _classes(e)))
        assert re.search(r"Entschieden in\s+#\d+", _text(decided)), f"„{name}“ ohne Issue, das ihn entschieden hat"
    names = [_text(_one(_by_tag(entry, "h2"))) for entry in entries]
    for name in ("Meldungen", "Textfeld", "Feld zum Antippen", "Rollenkachel", "Profilkreis",
                 "Band der Testumgebung", "Knöpfe der Fehlerseite"):
        assert name in names, f"Baustein „{name}“ fehlt im Katalog"


def test_eigener_rechner_und_testumgebung_zeigen_den_katalog_im_betrieb_nicht():
    """BUILDING_BLOCKS_VISIBLE ergibt sich aus den Einstellungen des Rechners (config/settings.py)."""
    from tests.test_testumgebung import _setting

    assert _setting("settings.BUILDING_BLOCKS_VISIBLE", {"DJANGO_DEBUG": "1"}) == "True"
    assert _setting("settings.BUILDING_BLOCKS_VISIBLE", {"TEST_ENVIRONMENT": "1"}) == "True"
    assert _setting("settings.BUILDING_BLOCKS_VISIBLE", {}) == "False"


# ---------- Szenario 2: dasselbe Vorlagenstück wie auf den echten Seiten ----------


def _included(source: str) -> set[str]:
    """Vorlagenstücke, die eine Vorlage einbindet: mit include und über die Bausteine aus layout.py.

    Kommentare zählen nicht; sie nennen Bausteine oft nur als Beispiel, z. B. „{% textfeld form.feld %}“.
    """
    source = re.sub(r"{#.*?#}|{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", "", source, flags=re.S)
    names = set(re.findall(r"""{%\s*include\s+["']([^"']+)["']""", source))
    # Ein include mit einer Variablen statt eines festen Namens könnte hier nicht erkannt werden.
    assert not re.search(r"""{%\s*include\s+[^"'\s]""", source), "include ohne festen Namen"
    layout = LAYOUT.read_text()
    tags = dict(re.findall(r'@register\.inclusion_tag\("([^"]+)"\)\ndef (\w+)\(', layout))
    assert len(tags) == layout.count("@register.inclusion_tag"), "Baustein in layout.py in unbekannter Form"
    by_tag = {tag: template for template, tag in tags.items()}
    names |= {by_tag[tag] for tag in re.findall(r"{%\s*(\w+)", source) if tag in by_tag}
    return names


def test_katalog_und_mein_profil_binden_dieselben_vorlagenstuecke_ein():
    catalog = _included(CATALOG.read_text())
    profile = _included((ROOT / "core" / "templates" / "core" / "profil.html").read_text())

    shared = {"core/_meldung.html", "core/_antippfeld.html", "core/_rollenkachel.html"}
    assert shared <= profile, "„Mein Profil“ bindet die Bausteine nicht mehr ein"
    assert shared | {"core/_textfeld.html", "core/_profilkreis.html"} <= catalog


def test_meldungen_im_katalog_wie_auf_mein_profil(settings):
    settings.BUILDING_BLOCKS_VISIBLE = True
    people = build_org()
    client = _client_for(people.erika)

    catalog = _section(_tree(client.get(ADDRESS)), "h-meldungen")
    profile = _tree(client.get("/profil/"))

    in_catalog = {tuple(_classes(e)) for e in _all(catalog, lambda e: "a-meldung" in _classes(e))}
    on_profile = {tuple(_classes(e)) for e in _all(profile, lambda e: "a-meldung" in _classes(e))}
    assert in_catalog == {("a-meldung", kind) for kind in ("ist-info", "ist-warnung", "ist-fehler", "ist-erfolg")}
    assert on_profile <= in_catalog


# ---------- Szenario 3: entschieden, aber noch auf keiner Seite ----------


def test_baustein_ohne_echte_seite_traegt_den_vermerk(settings):
    settings.BUILDING_BLOCKS_VISIBLE = True
    people = build_org()

    root = _tree(_client_for(people.erika).get(ADDRESS))

    entries = _all(root, lambda e: e.name == "section" and "a-baustein" in _classes(e))
    for entry in entries:
        name = _text(_one(_by_tag(entry, "h2")))
        where = _text(_one(_all(entry, lambda e: "a-baustein-seiten" in _classes(e))))
        assert where == "noch auf keiner Seite" or where.startswith("Genutzt auf: "), f"„{name}“: {where}"
    # Das Textfeld bindet bisher keine Seite selbst ein; das Feld zum Antippen nutzt nur seine Eingabe.
    textfield = _one([e for e in entries if _text(_one(_by_tag(e, "h2"))) == "Textfeld"])
    assert _text(_one(_all(textfield, lambda e: "a-baustein-seiten" in _classes(e)))) == "noch auf keiner Seite"


def test_vermerk_noch_auf_keiner_seite_ohne_seiten_sonst_die_seiten():
    """Gegenprobe zum Vermerk: ohne Seite „noch auf keiner Seite“, mit Seiten deren Namen."""
    from django.template.loader import render_to_string

    def where(pages) -> str:
        block = {"id": "h-neu", "name": "Neu", "purpose": "Zum Testen.", "issues": [999], "pages": pages}
        root = _tree_of(render_to_string("core/_katalogeintrag.html", {"block": block}))
        return _text(_one(_all(root, lambda e: "a-baustein-seiten" in _classes(e))))

    assert where([]) == "noch auf keiner Seite"
    assert where(["Mein Profil", "Login-Seite"]) == "Genutzt auf: Mein Profil, Login-Seite"


def test_vermerk_passt_zu_den_vorlagen():
    """Ein Baustein mit Vermerk bindet keine Seite ein; einer mit Seiten wird irgendwo eingebunden."""
    from core.views import BUILDING_BLOCKS

    used = set()
    for name, source in _all_templates().items():
        if name != "core/bausteine.html":
            used |= _included(source)
    for block in BUILDING_BLOCKS.values():
        assert bool(block["pages"]) == (block["template"] in used), block["name"]


def _tree_of(html: str):
    from django.test.html import parse_html

    return parse_html(html)


# ---------- Szenario 4: ohne Login ----------


def test_ohne_login_fuehrt_der_katalog_zum_login(settings):
    settings.BUILDING_BLOCKS_VISIBLE = True

    response = Client().get(ADDRESS)

    assert response.status_code == 302
    assert response["Location"] == "/anmelden/?next=/bausteine/"


# ---------- Szenario 5: im Betrieb nicht, auch nicht für Admins ----------


def _missing(response) -> None:
    assert response.status_code == 404
    assert "Diese Seite gibt es nicht." in response.content.decode()


def test_im_betrieb_gibt_es_den_katalog_nicht_auch_nicht_fuer_admins(settings, org):  # noqa: F811
    settings.BUILDING_BLOCKS_VISIBLE = False
    settings.TEST_ENVIRONMENT = False

    for user in org.everyone:
        _missing(_client_for(user).get(ADDRESS))
        _missing(_client_for(user).post(ADDRESS))


def test_gegenprobe_dieselben_personen_sehen_den_katalog_auf_dem_eigenen_rechner(settings, org):  # noqa: F811
    settings.BUILDING_BLOCKS_VISIBLE = True

    for user in org.everyone:
        assert _client_for(user).get(ADDRESS).status_code == 200


# ---------- Szenario 6: die alte Adresse ----------


@pytest.mark.parametrize("visible", [True, False])
def test_die_alte_adresse_der_musterseite_gibt_es_nicht(settings, visible):
    settings.BUILDING_BLOCKS_VISIBLE = visible
    people = build_org()

    _missing(_client_for(people.erika).get("/muster/"))


# ---------- Szenario 7: Eingabefelder nur aus Bausteinen ----------

# Bausteine, aus denen ein Eingabefeld kommen darf: Textfeld (#111) und Feld zum Antippen (#180).
FIELD_BLOCKS = ("a-textfeld", "a-antippfeld")


def self_built_fields(html: str) -> list[str]:
    """Eingabefelder einer Seite, die nicht aus einem Baustein kommen, als Name oder Kennung.

    Versteckte Felder (z. B. der Formularschutz) und Knöpfe sind keine Eingabefelder.
    """
    from django.test.html import parse_html

    found = []

    def walk(element, inside_block: bool) -> None:
        for child in getattr(element, "children", []):
            if isinstance(child, str):
                continue
            in_block = inside_block or any(block in _classes(child) for block in FIELD_BLOCKS)
            is_field = child.name in ("input", "select", "textarea") and _attr(child, "type") not in (
                "hidden", "submit", "button", "reset")
            if is_field and not in_block:
                found.append(_attr(child, "name") or _attr(child, "id") or child.name)
            walk(child, in_block)

    walk(parse_html(html), False)
    return found


def _real_pages(org):  # noqa: F811
    """Jede echte Seite des Tools (ohne Katalog), als jede Person, lesend und mit Formular."""
    yield "Login-Seite", Client().get("/anmelden/")
    for pattern, entry in ALL:
        if entry.name == "building_blocks" or entry.name in PUBLIC:
            continue
        address = _example_address(pattern)
        for user in org.everyone:
            yield address, _client_for(user).get(address)
            yield f"{address} (Formular)", _client_for(user).post(address, {"scout_name": "x" * 500})


def test_jedes_eingabefeld_auf_echten_seiten_kommt_aus_einem_baustein(org):  # noqa: F811
    found = {}
    for page, response in _real_pages(org):
        if "html" in response.get("Content-Type", ""):
            fields = self_built_fields(response.content.decode())
            if fields:
                found[page] = fields

    assert found == {}, f"Selbst gebaute Eingabefelder statt Baustein (docs/gestaltung.md): {found}"


def test_gegenprobe_selbst_gebautes_feld_macht_die_pruefung_rot():
    page = """<form><input type="hidden" name="csrfmiddlewaretoken" value="x">
        <div class="a-textfeld"><label for="ort">Ort</label><input id="ort" name="ort"></div>
        <label for="name">Name</label><input id="name" name="name" class="form-control">
        <select name="stamm"><option>Stamm Walhall</option></select>
        <button type="submit">Speichern</button></form>"""

    assert self_built_fields(page) == ["name", "stamm"]


# ---------- Szenario 8: jedes Vorlagenstück, das Seiten einbinden, steht im Katalog ----------

# Vorlagenstücke, die Seiten einbinden, ohne dass sie als eigener Baustein in den Katalog gehören.
NOT_IN_CATALOG = {
    # Die Symbole: jedes ist Teil eines Bausteins und steht mit ihm im Katalog.
    "core/_symbole.svg": "Symbole",
    "core/lilie.svg": "Logo, Teil der Marke und der Login-Seite",
    # Der Rahmen jeder Seite mit Login (base_app.html): Der Katalog steht selbst darin.
    "core/_marke.html": "Rahmen jeder Seite",
    "core/_navigation.html": "Rahmen jeder Seite",
    "core/_konto.html": "Rahmen jeder Seite",
    "core/_fuss.html": "Rahmen jeder Seite",
}


def _all_templates() -> dict[str, str]:
    """Jede Vorlage des Tools mit dem Namen, den include nutzt, z. B. core/profil.html oder base_app.html."""
    found = {}
    for path in ROOT.glob("*/templates/**/*"):
        if path.is_file() and path.suffix in (".html", ".svg"):
            found["/".join(path.relative_to(ROOT).parts[2:])] = path.read_text()
    return found


def missing_from_catalog(templates: dict[str, str], catalog: str) -> list[str]:
    """Vorlagenstücke, die eine Vorlage außer dem Katalog einbindet und die der Katalog nicht zeigt."""
    used = set()
    for name, source in templates.items():
        if name != "core/bausteine.html":
            used |= _included(source)
    return sorted(used - _included(catalog) - set(NOT_IN_CATALOG))


def test_jedes_eingebundene_vorlagenstueck_steht_im_katalog():
    templates = _all_templates()
    assert "core/profil.html" in templates and "base_app.html" in templates

    assert missing_from_catalog(templates, CATALOG.read_text()) == []


def test_gegenprobe_neues_vorlagenstueck_ohne_katalog_macht_die_pruefung_rot():
    templates = dict(_all_templates(), **{"core/neue_seite.html": '{% include "core/_neu.html" %}'})

    assert missing_from_catalog(templates, CATALOG.read_text()) == ["core/_neu.html"]
    single_quotes = dict(templates, **{"core/neue_seite.html": "{% include 'core/_neu.html' %}"})
    assert missing_from_catalog(single_quotes, CATALOG.read_text()) == ["core/_neu.html"]
    with_entry = CATALOG.read_text() + '{% include "core/_neu.html" %}'
    assert missing_from_catalog(templates, with_entry) == []


def test_jede_ausnahme_wird_wirklich_eingebunden():
    """Bindet keine Vorlage eine Ausnahme mehr ein, gehört sie aus der Liste."""
    used = set()
    for source in _all_templates().values():
        used |= _included(source)

    assert set(NOT_IN_CATALOG) - used == set()
