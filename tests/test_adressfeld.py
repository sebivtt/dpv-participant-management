"""Tests für das Adressfeld mit Adresssuche über OpenStreetMap am Ort einer Veranstaltung (#163, VER-04).

Die Kennungen A1 bis A10, V1 bis V4 und G1 bis G9 verweisen auf die Szenarien vom 17.11.2026, Fassung nach dem
Zielbild (https://github.com/sebivtt/dpv-participant-management/issues/163#issuecomment-6943261413), die Wortlaute
auf den Text von #163. A10 (Handy, nur Tastatur) und das Ausblenden des Bundeslands im Browser prüft der Rauchtest
`rauchtests/test_adressfeld.py`. „Heute“ ist der 05.01.2028 wie in den Tests zu #379 und #380. Personen wie in den
Szenarien: Wanda (Stammesleitung Walhall), Fiete (Gruppenleitung Falken), Finn (Mitglied Sippe Falken), Otto (Konto
ohne Zuordnung), Max (nur Admin). Der Suchdienst ist nachgestellt (`tests/adresssuche_fake.py`); kein Test fragt das
echte OpenStreetMap. Alle Namen und Adressen sind erfunden.
"""

import logging
import threading
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest
from django.conf import settings as django_settings
from django.db import IntegrityError, connection, transaction
from django.test import Client
from django.utils import timezone

from access.rights import Rights
from core import address_search
from events.models import Event
from roles.models import Role
from tests.adresssuche_fake import ANSWERS, BURG
from tests.test_anmeldungen import start_support
from tests.test_benennen import dialog_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for
from tests.test_veranstaltungen import (
    CREATE,
    assert_no_access,
    build_people,
    edit_address,
    event_address,
    event_of,
)

pytestmark = pytest.mark.django_db
R = Role.Kind

TODAY = date(2028, 1, 5)
CREATE_SEARCH = "/veranstaltungen/erstellen/adresse-suchen/"
PFINGSTLAGER = {"name": "Pfingstlager 2028", "start": "2028-06-02", "start_time": "18:00", "end": "2028-06-05",
                "end_time": "12:00", "location": "Burg Ludwigstein"}
EMPTY_ADDRESS = {"street": "", "postal_code": "", "city": "", "state": "", "country": "DE"}
NOTHING_FOUND = "Keine Adresse gefunden. Du kannst sie unten selbst eintragen."
UNAVAILABLE = "Die Adresssuche ist gerade nicht erreichbar. Du kannst die Adresse unten selbst eintragen."
TOO_LITTLE = "Für die Suche gib bitte die Bezeichnung oder eine Straße mit PLZ oder Ort ein."
POSTAL_CODE_EMPTY = "Bitte gib die PLZ ein."
CITY_EMPTY = "Bitte gib den Ort ein."
FIVE_DIGITS = "Bitte gib 5 Ziffern ein."
SOURCE = "Adressdaten © OpenStreetMap-Mitwirkende"
SOURCE_LINK = "https://www.openstreetmap.org/copyright"
SEARCH_LABEL = "Adresse suchen"
TAKE_LABEL = "Übernehmen"
ADDRESS_NAMES = ("street", "postal_code", "city", "state", "country")


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    """Der Tag des Servers ist der 05.01.2028, wie in den Szenarien zu #379 und #380."""
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: TODAY)


@pytest.fixture
def org():
    return build_people()


@pytest.fixture
def pfingstlager(org):
    """Wandas „Pfingstlager 2028“ nach dem Anlegen, mit der Bezeichnung „Burg Ludwigstein“ und ohne Adresse (A7)."""
    entry = event_of(org.wanda, "Pfingstlager 2028", date(2028, 6, 2), date(2028, 6, 5))
    entry.location = "Burg Ludwigstein"
    entry.save()
    return entry


@pytest.fixture
def mit_adresse(pfingstlager):
    """Das Pfingstlager mit Adresse und Koordinaten aus einem übernommenen Treffer (A8)."""
    for name, value in {"street": "Burgweg 1", "postal_code": "99999", "city": "Musterhausen", "state": "HE",
                        "country": "DE", "latitude": Decimal("51.3260000"), "longitude": Decimal("9.9040000")}.items():
        setattr(pfingstlager, name, value)
    pfingstlager.save()
    return pfingstlager


# ---------- Adressen und Hilfen ----------


def basics_search_address(entry) -> str:
    return f"{event_address(entry)}anlegen/adresse-suchen/"


def edit_search_address(entry) -> str:
    return f"{edit_address(entry)}adresse-suchen/"


def address_field(root):
    """Der Baustein „Adressfeld“ auf der Seite."""
    return _one(_all(root, lambda e: "a-adressfeld" in _classes(e)))


def search_button(root):
    """Der zart blaue Knopf „Adresse suchen“ unter den Feldern."""
    return _one([button for button in _by_tag(address_field(root), "button") if _visible_text(button) == SEARCH_LABEL])


def search_target(root) -> str:
    """Wohin „Adresse suchen“ das Formular schickt, ohne die Stelle auf der Seite (#…)."""
    return _attr(search_button(root), "formaction").split("#")[0]


