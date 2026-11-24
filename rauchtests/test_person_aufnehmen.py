"""Rauchtest „Person aufnehmen“ mit der Wahl im Dialog (#298): am PC und am Handy, je einmal nur mit der Tastatur, und ohne Skript.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall, wie Wanda in den
Szenarien; die Sippe Falken hat keine Gruppenleitung, also springt sie dort ein (PA5). Geprüft werden die
Teile, die nur ein Browser zeigt (PA2, PA7, PA9): Die Wahl ist modal, die obere Fläche hat beim Öffnen den
Fokus, Tab erreicht die untere, beide führen zu ihrem Weg, „Zurück“ führt zur Wahl, × und Escape schließen
zur Seite, und danach hat „Person aufnehmen“ wieder den Fokus; am Handy ist der Kopf von „Personen“
einzeilig, nichts steht seitlich über, und ohne Skript geht alles über Links. Die Regeln selbst prüft
tests/test_person_aufnehmen.py. Alle Namen sind erfunden.
"""

from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, expect_modal, login, run_axe, wait_for_page_below
from rauchtests.test_benennen import _walhall_for_erika
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _tab_key

PERSONS = '[aria-labelledby="h-personen"]'
BUTTON = "#person-aufnehmen"
TILES = "dialog .a-wahlflaeche"


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _focused_matches(page: Page, selector: str) -> bool:
    return page.evaluate("s => document.activeElement.matches(s)", selector)


def _focus_visible(page: Page) -> bool:
    return page.evaluate("document.activeElement.matches(':focus-visible')")


def test_am_pc_nur_mit_der_tastatur_beide_wege_zurueck_und_schliessen(pc):
    login(pc)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"
    choice = f"{page_address}person-aufnehmen/"
    pc.goto(page_address)
    expect(pc.locator(f"{PERSONS} .a-flaeche-aktion")).to_have_count(1)
    expect(pc.locator(BUTTON)).to_have_text("Person aufnehmen")

    _all_visible(_stations_to_element(pc, BUTTON, steps=60))
    pc.keyboard.press("Enter")
    pc.wait_for_url(choice)
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    expect_modal(dialog)
    expect(dialog.locator("h2")).to_have_text("Person aufnehmen")
    expect(pc.locator(TILES)).to_have_count(2)
    # PA2: Die obere Fläche hat beim Öffnen den Fokus, Tab erreicht die untere; der Fokus ist zu sehen.
    expect(pc.locator(TILES).first).to_be_focused()
    pc.keyboard.press(_tab_key(pc))
    expect(pc.locator(TILES).nth(1)).to_be_focused()
    assert _focus_visible(pc)
    assert run_axe(pc) == []

    # Untere Fläche: „Verwaltete Person anlegen“; „Zurück“ führt zur Wahl.
    pc.keyboard.press("Enter")
    pc.wait_for_url(f"{page_address}verwaltete-person/anlegen/")
    expect(dialog.locator("h2")).to_have_text("Verwaltete Person anlegen")
    _all_visible(_stations_to_element(pc, 'dialog .a-dialog-fuss a.btn-zart', steps=12))
    pc.keyboard.press("Enter")
    pc.wait_for_url(choice)
    expect(pc.locator(TILES).first).to_be_focused()

    # Obere Fläche: „Person mit Konto aufnehmen“; Escape schließt zur Seite, der Fokus kehrt zum Knopf zurück.
    pc.keyboard.press("Enter")
    pc.wait_for_url(f"{page_address}aufnehmen/")
    expect(dialog.locator("h2")).to_have_text("Person mit Konto aufnehmen")
    expect(dialog.get_by_role("link", name="Zurück")).to_be_visible()
    pc.keyboard.press("Escape")
    wait_for_page_below(pc, page_address, "person-aufnehmen")
    expect(dialog).to_have_count(0)
    assert _focused_matches(pc, BUTTON)

    # Aus der Wahl selbst schließt Escape ebenso zum Knopf.
    pc.keyboard.press("Enter")
    pc.wait_for_url(choice)
    pc.keyboard.press("Escape")
    wait_for_page_below(pc, page_address, "person-aufnehmen")
    assert _focused_matches(pc, BUTTON)


def test_am_pc_mit_der_maus_aufnehmen_und_fokus_danach_auf_dem_knopf(pc):
    login(pc)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"
    pc.goto(page_address)

    pc.locator(BUTTON).click()
    pc.locator(TILES).first.click()
    pc.wait_for_url(f"{page_address}aufnehmen/")
    pc.get_by_label("Mail oder Benutzername").fill("otto.ohne@example.org")
    pc.keyboard.press("Enter")
    _dialog(pc).locator(".a-treffer-knopf button").click()

    wait_for_page_below(pc, page_address, "person-aufnehmen")
    expect(pc.locator(".a-kurz")).to_contain_text("Otto Ohne gehört jetzt zu Sippe Falken.")
    # PA7: auch nach dem Aufnehmen hat „Person aufnehmen“ wieder den Fokus.
    assert _focused_matches(pc, BUTTON)


