"""Rauchtest der Seite „Verband“ und von „Rolle abgeben“ des Teams im Browser (#94): am PC und am Handy, nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und ist danach Verbandsleitung wie Vera
in den Szenarien, auf „Mein Profil“ zusätzlich im DPV-Veranstaltungsteam. Geprüft wird, was nur
ein Browser zeigt: Knöpfe sind mit der Tastatur erreichbar, Dialoge sind modal und halten den
Fokus, die kurze Meldung erscheint, nichts steht seitlich über, und die Seiten bestehen die Prüfung
auf Barrierefreiheit. Die Regeln selbst prüft tests/test_verband.py. Alle Namen sind erfunden.
"""

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, HANDY, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element
from roles.models import Role
from tests.test_rollen import give, person, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
ADDRESS = f"{BASE}/organisation/"


def _verband_for_erika() -> dict:
    """Der Verband mit Boreas (Bruno „Brummbär“ als Bundesleitung); Erika ist Verbandsleitung und im Team, Otto ohne Zuordnung."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    unit(U.ASSOCIATION, "DPBM Mosaik", dpv, has_rings=True)
    give(erika, R.FEDERATION_LEAD, dpv)
    give(erika, R.EVENT_TEAM, dpv)
    bruno = person("bruno.bund", "Bruno", "Bund")
    bruno.scout_name = "Brummbär"
    bruno.save()
    give(bruno, R.ASSOCIATION_LEAD, boreas)
    otto = person("otto.ohne", "Otto", "Ohne")
    otto.email = "otto.ohne@example.org"
    otto.last_login = timezone.now()
    otto.save()
    EmailAddress.objects.create(user=otto, email=otto.email, verified=True, primary=True)
    return {"dpv": dpv, "boreas": boreas, "bruno": bruno, "otto": otto}


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _settled(page: Page) -> None:
    """Erst prüfen, wenn die kurze Meldung fertig eingeblendet ist; mitten im Einblenden ist sie halb durchsichtig."""
    page.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")


def test_am_pc_nur_mit_der_tastatur_bundesleitung_benennen(pc):
    login(pc)
    units = _verband_for_erika()
    pc.goto(ADDRESS)
    expect(pc.locator("h1")).to_have_text("Verband")
    # „Bünde“ so groß wie „Verband“ (Sebastian, 30.10.2026, Punkt 3, nachgeschärft: zwei gleichrangige Teile).
    sizes = pc.evaluate("[document.querySelector('h1'), document.getElementById('h-buende')].map(e => getComputedStyle(e).fontSize)")
    assert len(set(sizes)) == 1, sizes
    assert run_axe(pc) == []

    selector = f'a[href="/organisation/verband/bund/{units["boreas"].key}/benennen/"]'
    stations = _stations_to_element(pc, selector, steps=60)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{ADDRESS}verband/bund/{units['boreas'].key}/benennen/")
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Bundesleitung benennen")
    field = pc.get_by_label("Mail oder Benutzername")
    expect(field).to_be_focused()
    assert run_axe(pc) == []

    pc.keyboard.type("otto.ohne@example.org")
    pc.keyboard.press("Enter")
    expect(dialog.locator(".a-treffer")).to_contain_text("Otto Ohne")
    expect(dialog.locator(".a-treffer")).to_contain_text("Mit dem Benennen wird die Person Mitglied von Pfadfinderbund Boreas.")
    stations = _stations_to_element(pc, ".a-treffer-knopf button", steps=10)
    _all_visible(stations)
    assert pc.evaluate("document.activeElement.closest('dialog') !== null")
    pc.keyboard.press("Enter")

    pc.wait_for_url(ADDRESS)
    expect(pc.locator(".a-kurz")).to_contain_text("Otto Ohne ist jetzt Bundesleitung von Pfadfinderbund Boreas.")
    expect(pc.locator(".a-bund").filter(has_text="Pfadfinderbund Boreas")).to_contain_text("Otto Ohne")
    _settled(pc)
    assert run_axe(pc) == []


def test_am_pc_escape_im_dialog_aendert_nichts(pc):
    login(pc)
    units = _verband_for_erika()
    pc.goto(f"{ADDRESS}verband/{units['dpv'].key}/team/benennen/")
    expect(_dialog(pc).locator("h2")).to_have_text("Teammitglied benennen")

    pc.keyboard.press("Escape")

    pc.wait_for_url(ADDRESS)
    expect(_dialog(pc)).to_have_count(0)


def test_am_handy_nur_mit_der_tastatur_bundesleitung_entfernen(handy):
    login(handy)
    units = _verband_for_erika()
    # Auch auf einem schmalen Handy steht nichts über: Die lange Rolle „DPV-Veranstaltungsteam“ mit „Rolle
    # abgeben“ ragte auf GitHub mit dessen breiterer Schrift 8 Pixel über, lokal erst unter 360 Pixel.
    handy.set_viewport_size({"width": 340, "height": handy.viewport_size["height"]})
    handy.goto(ADDRESS)
    _no_side_scroll(handy)
    handy.set_viewport_size(HANDY["viewport"])
    handy.goto(ADDRESS)
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    stations = _stations_to_element(handy, ".a-bund .a-leitung-knopf", steps=60)
    _all_visible(stations)
    expect(handy.locator(".a-bund .a-leitung-knopf")).to_have_text("Entfernen: Brummbär")
    handy.keyboard.press("Enter")

    dialog = _dialog(handy)
    expect(dialog).to_be_visible()
    expect(dialog.locator("h2")).to_have_text("Brummbär (Bruno Bund) als Bundesleitung von Pfadfinderbund Boreas entfernen?")
    expect(dialog).to_contain_text("Eine neue Bundesleitung kann nur die Verbandsleitung benennen. Trotzdem entfernen?")
    _no_side_scroll(handy)
    assert run_axe(handy) == []
    stations = _stations_to_element(handy, ".btn-gefahr", steps=10)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    handy.wait_for_url(ADDRESS)
    expect(handy.locator(".a-kurz")).to_contain_text("Brummbär (Bruno Bund) ist nicht mehr Bundesleitung von Pfadfinderbund Boreas.")
    expect(handy.locator(".a-bund").filter(has_text="Pfadfinderbund Boreas")).to_contain_text(
        "Pfadfinderbund Boreas hat keine Bundesleitung.")
    assert Role.objects.filter(user=units["bruno"], kind=R.ASSOCIATION_LEAD).count() == 0
    _no_side_scroll(handy)


def test_am_handy_nur_mit_der_tastatur_die_rolle_im_team_abgeben(handy):
    login(handy)
    _verband_for_erika()
    handy.goto(f"{BASE}/profil/")
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, ".a-kachel-knopf", steps=40)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    handy.wait_for_url(f"{BASE}/profil/team-abgeben/")
    dialog = _dialog(handy)
    expect(dialog.locator("h2")).to_have_text("Deine Rolle im DPV-Veranstaltungsteam abgeben?")
    assert run_axe(handy) == []
    stations = _stations_to_element(handy, ".btn-gefahr", steps=10)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    handy.wait_for_url(f"{BASE}/profil/")
    expect(handy.locator(".a-kurz")).to_contain_text("Du bist nicht mehr im DPV-Veranstaltungsteam.")
    expect(handy.locator(".a-kachel-knopf")).to_have_count(0)
    _settled(handy)
    assert run_axe(handy) == []


def test_am_pc_die_rolle_im_team_abgeben(pc):
    login(pc)
    _verband_for_erika()
    pc.goto(f"{BASE}/profil/")
    assert run_axe(pc) == []

    pc.locator(".a-kachel-knopf").click()
    _dialog(pc).get_by_role("button", name="Rolle abgeben").click()

    pc.wait_for_url(f"{BASE}/profil/")
    expect(pc.locator(".a-kurz")).to_contain_text("Du bist nicht mehr im DPV-Veranstaltungsteam.")


# ---------- #218: zurück zur Seite „Verband“ ----------


def _erika_leads_boreas_too() -> dict:
    """Erika ist Verbandsleitung und Bundesleitung von Boreas wie Vera in Szenario 1; der Verband hat den langen Namen aus Szenario 8."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "Deutscher Pfadfinderverband")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    give(erika, R.FEDERATION_LEAD, dpv)
    give(erika, R.MEMBER, boreas)
    give(erika, R.ASSOCIATION_LEAD, boreas)
    return {"boreas": boreas, "walhall": walhall}


