"""Tests für Uhrzeiten, Ort, Prüfungen und die Leitungsseite mit Kachel „Grunddaten“ (#379, Teil A von #29).

Die Kennungen A1 bis A5, AV1 bis AV3 und AG1 bis AG7 verweisen auf die Szenarien vom 17.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/379#issuecomment-6944637971), die Wortlaute auf
den Text von #379. AG8 (Handy, nur Tastatur) prüft der Rauchtest `rauchtests/test_grunddaten.py`. „Heute“ ist
in allen Szenarien der 05.01.2028; die Tests stellen den Tag des Servers darauf. Personen wie in den Szenarien:
Wanda (Stammesleitung Walhall), Fiete (Gruppenleitung Falken), Finn (Mitglied Sippe Falken), Vera
(Verbandsleitung), Max (nur Admin), Otto (Konto ohne Zuordnung). Alle Namen sind erfunden; „Burg Ludwigstein“
ist als Bezeichnung eines Orts aus dem Zielbild übernommen (#356). Seit #380 ist „Veranstaltung erstellen“ kein
Dialog mehr, sondern Schritt 1 eines Ablaufs (`tests/test_veranstaltung_anlegen.py`); nachgezogen sind nur die Stellen,
die das Formular dort suchen, und A4, wohin „Weiter“ führt.
"""

import hashlib
import re
from datetime import date, datetime, time
from pathlib import Path

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from access.rights import Rights
from events.models import Event
from tests.test_benennen import _one_after_the_other, dialog_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_veranstaltungen import (
    CREATE,
    CREATE_LABEL,
    LIST,
    NONE_YET,
    SCRIPT,
    assert_no_access,
    build_people,
    edit_address,
    event_address,
    event_of,
    field_errors,
    field_values,
    leads_of,
    open_create,
    step_form,
    summary_address,
)

pytestmark = pytest.mark.django_db

TODAY = date(2028, 1, 5)
TITLE = "Von mir geleitet"
PAST = "Der Beginn liegt in der Vergangenheit."
END_BEFORE_START = "Das Ende liegt vor dem Beginn."
DURATION_OK = "Ja, die Dauer stimmt"


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    """Der Tag des Servers ist der 05.01.2028, wie in den Szenarien."""
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: TODAY)


@pytest.fixture
def org():
    return build_people()


@pytest.fixture
def pfingstlager(org):
    """Wandas „Pfingstlager 2028“ aus P2: Tage ohne Uhrzeit und ohne Ort (A1)."""
    return event_of(org.wanda, "Pfingstlager 2028", date(2028, 6, 2), date(2028, 6, 5))


# ---------- Hilfen ----------


def create(user, client=None, **values):
    """Füllt „Veranstaltung erstellen“ aus wie A4 und klickt auf „Weiter“ (bis #380 „Anlegen“); die Uhrzeiten wie vorausgefüllt."""
    client = client or client_for(user)
    _found, creation_key = open_create(user, client=client)
    form = {"name": "Stammesthing Walhall", "start": "2028-01-14", "start_time": "18:00", "end": "2028-01-16",
            "end_time": "12:00", "location": ""}
    return client.post(CREATE, {**form, **values, "creation_key": creation_key})


def shown(entry) -> dict[str, str]:
    """Die Angaben, wie der Dialog des Stifts sie beim Öffnen zeigt, mit dem Stand für gleichzeitiges Speichern."""
    return {
        "name": entry.name,
        "start": entry.start.isoformat(),
        "start_time": entry.start_time.strftime("%H:%M") if entry.start_time else "",
        "end": entry.end.isoformat(),
        "end_time": entry.end_time.strftime("%H:%M") if entry.end_time else "",
        "location": entry.location,
        "version": str(entry.version),
    }


def save(user, entry, client=None, **values):
    """Ändert im Dialog des Stifts die Angaben und klickt auf „Speichern“."""
    return (client or client_for(user)).post(edit_address(entry), {**shown(entry), **values})


