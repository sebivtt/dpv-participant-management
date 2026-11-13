"""Rauchtest „… anlegen“ und „… bearbeiten“ (Name, Ring, Schalter „Hat Ringe“) im Browser (#95).

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall, wie Wanda in
den Szenarien; für die Ringe leitet sie den Bund, wie Bruno und Mona. Geprüft wird, was nur ein Browser
zeigt: Knopf „… anlegen“, Stift oben rechts im Kopf, Wahl des Rings und Schalter sind mit der Tastatur
erreichbar und stehen am Handy ohne seitlichen Überstand, der Dialog ist modal, Enter im Feld „Name“
schickt den Dialog ab, der Name bleibt beim Tippen wie am Handy mit Wortvorschlag stehen, die kurze
Meldung erscheint, auch ohne Skript, und die Seiten bestehen die Prüfung auf Barrierefreiheit. Die Regeln selbst prüft tests/test_einheiten_anlegen.py. Alle Namen sind erfunden.
"""

import re

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone
from roles.models import Role
from tests.test_rollen import give, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
CREATE_BUTTON = '[aria-labelledby="h-darunter"] .a-flaeche-aktion'
HEAD = ".a-orga-kopf"
PEN = f"{HEAD} .a-stift"
SWITCH = 'dialog input[role="switch"]'


