"""Rauchtest der mitlaufenden Zahl der Zeichen am Fahrtennamen (#215).

Die Nummern verweisen auf Sebastians Szenarien vom 30.10.2026 in #215
(https://github.com/sebivtt/dpv-participant-management/issues/215#issuecomment-6524812974).
Die Zahl schreibt erst das Skript; deshalb lässt sie sich nur im Browser prüfen. Was der Server
ausliefert, prüft tests/test_zeichenzahl.py. Jeder Test läuft in Chromium, Firefox und WebKit
(conftest.py). Alle Konten und Daten sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from accounts.keycloak_abgleich import trimmed
from rauchtests.conftest import BASE, PC, login, run_axe
from rauchtests.test_rauchtest import _press, _set_scout_name, _type_like_a_phone

pytestmark = pytest.mark.django_db(transaction=True)

TOO_LONG = "Dein Fahrtenname darf höchstens 30 Zeichen lang sein."


def _parts(page: Page):
    field = page.get_by_label("Fahrtenname", exact=True)
    count = page.locator(".a-zeichenzahl")
    message = page.locator("#id_scout_name-fehler")
    return field, count, message


def _to_end(field) -> None:
    """Cursor ans Ende; die Taste „Ende“ tut das am Mac nicht."""
    field.evaluate("el => el.setSelectionRange(el.value.length, el.value.length)")


def _shows(count, number: int) -> None:
    """Sichtbar „12/30“, Vorleseprogramme hören „12 von 30 Zeichen“."""
    expect(count).to_be_visible()
    expect(count.locator("[aria-hidden='true']")).to_have_text(f"{number}/30")
    expect(count.locator(".sr-nur")).to_have_text(f"{number} von 30 Zeichen")


def _red(page: Page, count) -> bool:
    """Rot heißt: dieselbe Farbe wie der Fehler am Feld."""
    red = page.evaluate("""() => { const e = document.createElement('div'); e.className = 'invalid-feedback';
        document.querySelector('[data-antippfeld]').appendChild(e); const c = getComputedStyle(e).color; e.remove(); return c; }""")
    return count.evaluate("e => getComputedStyle(e).color") == red


# Szenarien 1 bis 8 und 12, am PC und am Handy
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_zahl_beim_tippen_zu_lang_speichern_und_verwerfen(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    page.goto(f"{BASE}/profil/")
    field, count, message = _parts(page)

    # Im Ruhezustand keine Zahl.
    expect(count).to_be_hidden()
    # Szenario 1: leer geöffnet „0/30“, unten rechts unter der Eingabe.
    _press(page, page.locator("[data-oeffnen]"), device)
    _shows(count, 0)
    group = page.locator(".a-antippfeld-gruppe").bounding_box()
    place = count.bounding_box()
    assert place["y"] >= group["y"] + group["height"] - 1, (group, place)
    assert abs((place["x"] + place["width"]) - (group["x"] + group["width"])) <= 1, (group, place)
    # Die Knöpfe „Verwerfen“ und „Speichern“ verdecken die Zahl nicht.
    buttons = page.locator(".a-antippfeld-knoepfe").bounding_box()
    assert buttons["y"] >= place["y"] + place["height"] - 1, (place, buttons)
    expect(field).to_have_accessible_description("0 von 30 Zeichen")

    # Szenario 2: „Kiwi“ ergibt „4/30“; gespeichert, in Ruhe keine Zahl.
    field.press_sequentially("Kiwi")
    _shows(count, 4)
    assert not _red(page, count)
    _press(page, page.get_by_role("button", name="Speichern"), device)
    expect(page.locator("main .a-meldung.ist-erfolg")).to_contain_text("Dein Fahrtenname ist gespeichert.")
    expect(count).to_be_hidden()

    # Szenario 3: wieder geöffnet „4/30“.
    _press(page, page.get_by_role("button", name="Fahrtenname bearbeiten: Kiwi"), device)
    _shows(count, 4)

    # Szenario 4: genau 30 Zeichen, nicht rot, keine Meldung.
    field.fill("K" * 30)
    _shows(count, 30)
    assert not _red(page, count)
    expect(message).to_have_count(0)

    # Szenario 5: das 31. Zeichen; rot, sofort die Meldung darunter, der Text bleibt ganz.
    _to_end(field)
    field.press_sequentially("K")
    _shows(count, 31)
    assert _red(page, count)
    expect(message).to_have_text(TOO_LONG)
    expect(message).to_be_visible()
    expect(field).to_have_value("K" * 31)
    expect(field).to_have_attribute("aria-invalid", "true")
    assert message.bounding_box()["y"] >= count.bounding_box()["y"] + count.bounding_box()["height"] - 1
    assert page.locator(".a-antippfeld-knoepfe").bounding_box()["y"] >= message.bounding_box()["y"]
    assert run_axe(page) == []

    # Szenario 6: ein Zeichen gelöscht, wieder normal, die Meldung verschwindet.
    field.press("Backspace")
    _shows(count, 30)
    assert not _red(page, count)
    expect(message).to_have_count(0)
    expect(field).not_to_have_attribute("aria-invalid", "true")
    expect(field).to_have_accessible_description("30 von 30 Zeichen")

    # Szenario 7: 70 Zeichen eingefügt; alle stehen im Feld.
    pasted = ("Sturmvogel " * 7)[:70]
    field.fill("")
    field.evaluate(
        """(el, text) => {
            el.dispatchEvent(new InputEvent('beforeinput', {inputType: 'insertFromPaste', data: text, bubbles: true, cancelable: true}));
            el.value = text;
            el.dispatchEvent(new InputEvent('input', {inputType: 'insertFromPaste', data: text, bubbles: true}));
        }""",
        pasted,
    )
    expect(field).to_have_value(pasted)
    _shows(count, 70)
    assert _red(page, count)
    expect(message).to_have_text(TOO_LONG)

    # Szenario 8: Speichern bleibt möglich, nichts wird gespeichert, das Feld kommt offen zurück.
    speichern = page.get_by_role("button", name="Speichern")
    expect(speichern).to_be_enabled()
    if device == "handy":
        _press(page, speichern, device)
    else:
        field.press("Enter")
    expect(field).to_be_visible()
    expect(field).to_have_value(pasted)
    _shows(count, 70)
    assert _red(page, count)
    expect(message).to_have_count(1)
    expect(message).to_have_text(TOO_LONG)
    expect(field).to_have_accessible_description(f"{TOO_LONG} 70 von 30 Zeichen")
    assert get_user_model().objects.get(username="erika.testfrau").scout_name == "Kiwi"
    assert run_axe(page) == []

    # Wieder kurz genug: auch die Meldung vom Server verschwindet.
    field.fill("Kiwi")
    _shows(count, 4)
    expect(message).to_have_count(0)

    # Szenario 12: Verwerfen (am PC mit Esc); Zahl und Meldung weg, wieder geöffnet passend zum gespeicherten Namen.
    field.fill("K" * 40)
    expect(message).to_be_visible()
    if device == "handy":
        _press(page, page.get_by_role("button", name="Verwerfen"), device)
    else:
        page.keyboard.press("Escape")
    expect(count).to_be_hidden()
    expect(message).to_have_count(0)
    _press(page, page.get_by_role("button", name="Fahrtenname bearbeiten: Kiwi"), device)
    _shows(count, 4)
    assert not _red(page, count)

    # Der Knopf × öffnet das Feld leer: „0/30“.
    _press(page, page.get_by_role("button", name="Verwerfen"), device)
    _press(page, page.get_by_role("button", name="Fahrtenname leeren"), device)
    _shows(count, 0)


# Szenarien 9 und 10, dazu der Hinweis aus #214: gezählt wird genau wie auf dem Server
@pytest.mark.parametrize(
    "value",
    [
        "  Kiwi ",  # Szenario 9: Leerzeichen am Rand zählen nicht
        "Kiwi 🥝",  # Szenario 10: ein Emoji zählt als ein Zeichen
        "Müller",  # zerlegt geschriebener Umlaut: zwei Zeichen wie in Prüfung und Datenbank
        " ​Kiwi⁠　",  # unsichtbare Leerzeichen am Rand (#77)
        "\x1cKiwi\x85",  # Leerraum, den Python kennt, JavaScript aber nicht von selbst
        "Kleiner  Bär",  # innen zählt alles
        "​​",  # nur Unsichtbares: null
    ],
)
def test_zaehlt_wie_der_server(pc, value):
    login(pc)
    pc.goto(f"{BASE}/profil/")
    pc.locator("[data-oeffnen]").click()
    field, count, _ = _parts(pc)

    field.evaluate("(el, text) => { el.value = text; el.dispatchEvent(new Event('input', {bubbles: true})); }", value)

    _shows(count, len(trimmed(value)))


def test_dreissig_zeichen_mit_emoji_gelten_auch_beim_speichern(pc):
    login(pc)
    pc.goto(f"{BASE}/profil/")
    pc.locator("[data-oeffnen]").click()
    field, count, message = _parts(pc)
    value = "K" * 29 + "🥝"

    field.fill(value)
    _shows(count, 30)
    expect(message).to_have_count(0)
    field.press("Enter")
    expect(pc.locator("main .a-meldung.ist-erfolg")).to_contain_text("Dein Fahrtenname ist gespeichert.")
    assert get_user_model().objects.get(username="erika.testfrau").scout_name == value


# Szenario 11: am Handy mit Autokorrektur und Wortvorschlägen
def test_am_handy_stimmt_die_zahl_nach_jedem_vorschlag(handy):
    login(handy)
    handy.goto(f"{BASE}/profil/")
    handy.locator("[data-oeffnen]").tap()
    field, count, message = _parts(handy)

    _type_like_a_phone(field, "Kleiner ", "Bä", "Bär", " vom See")
    expect(field).to_have_value("Kleiner Bär vom See")
    _shows(count, 19)
    _type_like_a_phone(field, " und ", "Sturmvo", "Sturmvogel", "!")
    expect(field).to_have_value("Kleiner Bär vom See und Sturmvogel!")
    _shows(count, 35)
    expect(message).to_have_text(TOO_LONG)


# Szenario 13: die Meldung „zu lang“ wird einmal angesagt, nicht bei jedem Tastendruck
def test_die_meldung_wird_einmal_angesagt(pc):
    login(pc)
    _set_scout_name("K" * 30)
    pc.goto(f"{BASE}/profil/")
    pc.locator("[data-oeffnen]").click()
    field, count, message = _parts(pc)
    _to_end(field)

    field.press_sequentially("K")
    expect(message).to_have_attribute("role", "alert")
    # Weitere Zeichen: dieselbe Meldung bleibt stehen und wird nicht neu eingefügt (sonst neue Ansage).
    message.evaluate("e => { e.dataset.erste = 'ja'; }")
    field.press_sequentially("KKK")
    _shows(count, 34)
    expect(message).to_have_count(1)
    expect(message).to_have_attribute("data-erste", "ja")
    # Die Zahl selbst wird nicht angesagt: keine Live-Region um sie herum.
    assert count.evaluate("e => !e.closest('[aria-live], [role=status], [role=alert], [role=log]')")
    expect(field).to_have_accessible_description(f"{TOO_LONG} 34 von 30 Zeichen")


# Szenario 14: ohne Skript keine Zahl; der Fehler kommt erst beim Speichern
def test_ohne_skript_keine_zahl(pc, browser):
    login(pc)
    context = browser.new_context(java_script_enabled=False, storage_state=pc.context.storage_state(), **PC)
    page = context.new_page()
    try:
        page.goto(f"{BASE}/profil/")
        field, count, message = _parts(page)
        field.fill("K" * 31)
        expect(count).to_be_hidden()
        expect(message).to_have_count(0)
        page.get_by_role("button", name="Speichern").click()
        expect(message).to_have_text(TOO_LONG)
        expect(count).to_be_hidden()
    finally:
        context.close()


# Szenario 16: der Bausteinkatalog zeigt das Feld zum Antippen mit Zahl
def test_der_katalog_zeigt_die_zahl(pc, settings):
    settings.BUILDING_BLOCKS_VISIBLE = True
    login(pc)
    pc.goto(f"{BASE}/bausteine/")
    section = pc.locator("section[aria-labelledby='h-antippfeld']")
    section.get_by_role("button", name="Fahrtenname bearbeiten: Kiwi").click()
    _shows(section.locator(".a-zeichenzahl"), 4)
