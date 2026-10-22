"""Rauchtest der Knöpfe „Zurück“ und „Zur Startseite“ auf den Fehlerseiten im Browser (#21).

Ob „Zurück“ erscheint, entscheidet der Browser anhand der vorigen Seite; deshalb lässt es sich
nur hier prüfen. Die Nummern verweisen auf die Szenarien zu #21 (Planung am 22.10.2026). Jeder
Test läuft in Chromium, Firefox und WebKit (conftest.py). Alle Konten und Daten sind erfunden.
"""

import pytest
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_rauchtest import _all_visible, _tab_to

pytestmark = pytest.mark.django_db(transaction=True)

FOREIGN = "http://fremd.example"


def _click_link_to(page: Page, address: str, new_tab: bool = False) -> None:
    """Klickt auf der aktuellen Seite einen Link zu `address`, wie eine Person einen veralteten Link."""
    page.evaluate(
        """([address, newTab]) => {
            const link = document.createElement('a');
            link.href = address;
            link.textContent = 'Veralteter Link';
            if (newTab) link.target = '_blank';
            document.getElementById('inhalt').append(link);
        }""",
        [address, new_tab],
    )
    page.get_by_role("link", name="Veralteter Link").click()


def _send_expired_form(page: Page) -> None:
    """Schickt auf der aktuellen Seite ein Formular ohne gültigen Formularschutz ab, wie nach zu langem Warten."""
    page.evaluate(
        """() => {
            const form = document.createElement('form');
            form.method = 'post';
            form.action = '/abmelden/';
            form.innerHTML = '<button type="submit">Altes Formular abschicken</button>';
            document.getElementById('inhalt').append(form);
        }"""
    )
    page.get_by_role("button", name="Altes Formular abschicken").click()


def _back(page: Page):
    return page.get_by_role("link", name="Zurück", exact=True)


def _home(page: Page):
    return page.get_by_role("link", name="Zur Startseite")


# Szenarien 1, 5, 6 und 7: „Zurück“ führt auf die Seite des Tools, von der man kam
def test_aus_dem_tool_fuehrt_zurueck_auf_die_vorige_seite(pc, settings):
    settings.ROOT_URLCONF = "tests.urls"  # enthält Adressen für „kein Zugriff“ und Programmfehler
    login(pc)
    pages = [
        ("Diese Seite gibt es nicht.", lambda: _click_link_to(pc, "/gibt-es-nicht/")),
        ("Dafür fehlt dir die Berechtigung.", lambda: _click_link_to(pc, "/test/1/verboten/")),
        ("Das Formular ist abgelaufen.", lambda: _send_expired_form(pc)),
        ("Da ist etwas schiefgelaufen.", lambda: _click_link_to(pc, "/test/1/")),
    ]

    for heading, open_error_page in pages:
        pc.goto(f"{BASE}/muster/")
        open_error_page()
        expect(pc.get_by_role("heading", level=1)).to_have_text(heading)
        expect(_home(pc)).to_be_visible()
        expect(_back(pc), heading).to_be_visible()
        _back(pc).click()
        pc.wait_for_url(f"{BASE}/muster/")

    pc.goto(f"{BASE}/gibt-es-nicht/")
    _home(pc).click()
    pc.wait_for_url(f"{BASE}/")
    expect(pc.get_by_role("heading", level=1)).to_have_text("Hallo Erika!")


# Szenarien 2 und 4: direkt geöffnete Adresse, ohne Login
def test_direkt_geoeffnet_nur_zur_startseite_und_die_fuehrt_ohne_login_zum_login(pc):
    pc.goto(f"{BASE}/gibt-es-nicht/")

    expect(pc.get_by_role("heading", level=1)).to_have_text("Diese Seite gibt es nicht.")
    expect(_home(pc)).to_be_visible()
    expect(_back(pc)).to_be_hidden()
    _home(pc).click()
    pc.wait_for_url(f"{BASE}/anmelden/**")


# Szenario 3: Die fremde Seite erlaubt dem Browser ausdrücklich, sich selbst als vorige Seite zu
# nennen. So zeigt der Test, dass das Tool selbst prüft, und nicht nur der Browser schweigt.
def test_von_einer_fremden_seite_kein_zurueck(pc):
    pc.route(
        f"{FOREIGN}/**",
        lambda route: route.fulfill(
            content_type="text/html",
            body=f'<!doctype html><meta name="referrer" content="unsafe-url"><title>Fremd</title>'
            f'<a href="{BASE}/gibt-es-nicht/">Zum Tool</a>',
        ),
    )
    pc.goto(f"{FOREIGN}/stamm/")

    pc.get_by_role("link", name="Zum Tool").click()

    expect(pc.get_by_role("heading", level=1)).to_have_text("Diese Seite gibt es nicht.")
    assert pc.evaluate("document.referrer").startswith(FOREIGN), "Test ungültig: Browser nannte die fremde Seite nicht"
    expect(_home(pc)).to_be_visible()
    expect(_back(pc)).to_be_hidden()


# Szenario 9: Link aus dem Tool in einem neuen Tab
def test_im_neuen_tab_fuehrt_zurueck_ins_tool(pc):
    pc.goto(f"{BASE}/anmelden/")

    with pc.context.expect_page() as new_tab:
        _click_link_to(pc, "/gibt-es-nicht/", new_tab=True)
    tab = new_tab.value

    expect(tab.get_by_role("heading", level=1)).to_have_text("Diese Seite gibt es nicht.")
    _back(tab).click()
    tab.wait_for_url(f"{BASE}/anmelden/**")


# Szenario 8: nur mit der Tastatur, am PC und am Handy, beide Knöpfe ganz zu sehen
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_knoepfe_nur_mit_der_tastatur_und_ganz_zu_sehen(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    page.goto(f"{BASE}/anmelden/")
    _click_link_to(page, "/gibt-es-nicht/")
    expect(_back(page)).to_be_visible()

    width = page.viewport_size["width"]
    for button in (_back(page), _home(page)):
        box = button.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= width, f"Knopf ragt aus dem Bildschirm: {box}"
    stations = _tab_to(page, "Zurück")
    stations += _tab_to(page, "Zur Startseite", steps=1)
    _all_visible(stations)
    page.keyboard.press("Enter")
    page.wait_for_url(f"{BASE}/anmelden/**")


# Szenario 8: Prüfung auf Barrierefreiheit, auch wenn „Zurück“ zu sehen ist
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_fehlerseite_mit_zurueck_besteht_die_pruefung_auf_barrierefreiheit(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    page.goto(f"{BASE}/anmelden/")
    _click_link_to(page, "/gibt-es-nicht/")
    expect(_back(page)).to_be_visible()

    assert run_axe(page) == []
