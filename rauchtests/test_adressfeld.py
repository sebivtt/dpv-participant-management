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
from rauchtests.conftest import BASE, focus_visible, login, run_axe, ueber_schritt_einladungstext
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

    ueber_schritt_einladungstext(pc)
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

    # Enter im Namen speichert wie „Weiter“; in PLZ und den übrigen Feldern der Suche sucht Enter seit #410 (BA3).
    handy.locator('input[name="postal_code"]').fill("99999")
    handy.get_by_label("Name").press("Enter")
    ueber_schritt_einladungstext(handy)
    expect(handy.locator(f"{TILE} .a-kalender-ort .a-ort-zeile")).to_have_text(
        ["Burg Ludwigstein", "Burgweg 1a", "99999 Musterhausen"])
    assert Event.objects.get().latitude is None


# #400: Am Handy klebt die Kopfleiste oben. Nach „Adresse suchen“ rollte der Browser die Seite zu den Treffern, und wo
# „Straße und Hausnummer“ danach stand, war Zufall, manchmal halb unter der Kopfleiste; axe meldete dann „target-size“.
# Die Tests prüfen die Lage selbst, nicht nur das Ergebnis von axe, damit sie ohne die Behebung zuverlässig rot sind.
_LAGE = """() => {
    const box = e => e.getBoundingClientRect();
    const result = document.querySelector('.a-adressfeld .a-adresse-ergebnis');
    const start = result && (result.querySelector('.a-treffer') || result.firstElementChild);
    return {
        leiste: box(document.querySelector('.a-topbar')).bottom,
        hoehe: window.innerHeight,
        beschriftung: box(document.querySelector('label[for="id_street"]')).top,
        feld: box(document.getElementById('id_street')),
        anfang: start ? box(start) : null,
        fokus: document.activeElement === result ? 'ergebnis' : document.activeElement.id,
    };
}"""


def _bis_zur_suche(page: Page, location: str) -> None:
    login(page)
    _erika_in_den_falken()
    page.goto(CREATE)
    page.locator(f'{STEP} input[name="location"]').fill(location)
    page.locator(f'{STEP} input[name="location"]').focus()
    _zu(page, SEARCH, steps=10)
    page.wait_for_url(f"{CREATE}adresse-suchen/*")
    expect(page.locator(f"{FIELD} .a-adresse-ergebnis")).to_be_focused()


@pytest.mark.parametrize(("location", "start"), [
    ("Burg Ludwigstein", "Burg Ludwigstein"),
    ("Zeltplatz im Nirgendwo", "Keine Adresse gefunden."),
], ids=["s1-treffer", "s2-keine-treffer"])
def test_s1_s2_am_handy_steht_das_adressfeld_nach_der_suche_unter_der_kopfleiste(handy, osm, location, start):
    """#400, S1 und S2: „Straße und Hausnummer“ beginnt direkt unter der Kopfleiste, nichts davon verdeckt; darunter
    stehen Treffer oder Meldung im Bild, und der Fokus liegt bei ihnen."""
    _bis_zur_suche(handy, location)
    expect(handy.locator(f"{FIELD} .a-adresse-ergebnis")).to_contain_text(start)
    lage = handy.evaluate(_LAGE)

    assert lage["leiste"] <= lage["beschriftung"] <= lage["leiste"] + 16, lage
    assert lage["feld"]["top"] >= lage["leiste"] and lage["feld"]["bottom"] <= lage["hoehe"], lage
    assert lage["anfang"]["top"] >= lage["leiste"] and lage["anfang"]["bottom"] <= lage["hoehe"], lage
    assert lage["fokus"] == "ergebnis"
    _no_side_scroll(handy)
    assert run_axe(handy) == []


