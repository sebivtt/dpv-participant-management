"""Rauchtest des Hauptablaufs im Browser: Login, Startseite, Abmelden (#7, NFA-01, NFA-03).

Die Nummern verweisen auf Sebastians Szenarien zu #7 (Planung am 21.10.2026). Jeder Test
läuft in Chromium, Firefox und WebKit (conftest.py). Alle Konten und Daten sind erfunden.
"""

import sys

import pytest
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, OHNE_NAME, focus_visible, login, run_axe

pytestmark = pytest.mark.django_db(transaction=True)


def _on_login_page(page: Page) -> None:
    page.wait_for_url(f"{BASE}/anmelden/**")
    expect(page.get_by_role("button", name="Mit DPV-Konto anmelden")).to_be_visible()


def _password_requested_again(page: Page) -> None:
    """Nach vollständigem Abmelden fragt Keycloak wieder nach dem Passwort (Entscheidung zu #5)."""
    page.get_by_role("button", name="Mit DPV-Konto anmelden").click()
    expect(page.locator("#password")).to_be_visible()


# Szenario 1 und 2
def test_am_pc_seitenleiste_und_abmelden(pc):
    login(pc)

    sidebar = pc.get_by_role("complementary", name="Seitenleiste")
    expect(sidebar).to_be_visible()
    expect(sidebar.get_by_role("link", name="Startseite")).to_have_attribute("aria-current", "page")
    expect(sidebar.get_by_text("Erika", exact=True)).to_be_visible()
    expect(pc.get_by_role("heading", level=1)).to_have_text("Hallo Erika!")
    expect(pc.get_by_role("button", name="Menü")).to_be_hidden()

    sidebar.get_by_role("button", name="Abmelden").click()

    _on_login_page(pc)
    _password_requested_again(pc)


# Szenario 3
def test_am_handy_abmelden_ueber_das_menue(handy):
    login(handy)

    expect(handy.get_by_role("complementary", name="Seitenleiste")).to_be_hidden()
    expect(handy.get_by_role("link", name="Mein Profil")).to_be_visible()
    handy.get_by_role("button", name="Menü").click()
    menu = handy.get_by_role("dialog", name="Menü")
    expect(menu).to_be_visible()
    menu.get_by_role("button", name="Abmelden").click()

    _on_login_page(handy)
    _password_requested_again(handy)


def _tab_key(page: Page) -> str:
    """Die Taste, mit der man von Element zu Element springt.

    Safari und WebKit springen auf dem Mac mit Tab nur zwischen Eingabefeldern, solange die
    Mac-Einstellung „Tastaturnavigation“ aus ist; mit Wahltaste und Tab erreichen sie alles.
    """
    if page.context.browser.browser_type.name == "webkit" and sys.platform == "darwin":
        return "Alt+Tab"
    return "Tab"


def _tab_to(page: Page, text: str, steps: int = 25) -> list[dict]:
    """Drückt Tab, bis der Fokus auf `text` liegt; gibt jede Station mit Sichtbarkeit zurück."""
    stations = []
    for _ in range(steps):
        page.keyboard.press(_tab_key(page))
        station = focus_visible(page)
        stations.append(station)
        if station["text"] == text:
            return stations
    raise AssertionError(f"„{text}“ nach {steps} Mal Tab nicht erreicht: {[s['text'] for s in stations]}")


def _all_visible(stations: list[dict]) -> None:
    hidden = [s for s in stations if not s["sichtbar"]]
    assert not hidden, f"Fokus nicht zu sehen bei: {hidden}"


# Szenario 4, am PC
def test_nur_mit_der_tastatur_am_pc(pc):
    pc.goto(f"{BASE}/")
    stations = _tab_to(pc, "Mit DPV-Konto anmelden")
    pc.keyboard.press("Enter")
    pc.locator("#username").wait_for()
    pc.keyboard.type("erika.testfrau")
    pc.keyboard.press(_tab_key(pc))
    pc.keyboard.type("testpasswort-erika")
    pc.keyboard.press("Enter")
    pc.wait_for_url(f"{BASE}/")

    first = _tab_to(pc, "Zum Inhalt springen", steps=1)
    stations += first + _tab_to(pc, "Abmelden")
    _all_visible(stations)
    order = [s["text"] for s in stations]
    assert order.index("Startseite") < order.index("Abmelden"), order
    pc.keyboard.press("Enter")

    _on_login_page(pc)