def head(root) -> tuple[str, str]:
    """Der Kopf der Leitungsseite: Name und die Zeile darunter."""
    found = _one(_all(root, lambda e: "a-kopf" in _classes(e)))
    return _text(_one(_by_tag(found, "h1"))), _visible_text(_one(_by_tag(found, "p")))


def tile(root):
    """Die Kachel „Grunddaten“."""
    return _one(_by_tag(root, "section", aria_labelledby="h-grunddaten"))


def sheets(root) -> list[str]:
    """Die Kalenderblätter der Kachel, je Blatt der sichtbare Text, etwa „Fr 02 Jun 2028 18:00“."""
    return [_visible_text(sheet) for sheet in _all(tile(root), lambda e: "a-kalenderblatt" in _classes(e))]


def duration(root) -> str:
    return _visible_text(_one(_all(tile(root), lambda e: "a-kalender-dauer" in _classes(e))))


def place(root) -> str | None:
    found = _all(tile(root), lambda e: "a-kalender-ort" in _classes(e))
    return _visible_text(_one(found)) if found else None


def pencil(root):
    """Der Stift der Kachel „Grunddaten“ (Baustein „Bearbeiten-Symbol“)."""
    return _one(_all(tile(root), lambda e: "a-stift" in _classes(e)))


def rows(user) -> list[str]:
    """Die Zeilen unter „Von mir geleitet“, je Zeile der sichtbare Text, in ihrer Reihenfolge."""
    section = _one(_by_tag(page_tree(user, LIST), "section", aria_labelledby="h-veranstaltungen"))
    return [_visible_text(row) for row in _all(section, lambda e: "a-va-zeile" in _classes(e))]


def row_link(user, name: str) -> str:
    section = _one(_by_tag(page_tree(user, LIST), "section", aria_labelledby="h-veranstaltungen"))
    return _attr(_one([link for link in _by_tag(section, "a") if _visible_text(link) == name]), "href")


def switch_of(dialog):
    """Das Feld „Ja, die Dauer stimmt“ (Baustein „Schalter“), oder None."""
    found = _by_tag(dialog, "input", name="duration_ok")
    return _one(found) if found else None


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VA-02")
def test_a1_wanda_kommt_ueber_die_liste_zur_leitungsseite_mit_der_kachel_grunddaten(org, pfingstlager):
    assert row_link(org.wanda, "Pfingstlager 2028") == event_address(pfingstlager)

    root = page_tree(org.wanda, event_address(pfingstlager))

    assert head(root) == ("Pfingstlager 2028", "02.06.2028 bis 05.06.2028")
    assert _visible_text(_one(_by_tag(tile(root), "h2"))) == "Grunddaten"
    assert sheets(root) == ["Fr 02 Jun 2028", "Mo 05 Jun 2028"]
    assert duration(root) == "4 Tage"
    assert place(root) is None
    assert _attr(pencil(root), "href") == edit_address(pfingstlager)
    # Vorleseprogramme hören, was der Stift bearbeitet; sichtbar ist nur das Symbol.
    assert _text(_one(_all(pencil(root), lambda e: "sr-nur" in _classes(e)))) == "Grunddaten bearbeiten"
    # Der bisherige Knopf „Bearbeiten“ entfällt.
    assert not [link for link in _by_tag(root, "a") if _visible_text(link) == "Bearbeiten"]
    # Darunter der Abschnitt „Anmeldungen“ aus der Probe (#101), unverändert.
    registrations = _one(_by_tag(root, "section", aria_labelledby="h-anmeldungen"))
    assert "Zu dieser Veranstaltung gibt es noch keine Anmeldungen." in _visible_text(registrations)
    assert (pfingstlager.start_time, pfingstlager.end_time, pfingstlager.location) == (None, None, "")