def test_s3_am_handy_quer_rollt_die_seite_nur_bis_zum_anfang_der_treffer(handy, osm):
    """#400, S3: Passen Adressfeld und Treffer nicht zusammen ins Bild, steht der Anfang der Treffer unten im Bild,
    nicht weiter gerollt; der Fokus ist zu sehen (WCAG 2.4.11)."""
    handy.set_viewport_size({"width": 844, "height": 390})
    _bis_zur_suche(handy, "Burg Ludwigstein")
    lage = handy.evaluate(_LAGE)

    # Die Lage aus S1 ginge hier nicht: Der Anfang der Treffer läge unter dem Bild.
    assert lage["anfang"]["top"] >= lage["leiste"], lage
    assert lage["hoehe"] - 32 <= lage["anfang"]["bottom"] <= lage["hoehe"], lage
    assert lage["fokus"] == "ergebnis"
    assert focus_visible(handy)["sichtbar"]
    _no_side_scroll(handy)
    assert run_axe(handy) == []


def test_s4_am_handy_ist_die_strasse_nach_uebernehmen_ganz_zu_sehen(handy, osm):
    """#400, S4: Nach „Übernehmen“ liegt der Fokus wie bisher auf „Straße und Hausnummer“, und das Feld steht ganz im
    Bild, nicht unter der Kopfleiste."""
    _bis_zur_suche(handy, "Burg Ludwigstein")
    _zu(handy, TAKE, steps=5)
    _uebernommen(handy)
    expect(handy.locator('input[name="street"]')).to_be_focused()
    lage = handy.evaluate(_LAGE)

    assert lage["feld"]["top"] >= lage["leiste"] and lage["feld"]["bottom"] <= lage["hoehe"], lage
    assert lage["beschriftung"] >= lage["leiste"], lage
    _no_side_scroll(handy)
    assert run_axe(handy) == []


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
    ueber_schritt_einladungstext(page)
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


# ---------- Teil B von #398 (#410): Enter sucht, Seite bleibt stehen, „Adresse leeren“ ----------
#
# BA1 bis BA9, BV3, BG1 bis BG5: Szenarien vom 24.11.2026
# (https://github.com/sebivtt/dpv-participant-management/issues/410#issuecomment-7124249280). Was der Server tut, prüft
# tests/test_adressfeld.py.

CLEAR = f"{FIELD} button.a-adresse-leeren"
EDIT_SAVE = 'dialog.a-dialog .a-dialog-fuss button[type="submit"]'
# Wo „Straße und Hausnummer“ steht, im Bild und in der Seite; dazu, ob die Seite seit dem Messen neu geladen wurde.
_STRASSE = """() => {
    const street = document.getElementById('id_street');
    const dialog = street.closest('dialog');
    return {top: street.getBoundingClientRect().top, bottom: street.getBoundingClientRect().bottom,
            y: window.scrollY, innen: dialog ? dialog.scrollTop : null, hoehe: window.innerHeight,
            ende: dialog ? dialog.scrollTop + dialog.clientHeight >= dialog.scrollHeight - 1
                         : window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 1,
            fokus: document.activeElement.id, gleich: window.__gleicheSeite === true};
}"""


def _steht_still(vorher: dict, nachher: dict) -> None:
    """Die Straße steht, wo sie vor dem Klick stand. Ist die Seite kürzer geworden, weil die Treffer weg sind, geht das
    nicht ganz; dann steht die Seite (oder der Dialog) an ihrem Ende, nicht oben, und die Straße ist ganz zu sehen."""
    gleich = abs(nachher["top"] - vorher["top"]) <= 2
    am_ende = nachher["ende"] and 0 <= nachher["top"] and nachher["bottom"] <= nachher["hoehe"]
    assert gleich or am_ende, (vorher, nachher)
    def gerollt(lage: dict) -> float:
        return lage["innen"] if lage["innen"] is not None else lage["y"]

    assert gerollt(nachher) > 0 or gerollt(vorher) == 0, ("wieder oben", vorher, nachher)