def hits(root) -> list[tuple[str, str]]:
    """Die Treffer der Adresssuche: Bezeichnung und Adresse, in ihrer Reihenfolge."""
    found = []
    for entry in _all(address_field(root), lambda e: e.name == "li" and "a-treffer" in _classes(e)):
        title = _visible_text(_one(_all(entry, lambda e: "a-leitung-name" in _classes(e))))
        line = _visible_text(_one(_all(entry, lambda e: "a-treffer-ort" in _classes(e))))
        found.append((title, line))
    return found


def take_buttons(root) -> list:
    """Die Knöpfe „Übernehmen“ der Treffer."""
    return [button for button in _by_tag(address_field(root), "button") if _visible_text(button) == TAKE_LABEL]


def notices(root) -> list[tuple[str, str]]:
    """Die Meldungen im Adressfeld: Art (Klasse) und sichtbarer Text."""
    found = []
    for entry in _all(address_field(root), lambda e: "a-meldung" in _classes(e)):
        kind = next(name for name in _classes(entry) if name.startswith("ist-"))
        found.append((kind, _visible_text(_one(_all(entry, lambda e: "a-meldung-text" in _classes(e))))))
    return found


def form_values(root, form_id: str) -> dict[str, str]:
    """Alles, was das Formular `form_id` abschickt: Eingaben (auch versteckte) und die gewählte Möglichkeit jeder Auswahl."""
    form = _one(_by_tag(root, "form", id=form_id))
    inside = {id(element) for element in _all(form, lambda e: e.name in ("input", "select"))}

    def belongs(element) -> bool:
        return element.name in ("input", "select") and (_attr(element, "form") == form_id or id(element) in inside)

    found = {}
    for element in _all(root, belongs):
        name = _attr(element, "name")
        if not name or name == "csrfmiddlewaretoken":
            continue
        if element.name == "select":
            chosen = [option for option in _by_tag(element, "option") if _attr(option, "selected") is not None]
            found[name] = _attr(chosen[0], "value") if chosen else ""
        elif _attr(element, "type") == "checkbox":
            if _attr(element, "checked") is not None:
                found[name] = _attr(element, "value") or "on"
        else:
            found[name] = _attr(element, "value") or ""
    return found


def shown_address(root, form_id: str = "f-schritt") -> dict[str, str]:
    values = form_values(root, form_id)
    return {name: values.get(name) for name in ADDRESS_NAMES}


def field_errors(root) -> dict[str, str]:
    """Die Fehler am Feld im Adressfeld, je Feld."""
    found = {}
    for block in _all(address_field(root), lambda e: "a-textfeld" in _classes(e)):
        errors = _all(block, lambda e: "invalid-feedback" in _classes(e))
        if errors:
            field = _one(_all(block, lambda e: e.name in ("input", "select")))
            found[_attr(field, "name")] = _visible_text(_one(errors))
    return found


def open_step_one(client) -> dict[str, str]:
    """Öffnet Schritt 1 „Grunddaten“ einer neuen Veranstaltung; gibt zurück, was das Formular beim Öffnen schickt."""
    response = client.get(CREATE)
    assert response.status_code == 200, response.status_code
    return form_values(_tree(response), "f-schritt")


def search_in_step_one(client, **values):
    """Füllt Schritt 1 aus und tippt auf „Adresse suchen“; gibt die Antwort zurück."""
    opened = open_step_one(client)
    response = client.post(CREATE_SEARCH, {**opened, **PFINGSTLAGER, **EMPTY_ADDRESS, **values})
    assert response.status_code == 200, response.status_code
    return response


def take(client, root, number: int = 0, form_id: str = "f-schritt", **changes):
    """Tippt beim Treffer `number` auf „Übernehmen“, mit allen Eingaben der Seite; gibt die Antwort zurück."""
    button = take_buttons(root)[number]
    response = client.post(_attr(button, "formaction").split("#")[0],
                           {**form_values(root, form_id), **changes, _attr(button, "name"): _attr(button, "value")})
    assert response.status_code == 200, response.status_code
    return response


def weiter(client, root, **changes):
    """Tippt in Schritt 1 auf „Weiter“, mit allen Eingaben der Seite und den Änderungen."""
    form = _one(_by_tag(root, "form", id="f-schritt"))
    return client.post(_attr(form, "action"), {**form_values(root, "f-schritt"), **changes})


def created() -> Event:
    return Event.objects.get(name="Pfingstlager 2028")


def saved_address(entry) -> dict:
    entry.refresh_from_db()
    return {name: getattr(entry, name) for name in (*ADDRESS_NAMES, "latitude", "longitude")}


def place_lines(root) -> list[str]:
    """Der Ort in der Kachel „Grunddaten“ (auch in der Zusammenfassung), Zeile für Zeile."""
    tile = _one(_by_tag(root, "section", aria_labelledby="h-grunddaten"))
    found = _all(tile, lambda e: "a-kalender-ort" in _classes(e))
    if not found:
        return []
    block = _one(found)
    return [_visible_text(line) for line in _all(block, lambda e: "a-ort-zeile" in _classes(e))]


def head_line(root) -> str:
    found = _one(_all(root, lambda e: "a-kopf" in _classes(e)))
    return _visible_text(_one(_by_tag(found, "p")))


