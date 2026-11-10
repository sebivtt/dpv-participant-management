"""Rauchtest „Verschieben“ im Browser (#287): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall, wie Wanda in
den Szenarien; Walhall hat die Sippe Falken und die Meute Wölfe, Wilma ist direkt Mitglied. Für die
Ablehnung (PG1) leitet Erika stattdessen Boreas, wie Bruno. Geprüft werden die Teile, die nur ein
Browser zeigt: Der Knopf ist mit der Tastatur erreichbar und steht neben „Austragen“, ohne seitlich
überzustehen; der Dialog ist modal, die Pfeiltasten wechseln die Wahl, die Fehlermeldung steht im
Dialog, die kurze Meldung erscheint, auch ohne Skript, und die Seiten bestehen die Prüfung auf
Barrierefreiheit. Die Regeln selbst prüft tests/test_verschieben.py. Alle Namen sind erfunden.
"""

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element
from roles.models import Role
from tests.test_rollen import give, person, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
PERSONS = '[aria-labelledby="h-personen"]'


def _walhall_with_woelfe() -> dict:
    """Boreas mit Walhall (Sippe Falken, Meute Wölfe) und Zugvögel; Erika leitet Walhall, Wilma ist direkt dort."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    falken = unit(U.GROUP, "Sippe Falken", walhall)
    woelfe = unit(U.GROUP, "Meute Wölfe", walhall)
    zugvoegel = unit(U.TROOP, "Zugvögel", boreas)
    give(erika, R.TROOP_LEAD, walhall)
    wilma = person("wilma.walhall", "Wilma", "Walhall")
    give(wilma, R.MEMBER, walhall)
    return {"erika": erika, "boreas": boreas, "walhall": walhall, "falken": falken, "woelfe": woelfe,
            "zugvoegel": zugvoegel, "wilma": wilma}


def _page_of(where) -> str:
    return f"{BASE}/organisation/{where.key}/"


def _move_dialog(where, target) -> str:
    return f"{_page_of(where)}verschieben/{target.key}/"


def _button_for(target) -> str:
    return f'{PERSONS} .btn-verschieben[href$="/verschieben/{target.key}/"]'


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _membership(user) -> str:
    return Role.objects.select_related("unit").get(user=user, kind=R.MEMBER).unit.name


def test_am_pc_nur_mit_der_tastatur_verschieben(pc):
    login(pc)
    units = _walhall_with_woelfe()
    pc.goto(_page_of(units["walhall"]))
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, _button_for(units["wilma"]), steps=60)
    _all_visible(stations)
    expect(pc.locator(_button_for(units["wilma"]))).to_have_text("Verschieben: Wilma Walhall")
    pc.keyboard.press("Enter")

    pc.wait_for_url(_move_dialog(units["walhall"], units["wilma"]))
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Verschieben")
    expect(dialog.locator(".a-unterzeile")).to_have_text("Wilma Walhall aus Stamm Walhall")
    expect(dialog.locator(".a-auswahl-folge")).to_have_count(0)
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, ".a-auswahl input:checked", steps=10)
    _all_visible(stations)
    pc.keyboard.press("ArrowDown")
    expect(pc.get_by_label("Sippe Falken")).to_be_checked()

    stations = _stations_to_element(pc, "dialog .btn-primary", steps=10)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(_page_of(units["walhall"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Wilma Walhall gehört jetzt zu Sippe Falken.")
    expect(pc.locator(PERSONS)).not_to_contain_text("Wilma")
    assert _membership(units["wilma"]) == "Sippe Falken"
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []


def test_am_pc_escape_fuehrt_zurueck_und_verschiebt_niemanden(pc):
    login(pc)
    units = _walhall_with_woelfe()

    pc.goto(_move_dialog(units["walhall"], units["wilma"]))
    expect(_dialog(pc)).to_be_visible()
    pc.keyboard.press("Escape")
    pc.wait_for_url(_page_of(units["walhall"]))
    expect(_dialog(pc)).to_have_count(0)
    assert _membership(units["wilma"]) == "Walhall"


def test_am_handy_nur_mit_der_tastatur_verschieben(handy):
    login(handy)
    units = _walhall_with_woelfe()
    handy.goto(_page_of(units["walhall"]))
    _no_side_scroll(handy)
    wilma_button = f'.btn-verschieben[href$="/verschieben/{units["wilma"].key}/"]'
    entry = handy.locator(f"{PERSONS} li", has=handy.locator(wilma_button))
    expect(entry.locator(".btn")).to_have_text(["Verschieben: Wilma Walhall", "Austragen: Wilma Walhall"])

    stations = _stations_to_element(handy, _button_for(units["wilma"]), steps=60)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    handy.wait_for_url(_move_dialog(units["walhall"], units["wilma"]))
    expect(_dialog(handy)).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []
    expect(handy.get_by_label("Meute Wölfe")).to_be_checked()

    stations = _stations_to_element(handy, "dialog .btn-primary", steps=15)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    handy.wait_for_url(_page_of(units["walhall"]))
    expect(handy.locator(".a-kurz")).to_contain_text("Wilma Walhall gehört jetzt zu Meute Wölfe.")
    _no_side_scroll(handy)
    assert _membership(units["wilma"]) == "Meute Wölfe"


def test_am_pc_steht_die_ablehnung_im_dialog(pc):
    """PG1: Bea ist Stammesleitung der Zugvögel; Erika leitet Boreas und will sie nach Walhall verschieben."""
    login(pc)
    units = _walhall_with_woelfe()
    give(units["erika"], R.ASSOCIATION_LEAD, units["boreas"])
    bea = person("bea.boreas", "Bea", "Boreas")
    give(bea, R.MEMBER, units["boreas"])
    give(bea, R.TROOP_LEAD, units["zugvoegel"])

    pc.goto(_page_of(units["boreas"]))
    pc.locator(_button_for(bea)).click()
    pc.wait_for_url(_move_dialog(units["boreas"], bea))
    expect(pc.get_by_label("Stamm Walhall")).to_be_checked()
    _dialog(pc).locator(".btn-primary").click()

    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    expect(dialog.locator(".a-meldung.ist-fehler")).to_contain_text(
        "Bea Boreas ist Stammesleitung von Stamm Zugvögel. Diese Rolle passt nicht zu Stamm Walhall. "
        "Sie kann zuerst beendet werden.")
    assert run_axe(pc) == []
    assert _membership(bea) == "Pfadfinderbund Boreas"


def test_ohne_skript_verschiebt_der_knopf_die_gewaehlte_organisation(pc_ohne_skript):
    page = pc_ohne_skript
    login(page)
    units = _walhall_with_woelfe()
    page.goto(_move_dialog(units["walhall"], units["wilma"]))

    page.get_by_label("Sippe Falken").check()
    page.locator("dialog .btn-primary").click()

    page.wait_for_url(_page_of(units["walhall"]))
    # Ohne Skript steht die kurze Meldung fest oben auf der Seite (docs/gestaltung.md, „Kurze Meldung“).
    expect(page.locator("[data-kurz]")).to_contain_text("Wilma Walhall gehört jetzt zu Sippe Falken.")
    assert _membership(units["wilma"]) == "Sippe Falken"
