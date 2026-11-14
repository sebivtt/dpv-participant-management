"""Rauchtest der Sicherheitsrichtlinie für Skripte im Browser (#278).

Die Kürzel verweisen auf den Kommentar „Szenarien (14.11.2026)“ in #278. Dass jede Antwort die
Richtlinie trägt (E4), prüft tests/test_sicherheitsrichtlinie.py, die Testumgebung (E5) die
Container-Prüfung. Dass die übrigen Seiten wie immer gehen und kein Browser einen Verstoß meldet
(E2, E3), prüfen alle Rauchtests: Jeder wird rot, sobald der Browser einen meldet (conftest.py).

Eingeschmuggelt wird hier nichts ins Tool: Der Browser bekommt die echte Seite mit ihren echten
Kopfzeilen, der Test hängt nur auf dem Weg zum Browser ein Stück an. Der fremde Server
`fremd.example` ist ebenso nur im Test erfunden; jede Anfrage dorthin wird festgehalten.
"""

import pytest
from django.conf import settings
from playwright.sync_api import Page, Route, expect

from rauchtests.conftest import BASE, assert_no_csp_violations, csp_violations, login

# Ohne https: WebKit lädt sonst die Seite des Tools (http) nicht in den Rahmen der fremden Seite.
FOREIGN = "http://fremd.example"
PROFILE = f"{BASE}/profil/"


def _inject(page: Page, address: str, piece: str) -> None:
    """Hängt `piece` an den Inhalt der echten Seite unter `address` an, mit ihren echten Kopfzeilen."""

    def answer(route: Route) -> None:
        response = route.fetch()
        route.fulfill(response=response, body=response.text().replace("</main>", f"{piece}</main>"))

    page.route(address, answer)


def _record_foreign(page: Page) -> list[str]:
    """Hält jede Anfrage an den fremden Server fest; käme eine an, bekäme sie eine leere Antwort."""
    requests: list[str] = []

    def answer(route: Route) -> None:
        requests.append(route.request.url)
        route.fulfill(status=200, body="")

    page.context.route(f"{FOREIGN}/**", answer)
    return requests


def _wait_for_violations(page: Page, *rules: str) -> str:
    """Wartet, bis der Browser für jede Regel einen Verstoß gemeldet hat, und gibt alle Meldungen zurück.

    Ohne Richtlinie kommt keine Meldung; nach 5 Sekunden wird der Test dann rot.
    """
    for _ in range(50):
        found = " ".join(csp_violations(page.context))
        if all(rule in found for rule in rules):
            return found
        page.wait_for_timeout(100)
    raise AssertionError(f"Keine Meldung zu {rules}; gemeldet: {found!r}")


def _settle(page: Page) -> None:
    # Meldungen und Anfragen kommen ein wenig nach dem Laden der Seite.
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)


# E1: Login mit der Richtlinie, ohne Verstoß, in allen drei Browsern
def test_erika_meldet_sich_mit_der_richtlinie_an(pc):
    response = pc.goto(f"{BASE}/anmelden/")
    assert "content-security-policy" in response.headers

    login(pc)

    expect(pc.get_by_role("heading", name="Hallo Erika!")).to_be_visible()


# E1: Auch die Registrierung startet weiter bei Keycloak („Konto anlegen“), trotz der Regel für Formulare.
def test_registrierung_startet_weiter_bei_keycloak(pc):
    response = pc.goto(f"{BASE}/anmelden/")
    assert "content-security-policy" in response.headers

    pc.get_by_role("button", name="Noch kein Konto? Registrieren").click()

    pc.wait_for_url(f"{settings.KEYCLOAK_REALM_URL}/**")
    expect(pc.locator("#kc-register-form")).to_be_visible()


