"""Rauchtest der Zahl der Zeichen an Vor- und Nachname verwalteter Personen (#330, Szenarien 5 und 6).

Die Nummern verweisen auf Sebastians Szenarien vom 14.11.2026 in #330
(https://github.com/sebivtt/dpv-participant-management/issues/330#issuecomment-6876861670). Die Zahl
und die rote Meldung vor dem Speichern schreibt erst das Skript; deshalb lässt sie sich nur im Browser
prüfen. Erika leitet Walhall und springt in der Sippe Falken ein (VP-01, EH-18). Was der Server
ausliefert und speichert, prüft tests/test_namen_grenze.py. Alle Namen sind erfunden.
"""

import re
from datetime import date

import pytest
from playwright.sync_api import Page, expect

from persons.models import ManagedPerson
from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_benennen import _walhall_for_erika
from rauchtests.test_rauchtest import _press, _type_like_a_phone

pytestmark = pytest.mark.django_db(transaction=True)

FIRST_TOO_LONG = "Der Vorname darf höchstens 50 Zeichen lang sein."
LAST_TOO_LONG = "Der Nachname darf höchstens 50 Zeichen lang sein."


def _shows(page: Page, field_id: str, number: int) -> None:
    """Sichtbar „12/50“, Vorleseprogramme hören „12 von 50 Zeichen“."""
    count = page.locator(f"#{field_id}-zahl")
    expect(count).to_be_visible()
    expect(count.locator("[aria-hidden='true']")).to_have_text(f"{number}/50")
    expect(count.locator(".sr-nur")).to_have_text(f"{number} von 50 Zeichen")


def _too_long(page: Page, field_id: str, message: str) -> None:
    """Die Zahl ist rot wie die Meldung darunter, und die Meldung ist mit dem Feld verbunden."""
    count = page.locator(f"#{field_id}-zahl")
    error = page.locator(f"#{field_id}-fehler")
    expect(error).to_have_text(message)
    expect(count).to_have_class(re.compile(r"\bist-zu-lang\b"))
    assert count.evaluate("e => getComputedStyle(e).color") == error.evaluate("e => getComputedStyle(e).color")
    # Erst die Meldung, dann die Zahl, wie beim Fahrtennamen (#215).
    expect(page.locator(f"#{field_id}")).to_have_accessible_description(re.compile("^" + re.escape(message)))


def _type(page: Page, field, text: str, device: str) -> None:
    field.fill("")
    if device == "handy":
        _type_like_a_phone(field, text[:-2], text[-2], text[-2:], "")
    else:
        field.press_sequentially(text)


@pytest.mark.parametrize("device", ["pc", "handy"])
def test_s5_s6_zahl_beim_tippen_rot_bei_einundfuenfzig_und_dieselbe_meldung_nach_dem_speichern(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"

    # Szenario 5, beim Anlegen: „12/50“, bei 51 Zeichen rot mit Meldung.
    page.goto(f"{page_address}verwaltete-person/anlegen/")
    first = page.get_by_label("Vorname")
    first_id = first.get_attribute("id")
    _type(page, first, "Lena-Mariele", device)
    _shows(page, first_id, 12)
    expect(page.locator(f"#{first_id}-fehler")).to_have_count(0)
    _type(page, first, "L" * 51, device)
    _shows(page, first_id, 51)
    _too_long(page, first_id, FIRST_TOO_LONG)
    assert run_axe(page) == []

    # „Anlegen“: dieselbe Meldung am Feld, die Eingabe bleibt, niemand wird angelegt.
    page.get_by_label("Nachname").fill("Probe")
    page.get_by_label("Geburtsdatum").fill("2015-05-14")
    _press(page, page.locator("dialog.a-dialog .a-schalter"), device)
    _press(page, page.locator('dialog.a-dialog button[type="submit"]'), device)
    expect(page.locator(f"#{first_id}-fehler")).to_have_text(FIRST_TOO_LONG)
    expect(page.get_by_label("Vorname")).to_have_value("L" * 51)
    expect(page.get_by_label("Vorname")).to_have_attribute("aria-invalid", "true")
    assert not ManagedPerson.objects.filter(unit=units["falken"]).exists()

    # Szenario 6, beim Bearbeiten: derselbe Ablauf am Nachnamen.
    lena = ManagedPerson.objects.create(first_name="Lena", last_name="Probe", scout_name="Kiwi",
                                        birth_date=date(2015, 5, 14), unit=units["falken"])
    page.goto(f"{page_address}verwaltete-person/{lena.key}/bearbeiten/")
    last = page.get_by_label("Nachname")
    last_id = last.get_attribute("id")
    _shows(page, last_id, 5)
    _type(page, last, "P" * 51, device)
    _shows(page, last_id, 51)
    _too_long(page, last_id, LAST_TOO_LONG)
    _press(page, page.locator('dialog.a-dialog button[type="submit"]'), device)
    expect(page.locator(f"#{last_id}-fehler")).to_have_text(LAST_TOO_LONG)
    expect(page.get_by_label("Nachname")).to_have_value("P" * 51)
    lena.refresh_from_db()
    assert lena.last_name == "Probe"
    assert run_axe(page) == []