def _wanda_in_schritt_1(page: Page, location: str = "Burg Ludwigstein", name: str = "Pfingstlager 2028") -> None:
    login(page)
    _erika_in_den_falken()
    page.goto(CREATE)
    page.get_by_label("Name").fill(name)
    page.locator(f'{STEP} input[name="start"]').fill("2028-06-02")
    page.locator(f'{STEP} input[name="end"]').fill("2028-06-05")
    page.locator(f'{STEP} input[name="location"]').fill(location)


def _im_dialog_des_stifts(page: Page) -> None:
    """Legt das Pfingstlager mit Burg Ludwigstein, ohne Adresse, an und öffnet den Dialog des Stifts."""
    _wanda_in_schritt_1(page)
    page.locator(NEXT).click()
    ueber_schritt_einladungstext(page)
    page.locator(NEXT).click()
    page.wait_for_url(f"{LIST}*/")
    page.goto(f"{page.url}bearbeiten/")
    expect(_dialog(page)).to_be_visible()


def _leer(page: Page) -> None:
    for name in ("street", "postal_code", "city"):
        expect(page.locator(f'input[name="{name}"]')).to_have_value("")
    expect(page.locator('select[name="state"]')).to_have_value("")
    expect(page.locator('select[name="country"]')).to_have_value("DE")
    expect(page.locator('input[name="coordinates"]')).to_have_value("")
    expect(page.locator(f"{FIELD} .a-treffer")).to_have_count(0)
    expect(page.locator(f"{FIELD} .a-meldung")).to_have_count(0)
    expect(page.locator('input[name="location"]')).to_have_value("Burg Ludwigstein")


@pytest.mark.parametrize("field", ["location", "street", "postal_code", "city"])
def test_ba1_ba2_enter_in_bezeichnung_und_adresse_sucht(pc, osm, field):
    """BA1 und BA2: Enter in Bezeichnung, Straße, PLZ oder Ort wirkt wie „Adresse suchen“; nichts ist gespeichert."""
    _wanda_in_schritt_1(pc, location="" if field != "location" else "Burg Ludwigstein")
    if field != "location":
        pc.locator('input[name="street"]').fill("Burgweg 1")
        pc.locator('input[name="city"]').fill("Musterhausen")

    pc.locator(f'{STEP} [name="{field}"]').press("Enter")

    pc.wait_for_url(f"{CREATE}adresse-suchen/")
    expect(pc.locator(f"{FIELD} .a-treffer")).to_have_count(3 if field == "location" else 1)
    expect(pc.locator(f"{FIELD} .a-adresse-ergebnis")).to_be_focused()
    assert Event.objects.count() == 0
    assert len(osm.calls) == 1


def test_ba1_enter_in_der_bezeichnung_sucht_auch_im_dialog_des_stifts(pc, osm):
    _im_dialog_des_stifts(pc)

    pc.locator('input[name="location"]').press("Enter")

    pc.wait_for_url(f"{LIST}*/bearbeiten/adresse-suchen/")
    expect(_dialog(pc)).to_be_visible()
    expect(pc.locator(f"{FIELD} .a-treffer")).to_have_count(3)


@pytest.mark.parametrize("field", ["name", "start", "start_time", "end", "end_time"])
def test_ba3_enter_anderswo_ist_weiter(pc, osm, field):
    _wanda_in_schritt_1(pc)

    pc.locator(f'{STEP} [name="{field}"]').press("Enter")

    ueber_schritt_einladungstext(pc)
    assert osm.calls == []


def test_ba3_enter_im_namen_ist_im_dialog_des_stifts_speichern(pc, osm):
    _im_dialog_des_stifts(pc)
    pc.locator('dialog input[name="name"]').fill("Pfingstlager 28")

    pc.locator('dialog input[name="name"]').press("Enter")

    pc.wait_for_url(f"{LIST}*/")
    expect(pc.locator(".a-kurz")).to_contain_text("Die Angaben zu Pfingstlager 28 sind gespeichert.")
    assert osm.calls == []


