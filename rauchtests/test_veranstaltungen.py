"""Rauchtest „Veranstaltungen“ im Browser (#100, VG10): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und ist danach Mitglied der Sippe Falken, hat
also eine Zuordnung (VA-01). Geprüft werden die Teile, die nur ein Browser zeigt: der Punkt
„Veranstaltungen“ in der Seitenleiste und im Menü, „Veranstaltung erstellen“ (bis #380 ein Dialog, der den
Fokus hält), Beginn und Ende als Baustein „Datumsfeld“ (das Feld des Browsers, N3 zu #117), der Name auch wie am
Handy mit Autokorrektur und Wortvorschlägen, die kurze Meldung, der Knopf „Bearbeiten“, nichts steht
seitlich über, der Fokus ist zu sehen, und die Seiten bestehen die Prüfung auf Barrierefreiheit. Das Datum
setzt der Test mit `fill`, weil jeder Browser sein Datumsfeld anders bedienen lässt; erreicht wird das
Feld mit der Tastatur. Die Regeln selbst prüft tests/test_veranstaltungen.py. Alle Namen sind erfunden.

Seit #379 öffnet der Stift der Kachel „Grunddaten“ den Dialog statt des Knopfs „Bearbeiten“, und neben Beginn
und Ende steht je eine Uhrzeit; die Felder sucht der Test deshalb über ihren Namen. Ein Beginn vor heute ist
seit #379 verboten; damit die Tage aus #100 gültig bleiben, ist „heute“ hier der 05.01.2027. Uhrzeiten, Ort,
Kachel und Leitungsseite prüft rauchtests/test_grunddaten.py.

Seit #380 ist „Veranstaltung erstellen“ kein Dialog mehr, sondern Schritt 1 eines Ablaufs: „Weiter“ führt zur
Zusammenfassung, erst „Veranstaltung speichern“ dort zur Leitungsseite. Nachgezogen sind nur diese Wege; den
Ablauf selbst prüft rauchtests/test_veranstaltung_anlegen.py.
"""

from datetime import date

import pytest
from django.utils import timezone

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe, ueber_schritt_einladungstext
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone
from roles.models import Role
from tests.test_rollen import give, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
LIST = f"{BASE}/veranstaltungen/"
NAV_LINK = '.a-sidebar .a-navlink[href="/veranstaltungen/"]'
CREATE_BUTTON = '[aria-labelledby="h-veranstaltungen"] .a-flaeche-aktion[href="/veranstaltungen/erstellen/"]'
EDIT_BUTTON = 'main a.a-stift[href$="/bearbeiten/"]'
START = 'dialog input[name="start"]'
END = 'dialog input[name="end"]'
# Seit #163 steht davor im Adressfeld „Adresse suchen“; gemeint ist der Hauptknopf unten.
SUBMIT = 'dialog .a-dialog-fuss button[type="submit"]'
# Schritt 1 beim Anlegen (#380): die Felder im Formular des Schritts, „Weiter“ und auf der Zusammenfassung „Veranstaltung speichern“.
STEP_START = 'form#f-schritt input[name="start"]'
STEP_END = 'form#f-schritt input[name="end"]'
STEP_SUBMIT = 'form#f-schritt .a-schritt-rechts button[type="submit"]'
CREATED = "Probelager 2027 ist als Entwurf gespeichert. Nur die Leitung sieht die Veranstaltung."


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    """„Heute“ liegt vor den Tagen der Szenarien von #100; der Server läuft im selben Prozess wie der Test."""
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2027, 1, 5))