def test_am_handy_einzeilig_nur_mit_der_tastatur_und_mit_antippen(handy):
    login(handy)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"
    handy.goto(page_address)
    _no_side_scroll(handy)

    # PA9: Der Kopf von „Personen“ ist einzeilig, der Knopf steht neben der Überschrift, nicht darunter.
    title = handy.locator(f"{PERSONS} .a-flaeche-kopf h2").bounding_box()
    button = handy.locator(BUTTON).bounding_box()
    assert button["y"] < title["y"] + title["height"] and title["y"] < button["y"] + button["height"]
    assert button["x"] > title["x"] + title["width"]

    _all_visible(_stations_to_element(handy, BUTTON, steps=60))
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{page_address}person-aufnehmen/")
    expect(handy.locator(TILES).first).to_be_focused()
    _no_side_scroll(handy)
    # Am Handy ohne Pfeil (Nachklärung N5).
    expect(handy.locator("dialog .a-wahlflaeche-pfeil").first).to_be_hidden()
    assert run_axe(handy) == []

    handy.locator(TILES).nth(1).tap()
    handy.wait_for_url(f"{page_address}verwaltete-person/anlegen/")
    _no_side_scroll(handy)
    _dialog(handy).get_by_role("link", name="Zurück").tap()
    handy.wait_for_url(f"{page_address}person-aufnehmen/")
    _dialog(handy).get_by_role("link", name="Schließen").tap()
    wait_for_page_below(handy, page_address, "person-aufnehmen")
    expect(_dialog(handy)).to_have_count(0)


def test_ohne_skript_knopf_beide_flaechen_und_zurueck(pc_ohne_skript):
    page = pc_ohne_skript
    login(page)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"
    page.goto(page_address)

    page.locator(BUTTON).click()
    page.wait_for_url(f"{page_address}person-aufnehmen/**")
    expect(_dialog(page)).to_be_visible()
    page.locator(TILES).nth(1).click()
    page.wait_for_url(f"{page_address}verwaltete-person/anlegen/**")
    expect(_dialog(page).locator("h2")).to_have_text("Verwaltete Person anlegen")
    _dialog(page).get_by_role("link", name="Zurück").click()
    page.wait_for_url(f"{page_address}person-aufnehmen/**")
    page.locator(TILES).first.click()
    page.wait_for_url(f"{page_address}aufnehmen/**")
    expect(_dialog(page).locator("h2")).to_have_text("Person mit Konto aufnehmen")
    _dialog(page).get_by_role("link", name="Schließen").click()
    page.wait_for_url(f"{page_address}#person-aufnehmen")
    expect(_dialog(page)).to_have_count(0)


def test_am_handy_ohne_skript_bedienbar(handy_ohne_skript):
    page = handy_ohne_skript
    login(page)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"
    page.goto(page_address)
    _no_side_scroll(page)

    page.locator(BUTTON).tap()
    page.wait_for_url(f"{page_address}person-aufnehmen/**")
    _no_side_scroll(page)
    page.locator(TILES).first.tap()
    page.wait_for_url(f"{page_address}aufnehmen/**")
    _dialog(page).get_by_role("link", name="Zurück").tap()
    page.wait_for_url(f"{page_address}person-aufnehmen/**")
    expect(page.locator(TILES)).to_have_count(2)


# Anmerkung aus der Vorschau (15.11.2026): Am Handy verdeckte „Person aufnehmen“ Teile des Titels. Seitdem zeigt der
# Knopf in der Überschrift einer Fläche am Handy überall nur das Plus und bleibt in der Zeile; Vorleseprogramme lesen
# weiter seinen Text. Geprüft an allen drei Flächen der Seite von Walhall, auch auf einem sehr schmalen Handy.
HEADS = {"h-leitungen": "Stammesleitung benennen", "h-darunter": "Gruppe anlegen", "h-personen": "Person aufnehmen"}


def _overlap(a: dict, b: dict) -> bool:
    return a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and \
        a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]


def test_am_handy_zeigt_jeder_knopf_im_kopf_nur_das_plus_und_verdeckt_nichts(handy):
    login(handy)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['walhall'].key}/"

    for width in (390, 320):
        handy.set_viewport_size({"width": width, "height": 844})
        handy.goto(page_address)
        _no_side_scroll(handy)
        for heading, label in HEADS.items():
            head = handy.locator(f'[aria-labelledby="{heading}"] .a-flaeche-kopf')
            button = head.locator(".a-flaeche-aktion")
            expect(button).to_have_accessible_name(label)
            expect(button).to_have_text(label)
            box = button.bounding_box()
            # Nur das Plus: ein kleiner Knopf, der Text ist nicht zu sehen.
            assert box["width"] <= 48, (width, label, box)
            assert head.locator(".a-flaeche-aktion-text").evaluate(
                "e => e.getBoundingClientRect().width <= 1"), (width, label)
            # In der Zeile der Überschrift, ohne Titel oder Zahl zu verdecken.
            icon = head.locator(".a-flaeche-ic").bounding_box()
            assert box["y"] < icon["y"] + icon["height"] and icon["y"] < box["y"] + box["height"], (width, label)
            for part in ("h2", ".a-flaeche-zahl"):
                if head.locator(part).count():
                    assert not _overlap(box, head.locator(part).bounding_box()), (width, label, part)
    assert run_axe(handy) == []


def test_am_pc_steht_der_text_im_knopf(pc):
    login(pc)
    units = _walhall_for_erika()
    pc.goto(f"{BASE}/organisation/{units['walhall'].key}/")

    for heading, label in HEADS.items():
        button = pc.locator(f'[aria-labelledby="{heading}"] .a-flaeche-aktion')
        expect(button).to_have_text(label)
        assert button.bounding_box()["width"] > 100, label
