"""Rauchtest „Seite springt nicht, wenn ein Dialog aufgeht“ im Browser (#220).

Jeder Dialog hat eine eigene Adresse (#190); Öffnen, Schließen und Speichern laden deshalb die Seite
neu. Mit Skript merkt sich die Seite, wie weit sie gerollt war, und steht danach wieder dort; ohne
Skript springt sie zum Abschnitt mit dem Knopf, der den Dialog geöffnet hat. Wo die Seite steht,
entscheidet erst der Browser; deshalb lässt es sich nur hier prüfen. Die Nummern verweisen auf die
Szenarien vom 14.11.2026 in #220. Jeder Test läuft in Chromium, Firefox und WebKit (conftest.py).
Erika steht für Max und Erika aus den Szenarien; auf der Seite von Walhall ist sie Bundesleitung darüber,
damit Flink die letzte Leitung der Liste ist und auch ganz unten auf der Seite zu sehen bleibt. Alle Konten
und Daten sind erfunden.
"""

from datetime import date

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Page, expect

from persons.models import ManagedPerson
from rauchtests.conftest import BASE, login, wait_for_page_below
from roles.models import Role
from tests.test_rollen import give, person, unit
from units.models import Unit

pytestmark = pytest.mark.django_db(transaction=True)

R = Role.Kind
U = Unit.Kind
LEADS = '[aria-labelledby="h-leitungen"]'
PERSONS = '[aria-labelledby="h-personen"]'
# Macht jede Seite unten lang, bevor das Skript der Seite läuft (defer läuft erst nach „interactive“). Über die
# Schnittstelle des Browsers statt als Element <style>, das die Sicherheitsrichtlinie blockiert (#278).
PADDING = """document.addEventListener('readystatechange', () => {
    if (document.readyState === 'interactive') {
        const sheet = new CSSStyleSheet();
        sheet.replaceSync('.a-main-inhalt { padding-bottom: 3000px !important; }');
        document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];
    }
});"""
# So weit darf die Seite von der gemerkten Stelle abweichen: Rundung beim Rollen, sonst nichts.
EXACT = 2


def _erika() -> object:
    return get_user_model().objects.get(username="erika.testfrau")


def _lange_walhall(managed: bool = False, mia: bool = False) -> dict:
    """Walhall mit vielen Stammesleitungen, Flink (Finn Muster) als letzte; Erika leitet als Bundesleitung darüber.

    Alle Leitungen sind Mitglied der Sippe Falken; so steht unter „Personen“ von Walhall niemand, und
    „Entfernen“ bei Flink ist auch ganz unten auf der Seite zu sehen, am Handy ebenso.

    Mit `mia` ist Mia Mitglied von Walhall und lässt sich über ihre Mail benennen. Mit `managed` gibt es dazu Paul und viele
    weitere verwaltete Personen unter „Personen“ davor und danach, Paul mitten in der Liste.
    """
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    falken = unit(U.GROUP, "Sippe Falken", walhall)
    give(_erika(), R.ASSOCIATION_LEAD, boreas)
    # Die Leitungen sind Mitglied der Falken, damit sie nicht auch unter „Personen“ von Walhall stehen.
    leads = [person(f"lea.aal{number:02d}", "Lea", f"Aal{number:02d}") for number in range(15)]
    finn = person("finn.muster", "Finn", "Muster")
    finn.scout_name = "Flink"
    finn.save()
    for lead in [*leads, finn]:
        give(lead, R.MEMBER, falken)
        give(lead, R.TROOP_LEAD, walhall)
    if mia:
        member = person("mia.mitglied", "Mia", "Mitglied")
        member.email = "mia.mitglied@example.org"
        member.last_login = timezone.now()
        member.save()
        EmailAddress.objects.create(user=member, email=member.email, verified=True, primary=True)
        give(member, R.MEMBER, walhall)
    found = {"walhall": walhall, "finn": finn}
    if managed:
        found["paul"] = ManagedPerson.objects.create(first_name="Paul", last_name="Probe",
                                                     birth_date=date(2012, 9, 3), unit=walhall)
        for first_name, last_name in (("Anna", "Aal"), ("Zora", "Zett")):
            for number in range(15):
                ManagedPerson.objects.create(first_name=first_name, last_name=f"{last_name}{number:02d}",
                                             birth_date=date(2013, 1, 1), unit=walhall)
    return found


def _page_of(where) -> str:
    return f"{BASE}/organisation/{where.key}/"


def _y(page: Page) -> int:
    return page.evaluate("Math.round(scrollY)")


