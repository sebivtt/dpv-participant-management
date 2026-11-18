"""Rauchtest „Adressfeld mit Adresssuche“ im Browser (#163, A10, G7): am PC und am Handy, je nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und ist Mitglied der Sippe Falken, hat also eine
Zuordnung (VA-01, VA-07). „Heute“ ist der 05.01.2028 wie in den Szenarien zu #379 und #380; der Server läuft im selben
Prozess wie der Test, der Suchdienst von OpenStreetMap ist nachgestellt (`tests/adresssuche_fake.py`). Geprüft werden
die Teile, die nur ein Browser zeigt: Suchen, Treffer übernehmen und Speichern nur mit der Tastatur, in Schritt 1 und
im Dialog des Stifts; am Handy die Felder wie mit Autokorrektur und Wortvorschlägen getippt, alle Felder untereinander
und die Meldung unter der PLZ in einer Zeile; das Bundesland verschwindet bei einem anderen Land als Deutschland, auch
ohne Skript; nichts steht seitlich über, der Fokus ist zu sehen, und die Seiten bestehen die Prüfung auf
Barrierefreiheit. Die Regeln selbst prüft tests/test_adressfeld.py. Alle Namen und Adressen sind erfunden; „Burg
Ludwigstein“ stammt aus dem Zielbild (#356).
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Page, expect

from events.models import Event
from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone
from rauchtests.test_veranstaltungen import _dialog, _erika_in_den_falken

LIST = f"{BASE}/veranstaltungen/"
CREATE = f"{LIST}erstellen/"
STEP = "form#f-schritt"
FIELD = ".a-adressfeld"
SEARCH = f"{FIELD} button.a-adresse-suchen"
TAKE = f"{FIELD} .a-treffer button"
NEXT = f'{STEP} .a-schritt-rechts button[type="submit"]'
TILE = '[aria-labelledby="h-grunddaten"]'


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2028, 1, 5))


def _zu(page: Page, selector: str, steps: int = 30) -> None:
    """Mit Tab zum Element und Enter; jede Station hat einen sichtbaren Fokus."""
    stations = _stations_to_element(page, selector, steps=steps)
    _all_visible(stations)
    page.keyboard.press("Enter")


def _schritt_1(page: Page) -> None:
    page.goto(CREATE)
    expect(page.locator(f"{FIELD} legend")).to_have_text("Adresse")
    page.get_by_label("Name").fill("Pfingstlager 2028")
    page.locator(f'{STEP} input[name="start"]').fill("2028-06-02")
    page.locator(f'{STEP} input[name="end"]').fill("2028-06-05")
    _no_side_scroll(page)
    assert run_axe(page) == []


def _treffer_da(page: Page) -> None:
    """Nach „Adresse suchen“: die Treffer mit Quellenhinweis; der Fokus steht bei den Treffern, nicht oben auf der Seite."""
    expect(page.locator(f"{FIELD} .a-treffer .a-leitung-name")).to_have_text(
        ["Burg Ludwigstein", "Jugendburg Ludwigstein, Parkplatz", "Ludwigsteinstraße"])
    expect(page.locator(f"{FIELD} .a-quelle")).to_have_text("Adressdaten © OpenStreetMap-Mitwirkende")
    assert page.evaluate("() => !!document.activeElement.closest('.a-adressfeld')")
    _no_side_scroll(page)
    assert run_axe(page) == []


def _uebernommen(page: Page) -> None:
    expect(page.locator('input[name="street"]')).to_have_value("Burgweg 1")
    expect(page.locator('input[name="postal_code"]')).to_have_value("99999")
    expect(page.locator('input[name="city"]')).to_have_value("Musterhausen")
    expect(page.locator('select[name="state"]')).to_have_value("HE")
    expect(page.locator('select[name="country"]')).to_have_value("DE")
    expect(page.locator(f"{FIELD} .a-treffer")).to_have_count(0)


def test_am_pc_nur_mit_der_tastatur_suchen_uebernehmen_und_speichern(pc, osm):
    login(pc)
    _erika_in_den_falken()
    _schritt_1(pc)
    pc.locator(f'{STEP} input[name="location"]').focus()
    pc.keyboard.type("Burg Ludwigstein")

    _zu(pc, SEARCH, steps=10)
    pc.wait_for_url(f"{CREATE}adresse-suchen/*")
    _treffer_da(pc)
    _zu(pc, TAKE, steps=5)
    _uebernommen(pc)
    _zu(pc, NEXT, steps=15)

    pc.wait_for_url(f"{LIST}*/anlegen/zusammenfassung/")
    expect(pc.locator(f"{TILE} .a-kalender-ort .a-ort-zeile")).to_have_text(
        ["Burg Ludwigstein", "Burgweg 1", "99999 Musterhausen"])
    _no_side_scroll(pc)
    assert run_axe(pc) == []
    assert Event.objects.get().latitude is not None

    # A7: Auf der Leitungsseite sucht der Dialog des Stifts genauso.
    _zu(pc, NEXT)
    pc.wait_for_url(f"{LIST}*/")
    expect(pc.locator(".a-kopf p")).to_have_text(
        "02.06.2028 bis 05.06.2028 · Burg Ludwigstein, Burgweg 1, 99999 Musterhausen")
    _zu(pc, f"{TILE} a.a-stift", steps=30)
    pc.wait_for_url(f"{LIST}*/bearbeiten/")
    expect(_dialog(pc)).to_be_visible()
    pc.locator('input[name="street"]').fill("")
    pc.locator('input[name="postal_code"]').fill("")
    pc.locator('input[name="city"]').fill("")
    pc.locator('select[name="state"]').select_option("")
    _zu(pc, SEARCH, steps=20)
    pc.wait_for_url(f"{LIST}*/bearbeiten/adresse-suchen/*")
    expect(_dialog(pc)).to_be_visible()
    _treffer_da(pc)
    _zu(pc, TAKE, steps=5)
    pc.wait_for_url(f"{LIST}*/bearbeiten/adresse-suchen/*")
    _uebernommen(pc)
    _zu(pc, 'dialog.a-dialog .a-dialog-fuss button[type="submit"]', steps=20)
    pc.wait_for_url(f"{LIST}*/")
    expect(pc.locator(".a-kurz")).to_contain_text("Die Angaben zu Pfingstlager 2028 sind gespeichert.")


def test_am_handy_nur_mit_der_tastatur_wie_mit_autokorrektur(handy, osm):
    login(handy)
    _erika_in_den_falken()
    _schritt_1(handy)
    location = handy.locator(f'{STEP} input[name="location"]')
    _type_like_a_phone(location, "Burg ", "Ludwig", "Ludwigstein", "")
    expect(location).to_have_value("Burg Ludwigstein")

    # Alle Felder liegen untereinander, auch PLZ und Ort (Zielbild, Handy).
    boxes = [handy.locator(f'{FIELD} [name="{name}"]').bounding_box()
             for name in ("street", "postal_code", "city", "state", "country")]
    assert all(lower["y"] >= upper["y"] + upper["height"] for upper, lower in zip(boxes, boxes[1:], strict=False))
    _no_side_scroll(handy)

    _zu(handy, SEARCH, steps=10)
    handy.wait_for_url(f"{CREATE}adresse-suchen/*")
    _treffer_da(handy)
    _zu(handy, TAKE, steps=5)
    _uebernommen(handy)

    # G5: Die Meldung unter der PLZ passt in eine Zeile.
    street = handy.locator('input[name="street"]')
    street.fill("")
    _type_like_a_phone(street, "Burgweg ", "1", "1a", "")
    expect(street).to_have_value("Burgweg 1a")
    handy.locator('input[name="postal_code"]').fill("9999")
    _zu(handy, NEXT, steps=15)
    error = handy.locator(f"{FIELD} .invalid-feedback")
    expect(error).to_have_text("Bitte gib 5 Ziffern ein.")
    lines = error.evaluate("e => Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight))")
    assert lines == 1
    expect(street).to_have_value("Burgweg 1a")
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    # Enter in einem Feld speichert wie „Weiter“, nicht „Adresse suchen“.
    handy.locator('input[name="postal_code"]').fill("99999")
    handy.locator('input[name="postal_code"]').press("Enter")
    handy.wait_for_url(f"{LIST}*/anlegen/zusammenfassung/")
    expect(handy.locator(f"{TILE} .a-kalender-ort .a-ort-zeile")).to_have_text(
        ["Burg Ludwigstein", "Burgweg 1a", "99999 Musterhausen"])
    assert Event.objects.get().latitude is None


@pytest.mark.parametrize("device", ["pc", "pc_ohne_skript"])
def test_g7_bei_schweden_verschwindet_das_bundesland(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    _erika_in_den_falken()
    page.goto(CREATE)
    state = page.locator(f'{FIELD} select[name="state"]')

    expect(state).to_be_visible()
    page.locator(f'{FIELD} select[name="country"]').select_option("SE")
    expect(state).to_be_hidden()
    page.locator(f'{FIELD} select[name="country"]').select_option("DE")
    expect(state).to_be_visible()


def test_ohne_skript_suchen_und_uebernehmen(pc_ohne_skript, osm):
    """A9 im Browser: Ohne Skript kommt die Seite mit den Treffern und allen Eingaben zurück."""
    page = pc_ohne_skript
    login(page)
    _erika_in_den_falken()
    page.goto(CREATE)
    page.get_by_label("Name").fill("Pfingstlager 2028")
    page.locator(f'{STEP} input[name="start"]').fill("2028-06-02")
    page.locator(f'{STEP} input[name="end"]').fill("2028-06-05")
    page.locator(f'{STEP} input[name="location"]').fill("Burg Ludwigstein")
    page.locator(SEARCH).click()

    expect(page.locator(f"{FIELD} .a-treffer")).to_have_count(3)
    expect(page.get_by_label("Name")).to_have_value("Pfingstlager 2028")
    page.locator(TAKE).first.click()
    expect(page.locator('input[name="city"]')).to_have_value("Musterhausen")
    page.locator(NEXT).click()
    page.wait_for_url(f"{LIST}*/anlegen/zusammenfassung/")
    assert get_user_model().objects.filter(username="erika.testfrau").exists()
    assert Event.objects.get().city == "Musterhausen"


def test_ein_klick_auf_die_adresszeile_uebernimmt_den_treffer(pc, osm):
    """Vorschau (Sebastian, 18.11.2026): nicht nur „Übernehmen“, auch die Zeile selbst übernimmt."""
    login(pc)
    _erika_in_den_falken()
    _schritt_1(pc)
    pc.locator(f'{STEP} input[name="location"]').fill("Burg Ludwigstein")
    pc.locator(SEARCH).click()
    pc.wait_for_url(f"{CREATE}adresse-suchen/")
    # Mit der Maus mitten auf die Adresszeile, wie eine Person; `click()` auf den Text verweigert Playwright, weil die
    # Fläche des Knopfs darüber liegt, und genau das ist gewollt.
    first = pc.locator(f"{FIELD} .a-treffer .a-treffer-ort").first
    first.scroll_into_view_if_needed()
    line = first.bounding_box()
    pc.mouse.click(line["x"] + line["width"] / 2, line["y"] + line["height"] / 2)

    _uebernommen(pc)


def test_die_felder_der_adresse_stehen_dicht(pc):
    """Vorschau (Sebastian, 18.11.2026): die Felder näher zusammen, auch mit Zahl der Zeichen darunter. Runde 2: Die
    Zahl steht unter ihrem Feld, in derselben Zeile wie die Beschriftung des Felds darunter; zwischen Bezeichnung und
    Adresse keine Linie und keine sichtbare Überschrift „Adresse“."""
    login(pc)
    _erika_in_den_falken()
    pc.goto(CREATE)
    pc.locator(f'{FIELD} input[name="street"]').fill("Burgweg 1")
    street = pc.locator(f'{FIELD} input[name="street"]').bounding_box()
    postal = pc.locator(f'{FIELD} input[name="postal_code"]').bounding_box()
    # Die Zahl selbst (der Text); ihr Absatz nimmt keinen Platz ein.
    counter = pc.locator(f"{FIELD} #id_street-zahl span[aria-hidden]").bounding_box()
    label = pc.locator(f'{FIELD} label[for="id_postal_code"]').bounding_box()

    assert postal["y"] - (street["y"] + street["height"]) <= 48
    assert counter["y"] >= street["y"] + street["height"]
    assert abs((counter["y"] + counter["height"] / 2) - (label["y"] + label["height"] / 2)) <= 8
    location = pc.locator('input[name="location"]').bounding_box()
    assert street["y"] - (location["y"] + location["height"]) <= 48
    assert pc.locator(f"{FIELD} legend").evaluate("e => e.getBoundingClientRect().height") <= 1
    assert pc.locator(f"{FIELD} legend").evaluate("e => getComputedStyle(e).borderTopStyle") == "none"
