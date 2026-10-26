"""Rauchtest des Hauptablaufs im Browser: Login, Startseite, Mein Profil, Fahrtenname, Abmelden, Meldungen (#7, #96, #165, #13, #111, #180, NFA-01, NFA-03).

Die Nummern verweisen auf Sebastians Szenarien zu #7 (Planung am 21.10.2026). Jeder Test
läuft in Chromium, Firefox und WebKit (conftest.py). Alle Konten und Daten sind erfunden.
"""

import sys

import pytest
from playwright.sync_api import Page, expect

from django.contrib.auth import get_user_model

from rauchtests.conftest import BASE, OHNE_NAME, PC, focus_visible, login, run_axe
from roles.models import Role
from tests.test_rollen import give, unit
from units.models import Unit

pytestmark = pytest.mark.django_db(transaction=True)


def _on_login_page(page: Page) -> None:
    page.wait_for_url(f"{BASE}/anmelden/**")
    expect(page.get_by_role("button", name="Mit DPV-Konto anmelden")).to_be_visible()


def _password_requested_again(page: Page) -> None:
    """Nach vollständigem Abmelden fragt Keycloak wieder nach dem Passwort (Entscheidung zu #5)."""
    page.get_by_role("button", name="Mit DPV-Konto anmelden").click()
    expect(page.locator("#password")).to_be_visible()


# Szenario 1 und 2
def test_am_pc_seitenleiste_und_abmelden(pc):
    login(pc)

    sidebar = pc.get_by_role("complementary", name="Seitenleiste")
    expect(sidebar).to_be_visible()
    expect(sidebar.get_by_role("link", name="Startseite")).to_have_attribute("aria-current", "page")
    expect(sidebar.get_by_text("Erika", exact=True)).to_be_visible()
    expect(pc.get_by_role("heading", level=1)).to_have_text("Hallo Erika!")
    expect(pc.get_by_role("button", name="Menü")).to_be_hidden()

    sidebar.get_by_role("button", name="Abmelden").click()

    _on_login_page(pc)
    _password_requested_again(pc)


# Szenario 3
def test_am_handy_abmelden_ueber_das_menue(handy):
    login(handy)

    expect(handy.get_by_role("complementary", name="Seitenleiste")).to_be_hidden()
    expect(handy.get_by_role("link", name="Mein Profil")).to_be_visible()
    handy.get_by_role("button", name="Menü").click()
    menu = handy.get_by_role("dialog", name="Menü")
    expect(menu).to_be_visible()
    menu.get_by_role("button", name="Abmelden").click()

    _on_login_page(handy)
    _password_requested_again(handy)


def _tab_key(page: Page) -> str:
    """Die Taste, mit der man von Element zu Element springt.

    Safari und WebKit springen auf dem Mac mit Tab nur zwischen Eingabefeldern, solange die
    Mac-Einstellung „Tastaturnavigation“ aus ist; mit Wahltaste und Tab erreichen sie alles.
    """
    if page.context.browser.browser_type.name == "webkit" and sys.platform == "darwin":
        return "Alt+Tab"
    return "Tab"


def _tab_to(page: Page, text: str, steps: int = 25) -> list[dict]:
    """Drückt Tab, bis der Fokus auf `text` liegt; gibt jede Station mit Sichtbarkeit zurück."""
    stations = []
    for _ in range(steps):
        page.keyboard.press(_tab_key(page))
        station = focus_visible(page)
        stations.append(station)
        if station["text"] == text:
            return stations
    raise AssertionError(f"„{text}“ nach {steps} Mal Tab nicht erreicht: {[s['text'] for s in stations]}")


def _all_visible(stations: list[dict]) -> None:
    hidden = [s for s in stations if not s["sichtbar"] or s["kontrast"] < 3]
    assert not hidden, f"Fokus nicht oder zu schwach zu sehen bei: {hidden}"


