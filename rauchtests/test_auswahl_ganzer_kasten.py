"""Rauchtest: Ein Klick irgendwo in den Kasten einer Möglichkeit wählt sie (#329).

Baustein „Auswahl im Dialog“: Jede Möglichkeit steht in einem eigenen Kasten. Bis #329 wählte nur
ein Klick genau auf den Text oder den runden Knopf; ein Klick auf den Rand des Kastens tat nichts.
Wohin geklickt wird, entscheidet erst der Browser; deshalb lässt es sich nur hier prüfen. Die Nummern
verweisen auf die Szenarien zu #329 (14.11.2026). Geklickt wird wie mit einer echten Maus an eine
Stelle des Bildschirms, nicht auf ein Element. Jeder Test läuft in Chromium, Firefox und WebKit
(conftest.py). Alle Namen sind erfunden.
"""

import pytest
from playwright.sync_api import Locator, Page, expect

from rauchtests.conftest import BASE, focus_visible, login
from rauchtests.test_austragen import EXIT_BUTTON, _expel_dialog, _shown_previews
from rauchtests.test_benennen import _walhall_for_erika
from rauchtests.test_rauchtest import _stations_to_element
from rauchtests.test_verschieben import _membership, _move_dialog, _page_of, _walhall_with_woelfe

# Abstand der Klickstelle vom Rand des Kastens, in Pixeln: innerhalb des Innenabstands (10 Pixel
# oben und unten, 12 rechts), also neben Text und Knopf, aber noch im Kasten.
EDGE = 3


def _box(page: Page, input_selector: str) -> Locator:
    """Der Kasten der Möglichkeit, zu der das Optionsfeld gehört."""
    return page.locator(".a-auswahl-liste li", has=page.locator(input_selector))


def _box_with_label(page: Page, label: str) -> Locator:
    return page.locator(".a-auswahl-liste li", has=page.get_by_label(label, exact=True))


def _point(box: Locator, where: str) -> tuple[float, float]:
    """Eine Stelle am Rand des Kastens, auf der Seite: oben über dem Text, unten unter dem Text, rechts daneben
    oder auf der dünnen Linie, die den Kasten oben begrenzt."""
    box.scroll_into_view_if_needed()
    outer = box.bounding_box()
    text = box.locator("label").bounding_box()
    assert outer and text
    if where == "oben":
        return text["x"] + 5, outer["y"] + EDGE
    if where == "linie":
        return text["x"] + 5, outer["y"]
    if where == "unten":
        return text["x"] + 5, outer["y"] + outer["height"] - EDGE
    assert where == "rechts"
    x = outer["x"] + outer["width"] - EDGE - 2
    assert x > text["x"] + text["width"], "die Stelle liegt nicht rechts neben der Beschriftung"
    return x, outer["y"] + outer["height"] / 2


def _click(page: Page, box: Locator, where: str) -> None:
    x, y = _point(box, where)
    page.mouse.click(x, y)


def _what_is_hit(page: Page, x: float, y: float) -> str:
    """Was an dieser Stelle zuoberst liegt: der Kasten selbst („li“) oder etwas darin."""
    return page.evaluate("([x, y]) => document.elementFromPoint(x, y).tagName.toLowerCase()", [x, y])


def _cursor(page: Page, x: float, y: float) -> str:
    return page.evaluate("([x, y]) => getComputedStyle(document.elementFromPoint(x, y)).cursor", [x, y])


# Szenario 1: Klick oben in den Rand über dem Text; „Verschieben“ verschiebt dorthin (VP-07)
def test_am_pc_klick_oben_in_den_rand_waehlt_und_verschiebt(pc):
    login(pc)
    units = _walhall_with_woelfe()
    pc.goto(_move_dialog(units["walhall"], units["wilma"]))
    pc.get_by_label("Sippe Falken", exact=True).check()

    _click(pc, _box_with_label(pc, "Meute Wölfe"), "oben")
    expect(pc.get_by_label("Meute Wölfe", exact=True)).to_be_checked()

    pc.locator("dialog .btn-primary").click()
    pc.wait_for_url(_page_of(units["walhall"]))
    expect(pc.locator(".a-kurz")).to_contain_text("Wilma Walhall gehört jetzt zu Meute Wölfe.")
    assert _membership(units["wilma"]) == "Meute Wölfe"