@pytest.mark.rechtematrix("VA-02")
def test_a2_wanda_traegt_uhrzeiten_und_ort_ueber_den_stift_ein(org, pfingstlager):
    client = client_for(org.wanda)
    response = client.get(edit_address(pfingstlager))
    assert response.status_code == 200
    found = dialog_of(_tree(response))
    assert _text(_one(_by_tag(found, "h2"))) == "Pfingstlager 2028 bearbeiten"
    assert field_values(found) == {"name": "Pfingstlager 2028", "start": "2028-06-02", "start_time": "",
                                   "end": "2028-06-05", "end_time": "", "location": ""}
    # Seit #163 steht unter dem Ort das Adressfeld mit „Adresse suchen“ (tests/test_adressfeld.py).
    assert [_visible_text(button) for button in _by_tag(found, "button")] == ["Adresse suchen", "Speichern"]

    response = save(org.wanda, pfingstlager, client=client, start_time="18:00", end_time="12:00",
                    location="Burg Ludwigstein")

    assert response.status_code == 302
    assert response.url == event_address(pfingstlager)
    pfingstlager.refresh_from_db()
    assert (pfingstlager.start_time, pfingstlager.end_time, pfingstlager.location) == (
        time(18, 0), time(12, 0), "Burg Ludwigstein")
    page = client.get(response.url)
    assert short_notices(page) == ["Die Angaben zu Pfingstlager 2028 sind gespeichert."]
    root = _tree(page)
    assert head(root) == ("Pfingstlager 2028", "02.06.2028 bis 05.06.2028 · Burg Ludwigstein")
    assert sheets(root) == ["Fr 02 Jun 2028 18:00", "Mo 05 Jun 2028 12:00"]
    assert duration(root) == "4 Tage"
    assert place(root) == "Burg Ludwigstein"


@pytest.mark.rechtematrix("VA-02")
def test_a3_wanda_leert_beide_uhrzeiten_wieder(org, pfingstlager):
    Event.objects.filter(pk=pfingstlager.pk).update(start_time=time(18, 0), end_time=time(12, 0))
    pfingstlager.refresh_from_db()

    assert save(org.wanda, pfingstlager, start_time="", end_time="").status_code == 302

    pfingstlager.refresh_from_db()
    assert (pfingstlager.start_time, pfingstlager.end_time) == (None, None)
    root = page_tree(org.wanda, event_address(pfingstlager))
    assert sheets(root) == ["Fr 02 Jun 2028", "Mo 05 Jun 2028"]


@pytest.mark.rechtematrix("VA-01")
def test_a4_wanda_legt_das_stammesthing_ohne_ort_an_und_landet_auf_der_leitungsseite(org):
    client = client_for(org.wanda)
    section = _one(_by_tag(page_tree(org.wanda, LIST), "section", aria_labelledby="h-veranstaltungen"))
    button = _one([link for link in _by_tag(section, "a") if _visible_text(link) == CREATE_LABEL])
    assert _attr(button, "href") == CREATE
    # Plus weiß wie bei den anderen Knöpfen im Kopf einer Fläche (E1 aus #356): der Hauptknopf, kein gelbes Symbol.
    assert "btn-primary" in _classes(button)
    assert not _all(button, lambda e: "a-akzent" in _classes(e))

    found, _key = open_create(org.wanda, client=client)
    assert _text(_one(_by_tag(page_tree(org.wanda, CREATE), "h1"))) == CREATE_LABEL
    assert field_values(found) == {"name": "", "start": "", "start_time": "18:00", "end": "", "end_time": "12:00",
                                   "location": ""}
    # Seit #163 folgt unter dem Ort das Adressfeld (tests/test_adressfeld.py).
    labels = [_visible_text(label) for label in _by_tag(found, "label") if "sr-nur" not in _classes(label)]
    assert labels[:4] == ["Name (Pflicht)", "Beginn (Pflicht, Uhrzeit freiwillig)",
                          "Ende (Pflicht, Uhrzeit freiwillig)", "Ort"]
    assert labels[4:] == ["Straße und Hausnummer", "PLZ", "Ort", "Bundesland", "Land"]

    response = create(org.wanda, client=client)

    created = Event.objects.get()
    assert (created.name, created.start, created.start_time, created.end, created.end_time, created.location) == (
        "Stammesthing Walhall", date(2028, 1, 14), time(18, 0), date(2028, 1, 16), time(12, 0), "")
    assert leads_of(created) == {"wanda.walhall"}
    # Seit #380 führt „Weiter“ zur Zusammenfassung, erst „Veranstaltung speichern“ dort zur Leitungsseite.
    assert response.status_code == 302
    assert response.url == summary_address(created)
    response = client.post(response.url)
    assert response.url == event_address(created)
    page = client.get(response.url)
    assert short_notices(page) == [
        "Stammesthing Walhall ist als Entwurf gespeichert. Nur die Leitung sieht die Veranstaltung."]
    assert head(_tree(page)) == ("Stammesthing Walhall", "14.01.2028 bis 16.01.2028")


