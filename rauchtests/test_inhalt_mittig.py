"""Rauchtest: Band „Testumgebung“, Inhalt und Fußzeile stehen mittig rechts der Seitenleiste (#332).

Wo etwas steht, entscheidet erst der Browser; deshalb lässt es sich nur hier prüfen.
Die Nummern verweisen auf die „Szenarien (14.11.2026)“ in #332. Jeder Test läuft in Chromium,
Firefox und WebKit (conftest.py). Alle Konten und Daten sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, HANDY, _context, login
from rauchtests.test_kurzmeldung import _later, _save, _set_scout_name, _short, _stop_clock
from rauchtests.test_organisation import _no_side_scroll, _walhall_for_erika
from rauchtests.test_veranstaltungen import _erika_in_den_falken
from roles.models import Role
from tests.test_rollen import give

pytestmark = pytest.mark.django_db(transaction=True)

LEISTE = 264  # Breite der Seitenleiste am PC (core/static/core/app.css)
BREITESTER_BLOCK = LEISTE + 1180  # Höchstbreite des Inhaltsbereichs samt Rand, wie vor #332 (app.css, .a-main)
GROSS = {"viewport": {"width": 1920, "height": 1080}}

# Die drei Teile des Blocks: Band, Inhalt, Fußzeile
TEILE = (".a-testband", ".a-main-inhalt", "footer.a-fuss")


@pytest.fixture
def mit_band(tool, settings):
    """Das Band „Testumgebung“ ist eingeschaltet, damit es mitgemessen wird."""
    settings.TEST_ENVIRONMENT = True
    return tool


def _seite(browser, browser_name, breite: int, hoehe: int = 1000) -> Page:
    return _context(browser, browser_name, {"viewport": {"width": breite, "height": hoehe}}).new_page()


def _kasten(page: Page, selector: str) -> dict:
    return page.locator(selector).first.evaluate(
        """e => { const b = e.getBoundingClientRect();
            return {left: b.left, right: b.right, width: b.width,
                    vw: document.documentElement.clientWidth, innen: window.innerWidth}; }"""
    )


def _breite_wie_heute(kasten: dict) -> float:
    """Breite des Inhalts vor #332: Fläche rechts der Leiste, höchstens BREITESTER_BLOCK, abzüglich Rand max(24px, 4vw)."""
    rand = max(24, 0.04 * kasten["innen"])
    return min(kasten["vw"] - LEISTE, BREITESTER_BLOCK) - 2 * rand


def _mittig_rechts_der_leiste(page: Page) -> None:
    for teil in TEILE:
        expect(page.locator(teil).first).to_be_visible()
        kasten = _kasten(page, teil)
        # Gemessen bis zum rechten Fensterrand; eine Scrollleiste liegt im freien Platz rechts (#332, Befund M1).
        links, rechts = kasten["left"] - LEISTE, kasten["innen"] - kasten["right"]
        assert abs(links - rechts) <= 1, (teil, kasten)
        assert kasten["width"] == pytest.approx(_breite_wie_heute(kasten), abs=1), (teil, kasten)
    # Alle drei stehen als ein Block übereinander.
    kaesten = [_kasten(page, teil) for teil in TEILE]
    assert max(k["left"] for k in kaesten) - min(k["left"] for k in kaesten) <= 1, kaesten
    _no_side_scroll(page)


# Szenarien 1 und 2: großer Bildschirm, alle Seiten mit Seitenleiste
@pytest.mark.bausteinkatalog
def test_grosser_bildschirm_block_mittig_auf_allen_seiten(browser, browser_name, mit_band):
    page = _context(browser, browser_name, GROSS).new_page()
    login(page)
    units = _walhall_for_erika()
    # Als Verbandsleitung zeigt „/organisation/“ die Seite „Verband“ (Szenario 2), nicht die Seite „Organisation“.
    erika = get_user_model().objects.get(username="erika.testfrau")
    give(erika, Role.Kind.FEDERATION_LEAD, units["boreas"].parent)
    adressen = (
        "/profil/",
        f"/organisation/{units['walhall'].key}/",
        "/veranstaltungen/",
        "/organisation/",
        "/bausteine/",
    )
    for adresse in adressen:
        page.goto(f"{BASE}{adresse}")
        _mittig_rechts_der_leiste(page)
        if adresse == "/organisation/":
            expect(page.locator(".a-buende-titel")).to_be_visible()
    # Gegenprobe: Rechts bleibt nicht mehr die ganze freie Fläche leer.
    kasten = _kasten(page, ".a-main-inhalt")
    assert kasten["left"] - LEISTE > 100, kasten


# Szenario 3: Die kurze Meldung steht unten mittig unter dem Inhalt, wie bisher.
def test_grosser_bildschirm_kurze_meldung_mittig_unter_dem_inhalt(browser, browser_name, mit_band):
    page = _context(browser, browser_name, GROSS).new_page()
    login(page)
    _set_scout_name("Falkenflug")
    _stop_clock(page)
    page.goto(f"{BASE}/profil/")
    _save(page, "Kiwi")
    _later(page, 300)
    meldung = _short(page)
    expect(meldung).to_have_count(1)
    box = _kasten(page, "#kurzmeldungen .a-kurz")
    inhalt = _kasten(page, ".a-main-inhalt")
    mitte = (box["left"] + box["right"]) / 2
    assert abs(mitte - (LEISTE + box["vw"]) / 2) < 2, box
    # Mit Scrollleiste steht der Block um ihre halbe Breite neben der Mitte der Meldung (#332, Befund M1).
    leiste_rechts = box["innen"] - box["vw"]
    assert abs(mitte - (inhalt["left"] + inhalt["right"]) / 2) < 2 + leiste_rechts / 2, (box, inhalt)


