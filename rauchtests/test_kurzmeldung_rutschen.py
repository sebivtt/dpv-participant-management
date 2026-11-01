"""Rauchtest: Die kurze Meldung bringt die Seite nicht ins Rutschen (#226).

Die Nummern verweisen auf Sebastians „Szenarien (31.10.2026)“ in #226. Das Fenster ist so niedrig,
dass die Seite länger als der Bildschirm ist. Gemessen wird, wo der Inhalt steht, sobald der
Browser die Seite gelesen hat und bevor das Skript läuft (`STAND`): So sieht ihn der Browser zuerst,
und so muss er stehen bleiben, wenn die Meldung unten erscheint und wieder verschwindet. Vor der
Behebung stand die Meldung zuerst oben im Inhalt, und mit dem Wegnehmen rückte alles darunter um
ihre Höhe nach oben. Die Uhr steht still wie in test_kurzmeldung.py. Jeder Test läuft in Chromium,
Firefox und WebKit. Szenario 8 (ohne Skript) prüft test_kurzmeldung.py.
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


def _page(request, device: str, size: dict | None = None) -> Page:
    page: Page = request.getfixturevalue(device)
    page.set_viewport_size(size or NIEDRIG[device])
    login(page)
    page.add_init_script(STAND)
    return page


def _stand(page: Page) -> dict:
    return page.evaluate(
        """() => ({scroll: scrollY, top: document.querySelector(".a-main-inhalt").lastElementChild.getBoundingClientRect().top,
                  lang: document.documentElement.scrollHeight > innerHeight})"""
    )


def _nichts_rutscht(page: Page, text: str, lang: bool = True) -> None:
    """Die Meldung ist unten zu sehen; die Seite steht oben, und der Inhalt steht, wo er zuerst stand."""
    # Die Maus weg von der Meldung, sonst hält sie sie fest (#186, Szenario 4).
    page.mouse.move(5, 5)
    _later(page, 300)
    notice = _short(page)
    expect(notice).to_contain_text(text)
    expect(notice).to_be_in_viewport()
    first = page.evaluate("window.vorDemSkript")
    now = _stand(page)
    assert now["lang"] == lang, "Die Seite muss länger als der Bildschirm sein" if lang else "Die Seite muss ganz zu sehen sein"
    assert first["scroll"] == 0 and now["scroll"] == 0, (first, now)
    assert now["top"] == first["top"], (first, now)

    # Szenario 5: Auch wenn sie nach rund 6 Sekunden verschwindet, rutscht nichts.
    _later(page, 6500)
    expect(notice).to_have_count(0)
    assert _stand(page) == now


# Szenarien 1, 2 und 5: „Mein Profil“ am PC und am Handy
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
def test_profil_schliessen_mit_dem_x_rutscht_nichts(request, browser_name):
    page = _page(request, "pc")
    _set_scout_name("Kiwi")
    _stop_clock(page)
    page.goto(f"{BASE}/profil/")
    _save(page, "Falkenflug")
    _later(page, 300)
    first = page.evaluate("window.vorDemSkript")
    _short(page).get_by_role("button", name="Meldung schließen").click()
    expect(_short(page)).to_have_count(0)
    now = _stand(page)
    assert now["lang"] and now["scroll"] == 0 and now["top"] == first["top"], (first, now)


# Szenario 6: Fenster groß genug für die ganze Seite
def test_profil_im_grossen_fenster_rutscht_nichts(request, browser_name):
    page = _page(request, "pc", {"width": PC["viewport"]["width"], "height": 1400})
    _set_scout_name("Kiwi")
    _stop_clock(page)
    page.goto(f"{BASE}/profil/")
    _save(page, "Falkenflug")
    _nichts_rutscht(page, SAVED, lang=False)


# Szenario 7: Zu langer Fahrtenname; die Fehlermeldung steht am Feld, und die Seite rollt wie bisher zum Feld.
def test_profil_zu_lang_rollt_wie_bisher_zum_feld(request, browser_name):
    # So niedrig, dass das Feld ohne Hinrollen nicht zu sehen wäre; wie weit der Browser rollt, bleibt ihm überlassen.
    page = _page(request, "pc", {"width": PC["viewport"]["width"], "height": 230})
    _set_scout_name("Kiwi")
    _stop_clock(page)
    page.goto(f"{BASE}/profil/")
    _save(page, "K" * 31)
    _later(page, 300)
    field = page.get_by_label("Fahrtenname", exact=True)
    expect(field).to_be_focused()
    expect(field).to_be_in_viewport()
    expect(page.locator("[data-antippfeld] .invalid-feedback")).to_be_visible()
    assert page.evaluate("scrollY") > 0
    expect(_short(page)).to_have_count(0)


# Unabhängige Prüfung: Lädt das Skript nicht, bleibt „Speichern“ zu sehen und speichert.
def test_ohne_geladenes_skript_bleibt_speichern(request, browser_name):
    page = _page(request, "pc")
    page.route("**/core/app.js", lambda route: route.abort())
    page.goto(f"{BASE}/profil/")
    page.get_by_label("Fahrtenname", exact=True).fill("Kiwi")
    _submit(page, page.get_by_role("button", name="Speichern").click)
    expect(page.locator("[data-antippfeld]")).to_contain_text("Kiwi")


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