@pytest.mark.rechtematrix("VA-02")
def test_a5_die_liste_von_mir_geleitet_nach_beginn_mit_zeitraum_und_ort(org, pfingstlager):
    assert rows(org.wanda) == ["Pfingstlager 2028 02.06.2028 bis 05.06.2028"]
    Event.objects.filter(pk=pfingstlager.pk).update(start_time=time(18, 0), end_time=time(12, 0),
                                                    location="Burg Ludwigstein")
    event_of(org.wanda, "Stammesthing Walhall", date(2028, 1, 14), date(2028, 1, 16))
    event_of(org.fiete, "Sippenaktion Falken", date(2028, 1, 21), date(2028, 1, 23))

    section = _one(_by_tag(page_tree(org.wanda, LIST), "section", aria_labelledby="h-veranstaltungen"))
    assert _visible_text(_one(_by_tag(section, "h2"))) == TITLE
    assert rows(org.wanda) == [
        "Stammesthing Walhall 14.01.2028 bis 16.01.2028",
        "Pfingstlager 2028 02.06.2028, 18:00 bis 05.06.2028, 12:00 · Burg Ludwigstein",
    ]
    assert row_link(org.wanda, "Stammesthing Walhall") == event_address(Event.objects.get(name="Stammesthing Walhall"))
    # Ohne eigene Veranstaltung steht der Satz.
    section = _one(_by_tag(page_tree(org.finn, LIST), "section", aria_labelledby="h-veranstaltungen"))
    assert NONE_YET in _visible_text(section)
    assert rows(org.finn) == []


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/bearbeiten/")
def test_av1_niemand_ausser_wanda_sieht_die_leitungsseite_oder_den_stift(org, pfingstlager):
    smuggled = {**shown(pfingstlager), "name": "Gekapert", "location": "Woanders", "start_time": "08:00"}
    for user in (org.fiete, org.finn, org.vera, org.max):
        client = client_for(user)
        assert_like_missing(user, event_address(pfingstlager))
        assert_like_missing(user, edit_address(pfingstlager))
        for address in (event_address(pfingstlager), edit_address(pfingstlager)):
            assert client.get(address, **SCRIPT).status_code == 404, (user.username, address)
            assert client.post(address, smuggled).status_code == 404, (user.username, address)
            assert client.post(address, smuggled, **SCRIPT).status_code == 404, (user.username, address)

    pfingstlager.refresh_from_db()
    assert (pfingstlager.name, pfingstlager.location, pfingstlager.start_time) == ("Pfingstlager 2028", "", None)


@pytest.mark.rechtematrix("VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/bearbeiten/")
def test_av1_auch_im_support_zugang_fuer_walhall_sieht_max_nichts(org, pfingstlager):
    client = client_for(org.max)
    assert client.post(f"{unit_address(org.walhall)}support-zugang/", {"anlass": "lead_request"}).status_code == 302

    assert client.get(event_address(pfingstlager)).status_code == 404
    assert client.post(edit_address(pfingstlager), {**shown(pfingstlager), "location": "Woanders"}).status_code == 404
    assert_like_missing(org.max, edit_address(pfingstlager))
    pfingstlager.refresh_from_db()
    assert pfingstlager.location == ""


