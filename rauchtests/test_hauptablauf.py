"""Rauchtest des Hauptablaufs von P2 im Browser (#119): anlegen und Leitungswechsel, einmal mit der Maus, einmal nur mit der Tastatur.

Abschlusskriterium von P2 (#106). Die Kennungen H1 bis H6 verweisen auf den Kommentar „Szenarien (14.11.2026)“
in #119. Anders als die übrigen Rauchtests prüft dieser keine einzelne Seite, sondern ob die riskantesten Teile
zusammen funktionieren: Jede der vier Personen meldet sich wirklich über die Keycloak-Testumgebung an, jede in
ihrem eigenen Browserfenster, und alle sind gleichzeitig angemeldet. Die Regeln selbst prüfen
tests/test_verwaltete_personen.py, tests/test_entfernen.py und tests/test_benennen.py.

Die Personen der Szenarien nutzen vorhandene erfundene Konten aus dev/keycloak/dpv-realm.json, damit sich an der
Testumgebung nichts ändert (U2). Im Tool heißen sie so, wie Keycloak sie nennt:

- Fiete, Gruppenleitung der Sippe Falken: `gruppenleitung.falken` („Fiete Beispiel“),
- Wanda, Stammesleitung von Walhall: `erika.testfrau` („Erika Testfrau“), wie in den Rauchtests zu #117, #190 und #191,
- Frida, Mitglied der Falken und danach ihre Gruppenleitung: `mitglied.falken` („Finn Beispiel“),
- Zora, Stammesleitung der Zugvögel: `stammesleitung.leuchtturm` („Lars Beispiel“).

Rollen und Organisationen legt der Test nach dem Login direkt in der Datenbank an, wie die übrigen Rauchtests.
Damit Wanda Frida benennen kann, muss es Fridas Konto im Tool schon geben; deshalb meldet sie sich vorher einmal
in einem eigenen Fenster an, das danach zugeht. Das Datum setzt der Test mit `fill`, weil jeder Browser sein
Datumsfeld anders bedienen lässt; erreicht wird das Feld mit der Tastatur. Alle Namen sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from persons.models import ManagedPerson
from rauchtests.conftest import BASE, ERIKA, PC, _context, focus_visible, login
from rauchtests.test_rauchtest import _all_visible, _keycloak_look, _keycloak_marks_focus, _stations_to_element, _tab_key, _tab_to
from roles.models import Role
from tests.test_rollen import give, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind

FIETE = ("gruppenleitung.falken", "testpasswort-fiete")
WANDA = ERIKA
FRIDA = ("mitglied.falken", "testpasswort-finn")
ZORA = ("stammesleitung.leuchtturm", "testpasswort-lars")

PERSONS = '[aria-labelledby="h-personen"]'
ADD_BUTTON = f'{PERSONS} .a-flaeche-aktion[href$="/verwaltete-person/anlegen/"]'
REMOVE_BUTTON = '[aria-labelledby="h-leitungen"] .a-leitung-knopf'
APPOINT_BUTTON = '[aria-labelledby="h-leitungen"] .a-flaeche-aktion'
CONSENT = 'dialog input[name="consent"]'
SUBMIT = 'dialog.a-dialog button[type="submit"]'
NOT_FOUND = "Diese Seite gibt es nicht."


@pytest.fixture
def new_window(browser, browser_name, tool):
    """Öffnet je Person ein eigenes Browserfenster am PC, mit eigener Anmeldung; am Ende gehen alle zu."""
    contexts = []

    def open_window() -> Page:
        context = _context(browser, browser_name, PC)
        contexts.append(context)
        return context.new_page()

    yield open_window
    for context in contexts:
        context.close()


def _units() -> dict:
    """Boreas mit Walhall (darin die Sippe Falken) und den Zugvögeln; noch ohne Rollen."""
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    falken = unit(U.GROUP, "Sippe Falken", walhall)
    zugvoegel = unit(U.TROOP, "Zugvögel", boreas)
    return {"boreas": boreas, "walhall": walhall, "falken": falken, "zugvoegel": zugvoegel}


def _account(account):
    return get_user_model().objects.get(username=account[0])


def _page_of(where) -> str:
    return f"{BASE}/organisation/{where.key}/"


def _lena_edit(lena) -> str:
    return f'{PERSONS} a[href$="/verwaltete-person/{lena.key}/bearbeiten/"]'


def _log_in(page: Page, account, keyboard: bool) -> None:
    """Meldet sich über die Login-Seite und Keycloak an; nur mit der Tastatur wie in test_rauchtest.py (#78)."""
    if not keyboard:
        login(page, account)
        return
    page.goto(f"{BASE}/")
    stations = _tab_to(page, "Mit DPV-Konto anmelden")
    _all_visible(stations)
    page.keyboard.press("Enter")
    # Erst tippen, wenn Keycloak seine Seite fertig geladen hat, wie eine Person auch (#33).
    username = page.locator("#username")
    username.wait_for()
    page.wait_for_load_state("load")
    password_without_focus = _keycloak_look(page, "#password")
    expect(username).to_be_focused()
    _keycloak_marks_focus(page, "#username", password_without_focus)
    page.keyboard.type(account[0])
    expect(username, "Benutzername nicht vollständig im Feld").to_have_value(account[0])
    page.keyboard.press(_tab_key(page))
    expect(page.locator("#password")).to_be_focused()
    _keycloak_marks_focus(page, "#password", password_without_focus)
    page.keyboard.type(account[1])
    page.keyboard.press("Enter")
    page.wait_for_url(f"{BASE}/")


def _press(page: Page, selector: str, keyboard: bool, steps: int = 60) -> None:
    """Betätigt einen Knopf oder Link: mit der Maus per Klick, sonst mit Tab dorthin, sichtbarem Fokus und Enter."""
    if keyboard:
        _all_visible(_stations_to_element(page, selector, steps=steps))
        page.keyboard.press("Enter")
    else:
        page.locator(selector).click()


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _h1_fiete_legt_lena_an(page: Page, falken, keyboard: bool):
    page_address = _page_of(falken)
    page.goto(page_address)
    _press(page, ADD_BUTTON, keyboard)
    page.wait_for_url(f"{page_address}verwaltete-person/anlegen/")
    expect(_dialog(page)).to_be_visible()
    first = page.get_by_label("Vorname")
    expect(first).to_be_focused()

    if keyboard:
        # Auch in den Feldern muss der Fokus zu sehen sein (H6), nicht nur auf den Knöpfen.
        fields = [focus_visible(page)]
        page.keyboard.type("Lena")
        page.keyboard.press(_tab_key(page))
        expect(page.get_by_label("Nachname")).to_be_focused()
        fields.append(focus_visible(page))
        page.keyboard.type("Probe")
        page.keyboard.press(_tab_key(page))
        birth = page.get_by_label("Geburtsdatum")
        expect(birth).to_be_focused()
        fields.append(focus_visible(page))
        _all_visible(fields)
        birth.fill("2015-05-14")
        _all_visible(_stations_to_element(page, 'input[name="scout_name"]', steps=6))
        page.keyboard.type("Kiwi")
        # Der Regler der Einwilligung (#98) geht mit Tab und Leertaste.
        _all_visible(_stations_to_element(page, CONSENT, steps=4))
        page.keyboard.press("Space")
        expect(page.locator(CONSENT)).to_be_checked()
        _press(page, SUBMIT, keyboard, steps=4)
    else:
        first.fill("Lena")
        page.get_by_label("Nachname").fill("Probe")
        page.get_by_label("Geburtsdatum").fill("2015-05-14")
        page.get_by_label("Fahrtenname").fill("Kiwi")
        page.locator("dialog .a-schalter").click()
        expect(page.locator(CONSENT)).to_be_checked()
        page.locator(SUBMIT).click()

    page.wait_for_url(f"{page_address}#verwaltete-person-anlegen")
    expect(page.locator(".a-kurz")).to_contain_text("Kiwi (Lena Probe) gehört jetzt zu Sippe Falken.")
    expect(page.locator(PERSONS)).to_contain_text("Kiwi")
    return ManagedPerson.objects.get(first_name="Lena", last_name="Probe")


def _h2_wanda_entfernt_fiete_und_benennt_frida(page: Page, falken, keyboard: bool) -> None:
    page_address = _page_of(falken)
    page.goto(page_address)
    expect(page.locator(REMOVE_BUTTON)).to_contain_text("Fiete Beispiel")
    _press(page, REMOVE_BUTTON, keyboard)
    page.wait_for_url(f"{page_address}entfernen/**")
    expect(_dialog(page).locator("h2")).to_have_text("Fiete Beispiel als Gruppenleitung von Sippe Falken entfernen?")
    _press(page, "dialog .btn-gefahr", keyboard, steps=10)
    page.wait_for_url(page_address)
    expect(page.locator(".a-kurz")).to_contain_text("Fiete Beispiel ist nicht mehr Gruppenleitung von Sippe Falken.")

    _press(page, APPOINT_BUTTON, keyboard)
    page.wait_for_url(f"{page_address}benennen/")
    dialog = _dialog(page)
    field = page.get_by_label("Name, Fahrtenname, Mail oder Benutzername")
    expect(field).to_be_focused()
    if keyboard:
        _all_visible([focus_visible(page)])
        page.keyboard.type("Finn")
    else:
        field.fill("Finn")
    expect(dialog.locator(".a-treffer")).to_contain_text("Finn Beispiel")
    if keyboard:
        _press(page, ".a-treffer-knopf button", keyboard, steps=10)
    else:
        dialog.get_by_role("button", name="Benennen Finn Beispiel").click()
    page.wait_for_url(page_address)
    expect(page.locator(".a-kurz")).to_contain_text("Finn Beispiel ist jetzt Gruppenleitung von Sippe Falken.")


def _h3_fiete_findet_lena_nicht_mehr(page: Page, falken, lena, keyboard: bool) -> None:
    # Fietes Fenster zeigt noch die Seite der Falken aus H1, mit Lena und „Bearbeiten“.
    _press(page, _lena_edit(lena), keyboard)
    expect(page.get_by_role("heading", level=1)).to_have_text(NOT_FOUND)

    # Zurück: Die Seite der Falken kommt frisch vom Server und ist für Fiete jetzt selbst „nicht gefunden“, als
    # Mitglied ohne Leitungsrolle sieht er keine Organisation. Damit steht Lena in keiner Liste von ihm (H3).
    if keyboard:
        _all_visible(_tab_to(page, "Zurück"))
        page.keyboard.press("Enter")
    else:
        page.get_by_role("link", name="Zurück", exact=True).click()
    # Die Adresse zum Bearbeiten beginnt ebenso; erst die Seite der Falken selbst zählt, mit oder ohne Anker.
    page.wait_for_url(lambda url: url.split("#")[0] == _page_of(falken))
    expect(page.get_by_role("heading", level=1)).to_have_text(NOT_FOUND)


def _h4_frida_sieht_lena_sofort(page: Page, falken, lena, keyboard: bool) -> None:
    page_address = _page_of(falken)
    page.goto(page_address)
    expect(page.locator(PERSONS)).to_contain_text("Kiwi")
    _press(page, _lena_edit(lena), keyboard)
    page.wait_for_url(f"{page_address}verwaltete-person/{lena.key}/bearbeiten/")
    expect(_dialog(page).locator("h2")).to_have_text("Kiwi (Lena Probe) bearbeiten")
    if keyboard:
        expect(page.get_by_label("Vorname")).to_be_focused()
        page.keyboard.press("Escape")
        expect(_dialog(page)).to_have_count(0)


def _h5_zora_findet_lena_nirgends(page: Page, units: dict, lena) -> None:
    # Jede Seite, die Zora öffnen darf, auch Boreas über ihr; jede zeigt ihren Inhalt, nur Lena nicht.
    readable = {f"{BASE}/organisation/": "Zugvögel", _page_of(units["zugvoegel"]): "Zugvögel",
                _page_of(units["boreas"]): "Pfadfinderbund Boreas"}
    for address, shown in readable.items():
        page.goto(address)
        expect(page.get_by_role("heading", level=1)).not_to_have_text(NOT_FOUND)
        expect(page.locator("main")).to_contain_text(shown)
        expect(page.locator("body")).not_to_contain_text("Kiwi")
        expect(page.locator("body")).not_to_contain_text("Lena")
    for address in (_page_of(units["falken"]), f"{_page_of(units['falken'])}verwaltete-person/{lena.key}/bearbeiten/"):
        page.goto(address)
        expect(page.get_by_role("heading", level=1)).to_have_text(NOT_FOUND)


def _main_flow(new_window, keyboard: bool) -> None:
    """H1 bis H5; mit `keyboard` alles nur mit der Tastatur, auch die Anmeldung (H6)."""
    units = _units()

    fiete = new_window()
    _log_in(fiete, FIETE, keyboard)
    give(_account(FIETE), R.MEMBER, units["falken"])
    give(_account(FIETE), R.GROUP_LEAD, units["falken"])

    # Fridas Konto muss es im Tool schon geben, damit Wanda sie benennen kann (siehe oben).
    before = new_window()
    login(before, FRIDA)
    before.context.close()
    give(_account(FRIDA), R.MEMBER, units["falken"])

    # H1
    lena = _h1_fiete_legt_lena_an(fiete, units["falken"], keyboard)

    # H2
    wanda = new_window()
    _log_in(wanda, WANDA, keyboard)
    give(_account(WANDA), R.TROOP_LEAD, units["walhall"])
    _h2_wanda_entfernt_fiete_und_benennt_frida(wanda, units["falken"], keyboard)

    # H3
    _h3_fiete_findet_lena_nicht_mehr(fiete, units["falken"], lena, keyboard)

    # H4
    frida = new_window()
    _log_in(frida, FRIDA, keyboard)
    _h4_frida_sieht_lena_sofort(frida, units["falken"], lena, keyboard)

    # H5
    zora = new_window()
    _log_in(zora, ZORA, keyboard)
    give(_account(ZORA), R.TROOP_LEAD, units["zugvoegel"])
    _h5_zora_findet_lena_nirgends(zora, units, lena)


def test_hauptablauf_mit_der_maus(new_window):
    """H1 bis H5: anlegen, Leitungswechsel, „nicht gefunden“ für Fiete und Zora, Lena sofort bei Frida."""
    _main_flow(new_window, keyboard=False)


def test_hauptablauf_nur_mit_der_tastatur(new_window):
    """H6: derselbe Ablauf nur mit Tab, Enter, Leertaste und Escape, auch die Anmeldung, mit sichtbarem Fokus."""
    _main_flow(new_window, keyboard=True)