# Szenario 2: Klick weit rechts neben dem kurzen Text (VP-07)
def test_am_pc_klick_rechts_neben_den_text_waehlt_und_verschiebt(pc):
    login(pc)
    units = _walhall_with_woelfe()
    pc.goto(_move_dialog(units["walhall"], units["wilma"]))
    expect(pc.get_by_label("Sippe Falken", exact=True)).not_to_be_checked()

    _click(pc, _box_with_label(pc, "Sippe Falken"), "rechts")
    expect(pc.get_by_label("Sippe Falken", exact=True)).to_be_checked()

    # Auch die Linie, die den Kasten begrenzt, gehört zum Kasten (Befund aus der unabhängigen Prüfung).
    _click(pc, _box_with_label(pc, "Meute Wölfe"), "linie")
    expect(pc.get_by_label("Meute Wölfe", exact=True)).to_be_checked()
    _click(pc, _box_with_label(pc, "Sippe Falken"), "rechts")

    pc.locator("dialog .btn-primary").click()
    pc.wait_for_url(_page_of(units["walhall"]))
    assert _membership(units["wilma"]) == "Sippe Falken"


# Szenario 3: Austragen, Klick unten in den Rand von „Ganz austragen“; die Vorschau wechselt (PK-21)
def test_am_pc_austragen_klick_unten_in_den_rand_wechselt_die_vorschau(pc):
    login(pc)
    units = _walhall_for_erika()
    pc.goto(_expel_dialog(pc, units))
    assert "direkt zu Stamm Walhall" in _shown_previews(pc)[0]

    _click(pc, _box(pc, "input[value='ganz']"), "unten")
    expect(pc.locator(".a-auswahl input[value='ganz']")).to_be_checked()
    assert len(_shown_previews(pc)) == 1
    assert "keiner Organisation mehr an" in _shown_previews(pc)[0]


# Szenario 4: „Mein Profil“, Austreten, Klick in den Rand eines Kastens (EP-06)
def test_am_pc_austreten_klick_in_den_rand_waehlt(pc):
    login(pc)
    _walhall_for_erika()
    pc.goto(f"{BASE}/profil/")
    pc.locator(EXIT_BUTTON).click()
    pc.wait_for_url(f"{BASE}/profil/austreten/")
    last = pc.locator(".a-auswahl input").last
    expect(last).not_to_be_checked()

    _click(pc, pc.locator(".a-auswahl-liste li").last, "rechts")
    expect(last).to_be_checked()
    assert "keiner Organisation mehr an" in _shown_previews(pc)[0]


# Szenario 5: nur mit der Tastatur wie bisher; der Fokusrahmen sitzt am runden Knopf
def test_nur_mit_der_tastatur_wechseln_pfeiltasten_und_der_rahmen_sitzt_am_knopf(pc):
    login(pc)
    units = _walhall_with_woelfe()
    pc.goto(_move_dialog(units["walhall"], units["wilma"]))

    _stations_to_element(pc, ".a-auswahl input:checked", steps=10)
    # Der Rahmen gehört dem runden Knopf selbst, nicht dem Kasten oder der Beschriftung.
    station = focus_visible(pc)
    assert station["tag"] == "INPUT" and station["rahmen"] == "selbst", station
    assert station["sichtbar"] and station["kontrast"] >= 3, station
    pc.keyboard.press("ArrowDown")
    falken = pc.get_by_label("Sippe Falken", exact=True)
    expect(falken).to_be_checked()
    expect(falken).to_be_focused()


