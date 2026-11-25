"""Rauchtest „Veranstaltung anlegen in Schritten“ im Browser (#380, BG6 und B6): am PC und am Handy, je nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und ist Mitglied der Sippe Falken, hat also eine
Zuordnung (VA-01). „Heute“ ist wie in den Szenarien der 05.01.2028; der Server läuft im selben Prozess wie der Test.
Geprüft werden die Teile, die nur ein Browser zeigt: der ganze Ablauf mit der Tastatur, von „Veranstaltung erstellen“
über Schritt 1 und die Zusammenfassung, „Zurück“, den Dialog „Anlegen abbrechen?“, den Esc schließt, bis zu
„Veranstaltung speichern“ und „Entwurf löschen“; die Fortschrittsanzeige, der Name am Handy wie mit Autokorrektur und
Wortvorschlägen getippt, nichts steht seitlich über, der Fokus ist zu sehen, und die Seiten bestehen die Prüfung auf
Barrierefreiheit. Das Datum setzt der Test mit `fill` wie in rauchtests/test_veranstaltungen.py. Die Regeln selbst
prüft tests/test_veranstaltung_anlegen.py. Alle Namen sind erfunden; „Burg Ludwigstein“ stammt aus dem Zielbild (#356).
"""

from datetime import date

import pytest
from django.utils import timezone
from playwright.sync_api import Page, expect

from events.models import Event
from rauchtests.conftest import BASE, expect_modal, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone
from rauchtests.test_veranstaltungen import CREATE_BUTTON, _dialog, _erika_in_den_falken

LIST = f"{BASE}/veranstaltungen/"
STEP = "form#f-schritt"
# Seit #163 steht davor im Adressfeld „Adresse suchen“; gemeint ist der Hauptknopf rechts unten.
SUBMIT = f'{STEP} .a-schritt-rechts button[type="submit"]'
# Einfaches CSS, weil der Fokus mit `matches()` des Browsers geprüft wird: „Zurück“ ist der Link rechts, „Abbrechen“ links.
BACK = f"{STEP} .a-schritt-rechts > a"
CANCEL = f"{STEP} .a-schritt-knoepfe > a.btn-zart"
STEPS = "ol.a-schritte li"
SAVED = "Pfingstlager 2028 ist als Entwurf gespeichert. Nur die Leitung sieht die Veranstaltung."


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2028, 1, 5))


def _zu(page: Page, selector: str, steps: int = 30) -> None:
    """Mit Tab zum Element und Enter; jede Station hat einen sichtbaren Fokus."""
    stations = _stations_to_element(page, selector, steps=steps)
    _all_visible(stations)
    page.keyboard.press("Enter")


def _schritt_1(page: Page, steps: int) -> None:
    """Von der Liste mit „Veranstaltung erstellen“ zu Schritt 1."""
    page.goto(LIST)
    _zu(page, CREATE_BUTTON, steps=steps)
    page.wait_for_url(f"{LIST}erstellen/")
    expect(page.locator("h1")).to_have_text("Veranstaltung erstellen")
    expect(page.locator(STEPS)).to_have_text(["Schritt 1 Grunddaten", "Schritt 2 Zusammenfassung"])
    expect(page.locator(f"{STEPS}[aria-current='step']")).to_have_text("Schritt 1 Grunddaten")
    expect(page.get_by_label("Name")).to_be_focused()
    _no_side_scroll(page)
    assert run_axe(page) == []


def _ausfuellen(page: Page, phone: bool) -> None:
    """Füllt Schritt 1 aus wie in B1; die Uhrzeiten bleiben wie vorausgefüllt."""
    name = page.get_by_label("Name")
    if phone:
        # Wie am Handy: ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; nichts verschwindet.
        _type_like_a_phone(name, "Pfingst", "l", "lager", " 2028")
    else:
        page.keyboard.type("Pfingstlager 2028")
    expect(name).to_have_value("Pfingstlager 2028")
    page.locator(f'{STEP} input[name="start"]').fill("2028-06-02")
    page.locator(f'{STEP} input[name="end"]').fill("2028-06-05")
    page.locator(f'{STEP} input[name="location"]').fill("Burg Ludwigstein")
    _no_side_scroll(page)


