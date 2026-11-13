"""Gemeinsames für den Rauchtest im Browser (#7): Browser, Tool auf eigenem Port, Login.

Der Rauchtest bedient das Tool wie eine Person: in Chromium, Firefox und WebKit (die Technik
hinter Safari), am PC und mit Handy-Bildschirm, mit Maus und nur mit der Tastatur. Er meldet
sich wirklich bei der Keycloak-Testumgebung an (dev/docker-compose.yml) mit den erfundenen
Konten aus dev/keycloak/dpv-realm.json.

Er läuft in einem eigenen pytest-Lauf (pruefen.sh), weil Playwright in diesem Lauf eine
Ereignisschleife betreibt. Django hält Datenbankzugriffe daneben für unsicher und bricht sie
ab; pruefen.sh schaltet diese Warnung nur für diesen Lauf mit DJANGO_ALLOW_ASYNC_UNSAFE ab.
Die Datenbankzugriffe hier sind trotzdem sicher: Das Tool selbst läuft in einem eigenen Faden.

Das Tool läuft hier auf einem eigenen Port (tests/check_ports.py), nicht auf Port 8000 des
eigenen Tools aus README Schritt 9; beide können gleichzeitig laufen (#167). Ein Rauchtest aus
einer anderen Arbeitskopie läuft erst, wenn dieser fertig ist (#184).

Rauchtests haben keine eigene Zeitgrenze: Ein Test, der hängt, läuft lokal weiter, bis jemand den
Lauf abbricht; auf GitHub beendet ihn erst das Zeitlimit des Schritts „Prüfungen dieses Teils“
(#256, #307).

Auf GitHub läuft jeder Browser in einem eigenen Teil auf einem eigenen Rechner (#307):
`./pruefen.sh teil rauchtest-<browser>` setzt RAUCHTEST_BROWSER. Dann läuft nur dieser Browser,
und Tests ohne Browser laufen nur im Teil des ersten Browsers, damit jeder Test genau einmal läuft.
Ohne RAUCHTEST_BROWSER laufen wie bisher alle drei.
"""

import os
import sys
from pathlib import Path

import urllib.request

import pytest
from django.conf import settings
from playwright.sync_api import Browser, BrowserContext, Error, Page, sync_playwright

from tests.check_ports import PORT_RELEASE_SECONDS, SMOKE_TEST_LOCK_PORT, SMOKE_TEST_PORT, fail_if_busy, tell, wait_for_turn

# Das Kennzeichen der Tests zum Bausteinkatalog für den schnellen Lauf (#304), wie in tests/.
pytest_plugins = ["tests.katalogtests"]

# Keycloak lässt die Rückkehr zu diesem Port zu (dev/keycloak/dpv-realm.json), deshalb läuft das
# Tool im Rauchtest genau dort. pytest-django liest die Adresse beim ersten Start.
os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = f"localhost:{SMOKE_TEST_PORT}"
BASE = f"http://localhost:{SMOKE_TEST_PORT}"

BROWSERS = ["chromium", "firefox", "webkit"]
AXE = Path(__file__).resolve().parent.parent / "tests" / "vendor" / "axe-core" / "axe.min.js"

ERIKA = ("erika.testfrau", "testpasswort-erika")
OHNE_NAME = ("ohne.name", "testpasswort-ohne-name")

PC = {"viewport": {"width": 1366, "height": 900}}
HANDY = {"viewport": {"width": 390, "height": 844}, "has_touch": True}


def _selected_browser() -> str | None:
    """Der Browser aus RAUCHTEST_BROWSER (#307), ohne Angabe None für alle drei."""
    selected = os.environ.get("RAUCHTEST_BROWSER", "")
    if not selected:
        return None
    if selected not in BROWSERS:
        raise pytest.UsageError(f"RAUCHTEST_BROWSER={selected!r} ist kein Browser des Rauchtests; erlaubt: {', '.join(BROWSERS)}.")
    return selected


def pytest_configure(config):
    _selected_browser()


def pytest_generate_tests(metafunc):
    """Jeder Test, der einen Browser braucht, läuft in allen drei Browsern, mit RAUCHTEST_BROWSER nur in diesem."""
    if "browser_name" in metafunc.fixturenames:
        selected = _selected_browser()
        metafunc.parametrize("browser_name", [selected] if selected else BROWSERS, scope="session")


def pytest_collection_modifyitems(config, items):
    """Tests ohne Browser laufen nur im Teil des ersten Browsers (#307)."""
    selected = _selected_browser()
    if selected is None or selected == BROWSERS[0]:
        return
    without_browser = [item for item in items if "browser_name" not in getattr(item, "fixturenames", ())]
    if without_browser:
        config.hook.pytest_deselected(items=without_browser)
        items[:] = [item for item in items if item not in without_browser]


