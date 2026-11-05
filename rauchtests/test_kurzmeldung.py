"""Rauchtest der kurzen Meldungen und der Fehlermeldung an der Stelle der Handlung im Browser (#186, NFA-03).

Die Nummern verweisen auf Sebastians „Szenarien (27.10.2026)“ in #186. Was der Server
ausliefert, prüft tests/test_kurzmeldung.py. Damit die Tests nicht sekundenlang warten, stellt
Playwright die Uhr der Seite: Sie steht still, bis der Test sie vorstellt (`_later`). Jeder Test
läuft in Chromium, Firefox und WebKit (conftest.py). Alle Konten und Daten sind erfunden.
"""

import time
from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from playwright.sync_api import Error, Page, expect

from rauchtests.conftest import AXE, BASE, PC, login, run_axe
from rauchtests.test_rauchtest import _tab_to_element

pytestmark = pytest.mark.django_db(transaction=True)

SAVED = "Dein Fahrtenname ist gespeichert."
DELETED = "Dein Fahrtenname ist gelöscht."
FAILED = "Dein Fahrtenname konnte nicht gespeichert werden. Versuche es noch einmal."
LEISTE = 264  # Breite der Seitenleiste am PC (core/static/core/app.css)


def _stop_clock(page: Page) -> None:
    """Hält die Uhr aller folgenden Seiten an; Zeit vergeht nur noch mit `_later`."""
    # Bei angehaltener Uhr darf axe nie aufgerufen werden: axe wartet auf Zeitgeber, die dann nie
    # ablaufen, und der Test hängt (#186). `_axe` lässt die Uhr deshalb vorher kurz weiterlaufen.
    page.clock.install(time=datetime(2026, 10, 27, 10, 0, 0))
    page.clock.pause_at(datetime(2026, 10, 27, 10, 0, 1))


def _later(page: Page, ms: int) -> None:
    page.clock.run_for(ms)


def _pause_soon(page: Page) -> None:
    now = page.evaluate("Date.now()")
    page.clock.pause_at(datetime.fromtimestamp(now / 1000 + 0.05))


def _axe(page: Page) -> list[str]:
    """Prüfung auf Barrierefreiheit; axe wartet selbst auf Zeitgeber, deshalb läuft die Uhr dafür kurz weiter.

    Eine kurze Meldung wartet `run_axe` selbst ab und hält sie währenddessen fest (#232).
    """
    page.clock.resume()
    try:
        return run_axe(page)
    finally:
        try:
            _pause_soon(page)
        except Error as error:
            # Ist der Browser langsamer als der Puffer von 0,05 s, liegt der Haltepunkt schon in der
            # Vergangenheit. Playwright hält die Uhr trotzdem zuerst an und wirft erst danach (#253).
            # Ein zweiter Versuch mit frisch gelesener Zeit klappt also; jede andere Meldung und ein
            # zweites Scheitern bleiben ein Fehler.
            if "Cannot fast-forward to the past" not in str(error):
                raise
            _pause_soon(page)


def _short(page: Page):
    return page.locator("#kurzmeldungen .a-kurz")


def _set_scout_name(value: str) -> None:
    get_user_model().objects.filter(username="erika.testfrau").update(scout_name=value)


def _submit(page: Page, action) -> None:
    """Schickt mit `action` das Formular ab und wartet, bis die neue Seite geladen ist.

    `wait_for_load_state` allein reicht nicht: Startet der Browser den Seitenwechsel erst etwas
    später (WebKit auf GitHub), gilt noch die alte Seite als geladen. `_later` stellt dann deren
    Uhr vor, und auf der neuen erscheint die Meldung nie (#197).
    """
    with page.expect_navigation(wait_until="load"):
        action()


def _save(page: Page, value: str) -> None:
    """Öffnet das Feld „Fahrtenname“, trägt `value` ein und speichert mit Enter."""
    page.locator("[data-oeffnen]").click()
    field = page.get_by_label("Fahrtenname", exact=True)
    field.fill(value)
    _submit(page, lambda: field.press("Enter"))