def place_icon(root) -> str:
    """Das Symbol vor dem Ort in der Kachel."""
    tile = _one(_by_tag(root, "section", aria_labelledby="h-grunddaten"))
    block = _one(_all(tile, lambda e: "a-kalender-ort" in _classes(e)))
    return _attr(_by_tag(block, "use")[0], "href")


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VA-07")
def test_a1_wanda_findet_die_burg_ueber_die_bezeichnung_und_uebernimmt_den_treffer(org, osm):
    client = client_for(org.wanda)

    root = _tree(search_in_step_one(client))

    assert osm.calls[0]["q"] == "Burg Ludwigstein"
    assert hits(root) == [
        ("Burg Ludwigstein", "Burgweg 1, 99999 Musterhausen, Hessen"),
        ("Jugendburg Ludwigstein, Parkplatz", "Burgweg, 99999 Musterhausen, Hessen"),
        ("Ludwigsteinstraße", "Ludwigsteinstraße, 99990 Beispielheim, Niedersachsen"),
    ]
    source = _one(_all(address_field(root), lambda e: "a-quelle" in _classes(e)))
    assert _visible_text(source) == SOURCE
    assert _attr(_one(_by_tag(source, "a")), "href") == SOURCE_LINK
    assert notices(root) == []

    root = _tree(take(client, root))

    assert shown_address(root) == {"street": "Burgweg 1", "postal_code": "99999", "city": "Musterhausen",
                                   "state": "HE", "country": "DE"}
    assert form_values(root, "f-schritt")["location"] == "Burg Ludwigstein"
    assert hits(root) == []
    assert len(osm.calls) == 1, "Übernehmen fragt OpenStreetMap nicht noch einmal"

    response = weiter(client, root)

    assert response.status_code == 302, response.status_code
    assert saved_address(created()) == {"street": "Burgweg 1", "postal_code": "99999", "city": "Musterhausen",
                                        "state": "HE", "country": "DE", "latitude": Decimal("51.3260000"),
                                        "longitude": Decimal("9.9040000")}
    summary = _tree(client.get(response["Location"]))
    assert place_lines(summary) == ["Burg Ludwigstein", "Burgweg 1", "99999 Musterhausen"]


def test_a1_hoechstens_fuenf_treffer(org, osm):
    """„Bis zu 5 Treffer“: OpenStreetMap wird nach 5 gefragt; liefert es mehr, stehen trotzdem nur 5 da."""
    root = _tree(search_in_step_one(client_for(org.wanda), location="Zeltplatz am Seeweg"))

    assert osm.calls[0]["limit"] == "5"
    assert [title for title, _line in hits(root)] == [f"Zeltplatz {number}" for number in range(1, 6)]


def test_a1_die_zusammenfassung_und_die_leitungsseite_zeigen_die_adresse_mit_ortssymbol(org, osm):
    """Kachel mehrzeilig mit dem Ortssymbol statt des Gebäudes (Nachklärung Z2), Kopf der Leitungsseite in einer Zeile."""
    client = client_for(org.wanda)
    root = _tree(take(client, _tree(search_in_step_one(client))))
    summary = client.get(weiter(client, root)["Location"])
    summary_root = _tree(summary)

    assert place_icon(summary_root) == "#i-ort"

    page = client.post(summary.wsgi_request.path)
    leitung = _tree(client.get(page["Location"]))

    assert place_lines(leitung) == ["Burg Ludwigstein", "Burgweg 1", "99999 Musterhausen"]
    assert place_icon(leitung) == "#i-ort"
    assert head_line(leitung) == "02.06.2028 bis 05.06.2028 · Burg Ludwigstein, Burgweg 1, 99999 Musterhausen"


def test_a2_wanda_sucht_ueber_strasse_und_ort_plz_und_bundesland_werden_ergaenzt(org, osm):
    client = client_for(org.wanda)

    root = _tree(search_in_step_one(client, location="", street="Burgweg 1", city="Musterhausen"))

    assert osm.calls[0]["q"] == "Burgweg 1, Musterhausen"
    assert hits(root) == [("Burgweg 1", "Burgweg 1, 99999 Musterhausen, Hessen")]

    root = _tree(take(client, root))

    assert shown_address(root) == {"street": "Burgweg 1", "postal_code": "99999", "city": "Musterhausen",
                                   "state": "HE", "country": "DE"}
    assert form_values(root, "f-schritt")["location"] == ""


def test_a3_nur_von_hand_ohne_suche_und_ohne_koordinaten(org, osm):
    client = client_for(org.wanda)
    opened = open_step_one(client)

    response = client.post(CREATE, {**opened, **PFINGSTLAGER, "street": "Waldweg 3", "postal_code": "99998",
                                    "city": "Beispielstadt", "state": "TH", "country": "DE"})

    assert response.status_code == 302, response.status_code
    assert saved_address(created()) == {"street": "Waldweg 3", "postal_code": "99998", "city": "Beispielstadt",
                                        "state": "TH", "country": "DE", "latitude": None, "longitude": None}
    assert osm.calls == []


def test_a4_hausnummer_von_hand_geaendert_die_koordinaten_fallen_weg(org, osm):
    client = client_for(org.wanda)
    root = _tree(take(client, _tree(search_in_step_one(client))))

    response = weiter(client, root, street="Burgweg 1a")

    assert response.status_code == 302, response.status_code
    assert saved_address(created()) == {"street": "Burgweg 1a", "postal_code": "99999", "city": "Musterhausen",
                                        "state": "HE", "country": "DE", "latitude": None, "longitude": None}