@pytest.fixture(scope="session", autouse=True)
def _vorbedingungen(request):
    """Wartet, bis kein anderer Rauchtest läuft (#184), und bricht mit einer verständlichen
    Meldung ab, wenn Keycloak fehlt oder der Port des Rauchtests belegt ist."""
    with wait_for_turn(SMOKE_TEST_LOCK_PORT, "Rauchtest", say=tell(request.config)):
        _keycloak_erreichbar()
        fail_if_busy(SMOKE_TEST_PORT, "das Tool im Rauchtest", seconds=PORT_RELEASE_SECONDS)
        yield


def _keycloak_erreichbar():
    address = f"{settings.KEYCLOAK_REALM_URL}/.well-known/openid-configuration"
    try:
        urllib.request.urlopen(address, timeout=5).close()  # noqa: S310 -- feste Adresse aus .env, nicht von außen
    except OSError as error:
        pytest.fail(
            f"Keycloak unter {settings.KEYCLOAK_REALM_URL} nicht erreichbar ({type(error).__name__}). "
            "Erst die Keycloak-Testumgebung starten (README.md, „Projekt starten“, Schritt 7)."
        )


@pytest.fixture(scope="session")
def _playwright():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(_playwright, browser_name) -> Browser:
    """Startet den Browser einmal je Lauf.

    Firefox von Playwright startet unter macOS 27 nicht („Could not find profile folder“,
    belegt am 21.10.2026 auf Sebastians Mac, auch im eigenen Terminal). Nur genau dann wird
    Firefox auf dem Mac übersprungen, sichtbar im Ergebnis. Auf GitHub (CI) nie: Dort muss
    Firefox laufen, sonst ist die Prüfung rot.
    """
    try:
        browser = getattr(_playwright, browser_name).launch()
    except Error as error:
        known_mac_problem = (
            browser_name == "firefox"
            and sys.platform == "darwin"
            and "Could not find profile folder" in str(error)
            and not os.environ.get("CI")
        )
        if known_mac_problem:
            pytest.skip("Firefox startet unter macOS 27 nicht (bekanntes Problem); läuft auf GitHub mit.")
        raise
    yield browser
    browser.close()


@pytest.fixture
def tool(live_server, transactional_db, settings):
    """Das Tool auf dem Port des Rauchtests (BASE), mit leerer Datenbank für jeden Test.

    Wie auf dem eigenen Rechner ist der Bausteinkatalog zu sehen (#176), auch auf GitHub.
    """
    settings.ALLOWED_HOSTS = ["localhost"]
    settings.BUILDING_BLOCKS_VISIBLE = True
    return BASE


def _context(browser: Browser, browser_name: str, device: dict, **extra) -> BrowserContext:
    options = dict(device, locale="de-DE", **extra)
    # Firefox kennt keinen Handy-Modus; dort reichen Bildschirmgröße und Berührung.
    if device is HANDY and browser_name != "firefox":
        options["is_mobile"] = True
    return browser.new_context(**options)


@pytest.fixture
def pc(browser, browser_name, tool) -> Page:
    context = _context(browser, browser_name, PC)
    yield context.new_page()
    context.close()


@pytest.fixture
def handy(browser, browser_name, tool) -> Page:
    context = _context(browser, browser_name, HANDY)
    yield context.new_page()
    context.close()


@pytest.fixture
def pc_ohne_skript(browser, browser_name, tool) -> Page:
    """Wie `pc`, aber mit abgeschaltetem Skript im Browser (#280)."""
    context = _context(browser, browser_name, PC, java_script_enabled=False)
    yield context.new_page()
    context.close()


@pytest.fixture
def handy_ohne_skript(browser, browser_name, tool) -> Page:
    """Wie `handy`, aber mit abgeschaltetem Skript im Browser (#280)."""
    context = _context(browser, browser_name, HANDY, java_script_enabled=False)
    yield context.new_page()
    context.close()


def login(page: Page, account=ERIKA) -> None:
    """Meldet sich über die Login-Seite und das Formular von Keycloak an, wie eine Person mit der Maus."""
    page.goto(f"{BASE}/")
    page.get_by_role("button", name="Mit DPV-Konto anmelden").click()
    page.fill("#username", account[0])
    page.fill("#password", account[1])
    page.click("#kc-login")
    page.wait_for_url(f"{BASE}/")


# Wartezeit der Seite, bevor eine kurze Meldung in ihren Bereich wandert (SHORT_DELAY in core/static/core/app.js)
SHORT_DELAY_MS = 100