def _most(page: Page) -> int:
    """Wie weit die Seite höchstens rollen kann."""
    return page.evaluate("Math.round(document.scrollingElement.scrollHeight - innerHeight)")


def _roll_to(page: Page, y: int) -> int:
    """Rollt sofort; Bootstrap ließe die Seite sonst weich dorthin gleiten."""
    page.evaluate("y => scrollTo({top: y, behavior: 'instant'})", y)
    return _y(page)


def _at_bottom_of_window(page: Page, locator) -> int:
    """Rollt so, dass `locator` unten im Fenster steht, also nicht oben: Ein Sprung dorthin fiele auf.

    Mit etwas Abstand zum Rand: Steht der Knopf genau an der Kante, rollt Firefox ihn beim Klick erst selbst
    ganz ins Bild, und gemerkt wäre dann diese neue Stelle (Prüfung auf GitHub, Firefox, S1).
    """
    locator.evaluate("e => e.scrollIntoView({block: 'end', behavior: 'instant'})")
    page.evaluate("scrollBy({top: 60, behavior: 'instant'})")
    return _y(page)


def _on_top(page: Page, selector: str) -> None:
    """Wartet bis zu 5 Sekunden, bis `selector` oben im Fenster steht; ohne Skript gleitet die Seite weich dorthin.

    Von hier aus nachgesehen: Ohne Skript laufen in der Seite keine Zeitgeber, mit denen Playwright sonst wartet.
    """
    where = None
    for _ in range(50):
        # Am Handy steht die Leiste oben fest; der Abschnitt beginnt direkt darunter.
        where = page.evaluate(
            """s => {
                const bar = document.querySelector('.a-topbar');
                const below = bar && bar.offsetHeight ? bar.getBoundingClientRect().bottom : 0;
                return [Math.round(document.querySelector(s).getBoundingClientRect().top - below), scrollY];
            }""",
            selector,
        )
        if 0 <= where[0] <= 24 and where[1] > 0:
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"{selector} steht {where[0]} px unter dem oberen Rand, nicht oben im Fenster (Seite bei {where[1]})")


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _steht_bei(page: Page, spot: int) -> None:
    assert abs(_y(page) - spot) <= EXACT, f"Seite steht bei {_y(page)}, gemerkt war {spot}"


def _flink_entfernen(page: Page):
    return page.locator(f"{LEADS} .a-leitung", has_text="Flink").locator(".a-leitung-knopf")


def _erika_im_team_mit_vielen_rollen() -> None:
    """Erika ist im DPV-Veranstaltungsteam und leitet viele Gruppen; „Mein Profil“ ist lang."""
    erika = _erika()
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    for number in range(30):
        give(erika, R.GROUP_LEAD, unit(U.GROUP, f"Sippe {number:02d}", walhall))
    give(erika, R.EVENT_TEAM, dpv)


# S1, S2, S6: „Rolle abgeben“ auf „Mein Profil“ öffnen und auf jedem Weg schließen, am PC und am Handy.
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_rolle_abgeben_oeffnen_und_schliessen_laesst_die_seite_stehen(device, request, browser_name):
    page = request.getfixturevalue(device)
    login(page)
    _erika_im_team_mit_vielen_rollen()
    profile = f"{BASE}/profil/"
    page.goto(profile)
    give_up = page.locator(".a-kachel-knopf", has_text="Rolle abgeben")
    spot = _at_bottom_of_window(page, give_up)
    assert spot > 100, "Die Seite muss lang genug sein, damit ein Sprung auffällt."

    give_up.click()
    page.wait_for_url(f"{profile}team-abgeben/")
    expect(_dialog(page)).to_be_visible()
    _steht_bei(page, spot)

    _dialog(page).get_by_role("link", name="Abbrechen").click()
    page.wait_for_url(profile)
    expect(_dialog(page)).to_have_count(0)
    _steht_bei(page, spot)

    for close in ("×", "Escape", "daneben"):
        give_up.click()
        page.wait_for_url(f"{profile}team-abgeben/")
        expect(_dialog(page)).to_be_visible()
        _steht_bei(page, spot)
        if close == "×":
            _dialog(page).get_by_role("link", name="Schließen").click()
        elif close == "Escape":
            page.keyboard.press("Escape")
        else:
            page.mouse.click(5, 450)
        page.wait_for_url(profile)
        expect(_dialog(page)).to_have_count(0)
        _steht_bei(page, spot)


