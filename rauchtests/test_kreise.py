"""Rauchtest „Kreise“ im Browser (#381): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und ist danach Mitglied der Sippe Falken, hat also eine
Zuordnung (KR-01). Geprüft werden die Teile, die nur ein Browser zeigt: der Punkt „Kreise“ in der Seitenleiste, der
Dialog „Kreis anlegen“ mit der Zahl der Zeichen im mehrzeiligen Feld „Beschreibung“, die Seite des Kreises mit
„Person einladen“, Suchen und Einladen, der Hinweis auf der Startseite mit „Zur Einladung“, „Annehmen“, die kurzen
Meldungen, nichts steht seitlich über, der Fokus ist zu sehen, und die Seiten bestehen die Prüfung auf
Barrierefreiheit. Der Name wird auch wie am Handy mit Autokorrektur und Wortvorschlägen getippt. Die Regeln selbst
prüft tests/test_kreise.py. Alle Namen sind erfunden.
"""

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Page, expect

from circles.models import Circle, CircleInvitation, CircleMember
from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone
from roles.models import Role
from tests.test_rollen import give, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
LIST = f"{BASE}/kreise/"
NAV_LINK = '.a-sidebar .a-navlink[href="/kreise/"]'
CREATE_BUTTON = '[aria-labelledby="h-meine-kreise"] .a-flaeche-aktion[href="/kreise/anlegen/"]'
INVITE_BUTTON = '[aria-labelledby="h-mitglieder"] .a-flaeche-aktion'
SUBMIT = 'dialog .a-dialog-fuss button[type="submit"]'
SEARCH_FIELD = 'dialog input[name="suche"]'
INVITE_HIT = 'dialog .a-treffer button[type="submit"]'
DESCRIPTION = "Wir planen das Vorbereitungstreffen des DPV im Frühjahr 2028."


def _erika_und_svea() -> tuple:
    """Erika wird Mitglied der Sippe Falken; Svea ist Mitglied im Stamm Walhall und war schon einmal angemeldet."""
    users = get_user_model().objects
    erika = users.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    give(erika, R.MEMBER, unit(U.GROUP, "Sippe Falken", walhall))
    svea = users.create(username="svea.beispiel", first_name="Svea", last_name="Beispiel", scout_name="Möwe",
                        email="svea.beispiel@example.org", last_login=timezone.now())
    EmailAddress.objects.create(user=svea, email=svea.email, verified=True, primary=True)
    give(svea, R.MEMBER, walhall)
    return erika, svea


def _abstaende(page: Page) -> list[int]:
    """Die senkrechten Abstände zwischen aufeinanderfolgenden Flächen der Seite, in Pixeln (Vorschau, Sebastian, 27.11.2026)."""
    return page.evaluate("""() => {
        const flaechen = [...document.querySelectorAll("main .a-flaeche")].filter(e => e.offsetParent && !e.closest("dialog"));
        const found = [];
        for (let i = 1; i < flaechen.length; i++) {
            found.push(Math.round(flaechen[i].getBoundingClientRect().top - flaechen[i - 1].getBoundingClientRect().bottom));
        }
        return found;
    }""")


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def test_am_pc_nur_mit_der_tastatur_anlegen_und_einladen(pc):
    login(pc)
    _erika_und_svea()
    pc.goto(f"{BASE}/")

    stations = _stations_to_element(pc, NAV_LINK, steps=20)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(LIST)
    expect(pc.locator("h1")).to_have_text("Kreise")
    expect(pc.locator('[aria-labelledby="h-einladungen"]')).to_contain_text("Du hast keine offenen Einladungen.")
    # Zwischen „Einladungen“ und „Meine Kreise“ derselbe Abstand wie zwischen den Kacheln einer Veranstaltung.
    assert _abstaende(pc) == [20]
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, CREATE_BUTTON, steps=20)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    expect(_dialog(pc).locator("h2")).to_have_text("Kreis anlegen")
    expect(pc.get_by_label("Name")).to_be_focused()
    assert run_axe(pc) == []
    pc.keyboard.type("Planungsteam Vorbereitungstreffen")
    pc.keyboard.press("Tab")
    expect(pc.get_by_label("Beschreibung")).to_be_focused()
    pc.keyboard.type(DESCRIPTION)
    expect(_dialog(pc).locator(".a-zeichenzahl").nth(1)).to_contain_text(f"{len(DESCRIPTION)}/500")
    stations = _stations_to_element(pc, SUBMIT, steps=10)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{LIST}*/")
    expect(pc.locator(".a-kurz")).to_contain_text("Der Kreis „Planungsteam Vorbereitungstreffen“ ist angelegt.")
    expect(pc.locator("h1")).to_have_text("Planungsteam Vorbereitungstreffen")
    expect(pc.locator(".a-kopf")).to_contain_text(DESCRIPTION)
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, INVITE_BUTTON, steps=25)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    expect(_dialog(pc).locator("h2")).to_have_text("Person einladen")
    expect(pc.locator(SEARCH_FIELD)).to_be_focused()
    pc.keyboard.type("svea.beispiel@example.org")
    pc.keyboard.press("Enter")
    expect(_dialog(pc)).to_contain_text("Möwe (Svea Beispiel)")
    assert run_axe(pc) == []
    stations = _stations_to_element(pc, INVITE_HIT, steps=10)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    expect(pc.locator(".a-kurz")).to_contain_text("Möwe (Svea Beispiel) ist eingeladen.")
    expect(pc.locator('[aria-labelledby="h-offene-einladungen"]')).to_contain_text("Möwe (Svea Beispiel)")
    assert _abstaende(pc) == [20]


