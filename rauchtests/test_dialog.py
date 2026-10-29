"""Rauchtest des Bausteins „Dialog“ und des Handy-Menüs im Browser (#210).

Ob die Seite hinter einem offenen Dialog mitrollt und wo der Dialog senkrecht steht, entscheidet erst
der Browser; deshalb lässt es sich nur hier prüfen. Die Nummern verweisen auf die Szenarien zu #210:
D1 bis G5 vom 28.10.2026 (Mitrollen), M1 bis M8 vom 29.10.2026 (Dialog mittig). Jeder Test läuft in
Chromium, Firefox und WebKit (conftest.py). Am PC wird mit dem Mausrad gerollt, am Handy in Chromium
mit einer echten Wischgeste. WebKit kennt im Handy-Modus weder Mausrad noch Wischgeste; dort prüft der
Test nur die Regel, die das Rollen sperrt (app.css). Alle Konten und Daten sind erfunden.
"""

import pytest
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, PC, login
from rauchtests.test_entfernen import _walhall_for_erika as _mit_funke
from rauchtests.test_fussbereich import ABSTAND, _am_unteren_rand, _lage
from rauchtests.test_organisation import _walhall_for_erika

pytestmark = pytest.mark.django_db(transaction=True)

# Abstand des Dialogs zum Fensterrand, wenn er länger ist als das Fenster (app.css, dialog.a-dialog).
RAND = 16


def _lang(page: Page) -> None:
    """Macht die Seite unter dem Dialog deutlich länger als das Fenster, damit sie rollen könnte."""
    page.evaluate("document.querySelector('.a-main-inhalt').style.paddingBottom = '3000px'")


def _gerollt(page: Page) -> int:
    """Wie weit die Seite hinter dem Dialog gerollt ist: das Fenster und jede Fläche mit eigenem Rollen
    (Seitenleiste, Gliederung), aber nichts im offenen Dialog oder Menü."""
    return page.evaluate(
        """() => {
            let summe = document.scrollingElement.scrollTop;
            for (const el of document.querySelectorAll('body *')) {
                if (!el.closest('dialog[open]:not(.ist-vorschau)')) summe += el.scrollTop;
            }
            return Math.round(summe);
        }"""
    )


def _browser(page: Page) -> str:
    return page.context.browser.browser_type.name


def _am_handy(page: Page) -> bool:
    return page.viewport_size["width"] < 768


def _kann_rollen(page: Page) -> bool:
    """WebKit im Handy-Modus kann Playwright weder mit Mausrad noch mit dem Finger rollen lassen."""
    return not (_am_handy(page) and _browser(page) == "webkit")


def _gesperrt(page: Page) -> bool:
    return page.evaluate("getComputedStyle(document.documentElement).overflowY") == "hidden"


def _rollen(page: Page, x: float, y: float, mal: int = 3) -> None:
    """Rollt an der Stelle x, y nach unten: am Handy in Chromium mit dem Finger, sonst mit dem Mausrad."""
    if _am_handy(page) and _browser(page) == "chromium":
        cdp = page.context.new_cdp_session(page)
        for _ in range(mal):
            cdp.send("Input.synthesizeScrollGesture", {"x": x, "y": y, "yDistance": -300, "gestureSourceType": "touch"})
        cdp.detach()
    else:
        page.mouse.move(x, y)
        for _ in range(mal):
            page.mouse.wheel(0, 400)
            page.wait_for_timeout(150)
    page.wait_for_timeout(300)


def _mitte(dialog) -> dict:
    """Abstand des Dialogs zum oberen und unteren Fensterrand."""
    return dialog.evaluate(
        "d => { const b = d.getBoundingClientRect(); return {oben: b.top, unten: innerHeight - b.bottom}; }"
    )


def _steht_mittig(dialog) -> None:
    lage = _mitte(dialog)
    assert lage["oben"] == pytest.approx(lage["unten"], abs=1), lage
    assert lage["oben"] >= RAND - 1, lage


def _seite_steht(page: Page, dialog) -> None:
    """Rollt über dem Dialog und daneben; die Seite dahinter bewegt sich dabei nicht."""
    _lang(page)
    assert page.evaluate("document.scrollingElement.scrollHeight") > page.viewport_size["height"] + 1000
    if not _kann_rollen(page):
        assert _gesperrt(page), "Die Seite ist hinter dem Dialog nicht gesperrt"
        return
    box = dialog.bounding_box()
    _rollen(page, box["x"] + box["width"] / 2, box["y"] + 30)
    assert _gerollt(page) == 0, "Die Seite rollt über dem Dialog mit"
    # Rechts daneben: Der Dialog steht in der Mitte, das Menü am linken Rand.
    _rollen(page, page.viewport_size["width"] - 5, page.viewport_size["height"] - 40)
    assert _gerollt(page) == 0, "Die Seite rollt neben dem Dialog mit"