def test_am_handy_nur_mit_der_tastatur_von_walhall_zurueck_zur_seite_verband(handy):
    login(handy)
    units = _erika_leads_boreas_too()
    walhall = f"{ADDRESS}{units['walhall'].key}/"
    # Der lange Name bricht im Pfad um, auch auf einem schmalen Handy (Szenario 8).
    handy.set_viewport_size({"width": 340, "height": handy.viewport_size["height"]})
    handy.goto(walhall)
    expect(handy.locator(".a-pfad a").first).to_have_text("Deutscher Pfadfinderverband")
    _no_side_scroll(handy)
    handy.set_viewport_size(HANDY["viewport"])
    handy.goto(walhall)
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    stations = _stations_to_element(handy, ".a-orga-zurueck", steps=20)
    _all_visible(stations)
    expect(handy.locator(".a-orga-zurueck")).to_have_text("‹ Verband")
    handy.keyboard.press("Enter")

    handy.wait_for_url(ADDRESS)
    expect(handy.locator("h1")).to_have_text("Verband")


def test_am_pc_fuehrt_der_verband_im_pfad_zur_seite_verband(pc):
    login(pc)
    units = _erika_leads_boreas_too()
    pc.goto(f"{ADDRESS}{units['boreas'].key}/")
    expect(pc.locator(".a-orga-zurueck")).to_be_hidden()
    assert run_axe(pc) == []

    pc.locator(".a-pfad").get_by_role("link", name="Deutscher Pfadfinderverband").click()

    pc.wait_for_url(ADDRESS)
    expect(pc.locator("h1")).to_have_text("Verband")
