"""Rauchtest „Verschieben“, „Austragen“ und „Verwaltete Person löschen“ im Browser (#118): am PC und am Handy, je nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall; die Sippe Falken hat
keine Gruppenleitung, also springt sie dort ein (EH-18), wie Wanda in V6. Verwaltet sind Paul Probe direkt in
Walhall und Lena Probe „Kiwi“ in der Sippe Falken. Geprüft werden die Teile, die nur ein Browser zeigt: Die
Knöpfe sind mit der Tastatur erreichbar und stehen nebeneinander, ohne seitlich überzustehen; die Dialoge sind
modal, der Knopf „Verwaltete Person löschen“ steht links unten im Dialog „Bearbeiten“, „Nicht löschen“ führt
zurück, die kurze Meldung erscheint, auch ohne Skript, und die Seiten bestehen die Prüfung auf
Barrierefreiheit. Die Regeln selbst prüft tests/test_verwaltete_personen_verschieben.py. Alle Namen sind erfunden.
"""

from datetime import date

from playwright.sync_api import Page, expect

from persons.models import ManagedPerson
from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_benennen import _walhall_for_erika
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element

PERSONS = '[aria-labelledby="h-personen"]'
DELETE = 'dialog a.btn-entfernen'


def _with_managed() -> dict:
    """Erika leitet Walhall und springt für die Falken ein; dazu Paul in Walhall und Lena in den Falken."""
    units = _walhall_for_erika()
    units["paul"] = ManagedPerson.objects.create(first_name="Paul", last_name="Probe", birth_date=date(2012, 9, 3),
                                                 unit=units["walhall"])
    units["lena"] = ManagedPerson.objects.create(first_name="Lena", last_name="Probe", scout_name="Kiwi",
                                                 birth_date=date(2015, 5, 14), unit=units["falken"])
    return units


def _page_of(where) -> str:
    return f"{BASE}/organisation/{where.key}/"


def _managed_address(where, entry, action: str) -> str:
    return f"{_page_of(where)}verwaltete-person/{entry.key}/{action}/"


def _link(entry, action: str) -> str:
    return f'a[href$="/verwaltete-person/{entry.key}/{action}/"]'


def _button(entry, action: str) -> str:
    return f"{PERSONS} {_link(entry, action)}"


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _unit_of(entry) -> str:
    entry.refresh_from_db()
    return entry.unit.name