def test_a4_eine_erfundene_koordinate_im_formular_wird_nicht_gespeichert(org, osm):
    """Die Koordinaten kommen nur aus einem Treffer des Servers; ein verändertes Formular bringt keine eigenen hinein."""
    client = client_for(org.wanda)
    root = _tree(take(client, _tree(search_in_step_one(client))))

    response = weiter(client, root, coordinates="52.0000000,13.0000000")

    assert response.status_code == 302, response.status_code
    assert saved_address(created())["latitude"] is None


def test_a5_lagerplatz_ohne_strasse_nur_plz_und_ort(org):
    client = client_for(org.wanda)
    opened = open_step_one(client)

    response = client.post(CREATE, {**opened, **PFINGSTLAGER, **EMPTY_ADDRESS, "location": "Zeltplatz am Waldsee",
                                    "postal_code": "99997", "city": "Waldhausen"})

    assert response.status_code == 302, response.status_code
    assert saved_address(created()) == {"street": "", "postal_code": "99997", "city": "Waldhausen", "state": "",
                                        "country": "DE", "latitude": None, "longitude": None}


def test_a6_fiete_traegt_einen_ort_in_schweden_ein(org):
    client = client_for(org.fiete)
    opened = open_step_one(client)

    response = client.post(CREATE, {**opened, **PFINGSTLAGER, "location": "", "street": "", "state": "",
                                    "country": "SE", "postal_code": "123 45", "city": "Exempelby"})

    assert response.status_code == 302, response.status_code
    entry = created()
    assert saved_address(entry) == {"street": "", "postal_code": "123 45", "city": "Exempelby", "state": "",
                                    "country": "SE", "latitude": None, "longitude": None}
    client.post(response["Location"])
    leitung = _tree(client.get(event_address(entry)))
    assert place_lines(leitung) == ["123 45 Exempelby", "Schweden"]
    assert head_line(leitung) == "02.06.2028 bis 05.06.2028 · 123 45 Exempelby, Schweden"


def test_a6_die_auswahl_land_hat_alle_laender_deutschland_vorgewaehlt(org):
    root = _tree(client_for(org.wanda).get(CREATE))
    country = _one(_by_tag(address_field(root), "select", name="country"))
    options = {_attr(option, "value"): _text(option) for option in _by_tag(country, "option")}
    state = _one(_by_tag(address_field(root), "select", name="state"))

    assert form_values(root, "f-schritt")["country"] == "DE"
    assert options["DE"] == "Deutschland"
    assert options["SE"] == "Schweden"
    assert options["AT"] == "Österreich"
    assert len(options) >= 249
    assert [_text(option) for option in _by_tag(state, "option")][1:] == [
        "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen", "Hamburg", "Hessen",
        "Mecklenburg-Vorpommern", "Niedersachsen", "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen",
        "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"]


def test_a6_felder_beschriftungen_und_keine_pflicht_unter_der_ueberschrift(org):
    """Die Felder in der Reihenfolge des Zielbilds, ohne „(Pflicht)“ und ohne Satz „Freiwillig …“ (Nachklärung Z3)."""
    field = address_field(_tree(client_for(org.wanda).get(CREATE)))
    labels = [_visible_text(label) for label in _by_tag(field, "label")]

    assert _visible_text(_one(_by_tag(field, "legend"))) == "Adresse"
    assert labels == ["Straße und Hausnummer", "PLZ", "Ort", "Bundesland", "Land"]
    assert "Freiwillig" not in _visible_text(field)
    assert "Pflicht" not in _visible_text(field)


@pytest.mark.rechtematrix("VA-02")
@pytest.mark.rechtematrix("VA-07")
def test_a7_wanda_sucht_im_dialog_des_stifts_und_speichert_eine_neue_adresse(org, osm, pfingstlager):
    client = client_for(org.wanda)
    root = _tree(client.get(edit_address(pfingstlager)))
    dialog = dialog_of(root)

    assert search_target(dialog) == edit_search_address(pfingstlager)

    response = client.post(edit_search_address(pfingstlager), form_values(root, "f-dialog"))
    root = _tree(response)
    dialog = dialog_of(root)

    assert hits(dialog)[0] == ("Burg Ludwigstein", "Burgweg 1, 99999 Musterhausen, Hessen")

    root = _tree(take(client, root, form_id="f-dialog"))

    assert shown_address(root, "f-dialog")["street"] == "Burgweg 1"

    form = _one(_by_tag(root, "form", id="f-dialog"))
    response = client.post(_attr(form, "action"), form_values(root, "f-dialog"))

    assert response.status_code == 302, response.status_code
    assert saved_address(pfingstlager)["city"] == "Musterhausen"
    assert saved_address(pfingstlager)["latitude"] == Decimal("51.3260000")
    assert pfingstlager.version == 2


def test_a7_im_entwurf_sucht_schritt_1_ueber_die_eigene_adresse(org, osm):
    client = client_for(org.wanda)
    opened = open_step_one(client)
    response = client.post(CREATE, {**opened, **PFINGSTLAGER, **EMPTY_ADDRESS})
    entry = created()
    root = _tree(client.get(f"{event_address(entry)}anlegen/"))

    assert search_target(root) == basics_search_address(entry)

    root = _tree(client.post(basics_search_address(entry), form_values(root, "f-schritt")))

    assert hits(root)[0][0] == "Burg Ludwigstein"
    assert response.status_code == 302