def _erika_in_den_falken() -> None:
    """Erika wird Mitglied der Sippe Falken und hat damit eine Zuordnung (BER-03)."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    give(erika, R.MEMBER, unit(U.GROUP, "Sippe Falken", walhall))


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def test_am_pc_nur_mit_der_tastatur_erstellen_und_bearbeiten(pc):
    login(pc)
    _erika_in_den_falken()
    pc.goto(f"{BASE}/")

    stations = _stations_to_element(pc, NAV_LINK, steps=20)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(LIST)
    expect(pc.locator('[aria-labelledby="h-veranstaltungen"]')).to_contain_text("Du leitest noch keine Veranstaltung.")
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, CREATE_BUTTON, steps=20)
    _all_visible(stations)
    expect(pc.locator(CREATE_BUTTON)).to_have_text("Veranstaltung erstellen")
    pc.keyboard.press("Enter")
    pc.wait_for_url(f"{LIST}erstellen/")
    expect(pc.locator("h1")).to_have_text("Veranstaltung erstellen")
    name = pc.get_by_label("Name")
    expect(name).to_be_focused()
    assert run_axe(pc) == []

    pc.keyboard.type("Probelager 2027")
    pc.keyboard.press("Tab")
    start = pc.locator(STEP_START)
    expect(start).to_be_focused()
    assert start.get_attribute("type") == "date"
    start.fill("2027-05-15")
    stations = _stations_to_element(pc, 'input[name="end"]', steps=10)
    _all_visible(stations)
    end = pc.locator(STEP_END)
    assert end.get_attribute("type") == "date"
    end.fill("2027-05-17")
    stations = _stations_to_element(pc, STEP_SUBMIT, steps=20)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    ueber_schritt_einladungstext(pc, keyboard=True)
    stations = _stations_to_element(pc, STEP_SUBMIT, steps=30)
    _all_visible(stations)
    expect(pc.locator(STEP_SUBMIT)).to_have_text("Veranstaltung speichern")
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{LIST}*/")
    expect(pc.locator(".a-kurz")).to_contain_text(CREATED)
    expect(pc.locator("h1")).to_have_text("Probelager 2027")
    expect(pc.locator("main")).to_contain_text("15.05.2027 bis 17.05.2027")
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, EDIT_BUTTON, steps=20)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    expect(_dialog(pc).locator("h2")).to_have_text("Probelager 2027 bearbeiten")
    expect(pc.get_by_label("Name")).to_be_focused()
    pc.locator(END).fill("2027-05-18")
    stations = _stations_to_element(pc, SUBMIT, steps=20)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    expect(pc.locator(".a-kurz")).to_contain_text("Die Angaben zu Probelager 2027 sind gespeichert.")
    expect(pc.locator("main")).to_contain_text("15.05.2027 bis 18.05.2027")


def test_am_pc_fehler_am_feld_kommen_vom_tool(pc):
    login(pc)
    _erika_in_den_falken()
    pc.goto(f"{LIST}erstellen/")
    pc.locator(STEP_START).fill("2027-05-17")
    pc.locator(STEP_END).fill("2027-05-15")
    # Der Browser hält das leere Pflichtfeld nicht selbst an; die Meldungen kommen vom Tool.
    pc.get_by_role("button", name="Weiter").click()
    expect(pc.locator("main")).to_contain_text("Bitte gib den Namen ein.")
    expect(pc.locator("main")).to_contain_text("Das Ende liegt vor dem Beginn.")
    expect(pc.get_by_label("Name")).to_have_attribute("aria-invalid", "true")
    expect(pc.locator(STEP_END)).to_have_accessible_description("Das Ende liegt vor dem Beginn.")
    expect(pc.locator(STEP_START)).to_have_value("2027-05-17")
    assert run_axe(pc) == []

    # Seit #380 führt „Abbrechen“ in Schritt 1 ohne Rückfrage zur Liste (B5).
    pc.get_by_role("link", name="Abbrechen").click()
    pc.wait_for_url(LIST)
    expect(pc.locator("main")).to_contain_text("Du leitest noch keine Veranstaltung.")


def test_am_handy_nur_mit_der_tastatur_und_mit_autokorrektur(handy):
    login(handy)
    _erika_in_den_falken()
    handy.goto(LIST)
    _no_side_scroll(handy)
    expect(handy.locator(CREATE_BUTTON)).to_be_visible()
    assert run_axe(handy) == []

    stations = _stations_to_element(handy, CREATE_BUTTON, steps=30)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{LIST}erstellen/")
    expect(handy.locator("h1")).to_have_text("Veranstaltung erstellen")
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    # Wie am Handy: ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; nichts verschwindet.
    name = handy.get_by_label("Name")
    _type_like_a_phone(name, "Probe", "l", "lager", " 2027")
    expect(name).to_have_value("Probelager 2027")
    handy.locator(STEP_START).fill("2027-05-15")
    handy.locator(STEP_END).fill("2027-05-17")
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, STEP_SUBMIT, steps=20)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    ueber_schritt_einladungstext(handy, keyboard=True)
    stations = _stations_to_element(handy, STEP_SUBMIT, steps=30)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{LIST}*/")
    expect(handy.locator(".a-kurz")).to_contain_text(CREATED)
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    handy.goto(LIST)
    expect(handy.locator('[aria-labelledby="h-veranstaltungen"] li')).to_contain_text("Probelager 2027")
    _no_side_scroll(handy)