# Szenario 6: Über dem ganzen Kasten zeigt der Mauszeiger die Hand
def test_ueber_dem_ganzen_kasten_zeigt_der_mauszeiger_die_hand(pc):
    login(pc)
    units = _walhall_with_woelfe()
    pc.goto(_move_dialog(units["walhall"], units["wilma"]))

    box = _box_with_label(pc, "Sippe Falken")
    radio = pc.get_by_label("Sippe Falken", exact=True).bounding_box()
    assert radio
    points = {where: _point(box, where) for where in ("oben", "unten", "rechts", "linie")}
    points["Knopf"] = (radio["x"] + radio["width"] / 2, radio["y"] + radio["height"] / 2)
    for where, (x, y) in points.items():
        pc.mouse.move(x, y)
        assert _cursor(pc, x, y) == "pointer", f"keine Hand {where} im Kasten"


# Szenario 7: Am Handy wählt Antippen irgendwo im Kasten
def test_am_handy_antippen_im_rand_waehlt(handy):
    login(handy)
    units = _walhall_with_woelfe()
    handy.goto(_move_dialog(units["walhall"], units["wilma"]))

    x, y = _point(_box_with_label(handy, "Sippe Falken"), "unten")
    handy.touchscreen.tap(x, y)
    expect(handy.get_by_label("Sippe Falken", exact=True)).to_be_checked()

    x, y = _point(_box_with_label(handy, "Meute Wölfe"), "rechts")
    handy.touchscreen.tap(x, y)
    expect(handy.get_by_label("Meute Wölfe", exact=True)).to_be_checked()


# Szenario 8: ohne Skript genauso
def test_ohne_skript_klick_in_den_rand_waehlt_und_verschiebt(pc_ohne_skript):
    page = pc_ohne_skript
    login(page)
    units = _walhall_with_woelfe()
    page.goto(_move_dialog(units["walhall"], units["wilma"]))

    _click(page, _box_with_label(page, "Sippe Falken"), "oben")
    expect(page.get_by_label("Sippe Falken", exact=True)).to_be_checked()

    page.locator("dialog .btn-primary").click()
    page.wait_for_url(f"{_page_of(units['walhall'])}#abschnitt-personen")
    assert _membership(units["wilma"]) == "Sippe Falken"


# Szenario 9: Ein Klick in die Lücke zwischen zwei Kästen ändert die Wahl nicht
def test_klick_in_die_luecke_zwischen_zwei_kaesten_aendert_nichts(pc):
    login(pc)
    units = _walhall_with_woelfe()
    pc.goto(_move_dialog(units["walhall"], units["wilma"]))
    boxes = pc.locator(".a-auswahl-liste li")
    first, second = boxes.nth(0).bounding_box(), boxes.nth(1).bounding_box()
    assert first and second
    gap_top, gap_bottom = first["y"] + first["height"], second["y"]
    assert gap_bottom - gap_top >= 4, "keine Lücke zwischen den Kästen"
    before = [box.locator("input").is_checked() for box in boxes.all()]

    x, y = first["x"] + first["width"] / 2, (gap_top + gap_bottom) / 2
    assert _what_is_hit(pc, x, y) == "ul", "die Lücke gehört zu einem Kasten"
    pc.mouse.click(x, y)
    assert [box.locator("input").is_checked() for box in boxes.all()] == before


# Szenario 10: im Bausteinkatalog genauso, mit Vorschau
@pytest.mark.bausteinkatalog
def test_im_bausteinkatalog_klick_in_den_rand_waehlt(pc):
    login(pc)
    pc.goto(f"{BASE}/bausteine/")
    choice = pc.locator("section[aria-labelledby='h-auswahl'] .a-auswahl").first
    boxes = choice.locator(".a-auswahl-liste li")
    expect(boxes.nth(1).locator("input")).not_to_be_checked()

    _click(pc, boxes.nth(1), "unten")
    expect(boxes.nth(1).locator("input")).to_be_checked()
    expect(choice.locator(".a-auswahl-folge").nth(1)).to_be_visible()
    expect(choice.locator(".a-auswahl-folge").nth(0)).to_be_hidden()

    x, y = _point(boxes.nth(0), "rechts")
    assert _cursor(pc, x, y) == "pointer"
    pc.mouse.click(x, y)
    expect(boxes.nth(0).locator("input")).to_be_checked()
