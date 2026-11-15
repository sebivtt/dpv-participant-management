"""Rauchtest: Lange Namen brechen im Kopf jedes Dialogs um (#331).

Wo der Browser eine Zeile umbricht und ob etwas über den Rand ragt, entscheidet erst er selbst; deshalb
lässt es sich nur hier prüfen. Die Nummern verweisen auf die Szenarien zu #331 (14.11.2026). Jeder Test
läuft in Chromium, Firefox und WebKit (conftest.py), am PC und am Handy mit 375 Pixel Breite (Szenario 6).
Geregelt ist der Umbruch zentral im Baustein „Dialog“ (core/static/core/app.css); geprüft werden deshalb
Dialoge verschiedener Seiten mit langen Namen von Personen mit und ohne Konto und von Organisationen.
Alle Namen sind erfunden.
"""

from datetime import date

import pytest
from playwright.sync_api import Page, expect

from persons.models import ManagedPerson
from rauchtests.conftest import BASE, login
from rauchtests.test_entfernen import _walhall_for_erika
from rauchtests.test_fahrtenname_umbruch import _page
from rauchtests.test_organisation import _no_side_scroll
from roles.models import Role
from tests.test_rollen import give, person, unit
from units.models import Unit

pytestmark = pytest.mark.django_db(transaction=True)

R = Role.Kind
U = Unit.Kind

# Szenario 1: Vor- und Nachname je 50 Zeichen ohne Leerzeichen.
VORNAME_LANG = "Paulmaximilianfriedrichwilhelmkonstantinbartholoma"
NACHNAME_LANG = "Probehausenkirchbergwaldsteinmuehlenbachfeldhofenx"
# Szenario 2: Name aus Keycloak mit 120 Zeichen ohne Leerzeichen.
KONTO_LANG = "Finnfalkenflugwindwolkenbergsturmtalwiesenbachquellsteinhoehlenwaldrandhuegelseeuferdammweghofstaettenbrunnenplatzendeab"
# Szenario 4: Leitung mit langem Nachnamen.
LEITUNG_LANG = "Falkenhorstbergsteigerwaldlaeuferflussueberquererfeuerholzsammler"
# Szenario 5: Organisation mit 100 Zeichen ohne Leerzeichen.
ORGA_LANG = "Sippenachtfalkenmondscheinwanderungsgemeinschaftuebersiebenbergeundsiebentaelerbishinzumgrossenseeab"
# Szenario 7: normale, aber lange Namen mit Leerzeichen.
VORNAME_NORMAL = "Maximiliane Konstantina"
NACHNAME_NORMAL = "von Hohenzollern"


def test_lange_namen_haben_die_laengen_aus_den_szenarien():
    """Die Längen der Szenarien 1, 2 und 5, nachgezählt (Befund der unabhängigen Prüfung)."""
    assert (len(VORNAME_LANG), len(NACHNAME_LANG), len(KONTO_LANG), len(ORGA_LANG)) == (50, 50, 120, 100)

# Wo jede Zeile eines Textes endet, über alle Textteile des Elements hinweg; mit `normal` dieselbe Rechnung,
# als bräche der Text nur an den üblichen Stellen um, wie vor #331.
ZEILENENDEN = """(el, normal) => {
  const before = el.style.overflowWrap;
  if (normal) el.style.overflowWrap = 'normal';
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  const ends = [];
  let offset = 0;
  let top = null;
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    for (let i = 0; i < node.length; i++) {
      const range = document.createRange();
      range.setStart(node, i);
      range.setEnd(node, i + 1);
      const rect = [...range.getClientRects()].find(r => r.width > 0);
      if (!rect) continue;
      if (top !== null && rect.top > top + 2) ends.push(offset + i);
      top = rect.top;
    }
    offset += node.length;
  }
  el.style.overflowWrap = before;
  return {ends: ends, text: el.textContent};
}"""