@pytest.mark.rechtematrix("VA-03")
def test_av1_gegenprobe_wanda_sieht_und_speichert_weiter(org, pfingstlager):
    assert client_for(org.wanda).get(event_address(pfingstlager)).status_code == 200
    assert client_for(org.wanda).get(edit_address(pfingstlager), **SCRIPT).status_code == 200
    assert save(org.wanda, pfingstlager, location="Burg Ludwigstein").status_code == 302


@pytest.mark.rechtematrix("VA-05")
def test_av2_otto_sieht_kein_erstellen_und_legt_auch_mit_formular_nichts_an(org):
    client = client_for(org.otto)
    form = {"name": "Ottos Fahrt", "start": "2028-01-14", "start_time": "18:00", "end": "2028-01-16",
            "end_time": "12:00", "location": "Burg Ludwigstein", "creation_key": "b" * 20}

    assert_no_access(client.get(LIST))
    assert_no_access(client.get(CREATE))
    assert_no_access(client.post(CREATE, form))
    assert_no_access(client.post(CREATE, form, **SCRIPT))
    assert not Event.objects.exists()


@pytest.mark.rechtematrix("VA-04")
def test_av3_auf_der_leitungsseite_gibt_es_kein_loeschen(org, pfingstlager):
    client = client_for(org.wanda)
    for address in (event_address(pfingstlager), edit_address(pfingstlager)):
        assert "öschen" not in _visible_text(_tree(client.get(address))), address
        assert client.delete(address).status_code == 404
    for address in (f"{event_address(pfingstlager)}loeschen/", f"{event_address(pfingstlager)}delete/"):
        assert client.get(address).status_code == 404
        assert client.post(address).status_code == 404

    assert Event.objects.filter(pk=pfingstlager.pk).exists()
    assert client.get(event_address(pfingstlager)).status_code == 200


# ---------- Grenzfälle ----------


def test_ag1_beginn_vor_heute_geht_nicht_heute_geht_gleich_zu_welcher_uhrzeit(org, pfingstlager, monkeypatch):
    response = create(org.wanda, start="2028-01-04")

    assert response.status_code == 200
    assert field_errors(_tree(response)) == {"start": PAST}
    assert not Event.objects.exclude(pk=pfingstlager.pk).exists()

    response = save(org.wanda, pfingstlager, start="2028-01-04")
    assert response.status_code == 200
    assert field_errors(_tree(response)) == {"start": PAST}
    pfingstlager.refresh_from_db()
    assert pfingstlager.start == date(2028, 6, 2)

    # Heute um 14:00 einen Beginn heute um 10:00 eintragen: erlaubt, „vor dem heutigen Tag“ zählt nur den Tag.
    monkeypatch.setattr(timezone, "now", lambda: timezone.make_aware(datetime(2028, 1, 5, 14, 0)))
    assert create(org.wanda, name="Heute", start="2028-01-05", start_time="10:00").status_code == 302
    assert save(org.wanda, pfingstlager, start="2028-01-05", start_time="10:00", end="2028-01-07").status_code == 302
    pfingstlager.refresh_from_db()
    assert (pfingstlager.start, pfingstlager.start_time) == (date(2028, 1, 5), time(10, 0))