def test_bg1_enter_mit_nur_der_strasse_warnt_und_geht_nicht_weiter(pc, osm):
    _wanda_in_schritt_1(pc, location="")
    pc.locator('input[name="street"]').fill("Burgweg")

    pc.locator('input[name="street"]').press("Enter")

    pc.wait_for_url(f"{CREATE}adresse-suchen/")
    expect(pc.locator(f"{FIELD} .a-meldung.ist-warnung")).to_contain_text("Für die Suche gib bitte die Bezeichnung")
    assert osm.calls == []
    assert Event.objects.count() == 0


def test_bg2_enter_in_der_bezeichnung_sucht_auch_ohne_namen(pc, osm):
    _wanda_in_schritt_1(pc, name="")

    pc.locator('input[name="location"]').press("Enter")

    pc.wait_for_url(f"{CREATE}adresse-suchen/")
    expect(pc.locator(f"{FIELD} .a-treffer")).to_have_count(3)
    expect(pc.locator(f"{STEP} .invalid-feedback")).to_have_count(0)


def test_ba4_am_pc_bleibt_die_seite_nach_uebernehmen_stehen(pc, osm):
    """BA4: Die Seite sprang nach „Übernehmen“ an den Anfang (Chrome, Safari), weil der Browser nicht zur Straße rollt,
    wenn sie im Bild ist. Jetzt steht die Straße an derselben Stelle wie vor dem Klick, mit dem Fokus darauf."""
    _wanda_in_schritt_1(pc)
    pc.locator(SEARCH).click()
    pc.wait_for_url(f"{CREATE}adresse-suchen/")
    expect(pc.locator(f"{FIELD} .a-treffer")).to_have_count(3)
    # Wanda rollt bis zu den Treffern ans Ende der Seite; Safari rollt nach der Suche nicht von selbst dorthin.
    pc.evaluate("window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'})")
    vorher = pc.evaluate(_STRASSE)
    assert vorher["y"] > 0, vorher

    pc.locator(TAKE).first.click()
    _uebernommen(pc)
    # Manche Browser stellen die Seite nach dem Laden noch um; gemessen wird, wo sie danach steht.
    pc.wait_for_timeout(500)
    nachher = pc.evaluate(_STRASSE)

    _steht_still(vorher, nachher)
    assert nachher["fokus"] == "id_street"
    assert run_axe(pc) == []


@pytest.mark.parametrize("device", ["pc", "handy"])
def test_ba4_im_dialog_des_stifts_bleibt_die_strasse_im_bild(request, browser_name, osm, device):
    page: Page = request.getfixturevalue(device)
    _im_dialog_des_stifts(page)
    page.locator(SEARCH).click()
    page.wait_for_url(f"{LIST}*/bearbeiten/adresse-suchen/")
    expect(page.locator(f"{FIELD} .a-treffer")).to_have_count(3)
    page.locator(f"{FIELD} .a-quelle").evaluate("e => e.scrollIntoView({block: 'end'})")
    vorher = page.evaluate(_STRASSE)

    page.locator(TAKE).first.focus()
    page.keyboard.press("Enter")
    page.wait_for_url(f"{LIST}*/bearbeiten/adresse-suchen/")
    _uebernommen(page)
    page.wait_for_timeout(500)
    nachher = page.evaluate(_STRASSE)

    assert nachher["fokus"] == "id_street"
    assert 0 <= nachher["top"] and nachher["bottom"] <= nachher["hoehe"], (vorher, nachher)
    if vorher["top"] >= 0:
        _steht_still(vorher, nachher)


def test_ba4_am_handy_steht_die_strasse_nach_uebernehmen_im_bild_und_die_seite_oben_nicht(handy, osm):
    _wanda_in_schritt_1(handy)
    handy.locator(SEARCH).click()
    handy.wait_for_url(f"{CREATE}adresse-suchen/")
    handy.locator(TAKE).first.scroll_into_view_if_needed()

    handy.locator(TAKE).first.click()
    _uebernommen(handy)
    lage = handy.evaluate(_LAGE)

    assert lage["fokus"] == "id_street"
    assert lage["feld"]["top"] >= lage["leiste"] and lage["feld"]["bottom"] <= lage["hoehe"], lage
    assert handy.evaluate("window.scrollY") > 0