# Szenario 4, am PC
def test_nur_mit_der_tastatur_am_pc(pc):
    pc.goto(f"{BASE}/")
    stations = _tab_to(pc, "Mit DPV-Konto anmelden")
    pc.keyboard.press("Enter")
    # Erst tippen, wenn Keycloak seine Seite fertig geladen hat, wie eine Person auch. Sonst
    # ging in WebKit manchmal der erste Buchstabe verloren (#33).
    pc.locator("#username").wait_for()
    pc.wait_for_load_state("load")
    pc.keyboard.type("erika.testfrau")
    expect(pc.locator("#username"), "Benutzername nicht vollständig im Feld").to_have_value("erika.testfrau")
    pc.keyboard.press(_tab_key(pc))
    pc.keyboard.type("testpasswort-erika")
    pc.keyboard.press("Enter")
    pc.wait_for_url(f"{BASE}/")

    first = _tab_to(pc, "Zum Inhalt springen", steps=1)
    stations += first + _tab_to(pc, "Abmelden")
    _all_visible(stations)
    order = [s["text"] for s in stations]
    assert order.index("Startseite") < order.index("Abmelden"), order
    pc.keyboard.press("Enter")

    _on_login_page(pc)


# Szenario 4, am Handy: das Menü
def test_nur_mit_der_tastatur_am_handy_menue_auf_und_zu(handy):
    login(handy)
    menu = handy.get_by_role("dialog", name="Menü")

    stations = _tab_to(handy, "Menü")
    handy.keyboard.press("Enter")
    expect(menu).to_be_visible()
    assert handy.evaluate("document.getElementById('menue').contains(document.activeElement)")
    handy.keyboard.press("Escape")
    expect(menu).to_be_hidden()
    assert focus_visible(handy)["text"] == "Menü", "nach dem Schließen steht der Fokus nicht wieder auf „Menü“"

    handy.keyboard.press("Enter")
    stations += _tab_to(handy, "Abmelden")
    _all_visible(stations)
    handy.keyboard.press("Enter")

    _on_login_page(handy)


# Szenario 4, Musterseite: auch Bausteine wie „Veranstaltung erstellen“ zeigen den Fokus deutlich
def test_nur_mit_der_tastatur_auf_der_musterseite(pc):
    login(pc)
    pc.goto(f"{BASE}/muster/")

    stations = _tab_to(pc, "Zum Inhalt springen", steps=1) + _tab_to(pc, "Veranstaltung erstellen", steps=30)

    _all_visible(stations)


# Szenario 3: Menü schließt auch per Knopf und beim Antippen daneben
def test_handy_menue_schliesst_per_knopf_und_beim_antippen_daneben(handy):
    login(handy)
    menu = handy.get_by_role("dialog", name="Menü")

    handy.get_by_role("button", name="Menü").click()
    menu.get_by_role("button", name="Menü schließen").click()
    expect(menu).to_be_hidden()

    handy.get_by_role("button", name="Menü").click()
    expect(menu).to_be_visible()
    width = menu.bounding_box()["width"]
    handy.mouse.click(width + 20, 400)
    expect(menu).to_be_hidden()


# Blöcke: ein Klick irgendwo auf den Block führt zum Ziel
def test_klick_irgendwo_auf_einen_block_fuehrt_zum_ziel(pc):
    login(pc)
    pc.goto(f"{BASE}/muster/")

    # Wie eine Person auf die Stelle klicken: Über dem Block liegt absichtlich die Klickfläche des Links.
    def click_on(locator) -> None:
        box = locator.bounding_box()
        pc.mouse.click(box["x"] + 5, box["y"] + box["height"] / 2)

    click_on(pc.locator(".a-event").first.locator(".a-meta"))
    pc.wait_for_url(f"{BASE}/muster/#inhalt")
    pc.goto(f"{BASE}/muster/")
    click_on(pc.locator(".a-meldungen li").first.locator("span").first)
    pc.wait_for_url(f"{BASE}/muster/#h-kommend", timeout=3000)


# Szenario 5
def test_ohne_namen_personensymbol_im_kreis(pc):
    login(pc, OHNE_NAME)

    circle = pc.get_by_role("complementary", name="Seitenleiste").locator(".a-avatar")
    expect(circle).to_have_text("")
    expect(circle.locator("svg")).to_be_visible()
    expect(pc.get_by_text("Ergänze deinen Namen")).to_be_visible()


# Szenario 7
def test_entwurf_auch_ohne_farbe_erkennbar(pc):
    login(pc)
    pc.goto(f"{BASE}/muster/")

    styles = pc.eval_on_selector_all(".a-event", "rows => rows.map(r => getComputedStyle(r).borderTopStyle)")
    draft = pc.eval_on_selector(".a-event.ist-entwurf", "r => getComputedStyle(r).borderTopStyle")
    assert draft == "dashed"
    assert styles.count("dashed") == 1, styles


