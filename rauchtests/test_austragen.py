"""Rauchtest „Austragen“ und „Austreten“ im Browser (#286): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall, wie Wanda in
den Szenarien; die Sippe Falken hat keine Gruppenleitung, deshalb springt Erika dort ein (P12).
Geprüft werden die Teile, die nur ein Browser zeigt: Der Knopf ist mit der Tastatur erreichbar, der
Dialog ist modal, die Pfeiltasten wechseln die Wahl, und die Vorschau wechselt mit, auch ohne Skript
(Baustein „Auswahl im Dialog“). Die kurze Meldung erscheint, nichts steht seitlich über, und die
Seiten bestehen die Prüfung auf Barrierefreiheit. Die Regeln selbst prüft tests/test_austragen.py.
Alle Namen sind erfunden.
"""

from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_benennen import _walhall_for_erika
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element
from roles.models import Role

R = Role.Kind
PERSONS = '[aria-labelledby="h-personen"]'
EXPEL_BUTTON = f"{PERSONS} .btn-entfernen"
EXIT_BUTTON = ".a-mitgliedschaft .btn-entfernen"


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _shown_previews(page: Page) -> list[str]:
    """Die Vorschau, die gerade zu sehen ist; die der anderen Möglichkeiten ist versteckt."""
    return [text.strip() for text in page.locator(".a-auswahl-folge:visible").all_inner_texts()]


def _expel_dialog(page: Page, units: dict) -> str:
    falken = f"{BASE}/organisation/{units['falken'].key}/"
    return f"{falken}austragen/{units['finn'].key}/"


def test_am_pc_nur_mit_der_tastatur_austragen(pc):
    login(pc)
    units = _walhall_for_erika()
    falken = f"{BASE}/organisation/{units['falken'].key}/"
    pc.goto(falken)
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, EXPEL_BUTTON, steps=60)
    _all_visible(stations)
    expect(pc.locator(EXPEL_BUTTON)).to_have_text("Austragen: Flink")
    pc.keyboard.press("Enter")

    pc.wait_for_url(_expel_dialog(pc, units))
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Flink (Finn Falke) aus Sippe Falken austragen?")
    assert len(_shown_previews(pc)) == 1
    assert "direkt zu Stamm Walhall" in _shown_previews(pc)[0]
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, ".a-auswahl input:checked", steps=10)
    _all_visible(stations)
    pc.keyboard.press("ArrowDown")
    expect(pc.locator(".a-auswahl input[value='ganz']")).to_be_checked()
    assert len(_shown_previews(pc)) == 1
    assert "keiner Organisation mehr an" in _shown_previews(pc)[0]

    stations = _stations_to_element(pc, "dialog .btn-gefahr", steps=10)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(falken)
    expect(pc.locator(".a-kurz")).to_contain_text("Flink (Finn Falke) ist aus Sippe Falken ausgetragen.")
    expect(pc.locator(PERSONS)).not_to_contain_text("Flink")
    assert not Role.objects.filter(user=units["finn"]).exists()
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []


def test_am_pc_escape_fuehrt_zurueck_und_traegt_niemanden_aus(pc):
    login(pc)
    units = _walhall_for_erika()
    falken = f"{BASE}/organisation/{units['falken'].key}/"

    pc.goto(_expel_dialog(pc, units))
    expect(_dialog(pc)).to_be_visible()
    pc.keyboard.press("Escape")
    pc.wait_for_url(falken)
    expect(_dialog(pc)).to_have_count(0)
    assert Role.objects.get(user=units["finn"], kind=R.MEMBER).unit_id == units["falken"].pk


def test_ohne_skript_wechselt_die_vorschau_mit_der_wahl(pc_ohne_skript):
    page = pc_ohne_skript
    login(page)
    units = _walhall_for_erika()
    page.goto(_expel_dialog(page, units))
    assert "direkt zu Stamm Walhall" in _shown_previews(page)[0]

    page.get_by_label("Flink (Finn Falke) gehört danach keiner Organisation mehr an").check()
    assert len(_shown_previews(page)) == 1
    assert "keiner Organisation mehr an" in _shown_previews(page)[0]
    page.locator("dialog .btn-gefahr").click()

    page.wait_for_url(f"{BASE}/organisation/{units['falken'].key}/")
    # Ohne Skript steht die kurze Meldung fest oben auf der Seite (docs/gestaltung.md, „Kurze Meldung“).
    expect(page.locator("[data-kurz]")).to_contain_text("Flink (Finn Falke) ist aus Sippe Falken ausgetragen.")
    assert not Role.objects.filter(user=units["finn"]).exists()


def test_am_handy_nur_mit_der_tastatur_austreten(handy):
    login(handy)
    _walhall_for_erika()
    handy.goto(f"{BASE}/profil/")
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, EXIT_BUTTON, steps=60)
    _all_visible(stations)
    expect(handy.locator(EXIT_BUTTON)).to_have_text("Austreten")
    handy.keyboard.press("Enter")

    handy.wait_for_url(f"{BASE}/profil/austreten/")
    dialog = _dialog(handy)
    expect(dialog).to_be_visible()
    expect(dialog.locator("h2")).to_have_text("Austreten")
    _no_side_scroll(handy)
    assert run_axe(handy) == []
    preview = _shown_previews(handy)
    assert len(preview) == 1
    assert "Damit enden deine Rollen: Stammesleitung von Stamm Walhall." in preview[0]

    stations = _stations_to_element(handy, "dialog .btn-gefahr", steps=15)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    handy.wait_for_url(f"{BASE}/profil/")
    expect(handy.locator(".a-kurz")).to_contain_text("Du bist aus Stamm Walhall ausgetreten.")
    _no_side_scroll(handy)