# S3, S6: Nach „Entfernen“ steht die Seite so nah wie möglich an der Stelle von vorher, obwohl sie kürzer ist.
@pytest.mark.parametrize("device", ["pc", "handy"])
def test_nach_entfernen_steht_die_seite_so_nah_wie_moeglich(device, request, browser_name):
    page = request.getfixturevalue(device)
    login(page)
    found = _lange_walhall()
    address = _page_of(found["walhall"])
    page.goto(address)
    spot = _roll_to(page, _most(page))
    assert spot > 300, "Die Seite muss lang genug sein, damit ein Sprung auffällt."
    expect(_flink_entfernen(page)).to_be_in_viewport()

    _flink_entfernen(page).click()
    page.wait_for_url(f"{address}entfernen/**")
    expect(_dialog(page)).to_be_visible()
    _steht_bei(page, spot)
    _dialog(page).get_by_role("button", name="Entfernen").click()

    page.wait_for_url(address)
    expect(page.locator(".a-kurz")).to_contain_text("Flink (Finn Muster) ist nicht mehr Stammesleitung von Walhall.")
    expect(page.locator(LEADS)).not_to_contain_text("Flink")
    # Kürzer geworden: Die gemerkte Stelle gibt es nicht mehr, die Seite steht ganz unten, also so nah wie möglich.
    assert _most(page) < spot
    _steht_bei(page, _most(page))
    assert _y(page) > spot - 200


# S4: Suchen im Dialog „Stammesleitung benennen“ und Benennen lassen die Seite dahinter an ihrer Stelle.
def test_suchen_und_benennen_lassen_die_seite_stehen(pc):
    login(pc)
    found = _lange_walhall(mia=True)
    address = _page_of(found["walhall"])
    pc.goto(address)
    appoint = pc.locator(f"{LEADS} .a-flaeche-aktion")
    spot = _roll_to(pc, int(appoint.evaluate("e => e.getBoundingClientRect().top + scrollY")) - 80)
    assert spot > 50, "Die Seite muss gerollt sein, damit ein Sprung auffällt."
    expect(appoint).to_be_in_viewport()

    appoint.click()
    pc.wait_for_url(f"{address}benennen/")
    _steht_bei(pc, spot)
    _dialog(pc).get_by_label("Name, Fahrtenname, Mail oder Benutzername").fill("mia.mitglied@example.org")
    _dialog(pc).get_by_role("button", name="Suchen").click()
    pc.wait_for_url(f"{address}benennen/suchen/")
    expect(_dialog(pc).locator(".a-treffer")).to_contain_text("Mia Mitglied")
    _steht_bei(pc, spot)

    _dialog(pc).get_by_role("button", name="Benennen Mia Mitglied").click()
    pc.wait_for_url(address)
    expect(pc.locator(".a-kurz")).to_contain_text("Mia Mitglied ist jetzt Stammesleitung von Walhall.")
    _steht_bei(pc, spot)


# S7: Die Ablehnung steht im Dialog an der Stelle der Handlung (#186); die Seite dahinter bewegt sich nicht.
def test_ablehnung_im_dialog_laesst_die_seite_stehen(pc):
    login(pc)
    found = _lange_walhall()
    address = _page_of(found["walhall"])
    pc.goto(address)
    appoint = pc.locator(f"{LEADS} .a-flaeche-aktion")
    spot = _roll_to(pc, int(appoint.evaluate("e => e.getBoundingClientRect().top + scrollY")) - 80)
    assert spot > 50
    appoint.click()
    pc.wait_for_url(f"{address}benennen/")

    # Sich selbst zeigt der Dialog keinen Knopf (RO-12); das Formular, das ihn trotzdem schickt, lehnt das Tool ab.
    pc.evaluate(
        """([key, action]) => {
            const form = document.createElement('form');
            form.method = 'post';
            form.action = action;
            form.innerHTML = document.querySelector('dialog input[name="csrfmiddlewaretoken"]').outerHTML
                + '<input type="hidden" name="person" value="' + key + '">';
            document.querySelector('dialog .a-dialog-inhalt').appendChild(form);
            form.requestSubmit();
        }""",
        [_erika().key, f"{address}benennen/"],
    )
    expect(_dialog(pc)).to_contain_text("Dir selbst kannst du keine Rolle geben")
    _steht_bei(pc, spot)