@pytest.mark.parametrize("device", ["pc", "handy"])
def test_ba5_bv3_adresse_leeren_mit_skript(request, browser_name, osm, device):
    """BA5 und BV3: „Adresse leeren“ leert die Adresse im Browser, ohne die Seite neu zu laden: Sie bleibt an ihrer
    Stelle, der Fokus liegt auf der Straße, an OpenStreetMap geht nichts; danach geht es gleich wieder zur Suche."""
    page: Page = request.getfixturevalue(device)
    _wanda_in_schritt_1(page)
    page.locator(SEARCH).click()
    page.wait_for_url(f"{CREATE}adresse-suchen/")
    page.locator(TAKE).first.click()
    _uebernommen(page)
    expect(page.locator(CLEAR)).to_be_visible()
    page.evaluate("window.__gleicheSeite = true")
    vorher = page.evaluate(_STRASSE)
    calls = len(osm.calls)

    page.locator(CLEAR).click()

    _leer(page)
    nachher = page.evaluate(_STRASSE)
    assert nachher["gleich"], "die Seite wurde nicht neu geladen"
    _steht_still(vorher, nachher)
    assert nachher["fokus"] == "id_street"
    expect(page.locator(CLEAR)).to_be_hidden()
    assert len(osm.calls) == calls
    assert Event.objects.count() == 0
    _no_side_scroll(page)
    assert run_axe(page) == []

    page.locator(SEARCH).click()
    page.wait_for_url(f"{CREATE}adresse-suchen/")
    expect(page.locator(f"{FIELD} .a-treffer")).to_have_count(3)


@pytest.mark.parametrize("change", [
    ('input[name="street"]', "Burgweg 1"), ('input[name="postal_code"]', "9"), ('input[name="city"]', "M"),
    ('select[name="state"]', "HE"), ('select[name="country"]', "SE"),
], ids=["strasse", "plz", "ort", "bundesland", "land"])
def test_ba7_der_knopf_erscheint_sobald_etwas_in_der_adresse_steht(pc, change):
    _wanda_in_schritt_1(pc)
    expect(pc.locator(CLEAR)).to_be_hidden()

    selector, value = change
    if selector.startswith("select"):
        pc.locator(selector).select_option(value)
    else:
        pc.locator(selector).press_sequentially(value)

    expect(pc.locator(CLEAR)).to_be_visible()
    pc.locator(CLEAR).click()
    expect(pc.locator(CLEAR)).to_be_hidden()


def test_ba6_im_dialog_leeren_und_abbrechen_oder_speichern(pc, osm):
    _im_dialog_des_stifts(pc)
    pc.locator(SEARCH).click()
    pc.wait_for_url(f"{LIST}*/bearbeiten/adresse-suchen/")
    pc.locator(TAKE).first.focus()
    pc.keyboard.press("Enter")
    _uebernommen(pc)
    pc.locator(EDIT_SAVE).click()
    pc.wait_for_url(f"{LIST}*/")
    entry = Event.objects.get()
    assert entry.city == "Musterhausen"
    page_url = pc.url

    pc.goto(f"{page_url}bearbeiten/")
    pc.locator(CLEAR).click()
    _leer(pc)
    pc.locator("dialog .a-dialog-fuss a", has_text="Abbrechen").click()
    pc.wait_for_url(page_url)
    entry.refresh_from_db()
    assert entry.city == "Musterhausen"

    pc.goto(f"{page_url}bearbeiten/")
    pc.locator(CLEAR).click()
    pc.locator(EDIT_SAVE).click()
    pc.wait_for_url(page_url)
    entry.refresh_from_db()
    assert (entry.street, entry.city, entry.country, entry.latitude) == ("", "", "", None)
    assert entry.location == "Burg Ludwigstein"