# V1 und G1: Eingeschmuggeltes Skript läuft nicht; der Rauchtest wird rot und nennt den Verstoß.
def test_eingeschmuggeltes_skript_laeuft_nicht_und_der_rauchtest_nennt_es(pc, verstoesse_erwartet):
    login(pc)
    _inject(pc, PROFILE, '<script>document.title = "eingeschmuggelt";</script><p style="color: red">x</p>')

    pc.goto(PROFILE)
    _settle(pc)

    assert pc.title() != "eingeschmuggelt"
    _wait_for_violations(pc, "script-src", "style-src")
    with pytest.raises(AssertionError, match="script-src") as report:
        assert_no_csp_violations(csp_violations(pc.context))
    assert "style-src" in str(report.value)


# V2: Skript, Gestaltung, Schrift und Bild von einem fremden Server lädt der Browser nicht.
def test_nichts_von_fremden_servern(pc, verstoesse_erwartet):
    login(pc)
    foreign = _record_foreign(pc)
    # Die Schrift steht in einer Gestaltung, die scheinbar vom eigenen Server kommt; nur so prüft
    # der Test die Regel für Schriften und nicht die für Gestaltung.
    own_css = f"{BASE}/static/core/probe-fremde-schrift.css"
    pc.route(
        own_css,
        lambda route: route.fulfill(
            content_type="text/css",
            body=f"@font-face {{ font-family: Fremd; src: url({FOREIGN}/schrift.woff2); }} body {{ font-family: Fremd; }}",
        ),
    )
    _inject(
        pc,
        PROFILE,
        f'<script src="{FOREIGN}/skript.js"></script><link rel="stylesheet" href="{FOREIGN}/gestaltung.css">'
        f'<link rel="stylesheet" href="{own_css}"><img src="{FOREIGN}/bild.png" alt="">',
    )

    pc.goto(PROFILE)
    _settle(pc)

    _wait_for_violations(pc, "script-src", "style-src", "font-src", "img-src")
    assert foreign == []


# V3: Ein eingeschmuggeltes Formular an eine fremde Seite schickt der Browser nicht ab.
def test_eingeschmuggeltes_formular_an_fremde_seite_geht_nicht_ab(pc, verstoesse_erwartet):
    login(pc)
    foreign = _record_foreign(pc)
    _inject(pc, PROFILE, f'<form method="post" action="{FOREIGN}/abgreifen"><button>Weiter</button></form>')
    pc.goto(PROFILE)

    # Abschicken wie mit dem Knopf. Ein Klick wartete auf eine Weiterleitung, die nie kommt.
    pc.locator(f"form[action='{FOREIGN}/abgreifen']").evaluate("form => form.requestSubmit()")

    _wait_for_violations(pc, "form-action")
    _settle(pc)
    assert foreign == []
    assert pc.url == PROFILE


# V4: Eine fremde Seite kann das Tool nicht in einem Rahmen zeigen. Der Test entfernt den älteren Schutz
# gegen Einbetten (X-Frame-Options), damit nur die Richtlinie wirkt; der bleibt im Tool unverändert.
def test_fremde_seite_kann_das_tool_nicht_einbetten(pc):
    def without_old_protection(route: Route) -> None:
        response = route.fetch()
        headers = {k: v for k, v in response.headers.items() if k.lower() != "x-frame-options"}
        route.fulfill(response=response, headers=headers)

    pc.route(f"{BASE}/anmelden/", without_old_protection)
    pc.route(
        f"{FOREIGN}/rahmen",
        lambda route: route.fulfill(content_type="text/html", body=f'<iframe src="{BASE}/anmelden/"></iframe>'),
    )

    # Erst weiter, wenn das Tool dem Rahmen geantwortet hat; sonst wäre er nur noch leer.
    with pc.expect_response(f"{BASE}/anmelden/"):
        pc.goto(f"{FOREIGN}/rahmen")
    _settle(pc)

    frame = pc.frame_locator("iframe")
    expect(frame.get_by_role("button", name="Mit DPV-Konto anmelden")).to_have_count(0)