def test_ag2_bei_einer_laufenden_veranstaltung_gehen_name_und_ende_der_beginn_nicht_zurueck(org):
    singewettstreit = event_of(org.wanda, "Singewettstreit 2028", date(2028, 1, 3), date(2028, 1, 6))

    assert save(org.wanda, singewettstreit, name="Singewettstreit Walhall").status_code == 302
    singewettstreit.refresh_from_db()
    assert save(org.wanda, singewettstreit, end="2028-01-07").status_code == 302
    singewettstreit.refresh_from_db()
    assert (singewettstreit.name, singewettstreit.end) == ("Singewettstreit Walhall", date(2028, 1, 7))

    response = save(org.wanda, singewettstreit, start="2028-01-02")

    assert response.status_code == 200
    assert field_errors(_tree(response)) == {"start": PAST}
    singewettstreit.refresh_from_db()
    assert singewettstreit.start == date(2028, 1, 3)


def test_ag3_ende_vor_beginn_auch_am_selben_tag_mit_frueherer_uhrzeit(org, pfingstlager):
    for values in ({"start": "2028-06-02", "end": "2028-06-02", "start_time": "18:00", "end_time": "12:00"},
                   {"start": "2028-06-02", "end": "2028-06-01"}):
        response = create(org.wanda, **values)
        assert response.status_code == 200, values
        root = _tree(response)
        assert field_errors(root) == {"end": END_BEFORE_START}, values
        # Die Eingaben bleiben stehen.
        assert {name: field_values(step_form(root))[name] for name in values} == values
        response = save(org.wanda, pfingstlager, **values)
        assert field_errors(_tree(response)) == {"end": END_BEFORE_START}, values

    assert not Event.objects.exclude(pk=pfingstlager.pk).exists()
    pfingstlager.refresh_from_db()
    assert (pfingstlager.end, pfingstlager.end_time) == (date(2028, 6, 5), None)
    # Gegenprobe: Am selben Tag mit späterer Uhrzeit geht es.
    assert create(org.wanda, start="2028-06-02", end="2028-06-02", start_time="10:00",
                  end_time="16:00").status_code == 302


def test_ag4_ab_29_tagen_fragt_das_tool_ob_die_dauer_stimmt(org):
    client = client_for(org.wanda)
    _found, creation_key = open_create(org.wanda, client=client)
    form = {"name": "Bundeslager 2028", "start": "2028-07-20", "start_time": "18:00", "end": "2028-08-29",
            "end_time": "12:00", "location": "", "creation_key": creation_key}

    response = client.post(CREATE, form)

    assert response.status_code == 200
    root = _tree(response)
    assert field_errors(root) == {"end": "Die Veranstaltung dauert 41 Tage. Stimmt das?"}
    switch = switch_of(step_form(root))
    assert switch is not None
    assert _attr(switch, "checked") is None
    title = _one(_by_tag(root, "strong", id=_attr(switch, "aria-labelledby")))
    assert _visible_text(title) == DURATION_OK
    assert not Event.objects.exists()

    response = client.post(CREATE, {**form, "duration_ok": _attr(switch, "value")})

    assert response.status_code == 302
    assert Event.objects.get().name == "Bundeslager 2028"

    # 28 Tage ohne Nachfrage, 29 Tage mit.
    assert create(org.wanda, name="28 Tage", start="2028-07-01", end="2028-07-28").status_code == 302
    response = create(org.wanda, name="29 Tage", start="2028-07-01", end="2028-07-29")
    assert field_errors(_tree(response)) == {"end": "Die Veranstaltung dauert 29 Tage. Stimmt das?"}
    assert not Event.objects.filter(name="29 Tage").exists()