def test_a8_wanda_leert_alle_adressfelder_der_ort_hat_nur_die_bezeichnung(org, mit_adresse):
    client = client_for(org.wanda)
    root = _tree(client.get(edit_address(mit_adresse)))

    response = client.post(edit_address(mit_adresse), {**form_values(root, "f-dialog"), **EMPTY_ADDRESS})

    assert response.status_code == 302, response.status_code
    assert saved_address(mit_adresse) == {"street": "", "postal_code": "", "city": "", "state": "", "country": "",
                                          "latitude": None, "longitude": None}
    assert place_lines(_tree(client.get(event_address(mit_adresse)))) == ["Burg Ludwigstein"]


def test_a8_unveraendert_gespeichert_behaelt_die_adresse_ihre_koordinaten(org, mit_adresse):
    client = client_for(org.wanda)
    root = _tree(client.get(edit_address(mit_adresse)))

    response = client.post(edit_address(mit_adresse), {**form_values(root, "f-dialog"), "name": "Pfingstlager 28"})

    assert response.status_code == 302, response.status_code
    assert saved_address(mit_adresse)["latitude"] == Decimal("51.3260000")


def test_a9_ohne_skript_ist_adresse_suchen_ein_formular_und_alle_eingaben_bleiben(org, osm):
    """„Adresse suchen“ ist ein Knopf, der das Formular des Schritts an die eigene Adresse der Suche schickt."""
    client = client_for(org.wanda)
    root = _tree(client.get(CREATE))
    button = search_button(root)

    assert _attr(button, "type") == "submit"
    assert _attr(button, "form") == "f-schritt"
    assert search_target(root) == CREATE_SEARCH

    typed = {**PFINGSTLAGER, "start_time": "17:30", "street": "Burgweg", "postal_code": "", "city": "Musterhausn",
             "state": "HE", "country": "DE"}
    root = _tree(client.post(CREATE_SEARCH, {**open_step_one(client), **typed}))
    shown = form_values(root, "f-schritt")

    assert {name: shown.get(name) for name in typed} == typed
    assert Event.objects.count() == 0


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VA-07")
def test_v1_otto_ohne_zuordnung_sucht_nicht_und_an_openstreetmap_geht_nichts(org, osm):
    client = Client()
    client.force_login(org.otto)

    assert_no_access(client.post(CREATE_SEARCH, {**PFINGSTLAGER, **EMPTY_ADDRESS}))
    assert osm.calls == []


@pytest.mark.rechtematrix("VA-07")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/bearbeiten/adresse-suchen/")
def test_v1_otto_als_leitung_ohne_zuordnung_hat_keinen_knopf_und_die_adresse_ist_nicht_gefunden(org, osm):
    """Otto leitet eine Veranstaltung (VA-02 ohne Zuordnung, V4 aus #100); eintragen geht, suchen nicht."""
    entry = event_of(org.otto, "Ottos Fahrt", date(2028, 6, 2), date(2028, 6, 5))
    dialog = dialog_of(_tree(client_for(org.otto).get(edit_address(entry))))

    assert _all(dialog, lambda e: "a-adressfeld" in _classes(e))
    assert [button for button in _by_tag(dialog, "button") if _visible_text(button) == SEARCH_LABEL] == []
    assert_like_missing(org.otto, edit_search_address(entry))
    assert osm.calls == []


@pytest.mark.rechtematrix("VA-07")
def test_v2_max_als_admin_auch_im_support_zugang_sucht_nicht(org, osm):
    client = client_for(org.max)
    assert_no_access(client.post(CREATE_SEARCH, {**PFINGSTLAGER, **EMPTY_ADDRESS}))

    start_support(org.max, org.walhall)
    assert Rights(org.max).support is not None
    assert_no_access(client_for(org.max).post(CREATE_SEARCH, {**PFINGSTLAGER, **EMPTY_ADDRESS}))
    assert osm.calls == []


@pytest.mark.rechtematrix("VA-07")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anlegen/adresse-suchen/")
def test_v2_fremde_entwuerfe_und_veranstaltungen_sind_fuer_die_suche_nicht_gefunden(org, osm, pfingstlager):
    """Fiete hat eine Zuordnung, sucht aber nicht über Wandas Veranstaltung oder ihren Entwurf."""
    client = client_for(org.wanda)
    opened = open_step_one(client)
    client.post(CREATE, {**opened, **PFINGSTLAGER, "name": "Sommerfahrt 2028", **EMPTY_ADDRESS})
    draft = Event.objects.get(name="Sommerfahrt 2028")

    assert_like_missing(org.fiete, basics_search_address(draft))
    assert_like_missing(org.fiete, edit_search_address(pfingstlager))
    assert osm.calls == []


@pytest.mark.rechtematrix("VA-03")
def test_v3_finn_schickt_eine_adresse_fuer_wandas_pfingstlager_und_findet_nichts(org, osm, pfingstlager):
    form = {**PFINGSTLAGER, "start": "2028-06-02", "end": "2028-06-05", "street": "Fremdweg 9", "postal_code": "99990",
            "city": "Falschdorf", "state": "", "country": "DE", "version": str(pfingstlager.version)}
    client = client_for(org.finn)

    for address in (edit_address(pfingstlager), edit_search_address(pfingstlager)):
        assert client.post(address, form).status_code == 404

    assert saved_address(pfingstlager)["city"] == ""
    assert osm.calls == []