def test_bg3_leeren_entfernt_die_fehler_an_der_adresse(pc):
    _wanda_in_schritt_1(pc)
    pc.locator('input[name="street"]').fill("Burgweg 1")
    pc.locator('input[name="postal_code"]').fill("9999")
    pc.locator(NEXT).click()
    expect(pc.locator(f"{FIELD} .invalid-feedback")).to_have_text(["Bitte gib 5 Ziffern ein.", "Bitte gib den Ort ein."])

    pc.locator(CLEAR).click()

    expect(pc.locator(f"{FIELD} .invalid-feedback")).to_have_count(0)
    expect(pc.locator(f"{FIELD} .is-invalid")).to_have_count(0)
    expect(pc.locator(f"{FIELD} [aria-invalid]")).to_have_count(0)
    assert pc.locator('input[name="postal_code"]').get_attribute("aria-describedby") in (None, "")
    assert run_axe(pc) == []


def test_bg4_bg5_leeren_geht_auch_ohne_openstreetmap_und_nimmt_die_koordinaten_mit(pc, osm):
    _wanda_in_schritt_1(pc)
    pc.locator(SEARCH).click()
    pc.wait_for_url(f"{CREATE}adresse-suchen/")
    pc.locator(TAKE).first.click()
    _uebernommen(pc)
    osm.failure = TimeoutError()

    pc.locator(CLEAR).click()
    _leer(pc)
    for name, value in (("street", "Burgweg 1"), ("postal_code", "99999"), ("city", "Musterhausen")):
        pc.locator(f'input[name="{name}"]').fill(value)
    pc.locator('select[name="state"]').select_option("HE")
    pc.locator(NEXT).click()

    ueber_schritt_einladungstext(pc)
    entry = Event.objects.get()
    assert (entry.city, entry.latitude) == ("Musterhausen", None)


def _bis_beim_adressfeld(page: Page) -> None:
    """Ohne Skript rollt der Browser weich zur Stelle „#adressfeld“; gewartet wird, bis er dort angekommen ist: das
    Adressfeld oben im Bild, oder am Ende der Seite mit der Straße ganz im Bild. Nie oben auf der Seite."""
    lage, feld = {}, None
    for _ in range(50):
        lage = page.evaluate(_STRASSE)
        feld = page.locator(FIELD).evaluate("e => e.getBoundingClientRect().top")
        if lage["y"] > 0 and (abs(feld) <= 2 or (lage["ende"] and lage["top"] >= 0 and lage["bottom"] <= lage["hoehe"])):
            return
        page.wait_for_timeout(100)
    raise AssertionError(("nicht beim Adressfeld", lage, feld))


def test_ba8_ohne_skript_leeren_und_uebernehmen_bleiben_beim_adressfeld(pc_ohne_skript, osm):
    """BA8: ohne Skript ein gewöhnliches Formular; die Seite steht danach beim Adressfeld, nicht oben. Enter bleibt
    überall „Weiter“."""
    page = pc_ohne_skript
    _wanda_in_schritt_1(page)
    page.locator(SEARCH).click()
    page.wait_for_url(f"{CREATE}adresse-suchen/")
    page.locator(TAKE).first.click()
    page.wait_for_url(f"{CREATE}adresse-suchen/#adressfeld")
    _uebernommen(page)
    # Der Browser rollt weich zum Adressfeld; am Ende der Seite hält er früher an, die Straße ist dann ganz im Bild.
    _bis_beim_adressfeld(page)

    page.locator(CLEAR).click()
    page.wait_for_url(f"{CREATE}adresse-suchen/#adressfeld")
    _leer(page)
    _bis_beim_adressfeld(page)
    expect(page.locator(CLEAR)).to_be_hidden()

    page.locator('input[name="location"]').press("Enter")
    ueber_schritt_einladungstext(page)