# Szenario 4, am Handy: das Menü
def test_nur_mit_der_tastatur_am_handy_menue_auf_und_zu(handy):
    login(handy)
    menu = handy.get_by_role("dialog", name="Menü")

    stations = _tab_to(handy, "Menü")
    handy.keyboard.press("Enter")
    expect(menu).to_be_visible()
    assert handy.evaluate("document.getElementById('menue').contains(document.activeElement)")
    handy.keyboard.press("Escape")
    expect(menu).to_be_hidden()
    assert focus_visible(handy)["text"] == "Menü", "nach dem Schließen steht der Fokus nicht wieder auf „Menü“"

    handy.keyboard.press("Enter")
    stations += _tab_to(handy, "Abmelden")
    _all_visible(stations)
    handy.keyboard.press("Enter")

    _on_login_page(handy)


# Szenario 5
def test_ohne_namen_personensymbol_im_kreis(pc):
    login(pc, OHNE_NAME)

    circle = pc.get_by_role("complementary", name="Seitenleiste").locator(".a-avatar")
    expect(circle).to_have_text("")
    expect(circle.locator("svg")).to_be_visible()
    expect(pc.get_by_text("Ergänze deinen Namen")).to_be_visible()


# Szenario 7
def test_entwurf_auch_ohne_farbe_erkennbar(pc):
    login(pc)
    pc.goto(f"{BASE}/muster/")

    styles = pc.eval_on_selector_all(".a-event", "rows => rows.map(r => getComputedStyle(r).borderTopStyle)")
    draft = pc.eval_on_selector(".a-event.ist-entwurf", "r => getComputedStyle(r).borderTopStyle")
    assert draft == "dashed"
    assert styles.count("dashed") == 1, styles


# Szenario 8
def test_teilnehmende_am_handy_als_karten_am_pc_als_tabelle(pc, handy):
    def look(page: Page) -> dict:
        login(page)
        page.goto(f"{BASE}/muster/")
        return page.evaluate(
            """() => ({zeile: getComputedStyle(document.querySelector('.a-tabelle tbody tr')).display,
                      kopf: document.querySelector('.a-tabelle thead').getBoundingClientRect().height})"""
        )

    on_pc = look(pc)
    assert on_pc["zeile"] == "table-row"
    assert on_pc["kopf"] > 10
    on_phone = look(handy)
    assert on_phone["zeile"] in ("block", "grid")
    assert on_phone["kopf"] <= 1


# Eingaben wie am Handy (Erfahrung aus dem Vorgänger-Repo, CLAUDE.md)
def test_eingaben_wie_am_handy_bleiben_stehen(handy):
    login(handy)
    handy.goto(f"{BASE}/muster/")
    field = handy.get_by_label("Name der Veranstaltung")

    field.tap()
    # Ein Handy tippt Wörter oft als „Zusammensetzung“ und ersetzt sie per Wortvorschlag
    # oder Autokorrektur. Danach muss der Text im Feld stehen bleiben.
    field.press_sequentially("Pfingstlager ")
    field.evaluate(
        """el => {
            el.dispatchEvent(new CompositionEvent('compositionstart', {data: ''}));
            el.dispatchEvent(new CompositionEvent('compositionupdate', {data: 'Somme'}));
            el.value += 'Somme';
            el.dispatchEvent(new InputEvent('input', {inputType: 'insertCompositionText', data: 'Somme', bubbles: true}));
            el.dispatchEvent(new InputEvent('beforeinput', {inputType: 'insertReplacementText', data: 'Sommer', bubbles: true, cancelable: true}));
            el.value = el.value.replace(/Somme$/, 'Sommer');
            el.dispatchEvent(new InputEvent('input', {inputType: 'insertReplacementText', data: 'Sommer', bubbles: true}));
            el.dispatchEvent(new CompositionEvent('compositionend', {data: 'Sommer'}));
        }"""
    )
    field.press_sequentially(" 2027")
    handy.get_by_label("Organisation").focus()

    expect(field).to_have_value("Pfingstlager Sommer 2027")


# Szenario 10
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_seiten_bestehen_die_pruefung_auf_barrierefreiheit(request, browser_name, device, settings):
    settings.ROOT_URLCONF = "tests.urls"  # enthält eine Adresse, die die Fehlerseite auslöst
    page: Page = request.getfixturevalue(device)

    page.goto(f"{BASE}/anmelden/")
    findings = {"Login-Seite": run_axe(page)}
    login(page)
    findings["Startseite"] = run_axe(page)
    page.goto(f"{BASE}/muster/")
    findings["Musterseite"] = run_axe(page)
    if device == "handy":
        page.get_by_role("button", name="Menü").click()
        # Erst messen, wenn das Menü fertig eingeblendet ist; es startet halb durchsichtig.
        page.locator("#menue").evaluate("el => Promise.all(el.getAnimations().map(a => a.finished))")
        findings["Musterseite mit offenem Menü"] = run_axe(page)
    page.goto(f"{BASE}/test/1/")
    findings["Fehlerseite"] = run_axe(page)

    assert {name: found for name, found in findings.items() if found} == {}