def _scrolled(page: Page) -> None:
    """Wartet in echter Zeit, bis sanftes Scrollen fertig ist; die Uhr der Seite steht dabei still."""
    last, deadline = None, time.monotonic() + 5
    while time.monotonic() < deadline:
        now = page.evaluate("scrollY")
        if now == last:
            return
        last = now
        time.sleep(0.2)
    raise AssertionError("Die Seite scrollt nach 5 Sekunden noch")


def _box(locator) -> dict:
    return locator.evaluate(
        """e => { const b = e.getBoundingClientRect();
            return {left: b.left, right: b.right, top: b.top, bottom: b.bottom, width: b.width, height: b.height,
                    vw: document.documentElement.clientWidth, vh: window.innerHeight,
                    scroll: document.documentElement.scrollWidth}; }"""
    )


# Szenarien 1, 2, 3, 6, 7, 14 und 15
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_nach_dem_speichern_kurz_unten_mittig_und_wieder_weg(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    _set_scout_name("Falkenflug")
    _stop_clock(page)
    page.goto(f"{BASE}/profil/")
    # Der leere Bereich ist für Vorleseprogramme schon da, bevor eine Meldung hineinkommt (unabhängige Prüfung).
    assert page.locator("#kurzmeldungen").evaluate("e => getComputedStyle(e).display") != "none"

    # Szenario 1: unten mittig, mit Schatten und ×; oben auf der Seite keine Erfolgsmeldung.
    _save(page, "Kiwi")
    _later(page, 300)
    notice = _short(page)
    expect(notice).to_have_count(1)
    expect(notice).to_contain_text(SAVED)
    expect(notice).to_have_class("a-meldung ist-erfolg a-kurz")
    expect(page.locator("main .a-meldung.ist-erfolg")).to_have_count(1)
    assert notice.evaluate("e => getComputedStyle(e).boxShadow") != "none"
    close = notice.get_by_role("button", name="Meldung schließen")
    expect(close).to_be_visible()
    # Szenario 3: Der Cursor bleibt im Feld; das Vorleseprogramm hört „Erfolg: …“ aus dem Bereich.
    expect(page.locator("[data-oeffnen]")).to_be_focused()
    area = page.locator("#kurzmeldungen")
    expect(area).to_have_attribute("aria-live", "polite")
    assert "Erfolg: " in area.evaluate("e => e.textContent")
    expect(notice).not_to_have_attribute("role", "status")

    # Szenarien 14 und 15: Lage am PC und am Handy, nichts ragt über den Rand.
    box = _box(notice)
    assert box["scroll"] <= box["vw"], box
    assert box["vh"] - 40 <= box["bottom"] <= box["vh"], box
    if device == "pc":
        assert box["left"] >= LEISTE and box["width"] <= 560, box
        middle = (LEISTE + box["vw"]) / 2
        assert abs((box["left"] + box["right"]) / 2 - middle) < 2, box
    else:
        assert 0 < box["left"] <= 16 and box["vw"] - 16 <= box["right"] < box["vw"], box
    close_box = _box(close)
    assert round(close_box["width"]) >= 40 and round(close_box["height"]) >= 40 and close_box["right"] <= box["right"], close_box
    # Die Maus hält die Meldung während der Prüfung fest; danach zählt sie neu.
    notice.hover()
    assert _axe(page) == []
    page.mouse.move(5, 5)

    # Nach rund 6 Sekunden verschwindet sie von selbst.
    _later(page, 5000)
    expect(notice).to_have_count(1)
    _later(page, 1500)
    expect(notice).to_have_count(0)

    # Szenario 7: Nach dem Neuladen erscheint sie nicht noch einmal.
    page.reload()
    _later(page, 300)
    expect(_short(page)).to_have_count(0)
    expect(page.locator("main .a-meldung.ist-erfolg")).to_have_count(0)

    # Szenarien 2 und 6: gelöscht ebenso kurz; × schließt sofort.
    page.get_by_role("button", name="Fahrtenname leeren").click()
    _submit(page, page.get_by_role("button", name="Speichern").click)
    _later(page, 300)
    expect(_short(page)).to_contain_text(DELETED)
    if device == "handy":
        _short(page).get_by_role("button", name="Meldung schließen").tap()
    else:
        _short(page).get_by_role("button", name="Meldung schließen").click()
    expect(_short(page)).to_have_count(0)
    expect(page.locator("main .a-meldung.ist-erfolg")).to_have_count(0)


# Szenarien 4 und 5: Maus darüber und nur mit der Tastatur
def test_bleibt_stehen_mit_maus_oder_fokus_und_fokus_kehrt_zurueck(pc):
    login(pc)
    _set_scout_name("Falkenflug")
    _stop_clock(pc)
    pc.goto(f"{BASE}/profil/")
    _save(pc, "Kiwi")
    _later(pc, 300)
    notice = _short(pc)
    rest = pc.locator("[data-oeffnen]")
    expect(rest).to_be_focused()

    # Szenario 4: Solange die Maus darauf ist, bleibt sie; danach zählt sie neu.
    notice.hover()
    _later(pc, 20000)
    expect(notice).to_have_count(1)
    pc.mouse.move(5, 5)
    _later(pc, 5000)
    expect(notice).to_have_count(1)
    _later(pc, 1500)
    expect(notice).to_have_count(0)

    # Szenario 5: Mit Tab zum ×; solange der Fokus darin ist, bleibt sie; Enter schließt, der Fokus geht zurück.
    _set_scout_name("Falkenflug")
    pc.goto(f"{BASE}/profil/")
    _save(pc, "Kiwi")
    _later(pc, 300)
    expect(rest).to_be_focused()
    station = _tab_to_element(pc, ".a-kurz-zu", steps=4)
    assert station["sichtbar"] and station["kontrast"] >= 3, station
    _later(pc, 20000)
    expect(notice).to_have_count(1)
    pc.keyboard.press("Enter")
    expect(notice).to_have_count(0)
    expect(rest).to_be_focused()
    expect(rest).to_contain_text("Kiwi")


# Szenarien 8 und 8a: Fehlermeldung direkt unter dem Feld
def test_speichern_scheitert_fehlermeldung_unter_dem_feld_im_bild(browser, browser_name, tool, monkeypatch):
    # Niedriges Fenster, damit die Stelle unter dem Feld ohne Hinscrollen nicht zu sehen wäre.
    context = browser.new_context(viewport={"width": 1366, "height": 330}, locale="de-DE")
    page = context.new_page()
    try:
        login(page)
        _set_scout_name("Falkenflug")
        _stop_clock(page)
        page.goto(f"{BASE}/profil/")

        def fail(self, *args, **kwargs):
            raise DatabaseError("Datenbank weg")

        monkeypatch.setattr(get_user_model(), "save", fail)
        _save(page, "Kiwi")
        _later(page, 300)

        box = page.locator("[data-antippfeld]")
        error = box.locator(".a-meldung.ist-fehler")
        expect(error).to_contain_text(FAILED)
        expect(error).to_have_attribute("role", "alert")
        expect(page.locator("main .a-meldung.ist-fehler")).to_have_count(1)
        field = page.get_by_label("Fahrtenname", exact=True)
        expect(field).to_be_focused()
        expect(field).to_have_value("Kiwi")
        # Der Bildschirm zeigt die Stelle: Feld und Fehlermeldung ganz im Bild. Bootstrap scrollt sanft;
        # erst messen, wenn die Seite steht.
        _scrolled(page)
        for part in (field, error):
            where = _box(part)
            assert 0 <= where["top"] and where["bottom"] <= where["vh"], where
        # Sie verschwindet nicht von selbst und ist nicht kurz.
        _later(page, 20000)
        expect(error).to_be_visible()
        expect(_short(page)).to_have_count(0)
        # Verwerfen lässt sie stehen, und sie bleibt mit der Eingabe verknüpft (unabhängige Prüfung).
        page.keyboard.press("Escape")
        expect(error).to_be_visible()
        page.locator("[data-oeffnen]").click()
        expect(field).to_have_attribute("aria-describedby", "id_scout_name-meldung id_scout_name-zahl")

        # Szenario 8a: erneut speichern klappt; die Fehlermeldung ist weg, unten kurz die Erfolgsmeldung.
        monkeypatch.undo()
        field.fill("Kiwi")
        _submit(page, lambda: field.press("Enter"))
        _later(page, 300)
        expect(page.locator("main .a-meldung.ist-fehler")).to_have_count(0)
        expect(_short(page)).to_contain_text(SAVED)
    finally:
        context.close()


# Schickt ein Formular erst nach zwei zusätzlichen Abrufen der Seite ab. So kommt die neue Seite
# später, wie auf GitHub in WebKit (#197).
LATE_SUBMIT = """
window.addEventListener("submit", function (event) {
  if (event.defaultPrevented) return;
  event.preventDefault();
  var form = event.target;
  fetch(location.href).then(function () { return fetch(location.href); }).then(function () {
    HTMLFormElement.prototype.submit.call(form);
  });
});
"""


def test_speichern_wartet_auf_die_neue_seite_auch_wenn_sie_spaet_kommt(pc):
    """Wartete `_save` nur auf „Seite geladen“, stellte `_later` hier die Uhr der alten Seite vor, und die Meldung fehlte (#197)."""
    login(pc)
    _set_scout_name("Falkenflug")
    _stop_clock(pc)
    pc.add_init_script(LATE_SUBMIT)
    pc.goto(f"{BASE}/profil/")
    _save(pc, "Kiwi")
    _later(pc, 300)
    expect(_short(pc)).to_contain_text(SAVED)


# Szenarien 12, 13 und 18: Stapel im Bausteinkatalog, und Szenario 15: langer Text am Handy
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_stapel_im_katalog_hoechstens_drei_neueste_unten(request, browser_name, device):
    page: Page = request.getfixturevalue(device)
    login(page)
    _stop_clock(page)
    page.goto(f"{BASE}/bausteine/")
    section = page.locator("section[aria-labelledby='h-kurzmeldung']")
    expect(section.get_by_role("heading", name="Kurze Meldung")).to_be_visible()

    # Information mit langem Text: bricht um, × bleibt im Bild.
    section.get_by_role("button", name="Information zeigen").click()
    _later(page, 300)
    info = _short(page)
    expect(info).to_have_class("a-meldung ist-info a-kurz")
    box = _box(info)
    assert box["scroll"] <= box["vw"] and box["left"] >= 0 and box["right"] <= box["vw"], box
    close = _box(info.get_by_role("button", name="Meldung schließen"))
    assert close["right"] <= box["right"] and close["left"] >= box["left"], close
    info.hover()
    assert _axe(page) == []
    info.get_by_role("button", name="Meldung schließen").click()
    expect(_short(page)).to_have_count(0)

    # Vier nacheinander: höchstens drei, die neueste unten, jede mit eigener Zeit.
    section.get_by_role("button", name="Vier nacheinander zeigen").click()
    # Die Maus weg von den Meldungen, sonst hält sie sie fest (Szenario 4).
    page.mouse.move(5, 5)
    texts = []
    for _ in range(4):
        _later(page, 700)
        texts = _short(page).all_inner_texts()
    assert len(texts) == 3, texts
    tops = [b["top"] for b in (_box(n) for n in _short(page).all())]
    assert tops == sorted(tops), tops
    # Die älteste ist sofort weg; die übrigen verschwinden der Reihe nach.
    assert not any("Falken" in text for text in texts), texts
    assert "Biber" in texts[-1], texts
    _later(page, 6000 - 3 * 700 + 300)
    expect(_short(page)).to_have_count(2)
    _later(page, 700)
    expect(_short(page)).to_have_count(1)
    _later(page, 700)
    expect(_short(page)).to_have_count(0)

    # Szenario 12: Darüberfahren hält alle an, nicht nur die unter der Maus.
    section.get_by_role("button", name="Vier nacheinander zeigen").click()
    page.mouse.move(5, 5)
    for _ in range(4):
        _later(page, 700)
    _short(page).last.hover()
    _later(page, 20000)
    expect(_short(page)).to_have_count(3)
    page.mouse.move(5, 5)
    _later(page, 5000)
    expect(_short(page)).to_have_count(3)
    _later(page, 1500)
    expect(_short(page)).to_have_count(0)


# Szenario 16: Bewegung reduzieren
def test_bewegung_reduzieren_ohne_bewegung(browser, browser_name, tool):
    context = browser.new_context(reduced_motion="reduce", locale="de-DE", **PC)
    page = context.new_page()
    try:
        login(page)
        _stop_clock(page)
        page.goto(f"{BASE}/bausteine/")
        page.get_by_role("button", name="Erfolg zeigen").click()
        _later(page, 300)
        notice = _short(page)
        expect(notice).to_have_count(1)
        assert notice.evaluate("e => e.getAnimations().length") == 0
        assert notice.evaluate("e => getComputedStyle(e).transform") == "none"
        _later(page, 6000)
        expect(notice).to_have_count(0)
    finally:
        context.close()


def test_mit_bewegung_blendet_sie_sanft_ein(pc):
    """Gegenprobe zu Szenario 16: ohne die Einstellung gleitet sie kurz herein."""
    login(pc)
    _stop_clock(pc)
    pc.goto(f"{BASE}/bausteine/")
    pc.get_by_role("button", name="Erfolg zeigen").click()
    _later(pc, 150)
    assert _short(pc).evaluate("e => e.getAnimations().length") >= 1


# Szenario 17: ohne Skript fest oben wie bisher
def test_ohne_skript_steht_die_meldung_fest_oben(pc, browser):
    login(pc)
    context = browser.new_context(java_script_enabled=False, storage_state=pc.context.storage_state(), **PC)
    page = context.new_page()
    try:
        page.goto(f"{BASE}/profil/")
        field = page.get_by_label("Fahrtenname", exact=True)
        field.fill("Kiwi")
        page.get_by_role("button", name="Speichern").click()
        notice = page.locator("main .a-meldung.ist-erfolg")
        expect(notice).to_contain_text(SAVED)
        # Mit Skript nimmt sie oben keinen Platz ein (#226), ohne Skript ist sie dort zu sehen.
        expect(notice).to_be_visible()
        expect(notice.get_by_role("button", name="Meldung schließen")).to_be_hidden()
        heading = _box(page.get_by_role("heading", level=1))
        where = _box(notice)
        assert where["top"] > heading["bottom"] and where["bottom"] < _box(field)["top"], where
        assert notice.evaluate("e => getComputedStyle(e).position") == "static"
        assert notice.evaluate("e => getComputedStyle(e).boxShadow") == "none"
    finally:
        context.close()


def test_axe_haelt_die_uhr_auch_an_wenn_der_browser_langsam_ist(pc, monkeypatch):
    """Auch wenn der Haltepunkt von `_axe` wegen eines langsamen Browsers schon vorbei ist, muss die Uhr stehen (#253)."""
    _stop_clock(pc)
    pc.goto(f"{BASE}/")
    clock = pc.clock
    assert pc.clock is clock  # Die Hülle unten trifft nur, wenn `page.clock` jedes Mal dasselbe Objekt liefert.
    original = clock.pause_at

    calls = []

    def slow_pause_at(time_to_pause):
        calls.append(time_to_pause)
        time.sleep(0.2)
        return original(time_to_pause)

    def assert_clock_stands():
        first = pc.evaluate("Date.now()")
        time.sleep(0.3)
        assert pc.evaluate("Date.now()") == first

    monkeypatch.setattr(clock, "pause_at", slow_pause_at)
    _axe(pc)
    assert len(calls) == 2  # Der erste Versuch kam zu spät, der zweite traf die stehende Uhr.
    assert_clock_stands()
    # Auch die nächste Seite übernimmt die stehende Uhr, obwohl ein Versuch gescheitert ist.
    pc.reload()
    assert_clock_stands()


# Prüfung auf Barrierefreiheit und kurze Meldung (#232): `run_axe` wartet, bis die Meldung ganz sichtbar ist,
# und hält sie während der Prüfung fest.
SHORT_FADE_SLOWED = "2s"  # Ein- und Ausblenden so lang, dass ein Treffer mitten darin sicher ist
SHORT_TIME = 6000  # Standzeit einer kurzen Meldung (SHORT_TIME in core/static/core/app.js)


def _axe_file(tmp_path, delay_ms: int):
    """Eine Kopie von axe, deren `run` erst nach `delay_ms` losläuft und festhält, wie die Meldung dann aussieht.

    Das Ergebnis steht danach in `window.axeSaw`: wie viele Meldungen offen sind, wie viele gerade
    ausblenden und wie deckend die erste ist.
    """
    wrapper = f"""
;(function () {{
    const original = axe.run;
    axe.run = async function (...args) {{
        await new Promise((resolve) => setTimeout(resolve, {delay_ms}));
        const all = Array.from(document.querySelectorAll('#kurzmeldungen .a-kurz'));
        window.axeSaw = {{
            open: all.filter((n) => !n.classList.contains('ist-weg')).length,
            fading: all.filter((n) => n.classList.contains('ist-weg')).length,
            opacity: all.length ? Number(getComputedStyle(all[0]).opacity) : null,
        }};
        return original.apply(this, args);
    }};
}})();
"""
    path = tmp_path / "axe-langsam.js"
    path.write_text(AXE.read_text(encoding="utf-8") + wrapper, encoding="utf-8")
    return path


def _slow_fade(page: Page) -> None:
    """Streckt Ein- und Ausblenden der kurzen Meldung auf jeder neuen Seite, auch nach dem Speichern."""
    page.add_init_script(
        "document.addEventListener('DOMContentLoaded', () => {"
        "const s = document.createElement('style');"
        f"s.textContent = '.a-meldung.a-kurz, .a-meldung.a-kurz.ist-weg {{ animation-duration: {SHORT_FADE_SLOWED} !important; }}';"
        "document.head.appendChild(s); });"
    )


@pytest.mark.parametrize("device", ["pc", "handy"])
def test_axe_beginnt_nicht_mitten_im_einblenden(request, browser_name, monkeypatch, tmp_path, device):
    """Erscheint die Meldung erst während der Prüfung und blendet langsam ein, sieht axe sie erst, wenn sie ganz da ist."""
    page: Page = request.getfixturevalue(device)
    monkeypatch.setattr("rauchtests.conftest.AXE", _axe_file(tmp_path, delay_ms=1000))
    login(page)
    _set_scout_name("Falkenflug")
    _slow_fade(page)
    _stop_clock(page)
    page.goto(f"{BASE}/profil/")
    _save(page, "Kiwi")
    # Die Uhr steht noch: Die Meldung ist auf der neuen Seite noch gar nicht im Bereich.
    expect(_short(page)).to_have_count(0)
    assert _axe(page) == []
    saw = page.evaluate("window.axeSaw")
    assert saw == {"open": 1, "fading": 0, "opacity": 1}, saw


@pytest.mark.parametrize("device", ["pc", "handy"])
def test_axe_haelt_die_meldung_fest_auch_wenn_sie_gleich_verschwunden_waere(request, browser_name, monkeypatch, tmp_path, device):
    """Die Meldung hätte noch gut eine Sekunde; die Prüfung dauert drei. Sie darf trotzdem nicht ausblenden."""
    page: Page = request.getfixturevalue(device)
    monkeypatch.setattr("rauchtests.conftest.AXE", _axe_file(tmp_path, delay_ms=3000))
    login(page)
    _set_scout_name("Falkenflug")
    _stop_clock(page)
    page.goto(f"{BASE}/profil/")
    _save(page, "Kiwi")
    _later(page, 300)
    _later(page, SHORT_TIME - 1700)
    expect(_short(page)).to_have_count(1)
    assert _axe(page) == []
    saw = page.evaluate("window.axeSaw")
    assert saw == {"open": 1, "fading": 0, "opacity": 1}, saw
    # Danach zählt sie neu und verschwindet von selbst.
    _later(page, 100)
    expect(_short(page)).to_have_count(1)
    _later(page, SHORT_TIME + 500)
    expect(_short(page)).to_have_count(0)


def test_axe_meldet_einen_zu_blassen_text_der_kurzen_meldung_trotzdem(pc):
    """Gegenprobe: Das Warten und Festhalten schwächt die Prüfung nicht ab; ein echter Kontrastfehler fällt auf."""
    pc.add_init_script(
        "document.addEventListener('DOMContentLoaded', () => {"
        "const s = document.createElement('style');"
        "s.textContent = '.a-kurz p { color: #d0d0d0 !important; }';"
        "document.head.appendChild(s); });"
    )
    login(pc)
    _set_scout_name("Falkenflug")
    _stop_clock(pc)
    pc.goto(f"{BASE}/profil/")
    _save(pc, "Kiwi")
    _later(pc, 300)
    expect(_short(pc)).to_have_count(1)
    found = _axe(pc)
    assert any(line.startswith("color-contrast") for line in found), found
    expect(_short(pc)).to_have_count(1)