# Lage von Dialog, Titel und × und ob der Dialog seitlich rollt.
LAGE = """d => {
  const box = d.getBoundingClientRect();
  const titel = d.querySelector('h2').getBoundingClientRect();
  const x = d.querySelector('.a-dialog-kopf .a-schliessen');
  const kreuz = x.getBoundingClientRect();
  const mitte = document.elementFromPoint(kreuz.left + kreuz.width / 2, kreuz.top + kreuz.height / 2);
  const ragt = [...d.querySelectorAll('.a-dialog-kopf *, .a-dialog-inhalt *')]
    .filter(e => !e.closest('.sr-nur'))
    .map(e => [e.tagName + '.' + e.className, e.getBoundingClientRect()])
    .filter(([, r]) => r.width > 0 && (r.right > box.right + 0.5 || r.left < box.left - 0.5))
    .map(([name]) => name);
  return {
    breite: box.width,
    rollt: [d.scrollWidth, d.clientWidth, d.scrollLeft],
    titel_links: titel.left - box.left,
    kreuz: [kreuz.left - box.left, box.right - kreuz.right, kreuz.width],
    kreuz_klickbar: mitte !== null && x.contains(mitte),
    ragt: ragt,
  };
}"""


def _zeilenenden(element, normal: bool = False) -> dict:
    return element.evaluate(ZEILENENDEN, normal)


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _breite(page: Page) -> float:
    return _dialog(page).evaluate("d => d.getBoundingClientRect().width")


def _steht_richtig(page: Page, breite: float | None = None) -> None:
    """Szenarien 1, 6 und 8: so breit wie mit normalen Namen (`breite`), kein seitliches Rollen, Titel links
    sichtbar, × sichtbar und anklickbar."""
    dialog = _dialog(page)
    expect(dialog).to_be_visible()
    lage = dialog.evaluate(LAGE)
    if breite is not None:
        assert abs(lage["breite"] - breite) < 1, f"Dialog nicht so breit wie mit normalen Namen ({breite}): {lage}"
    breit, sichtbar, gerollt = lage["rollt"]
    assert breit <= sichtbar and gerollt == 0, f"Dialog rollt seitlich: {lage}"
    assert 0 <= lage["titel_links"] <= 24, f"Titel steht nicht links sichtbar: {lage}"
    assert lage["kreuz"][0] > 0 and lage["kreuz"][1] >= 0 and lage["kreuz"][2] > 0, f"× nicht im Dialog: {lage}"
    assert lage["kreuz_klickbar"], f"× ist verdeckt: {lage}"
    assert not lage["ragt"], f"Ragt über den Rand des Dialogs: {lage}"
    _no_side_scroll(page)


def _bricht_um(element, wort: str, im_wort: bool) -> None:
    """Der Text mit dem langen Wort bricht um; mit `im_wort` auch mitten in diesem Wort, weil es länger ist als
    eine Zeile. Dass dabei nichts über den Rand ragt, prüft `_steht_richtig`."""
    expect(element).to_contain_text(wort)
    zeilen = _zeilenenden(element)
    assert zeilen["ends"], f"Bricht nicht um: {zeilen}"
    if im_wort:
        anfang = zeilen["text"].index(wort)
        assert [i for i in zeilen["ends"] if anfang < i < anfang + len(wort)], f"{wort!r} bricht nicht im Wort um: {zeilen}"


def _daten() -> dict:
    """Erika leitet Walhall; in den Falken Fiete als Leitung, in der Meute Wölfe ohne Leitung Finn mit Konto
    (Erika springt dort ein), in Walhall Paul und Maxi ohne Konto, darunter eine Sippe mit langem Namen. Fiete, Finn, Paul und die Sippe haben lange Namen."""
    daten = _walhall_for_erika()
    fiete = daten["fiete"]
    fiete.last_name = LEITUNG_LANG
    fiete.save()
    daten["fiete_rolle"] = Role.objects.get(user=fiete, kind=R.GROUP_LEAD)
    daten["woelfe"] = unit(U.GROUP, "Meute Wölfe", daten["walhall"])
    finn = person("finn.falke", "Finn", KONTO_LANG)
    give(finn, R.MEMBER, daten["woelfe"])
    daten["finn"] = finn
    daten["paul"] = ManagedPerson.objects.create(first_name=VORNAME_LANG, last_name=NACHNAME_LANG,
                                                 birth_date=date(2012, 9, 3), unit=daten["walhall"])
    daten["maxi"] = ManagedPerson.objects.create(first_name=VORNAME_NORMAL, last_name=NACHNAME_NORMAL,
                                                 birth_date=date(2013, 4, 21), unit=daten["walhall"])
    daten["sippe"] = unit(U.GROUP, ORGA_LANG, daten["walhall"])
    return daten


