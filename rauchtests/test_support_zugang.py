"""Rauchtest „Support-Zugang“ im Browser (#92): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und ist hier nur Admin, wie Max in den
Szenarien. Geprüft werden die Teile, die nur ein Browser zeigt: Der Knopf „Support-Zugang starten“ im
Kopf der Seite ist mit der Tastatur erreichbar, am Handy unter dem Namen; der Dialog ist modal und hat
keinen Anlass vorgewählt; ohne Wahl steht die Meldung im Dialog; der Balken steht am PC beim Scrollen
oben, am Handy oben auf der Seite und bricht dort um, ohne seitlich überzustehen; „beenden“ ist mit der
Tastatur erreichbar; die Seiten bestehen die Prüfung auf Barrierefreiheit, und ohne Skript geht alles.
Die Regeln selbst prüft tests/test_support_zugang.py. Alle Namen sind erfunden.
"""

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element
from roles.models import AdminAccess, Role
from tests.test_rollen import give, person, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
START = ".a-orga-kopf .btn-verschieben"
BAR = ".a-supportbalken"


def _boreas_with_admin() -> dict:
    """Boreas mit Walhall (Sippe Falken) und Zugvögel; Wilma ist Mitglied von Walhall, Erika nur Admin."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    give(erika, R.ADMIN)
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    falken = unit(U.GROUP, "Sippe Falken", walhall)
    zugvoegel = unit(U.TROOP, "Zugvögel", boreas)
    wilma = person("wilma.walhall", "Wilma", "Walhall")
    give(wilma, R.MEMBER, walhall)
    return {"erika": erika, "boreas": boreas, "walhall": walhall, "falken": falken, "zugvoegel": zugvoegel,
            "wilma": wilma}


def _page_of(where) -> str:
    return f"{BASE}/organisation/{where.key}/"


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def test_am_pc_nur_mit_der_tastatur_starten_und_beenden(pc):
    login(pc)
    units = _boreas_with_admin()
    pc.goto(_page_of(units["walhall"]))
    expect(pc.locator(START)).to_have_text("Support-Zugang starten")
    expect(pc.locator(".a-orga-seite")).not_to_contain_text("Wilma")
    assert run_axe(pc) == []

    _all_visible(_stations_to_element(pc, START, steps=60))
    pc.keyboard.press("Enter")

    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Support-Zugang für Stamm Walhall starten")
    expect(dialog.locator("input[type=radio]:checked")).to_have_count(0)
    assert run_axe(pc) == []

    _all_visible(_stations_to_element(pc, "dialog input[type=radio]", steps=10))
    pc.keyboard.press("Space")
    expect(pc.get_by_label("Anfrage einer Leitung")).to_be_checked()
    _all_visible(_stations_to_element(pc, "dialog .btn-primary", steps=10))
    pc.keyboard.press("Enter")

    pc.wait_for_url(_page_of(units["walhall"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Support-Zugang für Stamm Walhall gestartet.")
    expect(pc.locator(BAR)).to_contain_text("Support-Zugang für Stamm Walhall aktiv bis")
    expect(pc.locator(".a-orga-seite")).to_contain_text("Wilma")
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []
    # Am PC bleibt der Balken beim Scrollen oben im Inhalt stehen (N1).
    pc.mouse.wheel(0, 2000)
    pc.wait_for_function("() => window.scrollY > 0")
    top = pc.locator(BAR).evaluate("e => e.getBoundingClientRect().top")
    assert 0 <= top < 120, top

    _all_visible(_stations_to_element(pc, f"{BAR} button", steps=80))
    pc.keyboard.press("Enter")

    pc.wait_for_url(_page_of(units["walhall"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Support-Zugang für Stamm Walhall beendet.")
    expect(pc.locator(BAR)).to_have_count(0)
    expect(pc.locator(".a-orga-seite")).not_to_contain_text("Wilma")
    actions = list(AdminAccess.objects.order_by("id").values_list("action", flat=True))
    assert (actions[0], actions[-1]) == (AdminAccess.Action.STARTED, AdminAccess.Action.ENDED)


def test_am_pc_ohne_anlass_steht_die_meldung_im_dialog(pc):
    login(pc)
    units = _boreas_with_admin()
    pc.goto(_page_of(units["walhall"]))

    pc.locator(START).click()
    _dialog(pc).locator(".btn-primary").click()

    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    expect(dialog.locator(".a-meldung.ist-fehler")).to_contain_text("Bitte wähle einen Anlass.")
    assert run_axe(pc) == []
    expect(pc.locator(BAR)).to_have_count(0)


def test_am_pc_escape_fuehrt_zurueck_und_startet_nichts(pc):
    login(pc)
    units = _boreas_with_admin()

    pc.goto(f"{_page_of(units['walhall'])}support-zugang/")
    expect(_dialog(pc)).to_be_visible()
    pc.keyboard.press("Escape")
    pc.wait_for_url(_page_of(units["walhall"]))
    expect(_dialog(pc)).to_have_count(0)
    assert not AdminAccess.objects.exists()


def test_am_handy_nur_mit_der_tastatur_starten(handy):
    login(handy)
    units = _boreas_with_admin()
    handy.goto(_page_of(units["walhall"]))
    _no_side_scroll(handy)
    # Am Handy steht der Knopf unter dem Namen (N4b).
    name = handy.locator(".a-orga-name").bounding_box()
    button = handy.locator(START).bounding_box()
    assert button["y"] >= name["y"] + name["height"] - 1

    _all_visible(_stations_to_element(handy, START, steps=60))
    handy.keyboard.press("Enter")
    expect(_dialog(handy)).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []
    _all_visible(_stations_to_element(handy, "dialog input[type=radio]", steps=10))
    handy.keyboard.press("Space")
    _all_visible(_stations_to_element(handy, "dialog .btn-primary", steps=15))
    handy.keyboard.press("Enter")

    handy.wait_for_url(_page_of(units["walhall"]))
    expect(handy.locator(BAR)).to_contain_text("Support-Zugang für Stamm Walhall aktiv bis")
    _no_side_scroll(handy)
    # Am Handy steht der Balken oben auf der Seite und scrollt mit (N1).
    assert handy.locator(BAR).evaluate("e => getComputedStyle(e).position") == "static"
    shown = handy.locator(BAR).bounding_box()
    assert shown["width"] <= handy.viewport_size["width"]
    handy.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(handy) == []


def test_ohne_skript_starten_und_beenden(pc_ohne_skript):
    page = pc_ohne_skript
    login(page)
    units = _boreas_with_admin()
    page.goto(f"{_page_of(units['walhall'])}support-zugang/")

    page.get_by_label("Fehlersuche").check()
    page.locator("dialog .btn-primary").click()

    page.wait_for_url(_page_of(units["walhall"]))
    expect(page.locator("[data-kurz]")).to_contain_text("Support-Zugang für Stamm Walhall gestartet.")
    page.locator(f"{BAR} button").click()
    page.wait_for_url(_page_of(units["walhall"]))
    expect(page.locator("[data-kurz]")).to_contain_text("Support-Zugang für Stamm Walhall beendet.")
    expect(page.locator(BAR)).to_have_count(0)
