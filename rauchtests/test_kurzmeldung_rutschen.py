"""Rauchtest: Die kurze Meldung bringt die Seite nicht ins Rutschen (#226).

Die Nummern verweisen auf Sebastians „Szenarien (31.10.2026)“ in #226. Das Fenster ist so niedrig,
dass die Seite länger als der Bildschirm ist. Gemessen wird, wo der Inhalt steht, sobald der
Browser die Seite gelesen hat und bevor das Skript läuft (`STAND`): So sieht ihn der Browser zuerst,
und so muss er stehen bleiben, wenn die Meldung unten erscheint und wieder verschwindet. Vor der
Behebung stand die Meldung zuerst oben im Inhalt, und mit dem Wegnehmen rückte alles darunter um
ihre Höhe nach oben. Die Uhr steht still wie in test_kurzmeldung.py. Jeder Test läuft in Chromium,
Firefox und WebKit. Szenario 7 (Fehler am Feld) und 8 (ohne Skript) prüft test_kurzmeldung.py.
Alle Konten und Daten sind erfunden.
"""

import pytest
from playwright.sync_api import Page, expect

from rauchtests import test_benennen, test_verband
from rauchtests.conftest import BASE, HANDY, PC, login
from rauchtests.test_kurzmeldung import SAVED, _later, _save, _set_scout_name, _short, _stop_clock, _submit

pytestmark = pytest.mark.django_db(transaction=True)

# Merkt sich, wo der Inhalt steht, sobald die Seite gelesen ist; das Skript (defer) läuft erst danach.
STAND = """
document.addEventListener("readystatechange", function () {
  if (document.readyState === "interactive") {
    window.vorDemSkript = {scroll: scrollY, top: document.querySelector(".a-main-inhalt").lastElementChild.getBoundingClientRect().top};
  }
});
"""
NIEDRIG = {"pc": {"width": PC["viewport"]["width"], "height": 420}, "handy": {"width": HANDY["viewport"]["width"], "height": 600}}


def _page(request, device: str) -> Page:
    page: Page = request.getfixturevalue(device)
    page.set_viewport_size(NIEDRIG[device])
    login(page)
    page.add_init_script(STAND)
    return page


def _stand(page: Page) -> dict:
    return page.evaluate(
        """() => ({scroll: scrollY, top: document.querySelector(".a-main-inhalt").lastElementChild.getBoundingClientRect().top,
                  lang: document.documentElement.scrollHeight > innerHeight})"""
    )


def _nichts_rutscht(page: Page, text: str) -> None:
    """Die Meldung ist unten zu sehen; die Seite steht oben, und der Inhalt steht, wo er zuerst stand."""
    _later(page, 300)
    notice = _short(page)
    expect(notice).to_contain_text(text)
    expect(notice).to_be_in_viewport()
    first = page.evaluate("window.vorDemSkript")
    now = _stand(page)
    assert now["lang"], "Die Seite muss länger als der Bildschirm sein"
    assert first["scroll"] == 0 and now["scroll"] == 0, (first, now)
    assert now["top"] == first["top"], (first, now)

    # Szenario 5: Auch wenn sie nach rund 6 Sekunden verschwindet, rutscht nichts.
    _later(page, 6500)
    expect(notice).to_have_count(0)
    assert _stand(page) == now


# Szenarien 1, 2, 5 und 6: „Mein Profil“ am PC und am Handy
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_profil_nach_dem_speichern_rutscht_nichts(request, browser_name, device):
    page = _page(request, device)
    _set_scout_name("Kiwi")
    _stop_clock(page)
    page.goto(f"{BASE}/profil/")
    heading = page.get_by_role("heading", name="Mein Profil", level=1)
    above = heading.bounding_box()
    _save(page, "Falkenflug")
    _nichts_rutscht(page, SAVED)
    assert heading.bounding_box() == above


# Szenario 5: Schließen mit dem ×
def test_profil_schliessen_mit_dem_x_rutscht_nichts(pc):
    pc.set_viewport_size(NIEDRIG["pc"])
    login(pc)
    pc.add_init_script(STAND)
    _set_scout_name("Kiwi")
    _stop_clock(pc)
    pc.goto(f"{BASE}/profil/")
    _save(pc, "Falkenflug")
    _later(pc, 300)
    first = pc.evaluate("window.vorDemSkript")
    _short(pc).get_by_role("button", name="Meldung schließen").click()
    expect(_short(pc)).to_have_count(0)
    now = _stand(pc)
    assert now["lang"] and now["scroll"] == 0 and now["top"] == first["top"], (first, now)


# Szenario 3: Seite „Verband“ nach dem Entfernen einer Rolle
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_verband_nach_dem_entfernen_rutscht_nichts(request, browser_name, device):
    page = _page(request, device)
    test_verband._verband_for_erika()
    _stop_clock(page)
    page.goto(f"{BASE}/organisation/")
    page.locator(".a-bund .a-leitung-knopf").click()
    _submit(page, test_verband._dialog(page).locator(".btn-gefahr").click)
    _nichts_rutscht(page, "Brummbär (Bruno Bund) ist nicht mehr Bundesleitung von Pfadfinderbund Boreas.")


# Szenario 4: Seite einer Organisation nach dem Benennen
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_organisation_nach_dem_benennen_rutscht_nichts(request, browser_name, device):
    page = _page(request, device)
    units = test_benennen._walhall_for_erika()
    _stop_clock(page)
    page.goto(f"{BASE}/organisation/{units['walhall'].key}/benennen/")
    field = page.get_by_label("Name, Fahrtenname, Mail oder Benutzername")
    field.fill("otto.ohne@example.org")
    _submit(page, lambda: field.press("Enter"))
    _submit(page, test_benennen._dialog(page).get_by_role("button", name="Benennen Otto Ohne").click)
    _nichts_rutscht(page, "Otto Ohne ist jetzt Stammesleitung von Walhall.")