def _rollt_normal(page: Page) -> None:
    _lang(page)
    if not _kann_rollen(page):
        assert not _gesperrt(page), "Die Seite bleibt nach dem Schließen gesperrt"
        return
    _rollen(page, page.viewport_size["width"] / 2, page.viewport_size["height"] / 2)
    assert page.evaluate("scrollY") > 0, "Die Seite rollt nach dem Schließen nicht"


def _benennen(page: Page) -> str:
    login(page)
    adresse = f"{BASE}/organisation/{_walhall_for_erika()['falken'].key}/"
    page.goto(f"{adresse}benennen/")
    return adresse


# D1, M1: am Laptop „Leitung benennen“
def test_am_pc_steht_benennen_mittig_und_die_seite_rollt_nicht_mit(pc):
    _benennen(pc)
    dialog = pc.locator("dialog.a-dialog")
    expect(dialog).to_be_visible()
    _steht_mittig(dialog)
    _seite_steht(pc, dialog)


# D2, M2: dasselbe am Handy
def test_am_handy_steht_benennen_mittig_und_die_seite_rollt_nicht_mit(handy):
    _benennen(handy)
    dialog = handy.locator("dialog.a-dialog")
    expect(dialog).to_be_visible()
    _steht_mittig(dialog)
    _seite_steht(handy, dialog)


# D3, M3: „Entfernen“ bei einer Leitung (#191), am Laptop und am Handy
@pytest.mark.parametrize("geraet", ["pc", "handy"])
# browser_name steht hier, damit der Test in allen drei Browsern läuft (conftest.py); das Gerät kommt erst im Test.
def test_entfernen_steht_mittig_und_die_seite_rollt_nicht_mit(request, browser_name, geraet):
    page = request.getfixturevalue(geraet)
    login(page)
    page.goto(f"{BASE}/organisation/{_mit_funke()['falken'].key}/")
    page.locator(".a-leitung-knopf").click()
    page.wait_for_url("**/entfernen/**")
    dialog = page.locator("dialog.a-dialog")
    expect(dialog).to_be_visible()
    _steht_mittig(dialog)
    _seite_steht(page, dialog)


# D4, G3: das Handy-Menü; nach dem Schließen rollt die Seite wieder
def test_am_handy_rollt_die_seite_hinter_dem_menue_nicht_mit(handy):
    login(handy)
    handy.get_by_role("button", name="Menü").click()
    menue = handy.get_by_role("dialog", name="Menü")
    expect(menue).to_be_visible()
    _seite_steht(handy, menue)
    handy.get_by_role("button", name="Menü schließen").click()
    expect(menue).to_be_hidden()
    _rollt_normal(handy)


# G1, M4: Der Dialog ist länger als der Bildschirm. Nur er rollt, bis zu seinem Ende; die Seite auch
# dann nicht. Oben und unten bleibt ein schmaler Rand.
def test_am_handy_rollt_ein_langer_dialog_allein_und_hat_oben_und_unten_rand(handy):
    handy.set_viewport_size({"width": 390, "height": 320})
    _benennen(handy)
    dialog = handy.locator("dialog.a-dialog")
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.scrollHeight > innerHeight"), "Der Dialog ist nicht länger als das Fenster"
    lage = _mitte(dialog)
    assert lage["oben"] == pytest.approx(RAND, abs=1), lage
    assert lage["unten"] == pytest.approx(RAND, abs=1), lage

    _lang(handy)
    if not _kann_rollen(handy):
        assert _gesperrt(handy), "Die Seite ist hinter dem Dialog nicht gesperrt"
        return
    _rollen(handy, 195, 160, mal=8)
    assert dialog.evaluate("d => Math.abs(d.scrollHeight - d.clientHeight - d.scrollTop) <= 1"), (
        "Der Dialog rollt nicht bis zu seinem Ende"
    )
    assert _gerollt(handy) == 0, "Am Ende des Dialogs rollt die Seite weiter"


