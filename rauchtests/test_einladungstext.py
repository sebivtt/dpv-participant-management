"""Rauchtest „Einladungstext mit einfachem Editor“ im Browser (#358): am PC und am Handy, mit Maus, Tippen, nur mit der
Tastatur und ohne Skript.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an, ist Mitglied der Sippe Falken und legt das
„Pfingstlager 2028“ an oder leitet es schon (wie in rauchtests/test_veroeffentlichen.py, mit Beginn relativ zu heute).
Geprüft wird, was nur ein Browser zeigt: der Editor (Trix vom eigenen Server) mit der Knopfleiste in drei Gruppen,
Knöpfe mindestens 36 Pixel groß mit Beschriftung für Vorleseprogramme, der Link über „Link setzen“, die Zahl der
Zeichen beim Tippen und rot über 10.000 (G1), Schreiben und Formatieren nur mit der Tastatur und am Handy mit
Autokorrektur und Wortvorschlägen, ohne dass etwas verschwindet (E5), Einfügen aus Word (E7), der breite Dialog mit
Escape (G7), am Handy bildschirmfüllend, und ohne Skript das Textfeld mit dem Hinweissatz (E6). Die Sicherheitsrichtlinie
prüft jeder Rauchtest selbst (`rauchtests/conftest.py`): Trix legt seine Gestaltung nur mit dem Schlüssel je Aufruf
in die Seite, sonst würde der Test rot. Die Regeln selbst prüft tests/test_einladungstext.py. Alle Namen, Adressen und
Nummern sind erfunden.
"""

import re

from playwright.sync_api import Page, expect

from events.models import Event
from rauchtests.conftest import BASE, expect_modal, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _tab_key
from rauchtests.test_veranstaltungen import _dialog, _erika_in_den_falken
from rauchtests.test_veroeffentlichen import _pfingstlager

LIST = f"{BASE}/veranstaltungen/"
EDITOR = "trix-editor"
TOOLBAR = ".a-editor [role=toolbar]"
COUNTER = ".a-editor .a-zeichenzahl"
# Sichtbar „708/10.000“; Vorleseprogramme hören im versteckten Teil „708 von 10.000 Zeichen“ (#215).
COUNT = f"{COUNTER} [aria-hidden=true]"
STEP_SUBMIT = 'form#f-schritt .a-schritt-rechts button[type="submit"]'
SAVED = "Der Einladungstext von Pfingstlager 2028 ist gespeichert."
BUTTONS = [["Fett", "Kursiv", "Durchgestrichen", "Link"], ["Überschrift", "Zitat", "Aufzählung", "Nummerierte Liste"],
           ["Rückgängig", "Wiederholen"]]


def _knopf(page: Page, name: str):
    return page.locator(TOOLBAR).get_by_role("button", name=name, exact=True)


def _knopfleiste(page: Page) -> None:
    """Die Knopfleiste wie im Zielbild: drei Gruppen, jeder Knopf mit Beschriftung und mindestens 36 Pixel groß."""
    toolbar = page.locator(TOOLBAR)
    expect(toolbar).to_have_attribute("aria-label", "Formatierung")
    groups = toolbar.locator("[role=group]")
    expect(groups).to_have_count(3)
    for index, names in enumerate(BUTTONS):
        buttons = groups.nth(index).locator("button")
        expect(buttons).to_have_count(len(names))
        for position, name in enumerate(names):
            button = buttons.nth(position)
            expect(button).to_have_accessible_name(name)
            box = button.bounding_box()
            assert box["width"] >= 36 and box["height"] >= 36, (name, box)
    # Kein Code, keine Anhänge, keine Bilder.
    expect(toolbar.locator('[data-trix-attribute="code"], [data-trix-action="attachFiles"]')).to_have_count(0)