# S8: Führt die Handlung auf eine andere Seite, beginnt diese oben.
def test_neue_veranstaltung_beginnt_oben(pc, monkeypatch):
    # Seit #379 ist ein Beginn vor heute verboten; „heute“ liegt vor dem Probelager (der Server läuft im selben Prozess).
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2027, 1, 5))
    login(pc)
    _lange_walhall()
    # Jede Seite bekommt unten viel Platz, damit auch die kurze Seite einer Veranstaltung rollen könnte.
    pc.add_init_script(PADDING)
    pc.goto(f"{BASE}/veranstaltungen/")
    create = pc.locator('[aria-labelledby="h-veranstaltungen"] .a-flaeche-aktion')
    spot = _roll_to(pc, int(create.evaluate("e => e.getBoundingClientRect().top + scrollY")) - 40)
    assert spot > 20
    create.click()
    pc.wait_for_url(f"{BASE}/veranstaltungen/erstellen/")
    # Seit #380 ist „Veranstaltung erstellen“ kein Dialog mehr, sondern eine eigene Seite: Sie beginnt oben.
    assert _y(pc) == 0
    step = pc.locator("form#f-schritt")
    step.get_by_label("Name").fill("Probelager 2027")
    # Seit #379 steht neben Beginn und Ende je eine Uhrzeit; die Felder sucht der Test über ihren Namen.
    step.locator('input[name="start"]').fill("2027-05-15")
    step.locator('input[name="end"]').fill("2027-05-17")
    # Seit #163 steht davor im Adressfeld „Adresse suchen“; gemeint ist „Weiter“.
    step.locator('.a-schritt-rechts button[type="submit"]').click()
    pc.wait_for_url(f"{BASE}/veranstaltungen/*/anlegen/zusammenfassung/")
    pc.get_by_role("button", name="Veranstaltung speichern").click()

    pc.wait_for_url(f"{BASE}/veranstaltungen/*/")
    expect(pc.locator("h1")).to_have_text("Probelager 2027")
    assert _most(pc) > spot
    assert _y(pc) == 0


# S8 (unabhängige Prüfung, Befund M1): Erika gibt ihre Verbandsleitung ab und ist noch Stammesleitung. Unter
# derselben Adresse „/organisation/“ steht danach statt „Verband“ die Seite ihres Stamms; die beginnt oben.
def test_andere_seite_unter_derselben_adresse_beginnt_oben(pc):
    login(pc)
    erika = _erika()
    dpv = unit(U.FEDERATION, "DPV")
    for number in range(15):
        unit(U.ASSOCIATION, f"Bund {number:02d}", dpv)
    walhall = unit(U.TROOP, "Walhall", Unit.objects.get(name="Bund 00"))
    give(erika, R.FEDERATION_LEAD, dpv)
    give(person("viktor.verband", "Viktor", "Verband"), R.FEDERATION_LEAD, dpv)
    give(erika, R.TROOP_LEAD, walhall)
    # Jede Seite bekommt unten viel Platz, damit auch die Seite des Stamms rollen könnte.
    pc.add_init_script(PADDING)
    pc.goto(f"{BASE}/organisation/")
    give_up = pc.locator('[aria-labelledby="h-verbandsleitung"] .a-leitung-knopf', has_text="Rolle abgeben")
    spot = _roll_to(pc, int(give_up.evaluate("e => e.getBoundingClientRect().top + scrollY")) - 80)
    assert spot > 50
    give_up.click()
    expect(_dialog(pc)).to_be_visible()
    _steht_bei(pc, spot)
    _dialog(pc).locator(".btn-gefahr").click()

    pc.wait_for_url(f"{BASE}/organisation/")
    expect(pc.locator(".a-orga-name")).to_have_text("Walhall")
    assert _most(pc) > spot
    assert _y(pc) == 0


# S9, S10: Später neu geöffnet, über einen Link oder direkt über die Adresse eines Dialogs, beginnt die Seite oben.
def test_spaeter_neu_geoeffnet_beginnt_die_seite_oben(pc):
    login(pc)
    found = _lange_walhall()
    address = _page_of(found["walhall"])
    pc.goto(address)
    spot = _roll_to(pc, _most(pc))
    _flink_entfernen(pc).click()
    pc.wait_for_url(f"{address}entfernen/**")
    dialog_address = pc.url
    _dialog(pc).get_by_role("link", name="Abbrechen").click()
    pc.wait_for_url(address)
    _steht_bei(pc, spot)

    # S9: über einen Link in der Gliederung
    pc.locator(".a-gliederung a[aria-current]").click()
    pc.wait_for_load_state()
    assert pc.url == address
    assert _y(pc) == 0

    # S10: direkt über die Adresse des Dialogs, etwa aus einem Lesezeichen
    _roll_to(pc, _most(pc))
    pc.goto(dialog_address)
    expect(_dialog(pc)).to_be_visible()
    assert _y(pc) == 0


