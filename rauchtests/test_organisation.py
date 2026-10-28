"""Rauchtest der Seite „Organisation“ im Browser (#189): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und bekommt danach die Stammesleitung von
Walhall, wie Wanda in den Szenarien. Geprüft werden die Teile, die nur ein Browser zeigt: was am PC
und am Handy sichtbar ist, dass nichts seitlich übersteht, dass der Fokus zu sehen ist und dass die
Seiten die Prüfung auf Barrierefreiheit bestehen. Die Regeln selbst prüfen tests/test_organisation.py.
Alle Namen sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_rauchtest import _all_visible, _stations_to_element
from roles.models import Role
from tests.test_rollen import give, person, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind


def _walhall_for_erika() -> dict:
    """Boreas mit Walhall (Sippe Falken ohne Leitung, Meute Wölfe mit Leitung) und Zugvögel; Erika leitet Walhall."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    falken = unit(U.GROUP, "Sippe Falken", walhall)
    woelfe = unit(U.GROUP, "Meute Wölfe", walhall)
    zugvoegel = unit(U.TROOP, "Zugvögel", boreas)
    unit(U.GROUP, "Sippe Adler", zugvoegel)
    give(erika, R.TROOP_LEAD, walhall)
    bruno = person("bruno.bund", "Bruno", "Bund")
    give(bruno, R.ASSOCIATION_LEAD, boreas)
    wim = person("wim.wolf", "Wim", "Wolf-Mit-Einem-Sehr-Langen-Doppelnamen-Ohne-Trennstelle")
    wim.email = "wim.wolf.mit.einer.sehr.langen.adresse.ohne.trennstelle@example.org"
    wim.save()
    give(wim, R.GROUP_LEAD, woelfe)
    return {"walhall": walhall, "falken": falken, "woelfe": woelfe, "boreas": boreas}


def _no_side_scroll(page: Page) -> None:
    width = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    assert width[0] <= width[1], f"Seite breiter als der Bildschirm: {width}"


def test_am_pc_gliederung_und_seite_nebeneinander_nur_mit_der_tastatur(pc):
    login(pc)
    units = _walhall_for_erika()
    # Die Rolle kam nach dem Laden; der Menüpunkt erscheint beim nächsten Klick.
    pc.reload()

    pc.get_by_role("link", name="Organisation").first.click()

    outline = pc.get_by_role("navigation", name="Gliederung")
    expect(outline).to_be_visible()
    expect(pc.locator(".a-orga-seite")).to_be_visible()
    expect(pc.locator(".a-orga-name")).to_have_text("Walhall")
    expect(outline.locator("details")).to_contain_text("1 weitere ohne Zugriff")
    assert run_axe(pc) == []
    # Gliederung und Seite nebeneinander, die Gliederung links
    boxes = [pc.locator(sel).bounding_box() for sel in (".a-gliederung", ".a-orga-seite")]
    assert boxes[0]["x"] < boxes[1]["x"] and abs(boxes[0]["y"] - boxes[1]["y"]) < 2, boxes

    falken = f".a-gliederung a[href='/organisation/{units['falken'].key}/']"
    stations = _stations_to_element(pc, falken, steps=30)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{BASE}/organisation/{units['falken'].key}/")
    expect(pc.get_by_role("heading", level=1)).to_have_text("Sippe Falken")
    expect(pc.locator(".a-orga-kopf")).to_contain_text("Du springst ein")
    expect(pc.locator(".a-orga-zurueck")).to_be_hidden()
    assert run_axe(pc) == []
    # Zur Seite darüber nur lesend, über den Pfad im Kopf
    boreas = f".a-pfad a[href='/organisation/{units['boreas'].key}/']"
    stations = _stations_to_element(pc, boreas, steps=40)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(f"{BASE}/organisation/{units['boreas'].key}/")
    expect(pc.locator(".a-orga-kopf")).to_contain_text("nur lesen")
    expect(pc.locator(".a-orgakachel.ist-ohne-zugriff")).to_contain_text("Zugvögel")
    assert run_axe(pc) == []


def test_am_pc_gliederung_so_hoch_wie_der_bildschirm_und_springt_nicht(pc):
    """Sebastian beim Testen (28.10.2026): Die Gliederung springt beim Wechsel nicht und bleibt beim Rollen stehen."""
    login(pc)
    units = _walhall_for_erika()
    screen = pc.viewport_size["height"]
    heights = []
    for address in ("/organisation/", f"/organisation/{units['falken'].key}/", f"/organisation/{units['walhall'].key}/"):
        pc.goto(f"{BASE}{address}")
        heights.append(round(pc.locator(".a-gliederung").bounding_box()["height"]))
    assert len(set(heights)) == 1, heights
    assert heights[0] == screen - 80, (heights, screen)
    # Lange Seite: Beim Rollen bleibt die Gliederung oben stehen.
    pc.evaluate("document.querySelector('.a-orga-seite').style.paddingBottom = '2000px'")
    pc.mouse.wheel(0, 1500)
    expect(pc.locator(".a-gliederung")).to_be_in_viewport()
    assert round(pc.locator(".a-gliederung").bounding_box()["y"]) == 40


def test_am_pc_kachel_darunter_oeffnet_die_organisation(pc):
    login(pc)
    units = _walhall_for_erika()
    pc.goto(f"{BASE}/organisation/{units['walhall'].key}/")

    pc.locator(".a-orgakachel", has_text="Meute Wölfe").click(position={"x": 12, "y": 60})

    pc.wait_for_url(f"{BASE}/organisation/{units['woelfe'].key}/")
    _no_side_scroll(pc)
    assert run_axe(pc) == []


def test_am_handy_zuerst_die_gliederung_dann_die_seite_auch_nur_mit_der_tastatur(handy):
    login(handy)
    units = _walhall_for_erika()

    handy.goto(f"{BASE}/organisation/")

    expect(handy.get_by_role("navigation", name="Gliederung")).to_be_visible()
    expect(handy.locator(".a-orga-seite")).to_be_hidden()
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    handy.get_by_role("link", name="Meute Wölfe").first.tap()
    handy.wait_for_url(f"{BASE}/organisation/{units['woelfe'].key}/")
    expect(handy.get_by_role("navigation", name="Gliederung")).to_be_hidden()
    expect(handy.get_by_role("heading", level=1)).to_have_text("Meute Wölfe")
    expect(handy.locator(".a-leitung")).to_contain_text("wim.wolf.mit.einer.sehr.langen.adresse")
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    back = handy.locator(".a-orga-zurueck")
    expect(back).to_be_visible()
    stations = _stations_to_element(handy, ".a-orga-zurueck", steps=15)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{BASE}/organisation/")
    expect(handy.get_by_role("navigation", name="Gliederung")).to_be_visible()


@pytest.mark.parametrize("device", ["pc", "handy"])
def test_ohne_leitungsrolle_kein_menuepunkt(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)

    if device == "handy":
        page.get_by_role("button", name="Menü").click()
    expect(page.get_by_role("link", name="Startseite").last).to_be_visible()
    expect(page.get_by_role("link", name="Organisation")).to_have_count(0)