def test_v4_der_suchtext_steht_in_keiner_adresse_und_geht_nur_per_formular(org, osm):
    client = client_for(org.wanda)
    root = _tree(client.get(CREATE))

    assert "?" not in _attr(search_button(root), "formaction")

    response = client.get(CREATE_SEARCH, {"location": "Burg Ludwigstein"})

    assert osm.calls == []
    assert response.status_code in (302, 404)


def test_v4_an_openstreetmap_geht_nur_der_suchtext(org, osm):
    client = client_for(org.wanda)

    search_in_step_one(client, street="Burgweg 1", city="Musterhausen")

    sent = osm.calls[0]
    assert sent["q"] == "Burg Ludwigstein, Burgweg 1, Musterhausen"
    assert set(sent) <= {"q", "format", "addressdetails", "limit", "accept-language", "countrycodes"}
    for value in sent.values():
        for detail in ("Wanda", "wanda", "Walhall", org.wanda.key, "Pfingstlager", "2028"):
            assert detail not in value


def test_v4_die_anfrage_traegt_nur_die_kennung_der_anwendung(monkeypatch, settings):
    """Die Anfrage selbst: nur über den Server, mit Kennung der Anwendung, ohne Cookie, Internetadresse oder Konto."""
    sent = []

    class Answer:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *args):
            return b"[]"

    def fake_urlopen(request, timeout=None):
        sent.append((request, timeout))
        return Answer()

    monkeypatch.undo()
    settings.ADDRESS_SEARCH_AGENT = "DPV-Anmeldetool (anmeldetool@example.org)"
    monkeypatch.setattr(address_search, "urlopen", fake_urlopen)

    assert address_search._request({"q": "Burg Ludwigstein"}) == []

    request, timeout = sent[0]
    assert urlsplit(request.full_url).netloc == "nominatim.openstreetmap.org"
    assert parse_qs(urlsplit(request.full_url).query)["q"] == ["Burg Ludwigstein"]
    assert request.get_method() == "GET"
    assert {name.lower() for name, _value in request.header_items()} == {"user-agent"}
    assert request.get_header("User-agent") == "DPV-Anmeldetool (anmeldetool@example.org)"
    assert timeout == django_settings.ADDRESS_SEARCH_TIMEOUT_SECONDS


def test_v4_der_suchtext_steht_in_keinem_protokoll(org, osm, caplog):
    """Auch nicht, wenn die Suche scheitert (G2)."""
    caplog.set_level(logging.DEBUG)
    osm.failure = TimeoutError("Zeitüberschreitung bei Burg Ludwigstein")
    client = client_for(org.wanda)

    search_in_step_one(client)
    osm.failure = None
    search_in_step_one(client, location="Zeltplatz am Seeweg")

    logged = "\n".join(record.getMessage() + str(record.exc_info or "") for record in caplog.records)
    assert "Ludwigstein" not in logged
    assert "Seeweg" not in logged


# ---------- Grenzfälle ----------


def test_g1_nichts_gefunden_ist_eine_information_und_die_felder_bleiben(org, osm):
    root = _tree(search_in_step_one(client_for(org.wanda), location="Zeltplatz am Nirgendsee", postal_code="99997"))

    assert notices(root) == [("ist-info", NOTHING_FOUND)]
    assert hits(root) == []
    assert shown_address(root) == {**EMPTY_ADDRESS, "postal_code": "99997"}


def test_g2_openstreetmap_antwortet_nicht_fehler_und_speichern_geht_trotzdem(org, osm):
    osm.failure = TimeoutError()
    client = client_for(org.wanda)

    root = _tree(search_in_step_one(client, postal_code="99999", city="Musterhausen"))

    assert notices(root) == [("ist-fehler", UNAVAILABLE)]
    response = weiter(client, root)
    assert response.status_code == 302, response.status_code
    assert saved_address(created())["city"] == "Musterhausen"


@pytest.mark.parametrize("failure", [OSError("Netz weg"), ValueError("kein JSON")])
def test_g2_auch_andere_ausfaelle_sind_nicht_erreichbar(org, osm, failure):
    osm.failure = failure

    root = _tree(search_in_step_one(client_for(org.wanda)))

    assert notices(root) == [("ist-fehler", UNAVAILABLE)]


def test_g2_eine_antwort_in_falscher_form_ist_nicht_erreichbar(org, monkeypatch):
    monkeypatch.setattr(address_search, "_request", lambda params: {"fehler": "unerwartet"})

    root = _tree(search_in_step_one(client_for(org.wanda)))

    assert notices(root) == [("ist-fehler", UNAVAILABLE)]


@pytest.mark.parametrize("values", [
    {"location": "", "street": "Burgweg"},
    {"location": "   ", "street": ""},
    {"location": "", "street": "", "postal_code": "99999", "city": "Musterhausen"},
    {"location": "", "street": "", "country": "SE"},
])
def test_g3_zu_wenig_fuer_die_suche_ist_eine_gelbe_warnung_und_es_geht_nichts_hinaus(org, osm, values):
    root = _tree(search_in_step_one(client_for(org.wanda), **values))

    assert notices(root) == [("ist-warnung", TOO_LITTLE)]
    assert osm.calls == []