def _boreas(lead: str) -> dict:
    """Boreas ohne Ringe mit Walhall (Sippe Falken) und Zugvögel; Erika leitet Walhall oder den Bund."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    falken = unit(U.GROUP, "Sippe Falken", walhall)
    zugvoegel = unit(U.TROOP, "Zugvögel", boreas)
    units = {"erika": erika, "boreas": boreas, "walhall": walhall, "falken": falken, "zugvoegel": zugvoegel}
    give(erika, R.TROOP_LEAD if lead == "walhall" else R.ASSOCIATION_LEAD, units[lead])
    return units


def _page_of(where) -> str:
    return f"{BASE}/organisation/{where.key}/"


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _children(where) -> set[str]:
    return set(Unit.objects.filter(parent=where).values_list("name", flat=True))


def test_am_pc_nur_mit_der_tastatur_eine_gruppe_anlegen(pc):
    login(pc)
    units = _boreas("walhall")
    pc.goto(_page_of(units["walhall"]))
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, CREATE_BUTTON, steps=60)
    _all_visible(stations)
    expect(pc.locator(CREATE_BUTTON)).to_have_text("Gruppe anlegen")
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{_page_of(units['walhall'])}anlegen/")
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    field = pc.get_by_label("Name (Pflicht)")
    expect(field).to_be_focused()
    assert run_axe(pc) == []
    field.press_sequentially("Sippe Kraniche")
    # Enter im Feld schickt den Dialog ab, obwohl das Feld über sein Attribut „form“ zum Knopf gehört.
    pc.keyboard.press("Enter")

    pc.wait_for_url(_page_of(units["walhall"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Sippe Kraniche ist angelegt.")
    expect(pc.locator('[aria-labelledby="h-darunter"]')).to_contain_text("Sippe Kraniche")
    assert "Sippe Kraniche" in _children(units["walhall"])
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []


def test_am_pc_nur_mit_der_tastatur_umbenennen_und_doppelten_namen_sehen(pc):
    login(pc)
    units = _boreas("walhall")
    pc.goto(_page_of(units["falken"]))
    expect(pc.locator(PEN)).to_have_accessible_name("Sippe Falken bearbeiten")

    stations = _stations_to_element(pc, PEN, steps=40)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(f"{_page_of(units['falken'])}bearbeiten/")
    dialog = _dialog(pc)
    expect(dialog.locator("h2")).to_have_text("Sippe Falken bearbeiten")
    field = pc.get_by_label("Name (Pflicht)")
    expect(field).to_have_value("Sippe Falken")
    expect(field).to_be_focused()
    # Ring und Schalter hat nur die Bundesleitung, und nur beim Stamm oder beim Bund.
    expect(dialog.locator('input[type="radio"]')).to_have_count(0)
    expect(dialog.locator(SWITCH)).to_have_count(0)
    assert run_axe(pc) == []

    field.fill("Sippe Habichte")
    stations = _stations_to_element(pc, "dialog .btn-primary", steps=10)
    _all_visible(stations)
    expect(pc.locator("dialog .btn-primary")).to_have_text("Speichern")
    pc.keyboard.press("Enter")
    pc.wait_for_url(_page_of(units["falken"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Sippe Falken heißt jetzt Sippe Habichte.")
    expect(pc.locator("h1")).to_have_text("Sippe Habichte")

    pc.goto(f"{_page_of(units['walhall'])}anlegen/")
    pc.get_by_label("Name (Pflicht)").fill(" sippe habichte ")
    pc.keyboard.press("Enter")
    expect(_dialog(pc).locator(".invalid-feedback")).to_have_text("Die Gruppe ‚Sippe Habichte‘ gibt es in Walhall schon.")
    assert run_axe(pc) == []


def test_am_pc_leerer_name_zeigt_die_meldung_des_tools_statt_der_blase_des_browsers(pc):
    """#296, N1 (Knopf „Anlegen“) und N2 (Enter im Feld „Name“ beim Bearbeiten): Der Browser hält das leere
    Pflichtfeld nicht selbst an; die Meldung des Tools steht rot unter dem Feld und ist mit ihm verbunden."""
    login(pc)
    units = _boreas("walhall")

    pc.goto(f"{_page_of(units['walhall'])}anlegen/")
    pc.locator("dialog .btn-primary").click()
    pc.wait_for_url(f"{_page_of(units['walhall'])}anlegen/")
    field = pc.get_by_label("Name (Pflicht)")
    expect(_dialog(pc).locator(".invalid-feedback")).to_have_text("Der Name darf nicht leer sein.")
    expect(field).to_have_attribute("aria-invalid", "true")
    # Die Meldung steht zuerst in der Beschreibung des Feldes, danach die Zahl der Zeichen.
    expect(field).to_have_accessible_description(re.compile(r"^Der Name darf nicht leer sein\."))
    assert _children(units["walhall"]) == {"Sippe Falken"}
    assert run_axe(pc) == []

    pc.goto(f"{_page_of(units['falken'])}bearbeiten/")
    field = pc.get_by_label("Name (Pflicht)")
    field.fill("")
    field.press("Enter")
    expect(_dialog(pc).locator(".invalid-feedback")).to_have_text("Der Name darf nicht leer sein.")
    expect(field).to_have_attribute("aria-invalid", "true")
    expect(_dialog(pc).locator("h2")).to_have_text("Sippe Falken bearbeiten")
    assert Unit.objects.get(pk=units["falken"].pk).name == "Sippe Falken"


def test_am_pc_escape_fuehrt_zurueck_und_legt_nichts_an(pc):
    login(pc)
    units = _boreas("walhall")

    pc.goto(f"{_page_of(units['walhall'])}anlegen/")
    pc.get_by_label("Name (Pflicht)").fill("Sippe Eulen")
    pc.keyboard.press("Escape")
    pc.wait_for_url(_page_of(units["walhall"]))
    expect(_dialog(pc)).to_have_count(0)
    assert "Sippe Eulen" not in _children(units["walhall"])


def test_am_handy_nur_mit_der_tastatur_und_mit_wortvorschlag_anlegen(handy):
    login(handy)
    units = _boreas("walhall")
    handy.goto(_page_of(units["walhall"]))
    _no_side_scroll(handy)
    expect(handy.locator(PEN)).to_have_accessible_name("Stamm Walhall bearbeiten")
    expect(handy.locator(PEN)).to_be_in_viewport()

    stations = _stations_to_element(handy, CREATE_BUTTON, steps=60)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{_page_of(units['walhall'])}anlegen/")
    expect(_dialog(handy)).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    field = handy.get_by_label("Name (Pflicht)")
    # Wie am Handy: ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; danach muss alles stehen bleiben.
    _type_like_a_phone(field, "Sippe", " Kran", " Kraniche", "")
    expect(field).to_have_value("Sippe Kraniche")
    expect(_dialog(handy).locator(".a-zeichenzahl")).to_contain_text("14/100")

    stations = _stations_to_element(handy, "dialog .btn-primary", steps=10)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(_page_of(units["walhall"]))
    expect(handy.locator(".a-kurz")).to_contain_text("Sippe Kraniche ist angelegt.")
    _no_side_scroll(handy)
    assert "Sippe Kraniche" in _children(units["walhall"])


def test_am_pc_ringe_einfuehren_und_am_handy_mit_der_tastatur_den_ring_wechseln(pc, handy):
    login(pc)
    units = _boreas("boreas")
    pc.goto(_page_of(units["boreas"]))
    pc.locator(PEN).click()
    pc.wait_for_url(f"{_page_of(units['boreas'])}bearbeiten/")
    switch = pc.locator(SWITCH)
    expect(switch).to_have_accessible_name("Hat Ringe")
    expect(switch).not_to_be_checked()
    expect(switch).to_be_enabled()
    assert run_axe(pc) == []
    # Mit der Tastatur: Tab bis zum Schalter, Leertaste schaltet ihn ein; der Fokus ist zu sehen.
    stations = _stations_to_element(pc, SWITCH, steps=10)
    _all_visible(stations)
    pc.keyboard.press(" ")
    expect(switch).to_be_checked()
    pc.locator("dialog .btn-primary").click()

    # Vor dem Speichern die Rückfrage aus O8; erst sie führt die Ringe ein.
    dialog = _dialog(pc)
    expect(dialog.locator("h2")).to_have_text("Ringe für Pfadfinderbund Boreas einführen?")
    expect(dialog).to_contain_text("Zurücknehmen lässt sich das vorerst nicht.")
    assert not Unit.objects.get(pk=units["boreas"].pk).has_rings
    assert run_axe(pc) == []
    dialog.locator(".btn-primary").click()
    pc.wait_for_url(_page_of(units["boreas"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Pfadfinderbund Boreas hat jetzt Ringe.")
    expect(pc.locator(CREATE_BUTTON)).to_have_text("Ring anlegen")

    # Danach steht der Schalter eingeschaltet und gesperrt da (EH-25).
    pc.goto(f"{_page_of(units['boreas'])}bearbeiten/")
    expect(pc.locator(SWITCH)).to_be_checked()
    expect(pc.locator(SWITCH)).to_be_disabled()
    expect(_dialog(pc)).to_contain_text("Ausschalten lässt sich das vorerst nicht.")
    nord = unit(U.RING, "Nord", units["boreas"])
    unit(U.RING, "Süd", units["boreas"])

    login(handy)
    handy.goto(_page_of(units["walhall"]))
    _no_side_scroll(handy)
    stations = _stations_to_element(handy, PEN, steps=40)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{_page_of(units['walhall'])}bearbeiten/")
    dialog = _dialog(handy)
    expect(dialog).to_be_visible()
    _no_side_scroll(handy)
    expect(dialog.locator("legend")).to_be_visible()
    expect(dialog.locator("legend")).to_have_text("Ring")
    # Die Überschrift „Ring“ sieht aus wie die Beschriftung „Name“ darüber, nicht wie eine große Überschrift.
    style = "e => [getComputedStyle(e).fontSize, getComputedStyle(e).fontWeight]"
    assert dialog.locator("legend").evaluate(style) == dialog.locator('label[for="id_name"]').evaluate(style)
    expect(handy.get_by_label("ohne Ring (bisher)")).to_be_checked()
    assert run_axe(handy) == []

    # Mit der Tastatur: Tab bis zur gewählten Möglichkeit, Pfeil nach unten wählt Ring Nord.
    stations = _stations_to_element(handy, 'dialog input[type="radio"]:checked', steps=10)
    _all_visible(stations)
    handy.keyboard.press("ArrowDown")
    expect(handy.get_by_label("Ring Nord")).to_be_checked()
    stations = _stations_to_element(handy, "dialog .btn-primary", steps=10)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(_page_of(units["walhall"]))
    expect(handy.locator(".a-kurz")).to_contain_text("Stamm Walhall gehört jetzt zu Ring Nord.")
    assert Unit.objects.get(pk=units["walhall"].pk).parent_id == nord.pk


def test_ohne_skript_legt_der_knopf_die_gruppe_an(pc_ohne_skript):
    page = pc_ohne_skript
    login(page)
    units = _boreas("walhall")
    page.goto(f"{_page_of(units['walhall'])}anlegen/")

    page.get_by_label("Name (Pflicht)").fill("Meute Wölfe")
    page.locator("dialog .btn-primary").click()

    page.wait_for_url(_page_of(units["walhall"]))
    expect(page.locator("[data-kurz]")).to_contain_text("Meute Wölfe ist angelegt.")
    assert "Meute Wölfe" in _children(units["walhall"])