def test_ba9_am_handy_sucht_die_eingabetaste_und_leeren_geht_mit_der_tastatur(handy, osm):
    """BA9: am Handy wie mit Autokorrektur und Wortvorschlägen getippt; die Eingabetaste sucht, und „Adresse leeren“
    erreicht man nur mit der Tastatur, mit sichtbarem Fokus."""
    _wanda_in_schritt_1(handy, location="")
    location = handy.locator(f'{STEP} input[name="location"]')
    _type_like_a_phone(location, "Burg ", "Ludwig", "Ludwigstein", "")

    location.press("Enter")

    handy.wait_for_url(f"{CREATE}adresse-suchen/")
    expect(handy.locator(f"{FIELD} .a-treffer")).to_have_count(3)
    _zu(handy, TAKE, steps=5)
    _uebernommen(handy)
    _zu(handy, CLEAR, steps=15)
    _leer(handy)
    expect(handy.locator('input[name="street"]')).to_be_focused()
    street = handy.locator('input[name="street"]')
    _type_like_a_phone(street, "Burgweg ", "1", "1", "")
    handy.locator('input[name="city"]').fill("Musterhausen")
    calls = len(osm.calls)
    street.press("Enter")
    handy.wait_for_url(f"{CREATE}adresse-suchen/")
    # Gesucht wird mit Bezeichnung und Adresse; die erfundenen Antworten kennen diese Verbindung nicht.
    expect(handy.locator(f"{FIELD} .a-adresse-ergebnis")).to_be_visible()
    assert osm.calls[calls]["q"] == "Burg Ludwigstein, Burgweg 1, Musterhausen"


# Befund M1 der unabhängigen Prüfung (#410): Nach „Übernehmen“ stellte das Skript nur das Feld unter die Kopfleiste; seine
# Beschriftung „Straße und Hausnummer“ lag dann verdeckt darunter, wenn die Straße vorher schon unter der Leiste stand.
# „Adresse leeren“ nutzt dieselbe Stelle im Skript; nach „Übernehmen“ ist die Seite aber zu kurz, um die Straße dafür
# unter die Leiste zu rollen, deshalb prüft der Test nur „Übernehmen“.
def test_m1_am_handy_ist_auch_die_beschriftung_der_strasse_zu_sehen(handy, osm):
    _wanda_in_schritt_1(handy)
    handy.locator(SEARCH).click()
    handy.wait_for_url(f"{CREATE}adresse-suchen/")
    # Die Straße liegt jetzt halb unter der Kopfleiste, ihre Beschriftung ganz.
    handy.evaluate("""() => window.scrollTo({top: window.scrollY + document.getElementById('id_street')
        .getBoundingClientRect().top - document.querySelector('.a-topbar').getBoundingClientRect().bottom + 10,
        behavior: 'instant'})""")

    # Ohne dass Playwright vorher selbst rollt, wie ein Tippen auf den Knopf an seiner Stelle.
    handy.locator(TAKE).first.evaluate("e => e.click()")
    _uebernommen(handy)
    lage = handy.evaluate(_LAGE)

    assert lage["fokus"] == "id_street"
    assert lage["beschriftung"] >= lage["leiste"], lage
    assert lage["feld"]["bottom"] <= lage["hoehe"], lage


def test_g3_am_pc_adresse_leeren_nur_mit_der_tastatur(pc, osm):
    """Befund G3 der unabhängigen Prüfung (#410): „Adresse leeren“ auch am PC nur mit der Tastatur, mit sichtbarem
    Fokus auf jeder Station; danach liegt der Fokus auf der Straße."""
    _wanda_in_schritt_1(pc)
    pc.locator(f'{STEP} input[name="location"]').press("Enter")
    pc.wait_for_url(f"{CREATE}adresse-suchen/")
    _zu(pc, TAKE, steps=5)
    _uebernommen(pc)

    _zu(pc, CLEAR, steps=15)

    _leer(pc)
    expect(pc.locator('input[name="street"]')).to_be_focused()
    assert focus_visible(pc)["sichtbar"]
