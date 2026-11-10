"""Rauchtest: Abmelden per Formular an Keycloak, mit und ohne Skript, am PC und am Handy (#280).

Die Kennungen E1 bis G2 verweisen auf den Kommentar „Szenarien (06.11.2026)“ im Issue #280.
Belegt gegen die Keycloak-Testumgebung, dass Keycloak das Formular annimmt und ohne Rückfrage
abmeldet, und dass dabei keine Adresse das Kennungs-Token enthält. Alle Konten sind erfunden.
"""

import pytest
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login
from rauchtests.test_rauchtest import _all_visible, _on_login_page, _password_requested_again, _tab_to

pytestmark = pytest.mark.django_db(transaction=True)

HINT_LOGGED_OUT = "Du bist abgemeldet."
# Knopf der kurzen Abmelde-Seite, den man ohne Skript sieht (E2).
FINISH_BUTTON = "Abmelden abschließen"


def _record_addresses(page: Page) -> list[str]:
    """Merkt sich jede Adresse, die der Browser ab jetzt aufruft, auch Weiterleitungen."""
    addresses: list[str] = []
    page.context.on("request", lambda request: addresses.append(request.url))
    return addresses


def _assert_no_token_in(addresses: list[str]) -> None:
    # Ein Kennungs-Token beginnt wie jedes JWT mit „eyJ“ (kodiertes „{"“).
    with_token = [address for address in addresses if "id_token_hint" in address or "eyJ" in address]
    assert not with_token, f"Adressen mit Token: {with_token}"
    assert addresses, "keine Adresse aufgezeichnet"


def _logged_out_hint(page: Page):
    return page.locator("main .a-meldung").filter(has_text=HINT_LOGGED_OUT)


# E1 und E3: am PC mit Skript ohne Rückfrage zurück zur Login-Seite, Hinweis einmal, kein Token in Adressen
def test_am_pc_mit_skript_ohne_rueckfrage_abgemeldet_und_ohne_token_in_adressen(pc):
    login(pc)
    addresses = _record_addresses(pc)

    pc.get_by_role("complementary", name="Seitenleiste").get_by_role("button", name="Abmelden").click()

    _on_login_page(pc)
    expect(_logged_out_hint(pc)).to_be_visible()
    _assert_no_token_in(addresses)
    pc.reload()
    _on_login_page(pc)
    expect(_logged_out_hint(pc)).to_have_count(0)
    _password_requested_again(pc)


# E2: ohne Skript am PC, nur mit der Tastatur: kurze Seite mit Knopf, danach wie E1
def test_am_pc_ohne_skript_nur_mit_der_tastatur_ueber_den_knopf_abgemeldet(pc_ohne_skript):
    page = pc_ohne_skript
    login(page)
    addresses = _record_addresses(page)

    stations = _tab_to(page, "Abmelden")
    page.keyboard.press("Enter")
    page.wait_for_url(f"{BASE}/abmelden/")
    expect(page.get_by_role("button", name=FINISH_BUTTON)).to_be_visible()
    stations += _tab_to(page, FINISH_BUTTON)
    _all_visible(stations)
    page.keyboard.press("Enter")

    _on_login_page(page)
    expect(_logged_out_hint(page)).to_be_visible()
    _assert_no_token_in(addresses)
    _password_requested_again(page)


# E2 am Handy: Den Weg zum Knopf „Abmelden“ ohne Skript regelt #281; hier schickt der Test das
# Formular „Abmelden“ der Seite selbst ab und prüft alles danach.
def test_am_handy_ohne_skript_kurze_seite_mit_knopf(handy_ohne_skript):
    page = handy_ohne_skript
    login(page)
    addresses = _record_addresses(page)

    page.locator("#menue form[action='/abmelden/']").evaluate("form => form.submit()")
    page.wait_for_url(f"{BASE}/abmelden/")
    button = page.get_by_role("button", name=FINISH_BUTTON)
    expect(button).to_be_in_viewport()
    button.tap()

    _on_login_page(page)
    expect(_logged_out_hint(page)).to_be_visible()
    _assert_no_token_in(addresses)
    _password_requested_again(page)


# G2: „Zurück“ nach dem Abmelden meldet nicht wieder an. Dass die kurze Seite nicht aus dem Speicher
# kommt (no-store) und erneutes Senden unschädlich ist, prüft tests/test_abmelden.py.
def test_zurueck_nach_dem_abmelden_meldet_nicht_wieder_an(pc):
    login(pc)
    pc.get_by_role("complementary", name="Seitenleiste").get_by_role("button", name="Abmelden").click()
    _on_login_page(pc)

    pc.go_back()
    pc.goto(f"{BASE}/")

    _on_login_page(pc)
    _password_requested_again(pc)
