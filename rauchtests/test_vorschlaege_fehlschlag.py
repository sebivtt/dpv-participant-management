"""Rauchtest: Vorschläge beim Benennen, wenn die Abfrage scheitert (#378).

Je Szenario ein Test nach Sebastians Szenarien vom 17.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/378, Kommentar „Szenarien (17.11.2026)“):
Erika Testfrau, Stammesleitung von Walhall, öffnet auf der Seite „Sippe Falken“ den Dialog
„Gruppenleitung benennen“; Finn Falke (Fahrtenname Flink) ist Mitglied der Sippe Falken. Den
Fehlschlag stellt der Browser nach: ohne Verbindung (S1, S5), mit einer Fehlerantwort (S2, S6) oder
mit einer Abfrage, die der Test festhält (S3, S4). Dass die Meldung vom Server kommt, prüft
tests/test_benennen.py. Alle Namen sind erfunden.
"""

from contextlib import suppress

from playwright.sync_api import Error, Page, Route, expect

from rauchtests.conftest import BASE, EXPECT_TIMEOUT_MS, login, run_axe
from rauchtests.test_benennen import _dialog, _walhall_for_erika
from rauchtests.test_organisation import _no_side_scroll

FIELD = "Name, Fahrtenname, Mail oder Benutzername"
SUGGESTIONS = "**/benennen/vorschlaege/"
FAILED = (
    "Die Vorschläge konnten gerade nicht geladen werden. Tippe weiter, um es noch einmal zu versuchen, oder finde "
    "die Person mit „Suchen“ über die genaue Mail oder den Benutzernamen."
)


def _open(page: Page):
    """Erika auf „Gruppenleitung benennen“ der Sippe Falken; gibt Dialog und Feld zurück."""
    login(page)
    units = _walhall_for_erika()
    page.goto(f"{BASE}/organisation/{units['falken'].key}/benennen/")
    dialog = _dialog(page)
    expect(dialog).to_be_visible()
    return dialog, page.get_by_label(FIELD)


def _flink_suggested(dialog) -> None:
    expect(dialog.locator(".a-treffer")).to_contain_text("Flink")
    expect(dialog.locator(".a-meldung")).to_have_count(0)


def _failure_shown(dialog) -> None:
    """Liste leer, an ihrer Stelle die Meldung als Fehler, die das Vorleseprogramm mit „Fehler“ vorweg ansagt."""
    notice = dialog.locator("[data-treffer] .a-meldung")
    expect(notice).to_have_count(1)
    expect(notice).to_have_class("a-meldung ist-fehler")
    expect(notice).to_have_attribute("role", "alert")
    expect(notice).to_have_text(f"Fehler: {FAILED}")
    expect(dialog.locator(".a-treffer")).to_have_count(0)
    expect(dialog.locator(".a-trefferliste, .a-treffer-titel")).to_have_count(0)


def _ohne_verbindung(page: Page) -> None:
    dialog, field = _open(page)
    field.press_sequentially("Fin")
    _flink_suggested(dialog)

    page.context.set_offline(True)
    field.press_sequentially("x")

    _failure_shown(dialog)
    page.context.set_offline(False)
    assert run_axe(page) == []


def test_s1_ohne_verbindung_am_pc(pc):
    _ohne_verbindung(pc)


def test_s1_ohne_verbindung_am_handy(handy):
    _ohne_verbindung(handy)
    _no_side_scroll(handy)


def test_s2_fehler_im_tool(pc):
    dialog, field = _open(pc)
    pc.route(SUGGESTIONS, lambda route: route.fulfill(status=500, body="Serverfehler"))

    field.press_sequentially("Fin")

    _failure_shown(dialog)


def test_s3_zu_langsam_dann_kommt_die_antwort_doch_noch(pc):
    dialog, field = _open(pc)
    field.press_sequentially("Fin")
    _flink_suggested(dialog)
    held: list[Route] = []
    pc.route(SUGGESTIONS, lambda route: held.append(route))

    field.press_sequentially("n")
    # Beim Warten bleiben die alten Vorschläge stehen, ohne Meldung.
    pc.wait_for_timeout(1500)
    assert len(held) == 1
    _flink_suggested(dialog)

    # Nach 5 Sekunden ohne Antwort; die Wartezeit beginnt erst hier, deshalb etwas Luft obendrauf.
    expect(dialog.locator("[data-treffer] .a-meldung")).to_have_count(1, timeout=EXPECT_TIMEOUT_MS + 5000)
    _failure_shown(dialog)
    # Die späte Antwort wird verworfen: Die Meldung bleibt, die Liste bleibt leer.
    pc.unroute(SUGGESTIONS)
    # Hat das Skript die Abfrage schon abgebrochen, kommt die Antwort gar nicht mehr an.
    with suppress(Error):
        held[0].fulfill(response=held[0].fetch())
    pc.wait_for_timeout(500)
    _failure_shown(dialog)


def test_s4_aeltere_abfrage_scheitert_erst_nach_der_neueren(pc):
    dialog, field = _open(pc)
    held: list[Route] = []

    def hold_first(route: Route) -> None:
        if held:
            route.continue_()
        else:
            held.append(route)

    pc.route(SUGGESTIONS, hold_first)
    with pc.expect_request(SUGGESTIONS):
        field.press_sequentially("Fin")
    field.press_sequentially("n")
    _flink_suggested(dialog)

    held[0].abort()
    pc.wait_for_timeout(500)

    _flink_suggested(dialog)
    expect(field).to_have_value("Finn")


def test_s5_verbindung_wieder_da(pc):
    dialog, field = _open(pc)
    field.press_sequentially("Fin")
    _flink_suggested(dialog)
    pc.context.set_offline(True)
    field.press_sequentially("x")
    _failure_shown(dialog)

    pc.context.set_offline(False)
    field.press("Backspace")

    _flink_suggested(dialog)


def test_s6_unter_drei_zeichen(pc):
    dialog, field = _open(pc)
    pc.route(SUGGESTIONS, lambda route: route.fulfill(status=500, body="Serverfehler"))
    field.press_sequentially("Fin")
    _failure_shown(dialog)

    field.press("Backspace")

    expect(field).to_have_value("Fi")
    expect(dialog.locator("[data-treffer]")).to_be_empty()


def test_u3_abgelaufene_anmeldung_fuehrt_zum_login_nicht_zur_meldung(pc):
    """Risikovariante zu U3 (#92): Die neue Fehlerbehandlung darf die Weiterleitung nicht verschlucken."""
    dialog, field = _open(pc)
    # Wie nach Ablauf der Sitzung: Das Formular bleibt gültig, die Anmeldung ist weg.
    pc.context.clear_cookies(name="sessionid")

    field.press_sequentially("Fin")

    pc.wait_for_url(f"{BASE}/anmelden/**")
    expect(pc.locator(".a-meldung", has_text="Die Vorschläge konnten")).to_have_count(0)