# Szenario 8
def test_teilnehmende_am_handy_als_karten_am_pc_als_tabelle(pc, handy):
    def look(page: Page) -> dict:
        login(page)
        page.goto(f"{BASE}/muster/")
        return page.evaluate(
            """() => ({zeile: getComputedStyle(document.querySelector('.a-tabelle tbody tr')).display,
                      kopf: document.querySelector('.a-tabelle thead').getBoundingClientRect().height})"""
        )

    on_pc = look(pc)
    assert on_pc["zeile"] == "table-row"
    assert on_pc["kopf"] > 10
    on_phone = look(handy)
    assert on_phone["zeile"] in ("block", "grid")
    assert on_phone["kopf"] <= 1


# Eingaben wie am Handy (Erfahrung aus dem Vorgänger-Repo, CLAUDE.md)
def test_eingaben_wie_am_handy_bleiben_stehen(handy):
    login(handy)
    handy.goto(f"{BASE}/muster/")
    field = handy.get_by_label("Name der Veranstaltung")

    field.tap()
    # Ein Handy tippt Wörter oft als „Zusammensetzung“ und ersetzt sie per Wortvorschlag
    # oder Autokorrektur. Danach muss der Text im Feld stehen bleiben.
    field.press_sequentially("Pfingstlager ")
    field.evaluate(
        """el => {
            el.dispatchEvent(new CompositionEvent('compositionstart', {data: ''}));
            el.dispatchEvent(new CompositionEvent('compositionupdate', {data: 'Somme'}));
            el.value += 'Somme';
            el.dispatchEvent(new InputEvent('input', {inputType: 'insertCompositionText', data: 'Somme', bubbles: true}));
            el.dispatchEvent(new InputEvent('beforeinput', {inputType: 'insertReplacementText', data: 'Sommer', bubbles: true, cancelable: true}));
            el.value = el.value.replace(/Somme$/, 'Sommer');
            el.dispatchEvent(new InputEvent('input', {inputType: 'insertReplacementText', data: 'Sommer', bubbles: true}));
            el.dispatchEvent(new CompositionEvent('compositionend', {data: 'Sommer'}));
        }"""
    )
    field.press_sequentially(" 2027")
    handy.get_by_label("Organisation").focus()

    expect(field).to_have_value("Pfingstlager Sommer 2027")


# Szenario 12 zu #111: Fahrtenname am Handy mit Autokorrektur und Wortvorschlägen
def _type_like_a_phone(field, first: str, composed: str, replaced: str, last: str) -> None:
    """Tippt wie ein Handy: Wörter als „Zusammensetzung“, eines ersetzt per Wortvorschlag oder Autokorrektur."""
    field.press_sequentially(first)
    field.evaluate(
        """(el, [composed, replaced]) => {
            el.dispatchEvent(new CompositionEvent('compositionstart', {data: ''}));
            el.dispatchEvent(new CompositionEvent('compositionupdate', {data: composed}));
            el.value += composed;
            el.dispatchEvent(new InputEvent('input', {inputType: 'insertCompositionText', data: composed, bubbles: true}));
            el.dispatchEvent(new InputEvent('beforeinput', {inputType: 'insertReplacementText', data: replaced, bubbles: true, cancelable: true}));
            el.value = el.value.slice(0, -composed.length) + replaced;
            el.dispatchEvent(new InputEvent('input', {inputType: 'insertReplacementText', data: replaced, bubbles: true}));
            el.dispatchEvent(new CompositionEvent('compositionend', {data: replaced}));
        }""",
        [composed, replaced],
    )
    field.press_sequentially(last)


