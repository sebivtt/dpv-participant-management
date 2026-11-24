"""Rauchtest: Datum und Uhrzeit stehen senkrecht mittig im Datumsfeld wie der Text im Textfeld (#409).

Wo der Browser den Text in seinem Datumsfeld zeichnet, sieht kein Skript; der Test misst es deshalb im
Bildschirmfoto des Felds. Wie der Browser ein Datum schreibt, hängt von seiner Spracheinstellung ab
(„02.06.2028“, „06/02/2028“), es beginnt aber immer mit Ziffern. Gemessen werden deshalb die ersten Ziffern
links im Feld und verglichen mit „02“ im Textfeld daneben: Stehen beide mittig, haben sie oben und unten
denselben Abstand zum Rand. Der Platzhalter („TT.MM.JJJJ“) steht auf derselben Grundlinie wie danach das
eingetragene Datum. Rechts zeichnen Chromium und Firefox ihr Kalender- oder Uhr-Symbol; dort misst der Test nicht.
Die Nummern verweisen auf die „Szenarien (24.11.2026)“ in #409; jeder Test läuft in Chromium, Firefox und
WebKit (der Technik hinter Safari, conftest.py). Alle Namen und Daten sind erfunden.
"""

import re
import struct
import zlib
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Locator, Page, expect

from events.models import Event
from rauchtests.conftest import BASE, HANDY, PC, _context, login
from rauchtests.test_benennen import _walhall_for_erika
from rauchtests.test_veranstaltungen import _erika_in_den_falken

pytestmark = pytest.mark.django_db(transaction=True)

LIST = f"{BASE}/veranstaltungen/"
STEP = "form#f-schritt"
DIALOG = "dialog.a-dialog"
# Ein Punkt Unterschied ist Kantenglättung; der Fehler aus #409 waren in Safari etwa 4 Punkte.
TOLERANZ = 1
# Rechts im Feld bleibt Platz für Kalender- oder Uhr-Symbol des Browsers und das Ausrufezeichen von Bootstrap.
RECHTS_FREI = 36
LINKS_FREI = 8  # links die runde Ecke des Rahmens; die Schrift beginnt erst nach dem Innenabstand
RAND = 3  # Rahmen des Felds, auch der rote, gehört nicht zur Schrift
# Gemessen werden nur die ersten Zeichen links, gut eine Ziffer breit: Wie der Browser das Datum schreibt, hängt
# von seiner Spracheinstellung ab („02.06.2028“, „06/02/2028“), es beginnt aber immer mit Ziffern.
ERSTE_ZEICHEN = 14


def _foto_fenster(browser, browser_name, device):
    """Ein Fenster wie `pc` oder `handy` aus conftest.py, in dem Playwright Bildschirmfotos machen darf.

    Für jedes Foto setzt Playwright einen eigenen Stil in die Seite; die Sicherheitsrichtlinie des Tools (#278)
    verbietet ihn, und der Wächter in conftest.py meldete das. Nur in diesen Fenstern gilt die Richtlinie
    deshalb nicht; dass das Tool sie einhält, prüfen die übrigen Rauchtests.
    """
    context = _context(browser, browser_name, device, bypass_csp=True)
    yield context.new_page()
    context.close()


@pytest.fixture
def pc(browser, browser_name, tool):
    yield from _foto_fenster(browser, browser_name, PC)


@pytest.fixture
def handy(browser, browser_name, tool):
    yield from _foto_fenster(browser, browser_name, HANDY)


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2028, 1, 5))