def test_ag4_auch_beim_bearbeiten_und_nur_fuer_die_bestaetigte_dauer(org, pfingstlager):
    response = save(org.wanda, pfingstlager, end="2028-07-12")

    assert field_errors(_tree(response)) == {"end": "Die Veranstaltung dauert 41 Tage. Stimmt das?"}
    confirmed = _attr(switch_of(dialog_of(_tree(response))), "value")

    # Wer danach eine andere Dauer einträgt, wird wieder gefragt; die Bestätigung gilt nur für die 41 Tage.
    response = save(org.wanda, pfingstlager, end="2028-07-20", duration_ok=confirmed)
    assert field_errors(_tree(response)) == {"end": "Die Veranstaltung dauert 49 Tage. Stimmt das?"}
    assert _attr(switch_of(dialog_of(_tree(response))), "checked") is None
    pfingstlager.refresh_from_db()
    assert pfingstlager.end == date(2028, 6, 5)

    assert save(org.wanda, pfingstlager, end="2028-07-12", duration_ok=confirmed).status_code == 302
    pfingstlager.refresh_from_db()
    assert pfingstlager.end == date(2028, 7, 12)
    # Ändert sie danach nur den Namen, fragt das Tool nicht wieder.
    assert save(org.wanda, pfingstlager, name="Großes Pfingstlager").status_code == 302


def test_ag5_ort_mit_101_zeichen_und_ort_nur_aus_leerzeichen(org, pfingstlager):
    response = create(org.wanda, location="x" * 101)

    assert response.status_code == 200
    root = _tree(response)
    assert field_errors(root) == {"location": "Der Ort darf höchstens 100 Zeichen lang sein."}
    # Nichts wird abgeschnitten.
    assert field_values(step_form(root))["location"] == "x" * 101
    response = save(org.wanda, pfingstlager, location="x" * 101)
    assert field_errors(_tree(response)) == {"location": "Der Ort darf höchstens 100 Zeichen lang sein."}
    assert not Event.objects.exclude(pk=pfingstlager.pk).exists()

    assert create(org.wanda, location="   ").status_code == 302
    assert Event.objects.exclude(pk=pfingstlager.pk).get().location == ""
    assert save(org.wanda, pfingstlager, location=" " + "x" * 100 + " ").status_code == 302
    pfingstlager.refresh_from_db()
    assert pfingstlager.location == "x" * 100


def test_ag6_uhrzeit_ohne_datum(org, pfingstlager):
    cases = [
        ({"start": "", "start_time": "18:00"}, {"start": "Bitte gib den Beginn ein."}),
        ({"end": "", "end_time": "12:00"}, {"end": "Bitte gib das Ende ein."}),
    ]
    for values, errors in cases:
        response = create(org.wanda, **values)
        assert response.status_code == 200, values
        assert field_errors(_tree(response)) == errors, values
        response = save(org.wanda, pfingstlager, **values)
        assert field_errors(_tree(response)) == errors, values

    assert not Event.objects.exclude(pk=pfingstlager.pk).exists()


def test_eine_unmoegliche_uhrzeit_steht_als_fehler_am_feld(org):
    """Am Browser vorbei geschickt: „25:00“ ist keine Uhrzeit; der Fehler steht am Feld (wie VG3 aus #100)."""
    response = create(org.wanda, start_time="25:00")

    assert field_errors(_tree(response)) == {"start": "Bitte gib eine gültige Uhrzeit ein."}
    assert not Event.objects.exists()


def test_ag7_ein_aelteres_zweites_fenster_ueberschreibt_nichts(org, pfingstlager):
    first, second = client_for(org.wanda), client_for(org.wanda)
    opened = shown(pfingstlager)
    first.get(edit_address(pfingstlager))
    second.get(edit_address(pfingstlager))

    assert first.post(edit_address(pfingstlager), {**opened, "location": "Burg Ludwigstein"}).status_code == 302
    response = second.post(edit_address(pfingstlager), {**opened, "name": "Pfingstlager Walhall"})

    assert response.status_code == 200
    pfingstlager.refresh_from_db()
    assert (pfingstlager.name, pfingstlager.location) == ("Pfingstlager 2028", "Burg Ludwigstein")
    found = dialog_of(_tree(response))
    assert "Pfingstlager 2028 wurde inzwischen geändert. Bitte prüfe die Angaben und speichere erneut." in (
        _visible_text(found))
    # Der Dialog zeigt den neuen Stand; erneut gespeichert gilt die Änderung.
    assert field_values(found)["location"] == "Burg Ludwigstein"
    version = _attr(_one(_by_tag(found, "input", name="version")), "value")
    assert second.post(edit_address(pfingstlager), {**shown(pfingstlager), "name": "Pfingstlager Walhall",
                                                     "version": version}).status_code == 302
    pfingstlager.refresh_from_db()
    assert (pfingstlager.name, pfingstlager.location) == ("Pfingstlager Walhall", "Burg Ludwigstein")


