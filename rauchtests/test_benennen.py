"""Rauchtest „Leitung benennen“ im Browser (#190): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall, wie Wanda in
den Szenarien. Geprüft werden die Teile, die nur ein Browser zeigt: Der Dialog ist modal und hält den
Fokus, Escape führt zurück, die Vorschläge kommen beim Tippen, auch wie am Handy mit Autokorrektur,
die kurze Meldung erscheint, nichts steht seitlich über, der Fokus ist zu sehen, und die Seiten
bestehen die Prüfung auf Barrierefreiheit. Die Regeln selbst prüft tests/test_benennen.py. Alle
Namen sind erfunden.
"""

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone
from roles.models import Role
from tests.test_rollen import give, person, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind


def _walhall_for_erika() -> dict:
    """Boreas mit Walhall (Sippe Falken mit Finn, ohne Leitung) und Zugvögel; Erika leitet Walhall, Otto hat kein Mitglied."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    falken = unit(U.GROUP, "Sippe Falken", walhall)
    unit(U.TROOP, "Zugvögel", boreas)
    give(erika, R.TROOP_LEAD, walhall)
    finn = person("finn.falke", "Finn", "Falke")
    finn.scout_name = "Flink"
    finn.save()
    give(finn, R.MEMBER, falken)
    otto = person("otto.ohne", "Otto", "Ohne")
    otto.email = "otto.ohne@example.org"
    otto.last_login = timezone.now()
    otto.save()
    EmailAddress.objects.create(user=otto, email=otto.email, verified=True, primary=True)
    return {"walhall": walhall, "falken": falken, "finn": finn, "otto": otto}


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def test_am_pc_nur_mit_der_tastatur_benennen(pc):
    login(pc)
    units = _walhall_for_erika()
    pc.goto(f"{BASE}/organisation/{units['falken'].key}/")
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, ".a-flaeche-aktion", steps=40)
    _all_visible(stations)
    expect(pc.locator(".a-flaeche-aktion")).to_have_text("Gruppenleitung benennen")
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{BASE}/organisation/{units['falken'].key}/benennen/")
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    field = pc.get_by_label("Name, Fahrtenname, Mail oder Benutzername")
    expect(field).to_be_focused()
    assert run_axe(pc) == []

    pc.keyboard.type("Fin")
    expect(dialog.locator(".a-treffer")).to_contain_text("Flink")
    expect(dialog.locator(".a-treffer")).to_contain_text("Sippe Falken")
    # Der Fokus bleibt im Dialog: Tab geht nie auf die Seite darunter.
    stations = _stations_to_element(pc, ".a-treffer-knopf button", steps=10)
    _all_visible(stations)
    assert pc.evaluate("document.activeElement.closest('dialog') !== null")
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{BASE}/organisation/{units['falken'].key}/")
    expect(pc.locator(".a-kurz")).to_contain_text("Flink (Finn Falke) ist jetzt Gruppenleitung von Sippe Falken.")
    expect(pc.locator(".a-leitung")).to_contain_text("Flink")
    expect(pc.locator(".a-orga-kopf")).not_to_contain_text("Du springst ein")
    # Erst prüfen, wenn die kurze Meldung fertig eingeblendet ist; mitten im Einblenden ist sie halb durchsichtig.
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []


def test_am_pc_escape_und_tippen_daneben_fuehren_zurueck(pc):
    login(pc)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"

    pc.goto(f"{page_address}benennen/")
    expect(_dialog(pc)).to_be_visible()
    pc.keyboard.press("Escape")
    pc.wait_for_url(page_address)
    expect(_dialog(pc)).to_have_count(0)

    pc.goto(f"{page_address}benennen/")
    pc.mouse.click(5, 450)
    pc.wait_for_url(page_address)

    pc.goto(f"{page_address}benennen/")
    _dialog(pc).get_by_role("link", name="Abbrechen").click()
    pc.wait_for_url(page_address)


def test_am_pc_suchen_findet_otto_ueber_die_genaue_mail(pc):
    login(pc)
    units = _walhall_for_erika()
    pc.goto(f"{BASE}/organisation/{units['walhall'].key}/benennen/")

    field = pc.get_by_label("Name, Fahrtenname, Mail oder Benutzername")
    field.fill("OTTO.OHNE@example.org")
    field.press("Enter")

    dialog = _dialog(pc)
    expect(dialog.locator(".a-treffer")).to_contain_text("Otto Ohne")
    expect(dialog.locator(".a-treffer")).to_contain_text("noch nirgends Mitglied")
    expect(field).to_have_value("OTTO.OHNE@example.org")
    assert run_axe(pc) == []
    dialog.get_by_role("button", name="Benennen Otto Ohne").click()

    pc.wait_for_url(f"{BASE}/organisation/{units['walhall'].key}/")
    expect(pc.locator(".a-kurz")).to_contain_text("Otto Ohne ist jetzt Stammesleitung von Walhall.")


def test_am_handy_nur_mit_der_tastatur_und_mit_autokorrektur(handy):
    login(handy)
    units = _walhall_for_erika()
    handy.goto(f"{BASE}/organisation/{units['falken'].key}/")
    _no_side_scroll(handy)
    expect(handy.locator(".a-flaeche-aktion")).to_be_visible()

    stations = _stations_to_element(handy, ".a-flaeche-aktion", steps=40)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{BASE}/organisation/{units['falken'].key}/benennen/")
    dialog = _dialog(handy)
    expect(dialog).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    field = handy.get_by_label("Name, Fahrtenname, Mail oder Benutzername")
    # Wie am Handy: ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; die Vorschläge kommen trotzdem.
    _type_like_a_phone(field, "Fa", "lk", "lke", "")
    expect(field).to_have_value("Falke")
    expect(dialog.locator(".a-treffer")).to_contain_text("Flink")
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, ".a-treffer-knopf button", steps=10)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{BASE}/organisation/{units['falken'].key}/")
    expect(handy.locator(".a-kurz")).to_contain_text("Flink (Finn Falke) ist jetzt Gruppenleitung von Sippe Falken.")
    _no_side_scroll(handy)