def test_g4_nur_die_strasse_und_weiter_plz_und_ort_fehlen_am_feld(org):
    client = client_for(org.wanda)
    opened = open_step_one(client)

    response = client.post(CREATE, {**opened, **PFINGSTLAGER, **EMPTY_ADDRESS, "street": "Burgweg 1"})

    assert response.status_code == 200, response.status_code
    root = _tree(response)
    assert field_errors(root) == {"postal_code": POSTAL_CODE_EMPTY, "city": CITY_EMPTY}
    assert form_values(root, "f-schritt")["street"] == "Burgweg 1"
    assert Event.objects.count() == 0


@pytest.mark.parametrize("values", [{"state": "HE"}, {"country": "SE"}])
def test_g4_auch_bundesland_oder_ein_anderes_land_allein_zaehlen_als_eintrag(org, values):
    client = client_for(org.wanda)
    response = client.post(CREATE, {**open_step_one(client), **PFINGSTLAGER, **EMPTY_ADDRESS, **values})

    assert field_errors(_tree(response)) == {"postal_code": POSTAL_CODE_EMPTY, "city": CITY_EMPTY}


def test_g4_das_vorgewaehlte_deutschland_allein_ist_keine_adresse(org):
    client = client_for(org.wanda)

    response = client.post(CREATE, {**open_step_one(client), **PFINGSTLAGER, **EMPTY_ADDRESS})

    assert response.status_code == 302, response.status_code
    assert saved_address(created()) == {"street": "", "postal_code": "", "city": "", "state": "", "country": "",
                                        "latitude": None, "longitude": None}


@pytest.mark.parametrize("postal_code", ["9999", "999999", "99a99", "99 999"])
def test_g5_in_deutschland_hat_die_plz_5_ziffern(org, postal_code):
    client = client_for(org.wanda)

    response = client.post(CREATE, {**open_step_one(client), **PFINGSTLAGER, **EMPTY_ADDRESS,
                                    "postal_code": postal_code, "city": "Musterhausen"})

    assert field_errors(_tree(response)) == {"postal_code": FIVE_DIGITS}
    assert Event.objects.count() == 0


def test_g5_leerzeichen_am_rand_zaehlen_nicht(org):
    client = client_for(org.wanda)

    response = client.post(CREATE, {**open_step_one(client), **PFINGSTLAGER, **EMPTY_ADDRESS,
                                    "postal_code": " 99999 ", "city": " Musterhausen ", "street": " Burgweg 1 "})

    assert response.status_code == 302, response.status_code
    assert saved_address(created())["postal_code"] == "99999"
    assert saved_address(created())["city"] == "Musterhausen"
    assert saved_address(created())["street"] == "Burgweg 1"


def test_g6_tippfehler_im_ort_der_treffer_berichtigt_ihn_die_bezeichnung_bleibt(org, osm):
    client = client_for(org.wanda)
    root = _tree(search_in_step_one(client, city="Musterhausn"))

    assert osm.calls[0]["q"] == "Burg Ludwigstein, Musterhausn"

    root = _tree(take(client, root, location="Burg Ludwigstein"))

    assert form_values(root, "f-schritt")["city"] == "Musterhausen"
    assert form_values(root, "f-schritt")["location"] == "Burg Ludwigstein"


def test_g6_uebernehmen_aendert_die_bezeichnung_nie(org, osm):
    """Auch wenn Wanda die Bezeichnung nach der Suche geändert hat, bleibt ihre Fassung stehen."""
    client = client_for(org.wanda)
    root = _tree(search_in_step_one(client))

    root = _tree(take(client, root, location="Jugendburg"))

    assert form_values(root, "f-schritt")["location"] == "Jugendburg"


def test_g6_ein_veraenderter_treffer_wird_nicht_uebernommen(org, osm):
    """Der Knopf „Übernehmen“ schickt den Treffer, wie der Server ihn gefunden hat; ein veränderter füllt nichts."""
    client = client_for(org.wanda)
    root = _tree(search_in_step_one(client))
    button = take_buttons(root)[0]

    response = client.post(CREATE_SEARCH, {**form_values(root, "f-schritt"), "treffer": _attr(button, "value") + "x"})

    assert response.status_code == 200
    assert shown_address(_tree(response)) == EMPTY_ADDRESS


def test_g7_bei_schweden_wird_kein_bundesland_gespeichert(org):
    client = client_for(org.wanda)

    response = client.post(CREATE, {**open_step_one(client), **PFINGSTLAGER, "street": "", "state": "HE",
                                    "country": "SE", "postal_code": "123 45", "city": "Exempelby"})

    assert response.status_code == 302, response.status_code
    assert saved_address(created())["state"] == ""
    assert saved_address(created())["city"] == "Exempelby"


def test_g7_das_bundesland_gehoert_zum_land_deutschland(org):
    """Das Feld Bundesland ist so markiert, dass es nur bei Deutschland zu sehen ist; ohne Skript macht das app.css."""
    field = address_field(_tree(client_for(org.wanda).get(CREATE)))
    state = _one(_all(field, lambda e: "a-bundesland" in _classes(e)))

    assert _by_tag(state, "select", name="state")


def test_g8_gleiche_suchen_merkt_sich_der_server(org, osm):
    """Ein Doppelklick oder dieselbe Suche kurz danach fragt OpenStreetMap nur einmal."""
    client = client_for(org.wanda)

    first = hits(_tree(search_in_step_one(client)))
    second = hits(_tree(search_in_step_one(client_for(org.fiete))))

    assert first == second
    assert len(osm.calls) == 1


