"""Rauchtest „Anmeldungen“ im Browser (#101, AG4): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an. Im ersten Teil leitet sie „Probelager 2027“, zu
dem Wanda als Stammesleitung von Walhall sich, Paul und Lena angemeldet hat (AN-01); im zweiten ist Erika selbst
Stammesleitung und Ansprechperson einer Anmeldung zu einer Veranstaltung, die Bea leitet, und kommt nur über die
Adresse dorthin (AN-02). Anmeldungen entstehen in P2 nur im Datenmodell (AN-06), deshalb legt der Test sie über
die zentrale Rechteprüfung an. Geprüft werden die Teile, die nur ein Browser zeigt: der Weg mit der Tastatur
von der Liste „Veranstaltungen“ über den Abschnitt „Anmeldungen“ zur Seite der Anmeldung, nichts steht seitlich
über, der Fokus ist zu sehen, und die Seiten bestehen die Prüfung auf Barrierefreiheit. Die Regeln selbst
prüft tests/test_anmeldungen.py. Alle Namen sind erfunden.
"""

from datetime import date

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from access.rights import Rights
from events.models import Event
from persons.models import ManagedPerson
from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element
from roles.models import Role
from tests.test_rollen import give, person, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
LIST = f"{BASE}/veranstaltungen/"
NAV_LINK = '.a-sidebar .a-navlink[href="/veranstaltungen/"]'
SECTION = '[aria-labelledby="h-anmeldungen"]'
NAMES = "Wanda Walhall, Paul Probe, Kiwi (Lena Probe)"


def _walhall():
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    return boreas, walhall, unit(U.GROUP, "Sippe Falken", walhall)


def _managed(where, first_name: str, born: str, scout_name: str = "") -> ManagedPerson:
    entry = ManagedPerson(unit=where, first_name=first_name, last_name="Probe", birth_date=date.fromisoformat(born),
                          scout_name=scout_name)
    entry.save()
    return entry


def _event(lead) -> Event:
    found = Event.objects.create(name="Probelager 2027", start=date(2027, 5, 15), end=date(2027, 5, 17))
    found.leads.add(lead)
    return found


def _erika_leitet_das_probelager() -> None:
    """Erika leitet „Probelager 2027“; Wanda hat sich, Paul und Lena angemeldet (AN-01)."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    _boreas, walhall, falken = _walhall()
    give(erika, R.MEMBER, falken)
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    give(wanda, R.MEMBER, walhall)
    give(wanda, R.TROOP_LEAD, walhall)
    paul, lena = _managed(walhall, "Paul", "2012-09-03"), _managed(falken, "Lena", "2015-05-14", "Kiwi")
    Rights(wanda).register(_event(erika), [wanda, paul, lena])


def _erika_meldet_an() -> str:
    """Erika ist Stammesleitung von Walhall und hat sich und Lena zu Beas Probelager angemeldet (AN-02)."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    boreas, walhall, falken = _walhall()
    give(erika, R.MEMBER, walhall)
    give(erika, R.TROOP_LEAD, walhall)
    bea = person("bea.boreas", "Bea", "Boreas")
    give(bea, R.MEMBER, boreas)
    give(bea, R.ASSOCIATION_LEAD, boreas)
    lena = _managed(falken, "Lena", "2015-05-14", "Kiwi")
    return Rights(erika).register(_event(bea), [erika, lena]).key


def _open_registration_with_the_keyboard(page: Page, steps: int) -> None:
    """Von der Liste „Veranstaltungen“ zur Seite des Probelagers und über den Abschnitt zur Anmeldung."""
    page.goto(LIST)
    stations = _stations_to_element(page, 'main li a[href^="/veranstaltungen/"]', steps=steps)
    _all_visible(stations)
    page.keyboard.press("Enter")
    page.wait_for_url(f"{LIST}*/")
    expect(page.locator(SECTION)).to_contain_text("Anmeldungen")
    expect(page.locator(f"{SECTION} li")).to_contain_text(NAMES)
    _no_side_scroll(page)
    assert run_axe(page) == []

    stations = _stations_to_element(page, f'{SECTION} a[href^="/anmeldungen/"]', steps=steps)
    _all_visible(stations)
    page.keyboard.press("Enter")
    page.wait_for_url(f"{BASE}/anmeldungen/*/")


def _shows_the_registration(page: Page) -> None:
    expect(page.locator("h1")).to_have_text("Anmeldung")
    main = page.locator("main")
    expect(main).to_contain_text("Probelager 2027")
    expect(main).to_contain_text("15.05.2027 bis 17.05.2027")
    expect(main).to_contain_text("Ansprechperson: Wanda Walhall")
    expect(page.locator('[aria-labelledby="h-anmeldung-personen"] li')).to_have_count(3)
    expect(main).to_contain_text("14.05.2015")
    _no_side_scroll(page)
    assert run_axe(page) == []


def test_am_pc_nur_mit_der_tastatur_zur_anmeldung(pc):
    login(pc)
    _erika_leitet_das_probelager()
    pc.goto(f"{BASE}/")
    stations = _stations_to_element(pc, NAV_LINK, steps=20)
    _all_visible(stations)

    _open_registration_with_the_keyboard(pc, steps=30)

    _shows_the_registration(pc)
    # Als Veranstaltungsleitung führt der Name der Veranstaltung zurück zu ihrer Seite.
    stations = _stations_to_element(pc, 'main a[href^="/veranstaltungen/"]', steps=30)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(f"{LIST}*/")
    expect(pc.locator("h1")).to_have_text("Probelager 2027")


def test_am_handy_nur_mit_der_tastatur_zur_anmeldung(handy):
    login(handy)
    _erika_leitet_das_probelager()

    _open_registration_with_the_keyboard(handy, steps=40)

    _shows_the_registration(handy)


def test_am_handy_die_ansprechperson_kommt_ueber_die_adresse(handy):
    login(handy)
    key = _erika_meldet_an()

    handy.goto(f"{BASE}/anmeldungen/{key}/")

    expect(handy.locator("h1")).to_have_text("Anmeldung")
    main = handy.locator("main")
    expect(main).to_contain_text("Probelager 2027")
    expect(main).to_contain_text("Ansprechperson: Erika Testfrau")
    # Die Veranstaltung selbst sieht Erika nicht (VA-03), ihr Name ist kein Link.
    expect(handy.locator('main a[href^="/veranstaltungen/"]')).to_have_count(0)
    expect(handy.locator('[aria-labelledby="h-anmeldung-personen"] li')).to_have_count(2)
    _no_side_scroll(handy)
    assert run_axe(handy) == []