@pytest.mark.parametrize("device", ["pc", "handy"])
def test_fahrtenname_eintragen_wie_am_handy_und_ueberall_sehen(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    page.goto(f"{BASE}/profil/")
    # Seit #180 öffnet sich das Feld erst beim Antippen (Zielbild „Mein Profil“).
    rest = page.get_by_role("button", name="Fahrtenname bearbeiten: Noch nicht angegeben")
    if device == "handy":
        rest.tap()
    else:
        rest.click()
    field = page.get_by_label("Fahrtenname", exact=True)
    expect(field).to_be_focused()
    expect(field).to_have_attribute("placeholder", "Fahrtennamen eingeben")
    # Weiß, damit es sich von den grauen, gesperrten Feldern abhebt (Zielbild zu #161).
    assert page.locator(".a-antippfeld-gruppe").evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)"

    _type_like_a_phone(field, "Kleiner ", "Bä", "Bär", " vom See")
    expect(field).to_have_value("Kleiner Bär vom See")
    page.get_by_role("button", name="Speichern").click()

    expect(page.locator("main .a-meldung.ist-erfolg")).to_contain_text("Dein Fahrtenname ist gespeichert.")
    expect(page.locator(".a-anzeigename")).to_have_text("Kleiner Bär vom See (Erika Testfrau)")
    expect(page.get_by_role("button", name="Fahrtenname bearbeiten: Kleiner Bär vom See")).to_be_visible()
    assert run_axe(page) == []
    page.goto(f"{BASE}/")
    expect(page.get_by_role("heading", level=1)).to_have_text("Hallo Kleiner Bär vom See!")

    # Zu lang: Fehler am Feld, die Eingabe bleibt stehen, und die Seite besteht die Prüfung.
    page.goto(f"{BASE}/profil/")
    page.get_by_role("button", name="Fahrtenname bearbeiten: Kleiner Bär vom See").click()
    page.get_by_label("Fahrtenname", exact=True).fill("K" * 51)
    page.get_by_role("button", name="Speichern").click()
    field = page.get_by_label("Fahrtenname", exact=True)
    # Szenario 7 zu #180: Das Feld bleibt offen, mit dem Fokus in der Eingabe.
    expect(field).to_be_focused()
    expect(field).to_have_value("K" * 51)
    expect(field).to_have_attribute("aria-invalid", "true")
    expect(page.locator("#id_scout_name-fehler")).to_be_visible()
    expect(page.locator("#id_scout_name-fehler")).to_have_text("Dein Fahrtenname darf höchstens 50 Zeichen lang sein.")
    width = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    assert width[0] <= width[1], f"Seite breiter als der Bildschirm: {width}"
    assert run_axe(page) == []


# Szenarien 1 bis 6, 8 und 10 zu #180: Feld zum Antippen und Kopfzeile wie im Zielbild, am PC und am Handy
def _set_scout_name(value: str) -> None:
    get_user_model().objects.filter(username="erika.testfrau").update(scout_name=value)


def _press(page: Page, locator, device: str) -> None:
    if device == "handy":
        locator.tap()
    else:
        locator.click()