def test_g8_die_bremse_ist_eine_sekunde():
    """Die Tests schalten die Bremse sonst ab (`tests/adresssuche_fake.py`); eingestellt ist eine Sekunde."""
    from config import settings as configured

    assert configured.ADDRESS_SEARCH_INTERVAL_SECONDS == 1.0


@pytest.mark.django_db(transaction=True)
def test_g8_wanda_und_fiete_suchen_gleichzeitig_die_zweite_wartet_keine_bekommt_einen_fehler(osm, settings):
    settings.ADDRESS_SEARCH_INTERVAL_SECONDS = 1.0
    org = build_people()
    answers: dict[str, list] = {}
    texts = {"wanda": "Burg Ludwigstein", "fiete": "Zeltplatz am Seeweg"}
    start = threading.Barrier(2)

    def search(name: str, user) -> None:
        try:
            client = client_for(user)
            opened = open_step_one(client)
            start.wait()
            response = client.post(CREATE_SEARCH, {**opened, **PFINGSTLAGER, **EMPTY_ADDRESS, "location": texts[name]})
            answers[name] = [response.status_code, notices(_tree(response)), len(hits(_tree(response)))]
        finally:
            connection.close()

    threads = [threading.Thread(target=search, args=(name, getattr(org, name))) for name in texts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert answers == {"wanda": [200, [], 3], "fiete": [200, [], 5]}
    assert len(osm.times) == 2
    assert abs(osm.times[1] - osm.times[0]) >= 0.95


def test_g8_bei_einer_langen_schlange_wartet_die_suche_nicht_endlos(org, osm, settings, monkeypatch):
    """Steht die Uhr weit in der Zukunft (etwa nach vielen Suchen auf einmal), ist die Suche „nicht erreichbar“."""
    from core.models import AddressSearchClock

    settings.ADDRESS_SEARCH_INTERVAL_SECONDS = 1.0
    AddressSearchClock.objects.update(last_request=timezone.now() + timedelta(minutes=5))
    sleeps = []
    monkeypatch.setattr(address_search.time, "sleep", sleeps.append)

    root = _tree(search_in_step_one(client_for(org.wanda)))

    assert notices(root) == [("ist-fehler", UNAVAILABLE)]
    assert osm.calls == []
    assert sum(sleeps) < 10


def test_g9_veranstaltungen_ohne_adresse_zeigen_nur_die_bezeichnung_und_speichern_weiter(org, pfingstlager):
    client = client_for(org.wanda)
    root = _tree(client.get(event_address(pfingstlager)))

    assert place_lines(root) == ["Burg Ludwigstein"]

    pfingstlager.location = ""
    pfingstlager.save()
    root = _tree(client.get(event_address(pfingstlager)))
    assert place_lines(root) == []

    # Wie ein Formular von vor #163, ohne Adressfelder: Speichern geht weiter.
    response = client.post(edit_address(pfingstlager), {"name": "Pfingstlager 2028", "start": "2028-06-02",
                                                        "end": "2028-06-05", "version": str(pfingstlager.version)})
    assert response.status_code == 302, response.status_code
    assert short_notices(client.get(response["Location"])) == ["Erfolg: Die Angaben zu Pfingstlager 2028 sind gespeichert."]


# ---------- Datenmodell ----------


@pytest.mark.parametrize("values", [
    {"state": "HE", "country": "SE", "postal_code": "123 45", "city": "Exempelby"},
    {"street": "Burgweg 1", "country": "DE"},
    {"postal_code": "99999", "country": "DE"},
    {"city": "Musterhausen", "postal_code": "99999"},
    {"latitude": Decimal("51.3"), "longitude": Decimal("9.9")},
    {"latitude": Decimal("51.3"), "postal_code": "99999", "city": "Musterhausen", "country": "DE"},
    {"city": " Musterhausen", "postal_code": "99999", "country": "DE"},
])
def test_die_datenbank_lehnt_unvollstaendige_adressen_ab(org, pfingstlager, values):
    for name, value in values.items():
        setattr(pfingstlager, name, value)

    with pytest.raises(IntegrityError), transaction.atomic():
        pfingstlager.save()


# ---------- Bausteinkatalog ----------


@pytest.mark.bausteinkatalog
def test_der_katalog_zeigt_das_adressfeld_mit_suche_und_die_trefferliste_der_orte(org):
    root = _tree(client_for(org.wanda).get("/bausteine/"))
    section = _one(_by_tag(root, "section", aria_labelledby="h-adressfeld"))

    assert _all(section, lambda e: "a-adressfeld" in _classes(e))
    assert search_button(section)
    places = _one(_by_tag(root, "section", aria_labelledby="h-trefferliste"))
    assert "Burg Ludwigstein" in _visible_text(places)
    assert TAKE_LABEL in _visible_text(places)
    assert "Treffer" in _visible_text(places)


def test_beispiele_sind_erfunden():
    """Die Antworten des nachgestellten Suchdienstes nennen nur erfundene Adressen mit PLZ ab 99990."""
    assert BURG["address"]["postcode"] == "99999"
    for entries in ANSWERS.values():
        for entry in entries:
            assert entry["address"]["postcode"] >= "99990"