def _seite(where) -> str:
    return f"{BASE}/organisation/{where.key}/"


def _verwaltet(daten: dict, wer: str, handlung: str) -> str:
    return f"{_seite(daten['walhall'])}verwaltete-person/{daten[wer].key}/{handlung}/"


@pytest.mark.parametrize("breite", [1366, 375])
def test_lange_namen_brechen_in_jedem_dialog_um(browser, browser_name, tool, breite):
    page = _page(browser, browser_name, breite)
    try:
        login(page)
        daten = _daten()
        dialog = _dialog(page)
        # Zum Vergleich: so breit ist ein Dialog mit normalen Namen.
        page.goto(_verwaltet(daten, "maxi", "verschieben"))
        breite_sonst = _breite(page)

        # Szenario 1: „Verschieben“ bei Paul, die Zeile unter dem Titel bricht um. Je 50 Zeichen passen am PC
        # in eine Zeile, am Handy nicht.
        page.goto(_verwaltet(daten, "paul", "verschieben"))
        _steht_richtig(page, breite_sonst)
        _bricht_um(dialog.locator(".a-dialog-kopf .a-unterzeile"), NACHNAME_LANG, im_wort=breite < 768)

        # Szenario 2: „… austragen?“ bei Finn mit Konto.
        page.goto(f"{_seite(daten['woelfe'])}austragen/{daten['finn'].key}/")
        _steht_richtig(page, breite_sonst)
        _bricht_um(dialog.locator("h2"), KONTO_LANG, im_wort=True)

        # Szenario 3: „… bearbeiten“ und „… löschen?“ bei Paul.
        for handlung in ("bearbeiten", "loeschen"):
            page.goto(_verwaltet(daten, "paul", handlung))
            _steht_richtig(page, breite_sonst)
            _bricht_um(dialog.locator("h2"), NACHNAME_LANG, im_wort=breite < 768)

        # Szenario 4: „… entfernen?“ bei Fiete als Leitung.
        page.goto(f"{_seite(daten['falken'])}entfernen/{daten['fiete_rolle'].key}/")
        _steht_richtig(page, breite_sonst)
        _bricht_um(dialog.locator("h2"), LEITUNG_LANG, im_wort=breite < 768)

        # Szenario 5: Organisation mit langem Namen, „… bearbeiten“.
        page.goto(f"{_seite(daten['sippe'])}bearbeiten/")
        _steht_richtig(page, breite_sonst)
        _bricht_um(dialog.locator("h2"), ORGA_LANG, im_wort=True)

        # Szenario 8: Das × schließt den Dialog, auch bei langem Namen.
        page.goto(_verwaltet(daten, "paul", "verschieben"))
        dialog.locator(".a-dialog-kopf .a-schliessen").click()
        page.wait_for_url(f"{_seite(daten['walhall'])}**")
        expect(dialog).to_have_count(0)
    finally:
        page.context.close()


# Szenario 7: Normale Namen brechen nur an Leerzeichen um, genau wie bisher.
@pytest.mark.parametrize("breite", [1366, 375])
def test_normale_namen_brechen_nur_an_leerzeichen_um(browser, browser_name, tool, breite):
    page = _page(browser, browser_name, breite)
    try:
        login(page)
        daten = _daten()
        dialog = _dialog(page)
        for handlung, wo in (("verschieben", ".a-dialog-kopf .a-unterzeile"), ("bearbeiten", "h2")):
            page.goto(_verwaltet(daten, "maxi", handlung))
            _steht_richtig(page)
            element = dialog.locator(wo)
            expect(element).to_contain_text(f"{VORNAME_NORMAL} {NACHNAME_NORMAL}")
            zeilen = _zeilenenden(element)
            assert all(zeilen["text"][i - 1] == " " for i in zeilen["ends"]), f"Bricht im Wort um: {zeilen}"
            assert zeilen["ends"] == _zeilenenden(element, normal=True)["ends"], f"Bricht anders um als bisher: {zeilen}"
    finally:
        page.context.close()
