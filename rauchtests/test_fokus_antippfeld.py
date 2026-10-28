"""Rauchtest der Fokusmarkierung am Feld zum Antippen (#207).

Wie ein Fokusrahmen aussieht, entscheidet erst der Browser; deshalb lässt es sich nur hier prüfen.
Die Nummern verweisen auf die Szenarien zu #207 (28.10.2026). „Rahmen außen“ heißt: der kräftige
Fokusrahmen (mindestens 2 Pixel, Kontrast mindestens 3 : 1, #78) um das ganze Feld, nicht innen
um die Eingabe und ohne blassen Schein. Jeder Test läuft in Chromium, Firefox und WebKit
(conftest.py). Alle Konten und Daten sind erfunden.
"""

import pytest
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, PC, focus_visible, login
from rauchtests.test_rauchtest import _press, _set_scout_name, _tab_key, _tab_to_element

pytestmark = pytest.mark.django_db(transaction=True)

GRUPPE = "a-antippfeld-gruppe"


def _rahmen_der_gruppe(page: Page) -> dict:
    return page.locator(f".{GRUPPE}").first.evaluate(
        "e => { const s = getComputedStyle(e);"
        " return {stil: s.outlineStyle, breite: s.outlineWidth, abstand: s.outlineOffset, farbe: s.outlineColor, schein: s.boxShadow} }"
    )


def _nur_aussen(page: Page) -> dict:
    """Genau eine Markierung: der kräftige Rahmen außen um das ganze Feld, innen keine, kein Schein."""
    station = focus_visible(page)
    assert station["rahmen"] == GRUPPE, f"Rahmen nicht außen um das Feld: {station}"
    assert not station["innen"], f"innen noch eine Markierung: {station}"
    assert station["sichtbar"] and station["kontrast"] >= 3, station
    rahmen = _rahmen_der_gruppe(page)
    assert rahmen["schein"] == "none", f"blasser Schein um das Feld: {rahmen}"
    assert page.evaluate("getComputedStyle(document.activeElement).boxShadow") == "none", "blasser Schein innen"
    assert float(rahmen["abstand"].removesuffix("px")) >= 0, f"Rahmen liegt innen: {rahmen}"
    return rahmen


# Szenario 1 (Maus) und Szenario 3 (Handy)
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_antippen_zeigt_nur_den_rahmen_aussen(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    page.goto(f"{BASE}/profil/")
    _press(page, page.locator("[data-oeffnen]"), device)
    expect(page.get_by_label("Fahrtenname", exact=True)).to_be_focused()
    _nur_aussen(page)


# Szenario 2: geschlossen mit Tab erreicht, dann Enter; Szenario 4: weiter zum ×-Knopf
def test_nur_mit_der_tastatur_rahmen_aussen_und_der_x_knopf_mit_eigenem(pc):
    login(pc)
    _set_scout_name("Falkenflug")
    pc.goto(f"{BASE}/profil/")

    _tab_to_element(pc, "[data-oeffnen]")
    geschlossen = _nur_aussen(pc)
    pc.keyboard.press("Enter")
    expect(pc.get_by_label("Fahrtenname", exact=True)).to_be_focused()
    offen = _nur_aussen(pc)
    assert offen == geschlossen, f"Rahmen springt beim Öffnen: {geschlossen} → {offen}"

    pc.keyboard.press("Escape")
    expect(pc.locator("[data-oeffnen]")).to_be_focused()
    pc.keyboard.press(_tab_key(pc))
    expect(pc.get_by_role("button", name="Fahrtenname leeren")).to_be_focused()
    station = focus_visible(pc)
    assert station["rahmen"] == "selbst" and station["sichtbar"] and station["kontrast"] >= 3, station
    assert _rahmen_der_gruppe(pc)["stil"] == "none", "das Feld neben dem ×-Knopf ist noch markiert"


# Szenario 5: Feld kommt offen mit Fehlermeldung zurück
def test_nach_einem_fehler_nur_der_rahmen_aussen(pc):
    login(pc)
    pc.goto(f"{BASE}/profil/")
    pc.locator("[data-oeffnen]").click()
    field = pc.get_by_label("Fahrtenname", exact=True)
    field.fill("K" * 51)
    pc.get_by_role("button", name="Speichern").click()
    expect(pc.locator("#id_scout_name-fehler")).to_be_visible()
    expect(field).to_be_focused()
    _nur_aussen(pc)


# Szenario 6: ohne Skript das einfache Formular
def test_ohne_skript_nur_der_rahmen_aussen(pc, browser):
    login(pc)
    context = browser.new_context(java_script_enabled=False, storage_state=pc.context.storage_state(), **PC)
    page = context.new_page()
    try:
        page.goto(f"{BASE}/profil/")
        field = page.get_by_label("Fahrtenname", exact=True)
        field.click()
        expect(field).to_be_focused()
        _nur_aussen(page)
    finally:
        context.close()


# Szenario 7: im Bausteinkatalog wie Szenarien 1 bis 4
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_im_bausteinkatalog_wie_auf_mein_profil(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    page.goto(f"{BASE}/bausteine/")
    section = page.locator("section[aria-labelledby='h-antippfeld']")
    _press(page, section.locator("[data-oeffnen]"), device)
    expect(section.locator(".form-control")).to_be_focused()
    _nur_aussen(page)
    if device == "pc":
        page.keyboard.press("Escape")
        expect(section.locator("[data-oeffnen]")).to_be_focused()
        _nur_aussen(page)
        page.keyboard.press(_tab_key(page))
        expect(section.locator("[data-leeren]")).to_be_focused()
        assert focus_visible(page)["rahmen"] == "selbst"
        assert _rahmen_der_gruppe(page)["stil"] == "none"