# Befund M1 der unabhängigen Prüfung (Entscheidung Sebastian, 15.11.2026): Nimmt die Scrollleiste Platz weg
# (meist Windows), verrutscht der Block nicht, wenn sie kommt oder geht, etwa beim Seitenwechsel oder hinter
# einem Dialog. Die Browser im Test blenden die Leiste sonst aus; ein eigenes Aussehen erzwingt eine feste.
FESTE_SCROLLLEISTE = "::-webkit-scrollbar { width: 16px; } ::-webkit-scrollbar-thumb { background: #888; }"


def test_scrollleiste_laesst_den_block_nicht_verrutschen(browser, browser_name, mit_band):
    page = _context(browser, browser_name, GROSS).new_page()
    login(page)
    page.goto(f"{BASE}/profil/")
    # Als eigenes Stylesheet aus dem Skript, nicht als <style>: Das ließe die Sicherheitsrichtlinie nicht zu.
    page.evaluate(
        "css => { const s = new CSSStyleSheet(); s.replaceSync(css); document.adoptedStyleSheets = [s]; }",
        FESTE_SCROLLLEISTE,
    )
    lagen = {}
    for overflow in ("scroll", "hidden"):
        page.evaluate(f"document.documentElement.style.overflowY = '{overflow}'")
        kasten = _kasten(page, ".a-main-inhalt")
        lagen[overflow] = kasten
    if lagen["scroll"]["innen"] == lagen["scroll"]["vw"]:
        pytest.skip(f"{browser_name} zeigt hier keine feste Scrollleiste; geprüft in Browsern, die eine zeigen (lokal WebKit)")
    assert lagen["scroll"]["left"] == pytest.approx(lagen["hidden"]["left"], abs=1), lagen
    # Mit Scrollleiste: links von der Seitenleiste so viel Platz wie rechts bis zum Fensterrand.
    mit = lagen["scroll"]
    assert abs((mit["left"] - LEISTE) - (mit["innen"] - mit["right"])) <= 1, mit
    _no_side_scroll(page)


# Szenario 4: Füllt der Inhalt die Fläche, ändert sich nichts: links und rechts nur der gewohnte Rand.
@pytest.mark.parametrize("breite", [1500, BREITESTER_BLOCK + LEISTE])
def test_inhalt_fuellt_die_flaeche_wie_heute(browser, browser_name, mit_band, breite):
    page = _seite(browser, browser_name, breite)
    login(page)
    page.goto(f"{BASE}/profil/")
    for teil in TEILE:
        kasten = _kasten(page, teil)
        rand = max(24, 0.04 * kasten["innen"])
        assert kasten["left"] == pytest.approx(LEISTE + rand, abs=1), (teil, kasten)
        assert kasten["width"] == pytest.approx(_breite_wie_heute(kasten), abs=1), (teil, kasten)
    _no_side_scroll(page)


# Szenario 5: unter 992 Pixel und am Handy unverändert, ohne Seitenleiste mit 16 Pixel Rand
@pytest.mark.parametrize("geraet", ["schmal", "handy"])
def test_kleiner_bildschirm_und_handy_unveraendert(browser, browser_name, mit_band, geraet):
    if geraet == "handy":
        page = _context(browser, browser_name, HANDY).new_page()
    else:
        page = _seite(browser, browser_name, 991)
    login(page)
    page.goto(f"{BASE}/profil/")
    for teil in TEILE:
        kasten = _kasten(page, teil)
        assert kasten["left"] == pytest.approx(16, abs=1), (teil, kasten)
        assert kasten["vw"] - kasten["right"] == pytest.approx(16, abs=1), (teil, kasten)
    _no_side_scroll(page)


# Szenario 6: Login- und Fehlerseite ohne Seitenleiste bleiben mittig im ganzen Fenster.
def test_seiten_ohne_seitenleiste_unveraendert(browser, browser_name, mit_band):
    page = _context(browser, browser_name, GROSS).new_page()
    for adresse in ("/", "/gibt-es-nicht/"):
        page.goto(f"{BASE}{adresse}")
        expect(page.locator(".a-sidebar")).to_have_count(0)
        for teil in (".a-einfach-karte", ".a-testband", "footer.a-fuss"):
            kasten = _kasten(page, teil)
            assert abs((kasten["left"] + kasten["right"]) / 2 - kasten["vw"] / 2) <= 1, (adresse, teil, kasten)


# Szenario 7: Ein Dialog steht weiter mittig im ganzen Fenster, nicht in der Fläche rechts der Leiste.
def test_dialog_mittig_im_ganzen_fenster(browser, browser_name, mit_band):
    page = _context(browser, browser_name, GROSS).new_page()
    login(page)
    _erika_in_den_falken()
    page.goto(f"{BASE}/veranstaltungen/erstellen/")
    expect(page.locator("dialog.a-dialog")).to_be_visible()
    kasten = _kasten(page, "dialog.a-dialog")
    assert abs((kasten["left"] + kasten["right"]) / 2 - kasten["vw"] / 2) <= 1, kasten