def _pixel_zeilen(png: bytes) -> list[list[tuple[int, int, int]]]:
    """Liest ein Bildschirmfoto von Playwright (PNG, 8 Bit je Farbe) als Zeilen von Farben, ohne weiteres Paket."""
    position, daten, breite, hoehe, art = 8, b"", 0, 0, 0
    while position < len(png):
        laenge, typ = struct.unpack(">I4s", png[position:position + 8])
        inhalt = png[position + 8:position + 8 + laenge]
        position += 12 + laenge
        if typ == b"IHDR":
            breite, hoehe, tiefe, art = struct.unpack(">IIBB", inhalt[:10])
            assert tiefe == 8 and art in (2, 6), f"unerwartetes PNG: Tiefe {tiefe}, Farbart {art}"
        elif typ == b"IDAT":
            daten += inhalt
    roh, je_punkt = zlib.decompress(daten), 4 if art == 6 else 3
    schritt, zeilen, vorige, stelle = breite * je_punkt, [], bytearray(breite * je_punkt), 0
    for _ in range(hoehe):
        filter_art, zeile = roh[stelle], bytearray(roh[stelle + 1:stelle + 1 + schritt])
        stelle += 1 + schritt
        for i in range(schritt):
            links = zeile[i - je_punkt] if i >= je_punkt else 0
            oben, oben_links = vorige[i], vorige[i - je_punkt] if i >= je_punkt else 0
            if filter_art == 1:
                zeile[i] = (zeile[i] + links) & 255
            elif filter_art == 2:
                zeile[i] = (zeile[i] + oben) & 255
            elif filter_art == 3:
                zeile[i] = (zeile[i] + (links + oben) // 2) & 255
            elif filter_art == 4:
                p = links + oben - oben_links
                naechste = min((abs(p - links), 0, links), (abs(p - oben), 1, oben), (abs(p - oben_links), 2, oben_links))
                zeile[i] = (zeile[i] + naechste[2]) & 255
        zeilen.append([tuple(zeile[x * je_punkt:x * je_punkt + 3]) for x in range(breite)])
        vorige = zeile
    return zeilen


def _schrift(feld: Locator) -> dict:
    """Abstand der ersten Zeichen links im Feld zum oberen und unteren Rand des Bilds, in Punkten der Seite."""
    # Ohne Fokus gibt es keine Schreibmarke und keinen markierten Teil des Datums; der blaue Rahmen des Fokus
    # blendet langsam aus, Playwright beendet das Ausblenden vor dem Foto.
    feld.blur()
    zeilen = _pixel_zeilen(feld.screenshot(scale="css", animations="disabled"))
    hoehe, breite = len(zeilen), len(zeilen[0])
    grund = zeilen[hoehe // 2][RAND]

    def ist_schrift(x: int, y: int) -> bool:
        return sum(abs(a - b) for a, b in zip(zeilen[y][x], grund, strict=True)) > 200

    innen = range(RAND, hoehe - RAND)
    links = next((x for x in range(LINKS_FREI, breite - RECHTS_FREI) if any(ist_schrift(x, y) for y in innen)), None)
    assert links is not None, "im Feld ist keine Schrift zu sehen"
    reihen = [y for y in innen if any(ist_schrift(x, y) for x in range(links, links + ERSTE_ZEICHEN))]
    return {"oben": reihen[0], "unten": hoehe - 1 - reihen[-1]}


def _gleich(gemessen: dict, vorbild: dict, was: str) -> None:
    for seite in ("oben", "unten"):
        assert abs(gemessen[seite] - vorbild[seite]) <= TOLERANZ, f"{was}: {gemessen}, Vorbild {vorbild}"


def _ziffern_mittig(textfeld: Locator, feld: Locator) -> None:
    """Die ersten Ziffern im Datums- oder Uhrzeitfeld stehen so wie Ziffern im Textfeld daneben."""
    expect(feld).to_be_visible()
    hoch, vorbild_hoch = feld.bounding_box()["height"], textfeld.bounding_box()["height"]
    assert abs(hoch - vorbild_hoch) < 0.5, f"Feld {hoch} hoch, Textfeld {vorbild_hoch}"
    vorher = textfeld.input_value()
    textfeld.fill("02")
    vorbild = _schrift(textfeld)
    textfeld.fill(vorher)
    _gleich(_schrift(feld), vorbild, f"{feld.get_attribute('name')} = {feld.input_value()!r} gegen „02“ im Textfeld")


def _platzhalter_mittig(textfeld: Locator, feld: Locator, wert: str) -> None:
    """Der Platzhalter steht auf derselben Höhe wie danach das eingetragene Datum, und das steht mittig."""
    expect(feld).to_have_value("")
    platzhalter = _schrift(feld)
    feld.fill(wert)
    _ziffern_mittig(textfeld, feld)
    # Verglichen wird die Grundlinie: Die ersten Zeichen des Platzhalters sind je nach Sprache Groß- oder
    # Kleinbuchstaben („TT“, „mm“), stehen aber wie die Ziffern auf der Grundlinie.
    eingetragen = _schrift(feld)
    assert abs(platzhalter["unten"] - eingetragen["unten"]) <= TOLERANZ, (
        f"{feld.get_attribute('name')}: Platzhalter {platzhalter}, eingetragen {eingetragen}")


def _schritt_1_mittig(page: Page) -> None:
    """AA1: Platzhalter und vorausgefüllte Uhrzeiten, dann ein eingetragenes Datum, mittig wie im Feld „Name“."""
    page.goto(f"{LIST}erstellen/")
    name = page.locator(f'{STEP} input[name="name"]')
    _ziffern_mittig(name, page.locator(f'{STEP} input[name="start_time"]'))
    _ziffern_mittig(name, page.locator(f'{STEP} input[name="end_time"]'))
    _platzhalter_mittig(name, page.locator(f'{STEP} input[name="start"]'), "2028-06-02")
    _platzhalter_mittig(name, page.locator(f'{STEP} input[name="end"]'), "2028-06-05")


def _stift_dialog_mittig(page: Page) -> None:
    """AA2: Im Dialog des Stifts auf der Leitungsseite stehen Datum und Uhrzeit ebenso mittig."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    found = Event.objects.create(name="Pfingstlager 2028", start=date(2028, 6, 2), end=date(2028, 6, 5))
    found.leads.add(erika)
    page.goto(f"{LIST}{found.key}/bearbeiten/")
    name = page.locator(f'{DIALOG} input[name="name"]')
    _ziffern_mittig(name, page.locator(f'{DIALOG} input[name="start"]'))
    _ziffern_mittig(name, page.locator(f'{DIALOG} input[name="end"]'))
    page.locator(f'{DIALOG} input[name="start_time"]').fill("18:00")
    _ziffern_mittig(name, page.locator(f'{DIALOG} input[name="start_time"]'))


def test_aa1_am_pc_schritt_1_von_veranstaltung_erstellen(pc):
    login(pc)
    _erika_in_den_falken()
    _schritt_1_mittig(pc)


def test_aa2_am_pc_im_dialog_des_stifts(pc):
    login(pc)
    _erika_in_den_falken()
    _stift_dialog_mittig(pc)


def test_aa2_am_handy_schritt_1_und_dialog_des_stifts(handy):
    login(handy)
    _erika_in_den_falken()
    _schritt_1_mittig(handy)
    _stift_dialog_mittig(handy)


def test_aa3_geburtsdatum_im_dialog_verwaltete_person_anlegen(pc):
    login(pc)
    units = _walhall_for_erika()
    pc.goto(f"{BASE}/organisation/{units['falken'].key}/verwaltete-person/anlegen/")
    _platzhalter_mittig(pc.locator(f'{DIALOG} input[name="first_name"]'), pc.locator(f'{DIALOG} input[name="birth_date"]'),
                        "2015-05-14")


def test_aa4_mit_fehler_bleibt_alles_mittig(pc):
    login(pc)
    _erika_in_den_falken()
    pc.goto(f"{LIST}erstellen/")
    name = pc.locator(f'{STEP} input[name="name"]')
    name.fill("Pfingstlager 2028")
    pc.locator(f'{STEP} input[name="start"]').fill("2028-06-05")
    pc.locator(f'{STEP} input[name="end"]').fill("2028-06-02")
    pc.get_by_role("button", name="Weiter").click()
    end = pc.locator(f'{STEP} input[name="end"]')
    expect(end).to_have_accessible_description("Das Ende liegt vor dem Beginn.")
    expect(end).to_have_class(re.compile(r"\bis-invalid\b"))
    # Gleicher Abstand oben und unten wie im Textfeld heißt auch: oben und unten ist nichts abgeschnitten.
    _ziffern_mittig(name, end)
    _ziffern_mittig(name, pc.locator(f'{STEP} input[name="end_time"]'))


@pytest.mark.bausteinkatalog
def test_im_bausteinkatalog(pc, settings):
    settings.BUILDING_BLOCKS_VISIBLE = True
    login(pc)
    pc.goto(f"{BASE}/bausteine/")
    textfeld = pc.locator("section[aria-labelledby='h-textfeld'] input.form-control").first
    section = pc.locator("section[aria-labelledby='h-datumsfeld']")
    for feld in ("birth_date", "start", "start_time"):
        _ziffern_mittig(textfeld, section.locator(f'input[name="{feld}"]'))
