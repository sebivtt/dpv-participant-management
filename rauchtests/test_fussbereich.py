"""Rauchtest der Lage des Fußbereichs im Browser (#206).

Wo der Fußbereich steht, entscheidet erst der Browser; deshalb lässt es sich nur hier prüfen.
Die Nummern verweisen auf die Szenarien zu #206 (28.10.2026). Jeder Test läuft in Chromium,
Firefox und WebKit (conftest.py). Alle Konten und Daten sind erfunden.
"""

import pytest
from playwright.sync_api import Page

from rauchtests.conftest import BASE, login

pytestmark = pytest.mark.django_db(transaction=True)

# Abstand zwischen Inhalt und Linie des Fußbereichs wie bisher (app.css, .a-fuss).
ABSTAND = 56


def _lage(page: Page) -> dict:
    """Wo der Fußbereich steht, gemessen auf der ganzen Seite (nicht nur im sichtbaren Teil)."""
    return page.evaluate(
        """() => {
            const fuss = document.querySelector('footer');
            const main = fuss.closest('main');
            const box = fuss.getBoundingClientRect();
            // Unterkante des Inhalts davor; die kurzen Meldungen schweben über allem und zählen nicht mit.
            let inhalt = main.getBoundingClientRect().top;
            for (const el of main.querySelectorAll('*')) {
                if (fuss.contains(el) || el.closest('.a-kurz-bereich') || el.matches('.a-main-inhalt')) continue;
                inhalt = Math.max(inhalt, el.getBoundingClientRect().bottom);
            }
            return {
                oben: box.top + scrollY, unten: box.bottom + scrollY, links: box.left, rechts: box.right,
                inhalt: inhalt + scrollY,
                position: getComputedStyle(fuss).position,
                rand: parseFloat(getComputedStyle(main).paddingBottom),
                fenster: innerHeight, breite: document.documentElement.clientWidth,
                seite: document.documentElement.scrollHeight,
            };
        }"""
    )


def _am_unteren_rand(page: Page) -> None:
    lage = _lage(page)
    # Die Seite ist genau so hoch wie das Fenster: keine leere Fläche darunter, nichts zu scrollen.
    assert lage["seite"] == lage["fenster"], lage
    # Unter dem Fußbereich liegt nur der gewohnte Rand des Inhalts.
    assert abs(lage["fenster"] - lage["rand"] - lage["unten"]) <= 1, lage
    assert lage["oben"] - lage["inhalt"] >= ABSTAND - 1, lage


# Szenario 1: kurze Seite am PC
def test_am_pc_steht_der_fussbereich_bei_kurzem_inhalt_am_unteren_rand(pc):
    login(pc)
    _am_unteren_rand(pc)


# Szenario 2: kurze Seite am Handy, unter der schmalen Leiste mit „Menü“
def test_am_handy_steht_der_fussbereich_bei_kurzem_inhalt_am_unteren_rand(handy):
    login(handy)
    _am_unteren_rand(handy)


# Szenario 3: lange Seite; der Fußbereich folgt dem Inhalt, klebt nicht und überdeckt nichts
def _nach_dem_inhalt(page: Page) -> None:
    login(page)
    page.goto(f"{BASE}/bausteine/")
    lage = _lage(page)
    assert lage["position"] == "static", lage
    assert lage["oben"] > lage["fenster"], "Der Fußbereich ist ohne Scrollen zu sehen"
    # Abstand zum Inhalt genau wie bisher, weder größer noch überdeckt
    assert lage["oben"] - lage["inhalt"] == pytest.approx(ABSTAND, abs=1), lage
    assert abs(lage["seite"] - lage["rand"] - lage["unten"]) <= 1, lage

    page.evaluate("scrollTo(0, document.documentElement.scrollHeight)")
    nach_dem_scrollen = _lage(page)
    assert nach_dem_scrollen["oben"] == pytest.approx(lage["oben"], abs=1), "Der Fußbereich wandert beim Scrollen mit"


def test_am_pc_steht_der_fussbereich_bei_langem_inhalt_nach_dem_inhalt(pc):
    _nach_dem_inhalt(pc)


def test_am_handy_steht_der_fussbereich_bei_langem_inhalt_nach_dem_inhalt(handy):
    _nach_dem_inhalt(handy)


# Szenario 4: Login- und Fehlerseite unverändert, Fußbereich mittig unter der Karte
@pytest.mark.parametrize("adresse", ["/anmelden/", "/gibt-es-nicht/"])
def test_auf_login_und_fehlerseite_steht_der_fussbereich_mittig_unter_der_karte(pc, adresse):
    pc.goto(f"{BASE}{adresse}")
    lage = pc.evaluate(
        """() => {
            const main = document.querySelector('main').getBoundingClientRect();
            const erstes = document.querySelector('main').firstElementChild.getBoundingClientRect();
            const karte = document.querySelector('.a-einfach-karte').getBoundingClientRect();
            const fuss = document.querySelector('footer').getBoundingClientRect();
            return {main_oben: main.top, main_unten: main.bottom, oben: erstes.top,
                    karte_unten: karte.bottom, fuss_oben: fuss.top, fuss_unten: fuss.bottom,
                    links: fuss.left, rechts: fuss.right, breite: document.documentElement.clientWidth};
        }"""
    )
    # Direkt unter der Karte, mit dem gewohnten Abstand (app.css, .a-einfach-main)
    assert lage["fuss_oben"] - lage["karte_unten"] == pytest.approx(24, abs=1), lage
    # Karte und Fußbereich zusammen senkrecht und waagrecht mittig
    assert lage["oben"] - lage["main_oben"] == pytest.approx(lage["main_unten"] - lage["fuss_unten"], abs=1), lage
    assert lage["links"] == pytest.approx(lage["breite"] - lage["rechts"], abs=1), lage