def test_am_pc_nur_mit_der_tastatur_verschieben_austragen_und_loeschen(pc):
    login(pc)
    units = _with_managed()
    pc.goto(_page_of(units["walhall"]))
    assert run_axe(pc) == []

    # Verschieben: Paul aus Walhall in die Sippe Falken.
    stations = _stations_to_element(pc, _button(units["paul"], "verschieben"), steps=60)
    _all_visible(stations)
    expect(pc.locator(_button(units["paul"], "verschieben"))).to_have_text("Verschieben: Paul Probe")
    pc.keyboard.press("Enter")
    pc.wait_for_url(_managed_address(units["walhall"], units["paul"], "verschieben"))
    dialog = _dialog(pc)
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator(".a-unterzeile")).to_have_text("Paul Probe aus Stamm Walhall")
    assert run_axe(pc) == []
    stations = _stations_to_element(pc, "dialog .btn-primary", steps=10)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(_page_of(units["walhall"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Paul Probe gehört jetzt zu Sippe Falken.")
    assert _unit_of(units["paul"]) == "Sippe Falken"

    # Austragen: Paul aus den Falken wieder nach Walhall.
    pc.goto(_page_of(units["falken"]))
    stations = _stations_to_element(pc, _button(units["paul"], "austragen"), steps=60)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(_managed_address(units["falken"], units["paul"], "austragen"))
    expect(_dialog(pc).locator("h2")).to_have_text("Paul Probe aus Sippe Falken austragen?")
    assert run_axe(pc) == []
    stations = _stations_to_element(pc, "dialog .btn-gefahr", steps=10)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(_page_of(units["falken"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Paul Probe ist aus Sippe Falken ausgetragen.")
    assert _unit_of(units["paul"]) == "Walhall"

    # Löschen: im Dialog „Bearbeiten“ links unten, dann die Rückfrage.
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    stations = _stations_to_element(pc, _button(units["lena"], "bearbeiten"), steps=60)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    expect(_dialog(pc).locator("h2")).to_have_text("Kiwi (Lena Probe) bearbeiten")
    delete = pc.locator(DELETE)
    expect(delete).to_have_text("Verwaltete Person löschen")
    # Links unten: links neben „Abbrechen“ und „Speichern“, auf derselben Höhe.
    footer = pc.locator("dialog .a-dialog-fuss .btn")
    boxes = [footer.nth(index).bounding_box() for index in range(footer.count())]
    assert [box["x"] for box in boxes] == sorted(box["x"] for box in boxes)
    assert boxes[0]["x"] < boxes[1]["x"] - boxes[0]["width"]
    assert run_axe(pc) == []
    stations = _stations_to_element(pc, DELETE, steps=15)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(_managed_address(units["falken"], units["lena"], "loeschen"))
    dialog = _dialog(pc)
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Kiwi (Lena Probe) endgültig löschen?")
    expect(dialog).to_contain_text("Das lässt sich nicht rückgängig machen.")
    expect(dialog.locator(".a-dialog-fuss .btn")).to_have_text(["Nicht löschen", "Endgültig löschen"])
    assert run_axe(pc) == []
    stations = _stations_to_element(pc, "dialog .btn-gefahr", steps=10)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(_page_of(units["falken"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Kiwi (Lena Probe) wurde gelöscht.")
    expect(pc.locator(PERSONS)).not_to_contain_text("Kiwi")
    assert not ManagedPerson.objects.filter(pk=units["lena"].pk).exists()
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []


def test_am_pc_nicht_loeschen_fuehrt_zurueck_und_escape_schliesst(pc):
    login(pc)
    units = _with_managed()

    pc.goto(_managed_address(units["falken"], units["lena"], "loeschen"))
    stations = _stations_to_element(pc, 'dialog .a-dialog-fuss a[href$="/bearbeiten/"]', steps=10)
    expect(pc.locator("dialog .a-dialog-fuss a.btn-zart")).to_have_text("Nicht löschen")
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(_managed_address(units["falken"], units["lena"], "bearbeiten"))
    expect(_dialog(pc).locator("h2")).to_have_text("Kiwi (Lena Probe) bearbeiten")

    pc.goto(_managed_address(units["falken"], units["lena"], "loeschen"))
    pc.keyboard.press("Escape")
    pc.wait_for_url(f"{_page_of(units['falken'])}#bearbeiten-{units['lena'].key}")
    expect(_dialog(pc)).to_have_count(0)
    assert ManagedPerson.objects.filter(pk=units["lena"].pk).exists()


def test_am_handy_nur_mit_der_tastatur_loeschen(handy):
    login(handy)
    units = _with_managed()
    handy.goto(_page_of(units["falken"]))
    _no_side_scroll(handy)
    entry = handy.locator(f"{PERSONS} li", has=handy.locator(_link(units["lena"], "bearbeiten")))
    expect(entry.locator(".btn")).to_have_text(["Bearbeiten: Kiwi", "Austragen: Kiwi"])
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, _button(units["lena"], "bearbeiten"), steps=60)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    expect(_dialog(handy).locator("h2")).to_have_text("Kiwi (Lena Probe) bearbeiten")
    _no_side_scroll(handy)
    stations = _stations_to_element(handy, DELETE, steps=15)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    handy.wait_for_url(_managed_address(units["falken"], units["lena"], "loeschen"))
    expect(_dialog(handy)).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []
    stations = _stations_to_element(handy, "dialog .btn-gefahr", steps=10)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    handy.wait_for_url(_page_of(units["falken"]))
    expect(handy.locator(".a-kurz")).to_contain_text("Kiwi (Lena Probe) wurde gelöscht.")
    _no_side_scroll(handy)
    assert not ManagedPerson.objects.filter(pk=units["lena"].pk).exists()


def test_am_handy_verschieben_ohne_seitliches_ueberstehen(handy):
    login(handy)
    units = _with_managed()
    handy.goto(_page_of(units["walhall"]))
    entry = handy.locator(f"{PERSONS} li", has=handy.locator(_link(units["paul"], "verschieben")))
    expect(entry.locator(".btn")).to_have_text(["Bearbeiten: Paul Probe", "Verschieben: Paul Probe",
                                                "Austragen: Paul Probe"])
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, _button(units["paul"], "verschieben"), steps=60)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(_managed_address(units["walhall"], units["paul"], "verschieben"))
    _no_side_scroll(handy)
    assert run_axe(handy) == []
    stations = _stations_to_element(handy, "dialog .btn-primary", steps=15)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(_page_of(units["walhall"]))
    expect(handy.locator(".a-kurz")).to_contain_text("Paul Probe gehört jetzt zu Sippe Falken.")
    assert _unit_of(units["paul"]) == "Sippe Falken"


def test_ohne_skript_loescht_der_rote_knopf(pc_ohne_skript):
    page = pc_ohne_skript
    login(page)
    units = _with_managed()
    page.goto(_managed_address(units["falken"], units["lena"], "loeschen"))

    page.locator("dialog .btn-gefahr").click()

    page.wait_for_url(_page_of(units["falken"]))
    # Ohne Skript steht die kurze Meldung fest oben auf der Seite (docs/gestaltung.md, „Kurze Meldung“).
    expect(page.locator("[data-kurz]")).to_contain_text("Kiwi (Lena Probe) wurde gelöscht.")
    assert not ManagedPerson.objects.filter(pk=units["lena"].pk).exists()