@pytest.mark.django_db(transaction=True)
def test_ag7_gleichzeitig_gespeichert_gelingt_genau_eine_aenderung():
    """Unabhängige Prüfung, B2: zwei Fenster speichern wirklich gleichzeitig; die Sperre lässt genau eines durch."""
    o = build_people()
    lager = event_of(o.wanda, "Pfingstlager 2028", date(2028, 6, 2), date(2028, 6, 5))
    values = {"name": "Pfingstlager 2028", "start": date(2028, 6, 2), "start_time": None, "end": date(2028, 6, 5),
              "end_time": None, "location": ""}

    results = _one_after_the_other(
        lambda: Rights(o.wanda).edit_event(lager.key, {**values, "location": "Burg Ludwigstein"}, "1"),
        lambda: Rights(o.wanda).edit_event(lager.key, {**values, "name": "Pfingstlager Walhall"}, "1"))

    assert sorted(done for done, _entry, _text in results) == [False, True]
    lager.refresh_from_db()
    assert (lager.name, lager.location, lager.version) == ("Pfingstlager 2028", "Burg Ludwigstein", 2)


def test_ag2_eine_uhrzeit_mit_sekunden_blockiert_spaeter_nicht_den_namen(org, monkeypatch):
    """Unabhängige Prüfung, V1: Am Browser vorbei mit Sekunden gespeichert, zeigt der Dialog nur Stunde und Minute.

    Ändert die Leitung bei der laufenden Veranstaltung danach nur den Namen, ist das kein geänderter Beginn (AG2).
    """
    assert create(org.wanda, name="Thing", start="2028-01-05", start_time="10:00:30").status_code == 302
    thing = Event.objects.get(name="Thing")
    assert thing.start_time == time(10, 0)
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2028, 1, 6))

    response = save(org.wanda, thing, name="Stammesthing", start_time="10:00")

    assert response.status_code == 302
    thing.refresh_from_db()
    assert thing.name == "Stammesthing"


# ---------- Datenmodell ----------


def test_die_datenbank_lehnt_ende_vor_beginn_am_selben_tag_und_ort_mit_leerzeichen_am_rand_ab(org):
    base = {"name": "Probe", "start": date(2028, 6, 2), "end": date(2028, 6, 2)}
    for values in ({"start_time": time(18, 0), "end_time": time(12, 0)}, {"location": " Burg"}):
        with pytest.raises(IntegrityError), transaction.atomic():
            Event.objects.create(**base, **values)

    Event.objects.create(**base, start_time=time(10, 0), end_time=time(16, 0))
    Event.objects.create(**{**base, "end": date(2028, 6, 3)}, start_time=time(18, 0), end_time=time(12, 0))


# ---------- Zielbild ----------

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "docs" / "zielbilder" / "veranstaltung.html"
CHECKSUM = "9d1c86c1d2a7531e05df07457e8a787d7664ba7476026c92784ec84d1f19184a"


def test_zielbild_liegt_unveraendert_mit_eintrag_im_repo():
    readme = (ROOT / "docs" / "zielbilder" / "README.md").read_text()

    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == CHECKSUM
    section = readme.split("## Veranstaltung", 1)
    assert len(section) == 2
    for must in (CHECKSUM, "16.11.2026", "Orientierung, keine Anforderung", "Abweichungen", "#356", "#379"):
        assert must in section[1].split("\n## ", 1)[0], must


def test_zielbild_laedt_nichts_von_fremden_servern():
    content = TARGET.read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert all(mail.endswith("@example.org") for mail in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", content))