@pytest.mark.parametrize("device", ["pc", "handy"])
def test_fahrtenname_antippen_verwerfen_leeren_und_speichern(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    _set_scout_name("Falkenflug")
    page.goto(f"{BASE}/profil/")
    field = page.get_by_label("Fahrtenname", exact=True)
    rest = page.get_by_role("button", name="Fahrtenname bearbeiten: Falkenflug")
    announcement = page.locator("[data-ansage]")

    # Szenario 1: in Ruhe wie die anderen Angaben, ohne Eingabe und ohne Knöpfe darunter.
    expect(rest).to_be_visible()
    expect(field).to_be_hidden()
    expect(page.get_by_role("button", name="Speichern")).to_be_hidden()
    expect(page.get_by_role("button", name="Fahrtenname leeren")).to_be_enabled()
    # Szenario 8: Fahrtenname groß, der Name kleiner und grauer dahinter.
    head = page.locator(".a-anzeigename")
    addition = page.locator(".a-anzeigename-zusatz")
    expect(addition).to_have_text("(Erika Testfrau)")
    size = "e => parseFloat(getComputedStyle(e).fontSize)"
    assert addition.evaluate(size) < head.evaluate(size)
    assert addition.evaluate("e => getComputedStyle(e).color") == "rgb(86, 99, 117)"
    assert run_axe(page) == []

    # Szenario 3: Antippen öffnet die Eingabe mit „Verwerfen“ und „Speichern“ darunter.
    _press(page, rest, device)
    expect(field).to_be_focused()
    expect(field).to_have_value("Falkenflug")
    expect(page.get_by_role("button", name="Verwerfen")).to_be_visible()
    expect(page.get_by_role("button", name="Speichern")).to_be_visible()
    assert run_axe(page) == []

    # Szenario 5: Verwerfen mit dem Knopf, mit Esc und mit Tippen außerhalb; nichts wird gespeichert.
    field.fill("Kolibri")
    _press(page, page.get_by_role("button", name="Verwerfen"), device)
    expect(rest).to_be_focused()
    expect(announcement).to_have_text("Änderungen verworfen.")
    _press(page, rest, device)
    field.fill("Kolibri")
    page.keyboard.press("Escape")
    expect(rest).to_be_focused()
    _press(page, rest, device)
    field.fill("Kolibri")
    _press(page, page.get_by_role("heading", level=1), device)
    expect(field).to_be_hidden()
    expect(rest).to_be_focused()
    expect(announcement).to_have_text("Änderungen verworfen.")
    assert get_user_model().objects.get(username="erika.testfrau").scout_name == "Falkenflug"
    if device == "handy":
        # Wer außerhalb einen Knopf antippt, behält ihn: Das Feld schließt, nimmt aber den Fokus nicht (unabhängige Prüfung).
        _press(page, rest, device)
        _press(page, page.get_by_role("button", name="Menü"), device)
        expect(page.get_by_role("dialog", name="Menü")).to_be_visible()
        expect(field).to_be_hidden()
        expect(rest).not_to_be_focused()
        _press(page, page.get_by_role("button", name="Menü schließen"), device)

    # Szenario 6: × öffnet das Feld leer; „Verwerfen“ lässt „Falkenflug“ stehen.
    _press(page, page.get_by_role("button", name="Fahrtenname leeren"), device)
    expect(field).to_be_focused()
    expect(field).to_have_value("")
    expect(announcement).to_have_text("Feld geleert. Mit Speichern übernehmen oder verwerfen.")
    _press(page, page.get_by_role("button", name="Verwerfen"), device)
    expect(rest).to_be_visible()

    # Szenario 4: ändern und speichern, am PC mit Enter, am Handy mit dem Knopf.
    _press(page, rest, device)
    field.fill("Kolibri")
    if device == "handy":
        _press(page, page.get_by_role("button", name="Speichern"), device)
    else:
        field.press("Enter")
    expect(page.locator("main .a-meldung.ist-erfolg")).to_contain_text("Dein Fahrtenname ist gespeichert.")
    rest = page.get_by_role("button", name="Fahrtenname bearbeiten: Kolibri")
    expect(rest).to_be_focused()
    expect(head).to_have_text("Kolibri (Erika Testfrau)")

    # Szenario 6: × und „Speichern“ löscht; danach „Noch nicht angegeben“, × ausgegraut, nur der Name oben.
    _press(page, page.get_by_role("button", name="Fahrtenname leeren"), device)
    _press(page, page.get_by_role("button", name="Speichern"), device)
    expect(page.locator("main .a-meldung.ist-erfolg")).to_contain_text("Dein Fahrtenname ist gelöscht.")
    expect(page.get_by_role("button", name="Fahrtenname bearbeiten: Noch nicht angegeben")).to_be_visible()
    expect(page.get_by_role("button", name="Fahrtenname leeren")).to_be_disabled()
    expect(head).to_have_text("Erika Testfrau")
    expect(addition).to_have_count(0)

    # Szenario 10: nichts ragt über den Rand, auch offen mit Knöpfen.
    _press(page, page.get_by_role("button", name="Fahrtenname bearbeiten: Noch nicht angegeben"), device)
    width = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    assert width[0] <= width[1], f"Seite breiter als der Bildschirm: {width}"
    box = page.locator(".a-antippfeld-knoepfe").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width[1], box


# Szenario 9 zu #180: nur mit der Tastatur
def test_fahrtenname_nur_mit_der_tastatur(pc):
    login(pc)
    pc.goto(f"{BASE}/profil/")
    rest = pc.locator("[data-oeffnen]")
    field = pc.get_by_label("Fahrtenname", exact=True)

    station = _tab_to_element(pc, "[data-oeffnen]")
    assert station["sichtbar"] and station["kontrast"] >= 3, station
    pc.keyboard.press("Enter")
    expect(field).to_be_focused()
    pc.keyboard.type("Kiwi")
    pc.keyboard.press("Escape")
    expect(rest).to_be_focused()
    expect(rest).to_contain_text("Noch nicht angegeben")
    assert focus_visible(pc)["sichtbar"]
    # Esc verwirft auch, wenn der Fokus mit Tab schon aus dem Feld hinaus ist (unabhängige Prüfung).
    pc.keyboard.press("Enter")
    pc.keyboard.type("Kiwi")
    for _ in range(4):
        pc.keyboard.press(_tab_key(pc))
    assert not pc.evaluate("document.querySelector('[data-antippfeld]').contains(document.activeElement)")
    pc.keyboard.press("Escape")
    expect(rest).to_be_focused()
    expect(rest).to_contain_text("Noch nicht angegeben")

    pc.keyboard.press("Enter")
    pc.keyboard.type("Kiwi")
    pc.keyboard.press("Enter")
    expect(pc.locator("main .a-meldung.ist-erfolg")).to_contain_text("Dein Fahrtenname ist gespeichert.")
    expect(rest).to_contain_text("Kiwi")
    expect(rest).to_be_focused()
    # Weiter mit Tab zum Knopf zum Leeren, auch er mit sichtbarem Fokus.
    pc.keyboard.press(_tab_key(pc))
    expect(pc.get_by_role("button", name="Fahrtenname leeren")).to_be_focused()
    assert focus_visible(pc)["sichtbar"]


# Szenario 11 zu #180: ohne Skript das einfache Formular
def test_fahrtenname_ohne_skript_speichern(pc, browser):
    # Anmelden mit Skript wie sonst auch; danach dieselbe Sitzung in einem Browser ohne Skript.
    login(pc)
    context = browser.new_context(java_script_enabled=False, storage_state=pc.context.storage_state(), **PC)
    page = context.new_page()
    try:
        page.goto(f"{BASE}/profil/")
        field = page.get_by_label("Fahrtenname", exact=True)
        expect(field).to_be_visible()
        expect(page.locator("[data-oeffnen]")).to_be_hidden()
        expect(page.get_by_role("button", name="Verwerfen")).to_be_hidden()
        field.fill("Kiwi")
        page.get_by_role("button", name="Speichern").click()
        expect(page.locator("main .a-meldung.ist-erfolg")).to_contain_text("Dein Fahrtenname ist gespeichert.")
        expect(page.locator(".a-anzeigename")).to_have_text("Kiwi (Erika Testfrau)")
    finally:
        context.close()


def _erika_with_roles() -> None:
    """Gibt der angemeldeten Erika Mitgliedschaft und Rollen, mit langen Namen wie im echten Leben."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(Unit.Kind.FEDERATION, "DPV")
    bund = unit(Unit.Kind.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    stamm = unit(Unit.Kind.TROOP, "Stamm Walhall vom Nordseestrand", bund)
    sippe = unit(Unit.Kind.GROUP, "Sippe Falkenhorst am Leuchtturm der Hallig Süderoog", stamm)
    give(erika, Role.Kind.MEMBER, sippe)
    give(erika, Role.Kind.TROOP_LEAD, stamm)
    give(erika, Role.Kind.EVENT_TEAM, dpv)


# Szenario 14 zu #96 und Szenario 17 zu #161: „Mein Profil“ am Handy ohne seitliches Wischen und nur mit der Tastatur
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_mein_profil_am_handy_und_nur_mit_der_tastatur(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    _erika_with_roles()
    # Sehr lange Angaben ohne Trennstelle (unabhängige Prüfung zu #161); sie gelten bis zur nächsten Anmeldung.
    get_user_model().objects.filter(username="erika.testfrau").update(
        last_name="Testfrau-Mustermann-Beispielname-von-und-zu-Hohenlinden",
        email="erika.testfrau.mit.einer.sehr.langen.adresse.ohne.trennstelle@example.org",
    )

    page.goto(f"{BASE}/profil/")

    expect(page.get_by_role("heading", level=1)).to_have_text("Mein Profil")
    expect(page.locator(".a-anzeigename")).to_have_text("Erika Testfrau-Mustermann-Beispielname-von-und-zu-Hohenlinden")
    expect(page.get_by_role("heading", level=2, name="Deine Angaben")).to_be_attached()
    expect(page.get_by_role("heading", level=2, name="Organisation und Rollen")).to_be_visible()
    membership = page.locator(".a-mitgliedschaft")
    expect(membership).to_contain_text("Mitgliedschaft")
    expect(membership).to_contain_text("Sippe Falkenhorst am Leuchtturm der Hallig Süderoog")
    expect(membership).to_contain_text("Pfadfinderbund Boreas › Stamm Walhall vom Nordseestrand")
    expect(page.locator(".a-rollenkacheln > li")).to_have_count(2)
    width = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    assert width[0] <= width[1], f"Seite breiter als der Bildschirm: {width}"
    # Am Handy stehen Felder und Kacheln untereinander, am PC nebeneinander.
    columns = 1 if device == "handy" else 2
    tops = page.locator(".a-felder > div").evaluate_all("els => els.map(e => Math.round(e.getBoundingClientRect().top))")
    assert len(set(tops)) == 4 // columns, tops
    tiles = page.locator(".a-rollenkacheln > li").evaluate_all("els => els.map(e => Math.round(e.getBoundingClientRect().top))")
    assert (len(set(tiles)) == 2) == (device == "handy"), tiles
    # Farben nach Sebastians Vorgabe bei der Klärung von #161: Mitgliedschaft zart blau ohne Verlauf,
    # Kacheln weiß mit feinem grauem Rand, oben ein schmaler blauer Streifen, ohne Schatten.
    look = "e => { const s = getComputedStyle(e); return [s.backgroundColor, s.backgroundImage, s.boxShadow] }"
    assert membership.evaluate(look) == ["rgb(233, 239, 246)", "none", "none"]
    tile = page.locator(".a-rollenkacheln > li").first
    assert tile.evaluate(look) == ["rgb(255, 255, 255)", "none", "none"]
    borders = tile.evaluate(
        "e => { const s = getComputedStyle(e); return ['Top', 'Right', 'Bottom', 'Left'].map("
        "side => s['border' + side + 'Width'] + ' ' + s['border' + side + 'Style'] + ' ' + s['border' + side + 'Color']) }"
    )
    assert borders == ["3px solid rgb(26, 75, 126)"] + ["1px solid rgb(219, 226, 234)"] * 3
    # Die Rollenmarke in der Kachel bleibt zart blau (Sebastian, Nachtrag vom 25.10.2026 in #161).
    assert tile.locator(".a-rollenmarke").evaluate(look) == ["rgb(233, 239, 246)", "none", "none"]
    # axe vor dem Tabben: Direkt nach dem Fokus auf „Abmelden“ misst es die Farben des Knopfs mitten
    # im Übergang und meldet zu wenig Kontrast; kurz danach ist alles in Ordnung (geprüft am 25.10.2026).
    assert run_axe(page) == []
    stations = _tab_to(page, "Menü" if device == "handy" else "Abmelden")
    _all_visible(stations)


def _tab_to_element(page: Page, selector: str, steps: int = 25) -> dict:
    """Drückt Tab, bis der Fokus auf dem Element `selector` liegt; gibt diese Station zurück."""
    for _ in range(steps):
        page.keyboard.press(_tab_key(page))
        if page.evaluate("s => document.activeElement.matches(s)", selector):
            return focus_visible(page)
    raise AssertionError(f"„{selector}“ nach {steps} Mal Tab nicht erreicht")


def _ring(circle) -> str:
    return circle.locator(".a-avatar").evaluate("e => getComputedStyle(e).boxShadow")


# Szenarien 1, 2, 4 und 5 zu #13: Profilkreis am PC und am Handy, mit Maus und nur mit der Tastatur
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_profilkreis_fuehrt_zu_mein_profil_auch_nur_mit_der_tastatur(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    selector = "aside .a-profil" if device == "pc" else ".a-topbar .a-profil"
    circle = page.locator(selector)
    expect(circle).not_to_have_attribute("aria-current", "page")
    assert _ring(circle) == "none", "auf der Startseite ist der Kreis hervorgehoben"

    circle.click()

    page.wait_for_url(f"{BASE}/profil/")
    expect(page.get_by_role("heading", level=1)).to_have_text("Mein Profil")
    expect(circle).to_have_attribute("aria-current", "page")
    # Nur ein gelber Ring direkt am Kreis, ohne weißen Spalt (Sebastian, 26.10.2026).
    assert "rgb(240, 173, 44)" in _ring(circle), f"auf „Mein Profil“ ist der Kreis nicht hervorgehoben: {_ring(circle)}"

    page.goto(f"{BASE}/")
    station = _tab_to_element(page, selector)
    assert station["sichtbar"] and station["kontrast"] >= 3, station
    page.keyboard.press("Enter")

    page.wait_for_url(f"{BASE}/profil/")
    expect(page.get_by_role("heading", level=1)).to_have_text("Mein Profil")


# Szenario 10
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_seiten_bestehen_die_pruefung_auf_barrierefreiheit(request, browser_name, device, settings):
    settings.ROOT_URLCONF = "tests.urls"  # enthält eine Adresse, die die Fehlerseite auslöst
    page: Page = request.getfixturevalue(device)

    page.goto(f"{BASE}/anmelden/")
    findings = {"Login-Seite": run_axe(page)}
    # Login-Seite mit Fehlermeldung (#165): Unzulässige Angaben beim Start führen mit Hinweis zurück.
    page.locator("form").first.evaluate("form => { form.action += '?scope=fremd'; form.submit(); }")
    expect(page.get_by_role("alert")).to_contain_text("Die Anmeldung wurde abgebrochen.")
    findings["Login-Seite mit Fehlermeldung"] = run_axe(page)
    login(page)
    findings["Startseite"] = run_axe(page)
    page.goto(f"{BASE}/profil/")
    findings["Mein Profil ohne Organisation"] = run_axe(page)
    page.goto(f"{BASE}/muster/")
    findings["Musterseite"] = run_axe(page)
    if device == "handy":
        page.get_by_role("button", name="Menü").click()
        # Erst messen, wenn das Menü fertig eingeblendet ist; es startet halb durchsichtig.
        page.locator("#menue").evaluate("el => Promise.all(el.getAnimations().map(a => a.finished))")
        findings["Musterseite mit offenem Menü"] = run_axe(page)
    page.goto(f"{BASE}/test/1/")
    findings["Fehlerseite"] = run_axe(page)
    # Die übrigen Fehlerseiten haben denselben Aufbau (#58); zwei davon stellvertretend.
    page.goto(f"{BASE}/gibt-es-nicht/")
    expect(page.get_by_role("heading", level=1)).to_have_text("Diese Seite gibt es nicht.")
    findings["Seite nicht gefunden"] = run_axe(page)
    page.goto(f"{BASE}/test/1/verboten/")
    expect(page.get_by_role("heading", level=1)).to_have_text("Dafür fehlt dir die Berechtigung.")
    findings["Kein Zugriff"] = run_axe(page)

    assert {name: found for name, found in findings.items() if found} == {}


# Szenarien 10, 11 und 13 zu #165
def _notices_fit(page: Page) -> list[str]:
    """Was an den Meldungen der Seite nicht passt: über den Rand, Symbol nicht links, überlappend."""
    return page.evaluate(
        """() => {
            const problems = [];
            const width = document.documentElement.clientWidth;
            if (document.documentElement.scrollWidth > width) problems.push('Seite breiter als der Bildschirm');
            const boxes = [...document.querySelectorAll('main .a-meldung')].filter(e => e.offsetParent);
            boxes.forEach((notice, i) => {
                const box = notice.getBoundingClientRect();
                const icon = notice.querySelector('.a-meldung-ic').getBoundingClientRect();
                const text = notice.querySelector('.a-meldung-text').getBoundingClientRect();
                const name = `Meldung ${i + 1}`;
                if (box.left < 0 || box.right > width) problems.push(`${name} ragt über den Rand`);
                if (notice.scrollWidth > notice.clientWidth) problems.push(`${name} läuft innen über`);
                if (!(icon.right <= text.left && Math.abs(icon.top - box.top) < 20)) problems.push(`${name}: Symbol nicht links oben`);
                const next = boxes[i + 1];
                if (next && next.parentElement === notice.parentElement && next.getBoundingClientRect().top <= box.bottom) {
                    problems.push(`${name} und die nächste stehen nicht getrennt`);
                }
            });
            return boxes.length ? problems : ['keine Meldung gefunden'];
        }"""
    )


def test_meldungen_am_handy_brechen_um_und_bestehen_die_pruefung(handy):
    """Konto ohne Namen und ohne Organisation: zwei getrennte Warnmeldungen und die Informationsmeldung."""
    login(handy, OHNE_NAME)

    findings = {}
    for address in ("/", "/profil/", "/muster/"):
        handy.goto(f"{BASE}{address}")
        findings[address] = _notices_fit(handy) + run_axe(handy)
    handy.goto(f"{BASE}/profil/")
    warnings = handy.locator("main .a-meldung.ist-warnung")
    expect(warnings).to_have_count(2)
    expect(warnings.nth(0)).to_contain_text("Ergänze deinen Namen")
    expect(warnings.nth(1)).to_contain_text("Du bist noch keiner Organisation zugeordnet.")

    assert {address: found for address, found in findings.items() if found} == {}