# S11: Der Knopf „Bearbeiten“ bekommt wie bisher den Fokus (#117), die Seite steht trotzdem an der gemerkten Stelle.
def test_bearbeiten_bei_verwalteter_person_fokus_ohne_sprung(pc):
    _bearbeiten_fokus_ohne_sprung(pc)


def test_bearbeiten_fokus_ohne_sprung_auch_wenn_der_test_spaet_nach_der_adresse_fragt(pc, monkeypatch):
    """Wie S11, nur fragt der Test jedes Mal erst 1,5 Sekunden später nach der Adresse (#349).

    So langsam war Firefox auf GitHub einmal (Lauf 43705804661): Die Seite war schon geladen, und ihr Skript
    hatte die Kennung des Knopfs schon aus der Adresse genommen.
    """
    original = pc.wait_for_url

    def late_wait_for_url(*args, **options):
        # Nicht time.sleep: Dann stünde auch Playwright still und erführe erst danach, was die Seite inzwischen tat.
        pc.wait_for_timeout(1500)
        return original(*args, **options)

    monkeypatch.setattr(pc, "wait_for_url", late_wait_for_url)
    _bearbeiten_fokus_ohne_sprung(pc)


def _bearbeiten_fokus_ohne_sprung(pc: Page) -> None:
    login(pc)
    found = _lange_walhall(managed=True)
    address = _page_of(found["walhall"])
    pc.goto(address)
    edit = pc.locator(f'{PERSONS} a[href*="/verwaltete-person/{found["paul"].key}/bearbeiten/"]')
    spot = _at_bottom_of_window(pc, edit)
    assert spot > 300 and _most(pc) - spot > 300, "Ein Sprung zum Knopf muss auffallen."

    edit.click()
    pc.wait_for_url(f"{address}verwaltete-person/{found['paul'].key}/bearbeiten/")
    _steht_bei(pc, spot)
    _dialog(pc).get_by_role("link", name="Abbrechen").click()

    wait_for_page_below(pc, address, f"bearbeiten-{found['paul'].key}")
    expect(edit).to_be_focused()
    _steht_bei(pc, spot)


# S12: Ohne Skript springen Öffnen, Abbrechen und Entfernen zum Abschnitt „Leitungen“, am PC und am Handy.
@pytest.mark.parametrize("device", ["pc_ohne_skript", "handy_ohne_skript"])
def test_ohne_skript_springt_die_seite_zum_abschnitt(device, request, browser_name):
    page = request.getfixturevalue(device)
    login(page)
    found = _lange_walhall()
    address = _page_of(found["walhall"])
    page.goto(address)

    def _section_on_top() -> None:
        _on_top(page, "#abschnitt-leitungen")

    _flink_entfernen(page).click()
    page.wait_for_url(f"{address}entfernen/*/#abschnitt-leitungen")
    expect(_dialog(page)).to_be_visible()
    _section_on_top()

    _dialog(page).get_by_role("link", name="Abbrechen").click()
    page.wait_for_url(f"{address}#abschnitt-leitungen")
    expect(_dialog(page)).to_have_count(0)
    _section_on_top()

    _flink_entfernen(page).click()
    page.wait_for_url(f"{address}entfernen/*/#abschnitt-leitungen")
    _dialog(page).get_by_role("button", name="Entfernen").click()
    page.wait_for_url(f"{address}#abschnitt-leitungen")
    expect(page.locator(LEADS)).not_to_contain_text("Flink")
    expect(page.locator("main")).to_contain_text("Flink (Finn Muster) ist nicht mehr Stammesleitung von Walhall.")
    _section_on_top()


# S13: Ohne Skript springt die Seite bei verwalteten Personen wie bisher zum Knopf „Bearbeiten“ (#117).
def test_ohne_skript_bei_verwalteter_person_zum_knopf(pc_ohne_skript):
    page = pc_ohne_skript
    login(page)
    found = _lange_walhall(managed=True)
    address = _page_of(found["walhall"])
    page.goto(address)
    edit = page.locator(f'{PERSONS} a[href*="/verwaltete-person/{found["paul"].key}/bearbeiten/"]')

    edit.click()
    page.wait_for_url(f"{address}verwaltete-person/{found['paul'].key}/bearbeiten/#abschnitt-personen")
    _on_top(page, "#abschnitt-personen")

    _dialog(page).get_by_role("link", name="Abbrechen").click()
    page.wait_for_url(f"{address}#bearbeiten-{found['paul'].key}")
    _on_top(page, f"#bearbeiten-{found['paul'].key}")