def _editor_bereit(page: Page) -> None:
    """Der Editor steht statt des Textfelds da; ohne Skript gäbe es den Hinweissatz."""
    expect(page.locator(EDITOR)).to_be_visible()
    expect(page.locator(".a-editor textarea")).to_have_count(0)
    expect(page.get_by_text("Ohne JavaScript siehst du die Formatierung als Zeichen.")).to_have_count(0)
    expect(page.locator(EDITOR)).to_have_accessible_name("Einladungstext")


LINK_FIELD = ".a-editor-link"


def _link_feld(page: Page):
    """Das Feld „Adresse“ für einen Link: schwebt direkt unter dem gewählten Text, über allem anderen, und zeigt ohne
    Link „Link setzen“ und „Verwerfen“ (Vorschau, Sebastian, 26.11.2026)."""
    field = page.locator(LINK_FIELD)
    expect(field).to_be_visible()
    expect(field.locator("button:visible")).to_have_text(["Link setzen", "Verwerfen"])
    selection = page.locator(EDITOR).evaluate(
        "element => { const [start, end] = element.editor.getSelectedRange();"
        " const a = element.editor.getClientRectAtPosition(start), b = element.editor.getClientRectAtPosition(end);"
        " return {bottom: Math.max(a.bottom, b.bottom), left: a.left}; }")
    box = field.bounding_box()
    editor = page.locator(EDITOR).bounding_box()
    assert selection["bottom"] <= box["y"] <= selection["bottom"] + 16, (selection, box)
    assert editor["x"] - 1 <= box["x"] and box["x"] + box["width"] <= editor["x"] + editor["width"] + 1, (editor, box)
    # Über allem anderen: An seiner Mitte liegt das Feld selbst, nicht der Text darunter.
    middle = page.evaluate("([x, y]) => document.elementFromPoint(x, y).closest('.a-editor-link') !== null",
                           [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
    assert middle
    return field.get_by_label("Adresse", exact=True)


def _schritt_2(page: Page) -> None:
    """Legt das Pfingstlager mit Schritt 1 an und steht danach in Schritt 2 „Einladungstext“."""
    page.goto(f"{LIST}erstellen/")
    page.get_by_label("Name").fill("Pfingstlager 2028")
    page.locator('form#f-schritt input[name="start"]').fill("2028-06-02")
    page.locator('form#f-schritt input[name="end"]').fill("2028-06-05")
    page.locator(STEP_SUBMIT).click()
    page.wait_for_url(f"{LIST}*/anlegen/einladungstext/")
    expect(page.locator("ol.a-schritte li[aria-current='step']")).to_have_text("Schritt 2 Einladungstext")


def _gezeichnet(page: Page) -> None:
    """Wartet, bis der Browser zweimal gezeichnet hat; so ist auch Trix mit dem eben Getippten fertig.

    Ein Kürzel wie Cmd/Strg+B, das Trix noch vor diesem Zeichnen bekommt, setzt Trix danach wieder zurück; eine Person
    tippt nie so schnell, der Test schon.
    """
    page.evaluate("() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)))")


def _gespeichert() -> str:
    return Event.objects.get(name="Pfingstlager 2028").invitation_text


# ---------- E1, E4: am PC mit der Maus ----------


def test_e1_am_pc_mit_der_maus_schreiben_formatieren_und_einen_link_setzen(pc):
    login(pc)
    _erika_in_den_falken()
    _schritt_2(pc)
    _editor_bereit(pc)
    _knopfleiste(pc)
    # Mit Skript steht die Zahl der Zeichen da, wie beim Textfeld (#215); ohne Skript nicht (E6).
    expect(pc.locator(COUNT)).to_have_text("0/10.000")
    _no_side_scroll(pc)
    assert run_axe(pc) == []

    pc.locator(EDITOR).click()
    pc.keyboard.type("Packliste")
    _knopf(pc, "Überschrift").click()
    expect(_knopf(pc, "Überschrift")).to_have_attribute("aria-pressed", "true")
    pc.keyboard.press("Enter")
    _knopf(pc, "Aufzählung").click()
    pc.keyboard.type("Kluft und Halstuch")
    pc.keyboard.press("Enter")
    pc.keyboard.type("Schlafsack")
    pc.keyboard.press("Enter")
    pc.keyboard.press("Enter")
    pc.keyboard.type("Die ")
    _knopf(pc, "Fett").click()
    pc.keyboard.type("Anfahrt")
    _knopf(pc, "Fett").click()
    for _ in range(len("Anfahrt")):
        pc.keyboard.press("Shift+ArrowLeft")
    # Vorschau (Sebastian, 26.11.2026): Das Feld schwebt genau unter dem gewählten Text über allem anderen, wie die
    # Knöpfe beim Fahrtennamen; ohne Link darin „Link setzen“ und „Verwerfen“.
    _knopf(pc, "Link").click()
    address = _link_feld(pc)
    expect(address).to_be_visible()
    address.fill("https://example.org/falsch")
    pc.locator(LINK_FIELD).get_by_role("button", name="Verwerfen").click()
    expect(pc.locator(LINK_FIELD)).to_be_hidden()
    expect(pc.locator(f"{EDITOR} a")).to_have_count(0)

    _knopf(pc, "Link").click()
    _link_feld(pc).fill("https://example.org/anfahrt")
    pc.locator(LINK_FIELD).get_by_role("button", name="Link setzen").click()
    expect(pc.locator(LINK_FIELD)).to_be_hidden()
    expect(pc.locator(f"{EDITOR} a")).to_have_attribute("href", "https://example.org/anfahrt")
    # Mit Link darin statt „Verwerfen“ „Link entfernen“; Escape schließt das Feld, ohne etwas zu ändern.
    _knopf(pc, "Link").click()
    expect(pc.locator(f"{LINK_FIELD} button:visible")).to_have_text(["Link setzen", "Link entfernen"])
    pc.keyboard.press("Escape")
    expect(pc.locator(LINK_FIELD)).to_be_hidden()
    expect(pc.locator(f"{EDITOR} a")).to_have_count(1)
    # Weiter am Ende des Texts.
    pc.locator(EDITOR).evaluate(
        "element => { element.focus(); const end = element.editor.getDocument().getLength() - 1;"
        " element.editor.setSelectedRange([end, end]); }")
    pc.keyboard.type(" steht hier.")

    # Die Zahl der Zeichen läuft beim Tippen mit, ohne Formatierung gezählt (#215).
    text = "Packliste" + "Kluft und Halstuch" + "Schlafsack" + "Die Anfahrt steht hier."
    expect(pc.locator(COUNTER)).to_be_visible()
    expect(pc.locator(COUNT)).to_have_text(f"{len(text)}/10.000")
    expect(pc.locator(COUNTER)).not_to_have_class("ist-zu-lang")
    _no_side_scroll(pc)
    assert run_axe(pc) == []

    pc.locator(STEP_SUBMIT).click()
    pc.wait_for_url(f"{LIST}*/anlegen/zusammenfassung/")
    section = pc.locator('[aria-labelledby="h-einladungstext"]')
    expect(section.locator("h3", has_text="Packliste")).to_be_visible()
    expect(section.locator("li")).to_have_text(["Kluft und Halstuch", "Schlafsack"])
    link = section.get_by_role("link", name="Anfahrt")
    expect(link).to_have_attribute("href", "https://example.org/anfahrt")
    expect(link).to_have_attribute("target", "_blank")
    # Was danach an derselben Stelle getippt ist, bleibt fett wie das Wort davor (so arbeitet jeder Editor).
    expect(section.locator("strong").first).to_contain_text("Anfahrt")
    _no_side_scroll(pc)
    assert run_axe(pc) == []
    assert "<h3>Packliste</h3>" in _gespeichert()


# ---------- E5: nur mit der Tastatur ----------


def _nur_mit_der_tastatur(page: Page) -> None:
    login(page)
    _erika_in_den_falken()
    _schritt_2(page)
    _editor_bereit(page)
    tab = _tab_key(page)

    # Die Knopfleiste ist ein Halt der Tab-Taste; darin wechseln Pfeile, Pos1 und Ende; danach kommt der Editor.
    stations = _stations_to_element(page, f"{TOOLBAR} button", steps=40)
    _all_visible(stations)
    expect(page.locator(f"{TOOLBAR} button").first).to_be_focused()
    page.keyboard.press("ArrowRight")
    expect(_knopf(page, "Kursiv")).to_be_focused()
    page.keyboard.press("End")
    expect(_knopf(page, "Wiederholen")).to_be_focused()
    page.keyboard.press("Home")
    expect(_knopf(page, "Fett")).to_be_focused()
    _all_visible(_stations_to_element(page, EDITOR, steps=3))

    # Aufzählung über die Knopfleiste: zurück mit Shift+Tab, Pfeile, Enter; danach geht es im Text weiter.
    page.keyboard.press(f"Shift+{tab}")
    expect(_knopf(page, "Fett")).to_be_focused()
    passed = []
    for _ in range(8):
        passed.append(page.evaluate("() => document.activeElement.getAttribute('aria-label')"))
        if passed[-1] == "Aufzählung":
            break
        page.keyboard.press("ArrowRight")
    assert passed[-1] == "Aufzählung", passed
    page.keyboard.press("Enter")
    expect(page.locator(EDITOR)).to_be_focused()
    expect(_knopf(page, "Aufzählung")).to_have_attribute("aria-pressed", "true")
    page.keyboard.type("Karte")
    page.keyboard.press("Enter")
    # Wie eine Person: erst weiter, wenn der neue Punkt zu sehen ist (Trix zeichnet ihn kurz danach).
    expect(page.locator(f"{EDITOR} li")).to_have_count(2)
    page.keyboard.type("Kompass mit ")
    expect(page.locator('input[name="invitation_text"]')).to_have_value(re.compile("Kompass mit"))
    _gezeichnet(page)
    page.keyboard.press("ControlOrMeta+b")
    expect(_knopf(page, "Fett")).to_have_attribute("aria-pressed", "true")
    page.keyboard.type("Rucksack")
    expect(page.locator('input[name="invitation_text"]')).to_have_value(re.compile("Rucksack"))
    # Tab in einem Listenpunkt rückt nicht ein, sondern führt aus dem Editor hinaus zum nächsten Halt.
    page.keyboard.press(tab)
    expect(page.locator(EDITOR)).not_to_be_focused()

    expect(page.locator(COUNT)).to_have_text(f"{len('KarteKompass mit Rucksack')}/10.000")
    _all_visible(_stations_to_element(page, STEP_SUBMIT, steps=10))
    page.keyboard.press("Enter")
    page.wait_for_url(f"{LIST}*/anlegen/zusammenfassung/")
    # Ein Leerzeichen vor einer Formatierung speichert Trix als geschütztes Leerzeichen; sichtbar ist es dasselbe.
    assert "<ul><li>Karte</li><li>Kompass mit <strong>Rucksack</strong></li></ul>" in _gespeichert().replace("\xa0", " ")


def test_e5_am_pc_nur_mit_der_tastatur(pc):
    _nur_mit_der_tastatur(pc)


def test_e5_am_handy_nur_mit_der_tastatur(handy):
    _nur_mit_der_tastatur(handy)


# ---------- E3, E5: am Handy im Dialog, mit Autokorrektur und Wortvorschlägen ----------


def _wie_am_handy(page: Page, first: str, composed: str, replaced: str, last: str) -> None:
    """Tippt wie ein Handy: ein Wort erst als Zusammensetzung, dann per Wortvorschlag ersetzt, danach weiter."""
    page.keyboard.type(first)
    page.keyboard.insert_text(composed)
    # Der Wortvorschlag ersetzt das angefangene Wort: Der Browser markiert es und setzt das Wort ein.
    page.locator(EDITOR).evaluate(
        "(element, length) => { const [, end] = element.editor.getSelectedRange();"
        " element.editor.setSelectedRange([end - length, end]); }", len(composed))
    page.keyboard.insert_text(replaced)
    page.keyboard.type(last)


def test_e3_am_handy_im_dialog_mit_wortvorschlaegen_und_die_kachel_zeigt_den_text(handy):
    login(handy)
    _erika_in_den_falken()
    entry = _pfingstlager()
    handy.goto(f"{LIST}{entry.key}/")
    section = handy.locator('[aria-labelledby="h-einladungstext"]')
    expect(section).to_contain_text("Noch kein Einladungstext.")
    section.get_by_role("link", name="Einladungstext bearbeiten").tap()

    handy.wait_for_url(f"{LIST}{entry.key}/einladungstext/")
    dialog = _dialog(handy)
    expect(dialog).to_be_visible()
    expect_modal(dialog)
    expect(dialog.locator("h2")).to_have_text("Einladungstext bearbeiten")
    # Am Handy füllt der breite Dialog den Bildschirm (Nachklärung N2).
    width = handy.viewport_size["width"]
    assert dialog.bounding_box()["width"] >= width - 1
    _editor_bereit(handy)
    _knopfleiste(handy)
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    handy.locator(EDITOR).tap()
    _wie_am_handy(handy, "Schlafsack und ", "Iso", "Isomatte", " nicht vergessen")
    expect(handy.locator(EDITOR)).to_have_text("Schlafsack und Isomatte nicht vergessen")
    dialog.get_by_role("button", name="Speichern").tap()

    handy.wait_for_url(f"{LIST}{entry.key}/")
    expect(handy.get_by_text(SAVED)).to_be_visible()
    expect(section).to_contain_text("Schlafsack und Isomatte nicht vergessen")
    _no_side_scroll(handy)
    entry.refresh_from_db()
    assert entry.invitation_text == "<div>Schlafsack und Isomatte nicht vergessen</div>"


# ---------- Breiter Dialog am PC, Escape (G7), Einfügen aus Word (E7) ----------


def test_g7_e7_am_pc_breiter_dialog_escape_aendert_nichts_und_eingefuegtes_aus_word(pc):
    login(pc)
    _erika_in_den_falken()
    entry = _pfingstlager()
    Event.objects.filter(pk=entry.pk).update(invitation_text="<div>Stand vorher</div>")
    address = f"{LIST}{entry.key}/einladungstext/"
    pc.goto(address)
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    # Breit: bis etwa 860 Pixel, breiter als der gewöhnliche Dialog.
    assert 700 < dialog.bounding_box()["width"] <= 862
    expect(pc.locator(EDITOR)).to_have_text("Stand vorher")

    pc.locator(EDITOR).click()
    pc.keyboard.press("ControlOrMeta+a")
    pc.keyboard.type("Wird verworfen")
    pc.keyboard.press("Escape")
    pc.wait_for_url(f"{LIST}{entry.key}/*")
    expect(_dialog(pc)).to_have_count(0)
    entry.refresh_from_db()
    assert entry.invitation_text == "<div>Stand vorher</div>"

    # E7: Eingefügtes aus Word behält nur die erlaubten Formatierungen; kein Text geht verloren.
    pc.goto(address)
    word = ('<p class="MsoNormal" style="font-family:Calibri"><span style="color:#C00000"><b>Packliste</b></span></p>'
            '<table><tr><td>Kluft</td><td>Halstuch</td></tr></table>')
    pc.locator(EDITOR).click()
    pc.keyboard.press("ControlOrMeta+a")
    # Wie Einfügen aus der Zwischenablage: ein Ereignis „paste“ mit dem HTML aus Word.
    pc.locator(EDITOR).evaluate(
        """(element, html) => {
            const data = new DataTransfer();
            data.setData('text/html', html);
            data.setData('text/plain', 'Packliste Kluft Halstuch');
            element.dispatchEvent(new ClipboardEvent('paste', {clipboardData: data, bubbles: true, cancelable: true}));
        }""", word)
    expect(pc.locator(EDITOR)).to_contain_text("Halstuch")
    _dialog(pc).get_by_role("button", name="Speichern").click()
    pc.wait_for_url(f"{LIST}{entry.key}/")
    expect(pc.get_by_text(SAVED)).to_be_visible()
    entry.refresh_from_db()
    # Trix setzt hinter den Absatz aus Word einen Zeilenumbruch; die Formatierung „fett“ bleibt.
    assert re.search(r"<strong>Packliste(<br>)?</strong>", entry.invitation_text), entry.invitation_text
    for kept in ("Kluft", "Halstuch"):
        assert kept in entry.invitation_text, kept
    for gone in ("style", "class", "table", "span"):
        assert gone not in entry.invitation_text, gone


# ---------- G1: zu lang ----------


def test_g1_die_zahl_wird_ueber_10000_rot_und_der_text_bleibt_im_editor(pc):
    login(pc)
    _erika_in_den_falken()
    entry = _pfingstlager()
    pc.goto(f"{LIST}{entry.key}/einladungstext/")
    pc.locator(EDITOR).click()
    pc.locator(EDITOR).evaluate("element => element.editor.insertString('a'.repeat(10000))")
    expect(pc.locator(COUNT)).to_have_text("10.000/10.000")
    expect(pc.locator(COUNTER)).not_to_have_class("ist-zu-lang")
    pc.keyboard.type("b")
    expect(pc.locator(COUNT)).to_have_text("10.001/10.000")
    expect(pc.locator(COUNTER)).to_have_class("a-zeichenzahl ist-zu-lang")
    # Nichts wird abgeschnitten.
    assert pc.locator(EDITOR).evaluate("element => element.editor.getDocument().toString().length") == 10_002

    _dialog(pc).get_by_role("button", name="Speichern").click()
    pc.wait_for_url(f"{LIST}{entry.key}/einladungstext/")
    expect(_dialog(pc).locator(".a-editor .invalid-feedback")).to_have_text(
        "Der Einladungstext ist zu lang: höchstens 10.000 Zeichen, jetzt 10.001.")
    expect(pc.locator(COUNT)).to_have_text("10.001/10.000")
    entry.refresh_from_db()
    assert entry.invitation_text == ""


# ---------- E6: ohne Skript ----------


def _ohne_skript(page: Page) -> None:
    login(page)
    _erika_in_den_falken()
    entry = _pfingstlager()
    Event.objects.filter(pk=entry.pk).update(invitation_text="<div>Die Anfahrt steht unten.</div>")
    page.goto(f"{LIST}{entry.key}/")
    page.locator('[aria-labelledby="h-einladungstext"]').get_by_role("link", name="Einladungstext bearbeiten").click()
    page.wait_for_url(f"{LIST}{entry.key}/einladungstext/")

    field = page.locator('textarea[name="invitation_text"]')
    expect(field).to_have_accessible_name("Einladungstext")
    expect(field).to_have_value("<div>Die Anfahrt steht unten.</div>")
    expect(page.get_by_text("Ohne JavaScript siehst du die Formatierung als Zeichen.")).to_be_visible()
    expect(page.locator(COUNTER)).to_be_hidden()
    _no_side_scroll(page)
    field.fill("<div>Die <strong>Anfahrt</strong> steht unten.</div>")
    page.get_by_role("button", name="Speichern").click()

    page.wait_for_url(f"{LIST}{entry.key}/")
    expect(page.locator('[aria-labelledby="h-einladungstext"] strong')).to_have_text("Anfahrt")
    _no_side_scroll(page)


def test_e6_am_pc_ohne_skript(pc_ohne_skript):
    _ohne_skript(pc_ohne_skript)


def test_e6_am_handy_ohne_skript(handy_ohne_skript):
    _ohne_skript(handy_ohne_skript)
