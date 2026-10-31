"""Rauchtest: Das × der Dialoge, der Menüknopf und das × im Handy-Menü heben sich beim Darüberfahren
und Drücken hervor wie die zarten Knöpfe (#216).

Ob ein Knopf sich unter der Maus hervorhebt, entscheidet erst der Browser; deshalb lässt es sich nur
hier prüfen. Die Nummern verweisen auf die Szenarien zu #216 (30.10.2026). S6 (das × schließt wie
bisher) prüft schon test_dialog.py (G2). Jeder Test läuft in Chromium, Firefox und WebKit (conftest.py).
Alle Konten und Daten sind erfunden.
"""

import pytest
from playwright.sync_api import Locator, expect

from rauchtests.conftest import BASE, focus_visible, login
from rauchtests.test_dialog import _benennen
from rauchtests.test_rauchtest import _tab_key

pytestmark = pytest.mark.django_db(transaction=True)

# Fläche, Farbe von Symbol und Schrift, Rahmen; die Werte aus app.css (:root)
RUHE = ["rgb(255, 255, 255)", "rgb(27, 37, 50)", "rgb(219, 226, 234)"]  # --flaeche, --text, --linie
HERVORGEHOBEN = ["rgb(233, 239, 246)", "rgb(26, 75, 126)", "rgb(26, 75, 126)"]  # --dpv-hauch, --dpv, --dpv


def _aussehen(knopf: Locator) -> list[str]:
    return knopf.evaluate(
        "e => { const s = getComputedStyle(e); return [s.backgroundColor, s.color, s.borderTopColor]; }"
    )


def _hebt_sich_hervor(knopf: Locator) -> None:
    """Ruhig, unter der Maus und beim Drücken hervorgehoben, nach dem Wegfahren wieder ruhig."""
    page = knopf.page
    page.mouse.move(0, 0)
    assert _aussehen(knopf) == RUHE, "in Ruhe"
    knopf.hover()
    assert _aussehen(knopf) == HERVORGEHOBEN, "unter der Maus"
    page.mouse.move(0, 0)
    assert _aussehen(knopf) == RUHE, "nach dem Wegfahren"
    # Drücken, ohne loszulassen; losgelassen wird erst in der Ecke des umgebenden Kopfs. Dorthin geht der
    # Klick, den der Browser danach auslöst; neben dem Dialog schlösse er ihn.
    knopf.hover()
    page.mouse.down()
    try:
        assert _aussehen(knopf) == HERVORGEHOBEN, "beim Drücken"
    finally:
        kopf = knopf.locator("xpath=..").bounding_box()
        page.mouse.move(kopf["x"] + 2, kopf["y"] + 2)
        page.mouse.up()


# S1: das × im Dialog „Leitung benennen“ am PC
def test_das_x_im_dialog_hebt_sich_unter_der_maus_hervor(pc):
    _benennen(pc)
    dialog = pc.locator("dialog.a-dialog")
    expect(dialog).to_be_visible()
    _hebt_sich_hervor(dialog.get_by_role("link", name="Schließen"))
    expect(dialog).to_be_visible()


# S2, S3: schmales Fenster wie am Handy, aber mit der Maus: der Menüknopf und das × im Menü
def test_menueknopf_und_x_im_menue_heben_sich_unter_der_maus_hervor(pc):
    pc.set_viewport_size({"width": 390, "height": 844})
    login(pc)
    menueknopf = pc.get_by_role("button", name="Menü", exact=True)
    _hebt_sich_hervor(menueknopf)
    menueknopf.click()
    menue = pc.get_by_role("dialog", name="Menü")
    expect(menue).to_be_visible()
    # Das × trägt beim Öffnen den Fokus (autofocus); der blaue Rahmen ändert an den Farben nichts.
    _hebt_sich_hervor(menue.get_by_role("button", name="Menü schließen"))
    expect(menue).to_be_visible()


# S4: mit der Tab-Taste auf dem × nur der bekannte blaue Fokusrahmen, keine blaue Fläche
def test_mit_der_tastatur_hat_das_x_nur_den_fokusrahmen(pc):
    _benennen(pc)
    schliessen = pc.locator("dialog.a-dialog").get_by_role("link", name="Schließen")
    expect(schliessen).to_be_visible()
    pc.mouse.move(0, 0)
    for _ in range(15):
        if schliessen.evaluate("e => e === document.activeElement"):
            break
        pc.keyboard.press(_tab_key(pc))
    assert schliessen.evaluate("e => e === document.activeElement"), "Tab erreicht das × nicht"
    fokus = focus_visible(pc)
    assert fokus["sichtbar"] and fokus["rahmen"] == "selbst", fokus
    assert _aussehen(schliessen) == RUHE


# S5: Im Bausteinkatalog hebt sich das × der Dialog-Vorschau genauso hervor
def test_im_bausteinkatalog_hebt_sich_das_x_der_vorschau_hervor(pc):
    login(pc)
    pc.goto(f"{BASE}/bausteine/")
    vorschau = pc.locator("dialog.a-dialog.ist-vorschau").first
    vorschau.scroll_into_view_if_needed()
    _hebt_sich_hervor(vorschau.get_by_role("link", name="Schließen"))
