"""Rauchtest: Ein langer Fahrtenname bricht in der Seitenleiste und im Menü um (#214).

Wo der Browser eine Zeile umbricht, entscheidet erst er selbst; deshalb lässt es sich nur hier prüfen.
Die Nummern verweisen auf die Szenarien zu #214 (30.10.2026). Jeder Test läuft in Chromium,
Firefox und WebKit (conftest.py). Alle Namen sind erfunden.
"""

import pytest
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, HANDY, _context, login
from rauchtests.test_rauchtest import _set_scout_name

pytestmark = pytest.mark.django_db(transaction=True)

STURMVOGEL = "Sturmvogelwanderfalkenflugkind"
WANDERFALKE = "Wanderfalke vom Hohen Meißner"

# Wo jede Zeile des Namens endet, und ob der Name oder der Profilkreis über einen Rand ragt.
LINES = """profil => {
  const name = profil.querySelector(':scope > span:last-child');
  const text = name.firstChild;
  const ends = [];
  let top = null;
  for (let i = 0; i < text.length; i++) {
    const range = document.createRange();
    range.setStart(text, i);
    range.setEnd(text, i + 1);
    const rect = [...range.getClientRects()].find(r => r.width > 0);
    if (!rect) continue;
    if (top !== null && rect.top > top + 2) ends.push(i);
    top = rect.top;
  }
  const outer = profil.parentElement.closest('.a-sidebar, .a-drawer').getBoundingClientRect();
  const box = profil.getBoundingClientRect();
  const own = name.getBoundingClientRect();
  return {
    ends: ends,
    inside: own.right <= box.right + 0.5 && box.right <= outer.right + 0.5 && box.left >= outer.left - 0.5,
    scroll: [profil.scrollWidth, profil.clientWidth, name.scrollWidth, name.clientWidth],
  };
}"""


def _check(profil, value: str, mid_word: bool) -> None:
    expect(profil).to_contain_text(value)
    result = profil.evaluate(LINES)
    assert result["inside"], f"Name ragt über den Rand: {result}"
    assert result["scroll"][0] <= result["scroll"][1] and result["scroll"][2] <= result["scroll"][3], result
    assert result["ends"], f"Name bricht nicht um: {result}"
    after_space = [value[i - 1] == " " for i in result["ends"]]
    if mid_word:
        assert not any(after_space), result
    else:
        # Szenario 6: nur an den Leerzeichen.
        assert all(after_space), f"{value!r} bricht mitten im Wort um: {result}"


def _menu(page: Page):
    page.get_by_role("button", name="Menü").click()
    menu = page.get_by_role("dialog", name="Menü")
    expect(menu).to_be_visible()
    return menu.locator(".a-profil")


def _page(browser, browser_name, width: int) -> Page:
    """Eine Seite mit eigener Breite; unter 768 Pixel wie ein Handy."""
    if width >= 768:
        return _context(browser, browser_name, {"viewport": {"width": width, "height": 900}}).new_page()
    device = dict(HANDY, viewport={"width": width, "height": 740})
    if browser_name != "firefox":
        device["is_mobile"] = True
    return _context(browser, browser_name, device).new_page()


# Szenarien 5 und 6 am PC
@pytest.mark.parametrize(("value", "mid_word"), [(STURMVOGEL, True), (WANDERFALKE, False)])
def test_seitenleiste_am_pc_bricht_um_und_nichts_ragt_hinaus(pc, browser_name, value, mid_word):
    login(pc)
    _set_scout_name(value)
    pc.goto(f"{BASE}/")
    _check(pc.locator(".a-sidebar .a-profil"), value, mid_word)


# Szenarien 5 und 6 im Menü am Handy, auch bei 340 Pixel Breite
@pytest.mark.parametrize("width", [390, 340])
@pytest.mark.parametrize(("value", "mid_word"), [(STURMVOGEL, True), (WANDERFALKE, False)])
def test_menue_am_handy_bricht_um_und_nichts_ragt_hinaus(browser, browser_name, tool, width, value, mid_word):
    page = _page(browser, browser_name, width)
    try:
        login(page)
        _set_scout_name(value)
        page.goto(f"{BASE}/")
        _check(_menu(page), value, mid_word)
    finally:
        page.context.close()


# Szenario 8: Namenszeile und Feld auf „Mein Profil“ zeigen den Namen vollständig, wie bisher
@pytest.mark.parametrize("width", [1366, 340])
def test_namenszeile_und_feld_auf_mein_profil_zeigen_den_namen_vollstaendig(browser, browser_name, tool, width):
    page = _page(browser, browser_name, width)
    try:
        login(page)
        _set_scout_name(STURMVOGEL)
        page.goto(f"{BASE}/profil/")
        head = page.locator(".a-anzeigename")
        expect(head).to_have_text(f"{STURMVOGEL} (Erika Testfrau)")
        rest = page.get_by_role("button", name=f"Fahrtenname bearbeiten: {STURMVOGEL}")
        expect(rest).to_contain_text(STURMVOGEL)
        for element in (head, rest):
            sizes = element.evaluate("e => [e.scrollWidth, e.clientWidth]")
            assert sizes[0] <= sizes[1], f"Überstand: {sizes}"
        width_ = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        assert width_[0] <= width_[1], f"Seite breiter als der Bildschirm: {width_}"
    finally:
        page.context.close()