# Wartet, bis eine kurze Meldung ganz da ist, und hält sie fest, solange axe läuft (#232):
# 1. Ein Zeitgeber gleicher Länge wie der der Seite läuft sicher nach ihrem ab; danach steckt keine Meldung
#    mehr im Warten, sondern steht im Bereich.
# 2. Die Maus „darüber“ hält alle Meldungen an. Sie beginnen während der Prüfung nicht zu verschwinden.
#    Endet dabei eine ältere, schon ausblendende Meldung, zählen die übrigen neu; volle 6 Sekunden bleiben ihnen.
# 3. Ein- und Ausblenden laufen zu Ende (Animationen bleiben an). `allSettled`, weil `finished` abgelehnt
#    wird, wenn die Meldung dabei entfernt wird.
# Danach gilt wieder die echte Lage von Maus und Fokus: Wer die Maus wirklich darauf hält, hält sie weiter.
_AXE_RUN = """async (delay) => {
    const area = document.getElementById('kurzmeldungen');
    if (area) {
        await new Promise((resolve) => setTimeout(resolve, delay));
        area.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
        await Promise.allSettled(area.getAnimations({subtree: true}).map((a) => a.finished));
    }
    try {
        return await axe.run(document, {runOnly: {type: 'tag',
            values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']}});
    } finally {
        if (area) area.dispatchEvent(new MouseEvent('mouseout', {bubbles: true}));
    }
}"""


def run_axe(page: Page) -> list[str]:
    """Prüft die Seite mit axe auf Barrierefreiheit (WCAG 2.2 A und AA) und gibt die Verstöße zurück.

    Eine kurze Meldung (#186) blendet ein und aus und verschwindet nach 6 Sekunden; mitten darin ist
    sie halb durchsichtig und fällt beim Kontrast durch. Deshalb steht sie während der Prüfung still
    und ganz sichtbar (siehe oben). Ein echter Kontrastfehler der Meldung fällt weiter auf.
    """
    page.add_script_tag(path=str(AXE))
    result = page.evaluate(_AXE_RUN, SHORT_DELAY_MS)
    return [
        f"{v['id']} ({v['impact']}): {v['help']} – {[n['target'] for n in v['nodes']][:3]}" for v in result["violations"]
    ]


def focus_visible(page: Page) -> dict:
    """Beschreibt das Element, auf dem gerade der Fokus liegt, und ob man das sieht.

    Ein Fokusrahmen braucht mindestens 3 : 1 Kontrast zu dem, was um ihn herum liegt
    (WCAG 1.4.11). Liegt er mit Abstand außen, ist das der Hintergrund des nächsten Elements
    mit eigener Farbe darüber, meist die Seite selbst. Dazu kommt, wo das Element auf der
    ganzen Seite steht (oben, unten, links), für die Reihenfolge der Halte (#78).

    Manche Bausteine zeichnen den Rahmen nicht am Element selbst, sondern außen um das Ganze,
    etwa das Feld zum Antippen (#207). Hat das Element selbst keinen Rahmen, zählt deshalb der
    nächste umgebende Rahmen, aber nur in der Farbe des Fokusrahmens (`--fokus`); ein anderer
    Rahmen drumherum macht den Fokus nicht sichtbar. „rahmen“ nennt, wer ihn zeichnet
    („selbst“ oder die erste Klasse des umgebenden Elements), „innen“, ob das Element selbst
    einen Rahmen hat.
    """
    return page.evaluate(
        """() => {
            const el = document.activeElement;
            const box = el.getBoundingClientRect();
            const rgb = c => (c.match(/[\\d.]+/g) || []).slice(0, 4).map(Number);
            const lum = ([r, g, b]) => [r, g, b].map(v => v / 255)
                .map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
                .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
            const strong = e => { const t = getComputedStyle(e); return t.outlineStyle !== 'none' && parseFloat(t.outlineWidth) >= 2; };
            const probe = document.body.appendChild(document.createElement('span'));
            probe.style.color = 'var(--fokus)';
            const fokus = rgb(getComputedStyle(probe).color).slice(0, 3);
            probe.remove();
            let frame = el;
            if (!strong(el)) {
                let around = el.parentElement;
                while (around && getComputedStyle(around).outlineStyle === 'none') around = around.parentElement;
                if (around && strong(around) && rgb(getComputedStyle(around).outlineColor).slice(0, 3).join() === fokus.join()) frame = around;
            }
            const s = getComputedStyle(frame);
            let behind = s.outlineOffset && parseFloat(s.outlineOffset) < 0 ? frame : frame.parentElement;
            while (behind && (rgb(getComputedStyle(behind).backgroundColor)[3] === 0)) behind = behind.parentElement;
            const ground = rgb(getComputedStyle(behind || document.body).backgroundColor);
            const [a, b] = [lum(rgb(s.outlineColor)), lum(ground)].sort((x, y) => y - x);
            return {text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().split('\\n')[0],
                    tag: el.tagName, kontrast: Math.round((a + 0.05) / (b + 0.05) * 100) / 100,
                    sichtbar: strong(frame) && box.width > 1 && box.height > 1,
                    rahmen: frame === el ? 'selbst' : frame.classList[0],
                    innen: getComputedStyle(el).outlineStyle !== 'none',
                    oben: box.top + scrollY, unten: box.bottom + scrollY, links: box.left};
        }"""
    )