def test_am_pc_zu_lange_beschreibung_rot_mit_meldung_vom_tool(pc):
    login(pc)
    _erika_und_svea()
    pc.goto(f"{LIST}anlegen/")
    pc.get_by_label("Name").fill("Planungsteam")
    description = pc.get_by_label("Beschreibung")
    description.fill("x" * 501)

    expect(_dialog(pc).locator(".a-zeichenzahl.ist-zu-lang")).to_contain_text("501/500")
    expect(description).to_have_attribute("aria-invalid", "true")
    pc.get_by_role("button", name="Kreis anlegen").click()
    expect(_dialog(pc)).to_contain_text("Die Beschreibung darf höchstens 500 Zeichen lang sein.")
    expect(pc.get_by_label("Beschreibung")).to_have_value("x" * 501)
    assert not Circle.objects.exists()
    assert run_axe(pc) == []


def test_am_handy_nur_mit_der_tastatur_annehmen_und_anlegen_mit_autokorrektur(handy):
    login(handy)
    erika, svea = _erika_und_svea()
    circle = Circle.objects.create(name="Singekreis Walhall", description="Wir singen jeden Freitag.")
    CircleMember.objects.create(circle=circle, user=svea, manages=True)
    CircleInvitation.objects.create(circle=circle, user=erika, invited_by=svea)
    handy.goto(f"{BASE}/")
    expect(handy.locator("main")).to_contain_text("Möwe (Svea Beispiel) lädt dich in den Kreis „Singekreis Walhall“ ein.")
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    stations = _stations_to_element(handy, 'main a[href="/kreise/"]', steps=20)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(LIST)
    _no_side_scroll(handy)
    assert _abstaende(handy) == [20]
    assert run_axe(handy) == []
    # Ohne eigenen Rand links: die Einladung hat ringsum denselben feinen Rand (Vorschau, Sebastian, 27.11.2026).
    widths = handy.locator(".a-einladung").evaluate(
        "e => [getComputedStyle(e).borderLeftWidth, getComputedStyle(e).borderRightWidth]")
    assert widths[0] == widths[1], widths
    stations = _stations_to_element(handy, '.a-einladung button.btn-primary', steps=20)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{LIST}*/")
    expect(handy.locator(".a-kurz")).to_contain_text("Du bist jetzt Mitglied von „Singekreis Walhall“.")
    expect(handy.locator('[aria-labelledby="h-mitglieder"]')).to_contain_text("Möwe (Svea Beispiel)")
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    handy.goto(LIST)
    expect(handy.locator('[aria-labelledby="h-meine-kreise"] .a-eintrag')).to_contain_text("2 Mitglieder")
    stations = _stations_to_element(handy, CREATE_BUTTON, steps=30)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    expect(_dialog(handy).locator("h2")).to_have_text("Kreis anlegen")
    _no_side_scroll(handy)
    # Wie am Handy: ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; nichts verschwindet.
    name = handy.get_by_label("Name")
    _type_like_a_phone(name, "Planungs", "t", "team", " Herbst")
    expect(name).to_have_value("Planungsteam Herbst")
    stations = _stations_to_element(handy, SUBMIT, steps=10)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{LIST}*/")
    expect(handy.locator("h1")).to_have_text("Planungsteam Herbst")
    _no_side_scroll(handy)
    assert run_axe(handy) == []