def _zusammenfassung(page: Page) -> None:
    page.wait_for_url(f"{LIST}*/anlegen/zusammenfassung/")
    expect(page.locator("h1")).to_have_text("Pfingstlager 2028")
    expect(page.locator(f"{STEPS}[aria-current='step']")).to_have_text("Schritt 2 Zusammenfassung")
    expect(page.locator('[aria-labelledby="h-grunddaten"] .a-kalenderblatt')).to_have_text(
        ["Beginn: Fr 02 Jun 2028 18:00", "Ende: Mo 05 Jun 2028 12:00"])
    _no_side_scroll(page)
    assert run_axe(page) == []


def test_am_pc_nur_mit_der_tastatur_durch_den_ganzen_ablauf(pc):
    login(pc)
    _erika_in_den_falken()
    _schritt_1(pc, steps=25)
    _ausfuellen(pc, phone=False)
    _zu(pc, SUBMIT, steps=22)
    _zusammenfassung(pc)

    # B2: „Zurück“ führt zu Schritt 1 mit allen Eingaben; ein geänderter Ort kommt in der Zusammenfassung an.
    _zu(pc, BACK)
    pc.wait_for_url(f"{LIST}*/anlegen/")
    expect(pc.get_by_label("Name")).to_have_value("Pfingstlager 2028")
    expect(pc.locator(f'{STEP} input[name="location"]')).to_have_value("Burg Ludwigstein")
    pc.locator(f'{STEP} input[name="location"]').fill("Zeltplatz Moor")
    _zu(pc, SUBMIT, steps=22)
    _zusammenfassung(pc)
    expect(pc.locator('[aria-labelledby="h-grunddaten"] .a-kalender-ort')).to_contain_text("Zeltplatz Moor")

    # B6: „Abbrechen“ öffnet den Dialog; Esc schließt ihn ohne Änderung.
    _zu(pc, CANCEL)
    pc.wait_for_url(f"{LIST}*/anlegen/abbrechen/")
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    expect_modal(dialog)
    expect(dialog.locator("h2")).to_have_text("Anlegen abbrechen?")
    expect(dialog.locator(".a-dialog-fuss button")).to_have_text(["Entwurf löschen", "Entwurf speichern"])
    _no_side_scroll(pc)
    assert run_axe(pc) == []
    pc.keyboard.press("Escape")
    pc.wait_for_url(f"{LIST}*/anlegen/zusammenfassung/")
    expect(_dialog(pc)).to_have_count(0)

    # B1: „Veranstaltung speichern“ führt zur Leitungsseite mit der kurzen Meldung.
    _zu(pc, SUBMIT)
    pc.wait_for_url(f"{LIST}*/")
    expect(pc.locator(".a-kurz")).to_contain_text(SAVED)
    expect(pc.locator("h1")).to_have_text("Pfingstlager 2028")
    assert Event.objects.get().creating_by is None


def test_am_handy_nur_mit_der_tastatur_abbrechen_und_entwurf_loeschen(handy):
    login(handy)
    _erika_in_den_falken()
    _schritt_1(handy, steps=30)
    _ausfuellen(handy, phone=True)
    _zu(handy, SUBMIT, steps=22)
    _zusammenfassung(handy)
    # Schmal rutschen die Knöpfe nicht seitlich hinaus; der Hauptknopf bleibt sichtbar.
    expect(handy.locator(SUBMIT)).to_be_visible()

    # B3: „Abbrechen“, dann „Entwurf löschen“ führt zur Liste mit der Meldung; der Entwurf ist weg.
    _zu(handy, CANCEL)
    handy.wait_for_url(f"{LIST}*/anlegen/abbrechen/")
    expect(_dialog(handy)).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []
    _zu(handy, ".a-dialog-fuss button.btn-gefahr", steps=10)
    handy.wait_for_url(LIST)
    expect(handy.locator(".a-kurz")).to_contain_text("Der Entwurf Pfingstlager 2028 ist gelöscht.")
    expect(handy.locator('[aria-labelledby="h-veranstaltungen"]')).to_contain_text("Du leitest noch keine Veranstaltung.")
    _no_side_scroll(handy)
    assert not Event.objects.exists()
