"""Tests für die Grundgestaltung und die Musterseite (#7, NFA-01, NFA-03, NFA-09).

Die Nummern verweisen auf Sebastians Szenarien zu #7 (Planung am 21.10.2026). Was nur ein
echter Browser zeigen kann (Tastatur, Handy, axe), prüft der Rauchtest in rauchtests/.
Alle Daten sind erfunden.
"""

import re
from datetime import date
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.test.html import Element, parse_html

pytestmark = pytest.mark.django_db

User = get_user_model()


# ---------- Hilfen: die Seite als Baum lesen statt als Text ----------


def _tree(response) -> Element:
    assert response.status_code in (200, 500), response.status_code
    return parse_html(response.content.decode())


def _attr(element: Element, name: str) -> str | None:
    for key, value in element.attributes:
        if key == name:
            return value if value is not None else ""
    return None


def _classes(element: Element) -> list[str]:
    return (_attr(element, "class") or "").split()


def _all(root, predicate) -> list[Element]:
    found = []
    for child in getattr(root, "children", []):
        if isinstance(child, Element):
            if predicate(child):
                found.append(child)
            found.extend(_all(child, predicate))
    return found


def _text(element) -> str:
    if isinstance(element, str):
        return element
    return " ".join(_text(child) for child in element.children).strip()


def _visible_text(element) -> str:
    """Text ohne das, was nur Bildschirmleser bekommen oder was ausgeblendet ist."""
    if isinstance(element, str):
        return element
    if "sr-nur" in _classes(element) or _attr(element, "aria-hidden") == "true":
        return ""
    return " ".join(_visible_text(child) for child in element.children).strip()


def _by_tag(root, tag: str, **attrs) -> list[Element]:
    return _all(root, lambda e: e.name == tag and all(_attr(e, k.replace("_", "-")) == v for k, v in attrs.items()))


def _one(found: list[Element]) -> Element:
    assert len(found) == 1, f"{len(found)} statt genau einem Element gefunden"
    return found[0]


def _sidebar(root) -> Element:
    return _one(_by_tag(root, "aside", aria_label="Seitenleiste"))


def _logged_in(first_name="Erika", last_name="Testfrau") -> Client:
    client = Client()
    user = User.objects.create(username=f"{first_name or 'ohne'}.{last_name or 'name'}", first_name=first_name,
                               last_name=last_name, email="erika.testfrau@example.org")
    client.force_login(user)
    return client


# ---------- Szenario 1: Seitenleiste am PC ----------


def test_startseite_hat_links_die_seitenleiste_und_keine_kopfzeile_ueber_dem_inhalt():
    root = _tree(_logged_in().get("/"))

    sidebar = _sidebar(root)
    brand = _one(_all(sidebar, lambda e: e.name == "a" and "a-marke" in _classes(e)))
    assert _attr(brand, "href") == "/"
    assert _all(brand, lambda e: e.name == "svg" and "lilie" in _classes(e)), "Lilie fehlt"
    assert "DPV Anmeldetool" in _text(brand)
    main = _one(_by_tag(root, "main"))
    assert not _by_tag(main, "header"), "über dem Inhalt steht eine Kopfzeile"
    assert "Hallo Erika!" in _text(_one(_by_tag(main, "h1")))


def test_navigation_zeigt_nur_die_startseite_hervorgehoben():
    root = _tree(_logged_in().get("/"))

    nav = _one(_by_tag(_sidebar(root), "nav", aria_label="Hauptnavigation"))
    links = _by_tag(nav, "a")
    assert [_text(link) for link in links] == ["Startseite"]
    assert _attr(links[0], "href") == "/"
    assert _attr(links[0], "aria-current") == "page"
    assert "Beispiel" not in _text(nav)


def test_unten_in_der_leiste_profilkreis_vorname_und_abmelden():
    root = _tree(_logged_in().get("/"))

    sidebar = _sidebar(root)
    profile = _one(_all(sidebar, lambda e: e.name == "a" and "a-profil" in _classes(e)))
    assert _attr(profile, "href") == "/"  # bis P5 zur Startseite (#13)
    assert "Mein Profil" in _text(profile)
    circle = _one(_all(profile, lambda e: "a-avatar" in _classes(e)))
    assert _text(circle) == "E"
    assert "Erika" in _visible_text(profile)
    form = _one(_by_tag(sidebar, "form", action="/abmelden/"))
    assert _attr(form, "method") == "post"
    assert "Abmelden" in _text(_one(_by_tag(form, "button")))


# ---------- Szenario 3: Handy-Leiste und Menü ----------