# G2: Nach dem Schließen mit ×, „Abbrechen“, Escape oder Tippen daneben rollt die Seite wieder
@pytest.mark.parametrize("weg", ["×", "Abbrechen", "Escape", "daneben"])
def test_am_pc_rollt_die_seite_nach_dem_schliessen_wieder(pc, weg):
    adresse = _benennen(pc)
    dialog = pc.locator("dialog.a-dialog")
    expect(dialog).to_be_visible()
    if weg == "×":
        dialog.get_by_role("link", name="Schließen").click()
    elif weg == "Abbrechen":
        dialog.get_by_role("link", name="Abbrechen").click()
    elif weg == "Escape":
        pc.keyboard.press("Escape")
    else:
        pc.mouse.click(5, 450)
    pc.wait_for_url(adresse)
    expect(dialog).to_have_count(0)
    _rollt_normal(pc)


# G4, M7: Im Bausteinkatalog stehen die Dialoge als Vorschau an ihrer Stelle; die Seite rollt normal
def test_im_bausteinkatalog_bleiben_die_vorschauen_in_der_seite_und_sie_rollt(pc):
    login(pc)
    pc.goto(f"{BASE}/bausteine/")
    vorschau = pc.locator("dialog.a-dialog.ist-vorschau").first
    expect(vorschau).to_be_visible()
    oben_in_der_seite = vorschau.evaluate("d => d.getBoundingClientRect().top + scrollY")
    _rollen(pc, 683, 450)
    assert pc.evaluate("scrollY") > 0, "Die Seite des Katalogs rollt nicht"
    vorschau.scroll_into_view_if_needed()
    assert vorschau.evaluate("d => getComputedStyle(d).position") == "static"
    assert vorschau.evaluate("d => d.getBoundingClientRect().top + scrollY") == pytest.approx(oben_in_der_seite, abs=1)


# M5: Ist die Seite weit gerollt, steht der Dialog trotzdem in der Mitte des Fensters
@pytest.mark.parametrize("geraet", ["pc", "handy"])
# browser_name steht hier, damit der Test in allen drei Browsern läuft (conftest.py); das Gerät kommt erst im Test.
def test_der_dialog_haengt_am_fenster_auch_wenn_die_seite_gerollt_ist(request, browser_name, geraet):
    page = request.getfixturevalue(geraet)
    _benennen(page)
    dialog = page.locator("dialog.a-dialog")
    expect(dialog).to_be_visible()
    _lang(page)
    # Das Rollen per Skript geht auch dann, wenn die Seite es mit Mausrad und Finger nicht tut; sofort,
    # nicht sanft wie sonst bei Bootstrap.
    page.evaluate("scrollTo({top: 1500, behavior: 'instant'})")
    assert page.evaluate("document.scrollingElement.scrollTop") > 0
    _steht_mittig(dialog)


# M6: Nach dem Schließen steht der Fußbereich wie bisher (#206)
def test_nach_dem_schliessen_steht_der_fussbereich_wie_bisher(pc):
    adresse = _benennen(pc)
    pc.locator("dialog.a-dialog").get_by_role("link", name="Abbrechen").click()
    pc.wait_for_url(adresse)
    lage = _lage(pc)
    if lage["seite"] == lage["fenster"]:
        _am_unteren_rand(pc)
    else:
        assert lage["oben"] - lage["inhalt"] == pytest.approx(ABSTAND, abs=1), lage


# G5, M8: ohne Skript steht der Dialog mittig, und die Seite rollt nicht mit
@pytest.mark.parametrize("dialog_adresse", ["benennen", "entfernen"])
def test_ohne_skript_steht_der_dialog_mittig_und_die_seite_rollt_nicht_mit(pc, browser, dialog_adresse):
    login(pc)
    falken = _mit_funke()["falken"]
    pc.goto(f"{BASE}/organisation/{falken.key}/")
    adresse = f"{BASE}/organisation/{falken.key}/benennen/"
    if dialog_adresse == "entfernen":
        adresse = BASE + pc.locator(".a-leitung-knopf").get_attribute("href")
    context = browser.new_context(java_script_enabled=False, storage_state=pc.context.storage_state(), **PC)
    page = context.new_page()
    try:
        page.goto(adresse)
        dialog = page.locator("dialog.a-dialog")
        expect(dialog).to_be_visible()
        _steht_mittig(dialog)
        _seite_steht(page, dialog)
        # Ohne Skript ist die Seite dahinter nicht gesperrt wie bei einem modalen Dialog. Auch die
        # Seitenleiste mit eigenem Rollen bleibt stehen, wenn das Fenster so niedrig ist, dass sie rollen könnte.
        page.set_viewport_size({"width": 1366, "height": 300})
        assert page.evaluate("(s => s.scrollHeight > s.clientHeight)(document.querySelector('.a-sidebar'))")
        _rollen(page, 100, 150)
        assert _gerollt(page) == 0, "Die Seitenleiste rollt hinter dem Dialog mit"
    finally:
        context.close()