def test_handy_leiste_mit_menue_lilie_und_profilkreis_abmelden_im_menue():
    root = _tree(_logged_in().get("/"))

    bar = _one(_all(root, lambda e: e.name == "header" and "a-topbar" in _classes(e)))
    button = _one(_by_tag(bar, "button", aria_controls="menue"))
    assert "Menü" in _text(button)
    assert _all(bar, lambda e: e.name == "svg" and "lilie" in _classes(e))
    assert _one(_by_tag(bar, "a", aria_label="Mein Profil"))
    menu = _one(_by_tag(root, "dialog", id="menue"))
    assert [_text(a) for a in _by_tag(_one(_by_tag(menu, "nav")), "a")] == ["Startseite"]
    form = _one(_by_tag(menu, "form", action="/abmelden/"))
    assert "Abmelden" in _text(form)


# ---------- Szenario 4 (Teil ohne Browser): Sprung zum Inhalt ----------


def test_tastatur_kommt_mit_dem_ersten_tab_direkt_zum_inhalt():
    root = _tree(_logged_in().get("/"))

    skip = _all(root, lambda e: e.name == "a")[0]
    assert _attr(skip, "href") == "#inhalt"
    assert "Zum Inhalt" in _text(skip)
    assert _one(_by_tag(root, "main", id="inhalt"))


# ---------- Szenario 5: ohne Namen ----------


def test_ohne_vornamen_zeigt_der_kreis_ein_personensymbol_und_keinen_leeren_namen():
    root = _tree(_logged_in(first_name="", last_name="").get("/"))

    profile = _one(_all(_sidebar(root), lambda e: e.name == "a" and "a-profil" in _classes(e)))
    circle = _one(_all(profile, lambda e: "a-avatar" in _classes(e)))
    assert _text(circle) == ""
    assert _all(circle, lambda e: e.name == "svg"), "Personensymbol fehlt"
    assert _visible_text(profile) == ""
    assert "Mein Profil" in _text(profile)
    assert "Ergänze deinen Namen" in _text(root)


# ---------- Szenario 6: Musterseite nur mit Login ----------


def test_musterseite_ohne_login_fuehrt_zum_login():
    response = Client().get("/muster/")

    assert response.status_code == 302
    assert response["Location"] == "/anmelden/?next=/muster/"


def test_musterseite_mit_login_zeigt_alle_fuenf_navigationspunkte_als_beispiel():
    root = _tree(_logged_in().get("/muster/"))

    nav = _one(_by_tag(_sidebar(root), "nav", aria_label="Hauptnavigation"))
    names = [_text(a) for a in _by_tag(nav, "a")]
    assert names == ["Startseite", "Veranstaltungen", "Teilnehmende", "Organisation", "Einstellungen"]
    assert "Beispiel" in _text(nav)


# ---------- Szenario 7: Zustände nie nur über Farbe ----------


def test_jedes_statuskennzeichen_hat_ein_wort_und_ein_symbol():
    root = _tree(_logged_in().get("/muster/"))

    badges = _all(root, lambda e: "a-status" in _classes(e))
    assert len(badges) >= 8
    for badge in badges:
        assert _text(badge), "Statuskennzeichen ohne Wort"
        assert _by_tag(badge, "svg"), f"„{_text(badge)}“ ohne Symbol"
    words = {_text(badge) for badge in badges}
    for word in ("Anmeldung offen", "Anmeldung ab 01.12.", "Anmeldung geschlossen", "Entwurf", "ausgebucht",
                 "angemeldet", "Warteliste", "abgemeldet"):
        assert word in words, f"„{word}“ fehlt"


def test_veranstaltungen_als_zeilen_mit_bild_und_lilie_als_standard():
    root = _tree(_logged_in().get("/muster/"))

    rows = _all(root, lambda e: e.name == "article" and "a-event" in _classes(e))
    assert len(rows) >= 5
    for row in rows:
        picture = _one(_all(row, lambda e: "a-bild" in _classes(e)))
        assert _by_tag(picture, "svg")
        link = _one(_by_tag(row, "a"))
        assert _text(link), "Zeile ohne Namen als Link"
    with_lily = [r for r in rows if _all(r, lambda e: e.name == "svg" and "lilie" in _classes(e))]
    assert 0 < len(with_lily) < len(rows), "Lilie nur, wo kein eigenes Bild hinterlegt ist"
    drafts = [r for r in rows if "ist-entwurf" in _classes(r)]
    assert len(drafts) == 1
    assert "Entwurf" in _text(drafts[0])


def test_angemeldete_mit_und_ohne_obergrenze():
    root = _tree(_logged_in().get("/muster/"))
    text = " ".join(_text(root).split())

    assert "23 von 40 angemeldet" in text
    assert "16 von 16 angemeldet" in text
    assert "31 angemeldet" in text
    assert "31 von" not in text


# ---------- Szenario 9: Pflichtfeld mit Fehlermeldung am Feld ----------


def test_pflichtfeld_ist_gekennzeichnet_und_die_fehlermeldung_haengt_am_feld():
    root = _tree(_logged_in().get("/muster/"))

    field = _one(_all(root, lambda e: e.name == "input" and _attr(e, "aria-invalid") == "true"))
    assert _attr(field, "required") is not None
    label = _one(_by_tag(root, "label", **{"for": _attr(field, "id")}))
    assert "Pflicht" in _text(label)
    error = _one(_by_tag(root, "div", id=_attr(field, "aria-describedby")))
    assert "Gib einen Namen für die Veranstaltung ein." in _text(error)


# ---------- Szenario 11: Fußbereich auf jeder Seite ----------


def _footer(root) -> Element:
    return _one(_by_tag(root, "footer"))


@pytest.mark.parametrize("address", ["/", "/muster/"])
def test_fussbereich_auf_den_seiten_mit_login(address):
    footer = _footer(_tree(_logged_in().get(address)))

    assert [_text(a) for a in _by_tag(footer, "a")] == ["Impressum", "Datenschutz"]
    assert "© DPV e.V. · Anmeldetool 2026" in _text(footer)


def test_fussbereich_auf_der_login_seite_ohne_seitenleiste():
    root = _tree(Client().get("/anmelden/"))

    assert not _by_tag(root, "aside")
    assert _all(root, lambda e: e.name == "svg" and "lilie" in _classes(e))
    assert "© DPV e.V. · Anmeldetool 2026" in _text(_footer(root))


def test_ziele_von_impressum_und_datenschutz_sind_einstellbar(settings):
    settings.IMPRESSUM_URL = "https://example.org/impressum"
    settings.DATENSCHUTZ_URL = "https://example.org/datenschutz"

    links = _by_tag(_footer(_tree(Client().get("/anmelden/"))), "a")

    assert [_attr(a, "href") for a in links] == ["https://example.org/impressum", "https://example.org/datenschutz"]


def test_impressum_und_datenschutz_zeigen_vorerst_auf_die_seiten_des_dpv():
    links = _by_tag(_footer(_tree(Client().get("/anmelden/"))), "a")

    assert all(_attr(a, "href").startswith("https://dpvonline.de/") for a in links)


def test_jahreszahl_zaehlt_automatisch_weiter(monkeypatch):
    monkeypatch.setattr("core.templatetags.layout.localdate", lambda: date(2027, 3, 1))

    footer = _footer(_tree(Client().get("/anmelden/")))

    assert "© DPV e.V. · Anmeldetool 2026–2027" in _text(footer)


def test_inhaber_im_copyright_ist_einstellbar(settings):
    settings.COPYRIGHT_HOLDER = "Beispielverband e.V."

    assert "© Beispielverband e.V. · Anmeldetool 2026" in _text(_footer(_tree(Client().get("/anmelden/"))))


# ---------- Szenario 12: Fehlerseite ----------


def test_fehlerseite_gestaltet_mit_nummer_ohne_seitenleiste_und_ohne_namen(settings):
    settings.ROOT_URLCONF = "tests.urls"
    erika = _logged_in()
    client = Client(raise_request_exception=False)
    client.cookies = erika.cookies

    response = client.get("/test/1/")

    assert response.status_code == 500
    root = _tree(response)
    assert not _by_tag(root, "aside")
    assert "Erika" not in _text(root)
    assert _all(root, lambda e: e.name == "svg" and "lilie" in _classes(e))
    assert "Wenn du dich meldest, nenne bitte diese Nummer" in _text(root)
    assert "© DPV e.V. · Anmeldetool 2026" in _text(_footer(root))


# ---------- Gestaltung kommt vom eigenen Server ----------


def test_gestaltung_kommt_vom_eigenen_server_auch_ohne_login():
    root = _tree(Client().get("/anmelden/"))

    sheets = [_attr(link, "href") for link in _by_tag(root, "link", rel="stylesheet")]
    scripts = [_attr(script, "src") for script in _by_tag(root, "script") if _attr(script, "src")]
    assert sheets, "keine Gestaltung eingebunden"
    for address in sheets + scripts:
        assert address.startswith("/static/"), f"{address} kommt nicht vom eigenen Server"
        response = Client().get(address)
        assert response.status_code == 200, f"{address} antwortet mit {response.status_code}"


# ---------- Logo ----------

LOGO_NOTE = "Das Logo ist Eigentum des DPV und nicht Teil der EUPL-Lizenz."
BASE_DIR = Path(__file__).resolve().parent.parent
LILY = BASE_DIR / "core" / "templates" / "core" / "lilie.svg"


def test_hinweis_zum_logo_steht_im_readme_und_neben_der_datei():
    assert LOGO_NOTE in (BASE_DIR / "README.md").read_text()
    assert LOGO_NOTE in (LILY.parent / "LOGO-HINWEIS.md").read_text()


def test_lilie_uebernimmt_die_farbe_ihrer_umgebung_und_enthaelt_nur_pfade():
    svg = LILY.read_text()

    assert 'fill="currentColor"' in svg
    assert "#1a4b7e" not in svg.lower()
    assert svg.count("<path ") == 8
    drawing = svg.split("#}", 1)[1]
    assert not re.search(r"<script|<image|<style|<foreignObject|href=|\son\w+=", drawing, re.IGNORECASE)
