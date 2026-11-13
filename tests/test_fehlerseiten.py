"""Tests für die Knöpfe „Zurück“ und „Zur Startseite“ auf den Fehlerseiten (#21, NFA-01, NFA-03).

Die Nummern verweisen auf die Szenarien zu #21 (Planung am 22.10.2026). Ob „Zurück“ erscheint,
entscheidet erst der Browser anhand der vorigen Seite; das prüft der Rauchtest in rauchtests/.
Hier wird geprüft, was der Server schickt. Alle Daten sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.test.html import Element, parse_html

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls")]

User = get_user_model()

# Eine vorige Seite, die der Browser mitschickt. Sie darf nie in der Fehlerseite stehen.
PREVIOUS_PAGE = "http://testserver/veranstaltungen/4711/?suche=erika"
FOREIGN_PAGE = "https://fremd.example/boese/"


def _logged_in_client() -> Client:
    client = Client(raise_request_exception=False)
    user = User.objects.create(username="erika.testfrau", first_name="Erika", last_name="Testfrau",
                               email="erika.testfrau@example.org")
    client.force_login(user)
    return client


def _not_found(client, **headers):
    return client.get("/gibt-es-nicht/", **headers)


def _forbidden(client, **headers):
    return client.get("/test/1/verboten/", **headers)


def _form_expired(client, **headers):
    # Ohne gültigen Formularschutz (CSRF), etwa weil das Formular zu lange offen war.
    client.handler.enforce_csrf_checks = True
    return client.post("/abmelden/", **headers)


def _bad_request(client, **headers):
    # Unbekannter Servername: Das Tool lehnt die Anfrage ab.
    return client.get("/anmelden/", HTTP_HOST="fremd.example", **headers)


def _server_error(client, **headers):
    return client.get("/test/1/", **headers)


ERROR_PAGES = [
    pytest.param(_not_found, 404, id="nicht-gefunden"),
    pytest.param(_forbidden, 403, id="kein-zugriff"),
    pytest.param(_form_expired, 403, id="formular-abgelaufen"),
    pytest.param(_bad_request, 400, id="ungueltige-anfrage"),
    pytest.param(_server_error, 500, id="programmfehler"),
]


def _attr(element: Element, name: str) -> str | None:
    for key, value in element.attributes:
        if key == name:
            return value if value is not None else ""
    return None


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


def _link(root, text: str) -> Element:
    found = _all(root, lambda e: e.name == "a" and _text(e) == text)
    assert len(found) == 1, f"{len(found)} statt genau einem Link „{text}“"
    return found[0]


def _page(request_page, status, **headers) -> Element:
    response = request_page(_logged_in_client(), **headers)
    assert response.status_code == status
    return parse_html(response.content.decode())


# Szenarien 4, 6 und 7
@pytest.mark.parametrize(("request_page", "status"), ERROR_PAGES)
def test_jede_fehlerseite_hat_den_knopf_zur_startseite(request_page, status):
    root = _page(request_page, status)

    assert _attr(_link(root, "Zur Startseite"), "href") == "/"


# Szenarien 2 und 10: ohne Skript, also ohne Prüfung der vorigen Seite, kein Knopf ins Leere
@pytest.mark.parametrize(("request_page", "status"), ERROR_PAGES)
def test_zurueck_kommt_versteckt_und_ohne_ziel_vom_server(request_page, status):
    root = _page(request_page, status, HTTP_REFERER=PREVIOUS_PAGE)

    back = _link(root, "Zurück")
    assert _attr(back, "hidden") is not None
    assert _attr(back, "href") is None


# „Wer darf das nicht?“: Die Fehlerseite zeigt keine Adresse, auch nicht die der vorigen Seite.
@pytest.mark.parametrize(("request_page", "status"), ERROR_PAGES)
@pytest.mark.parametrize("previous", [PREVIOUS_PAGE, FOREIGN_PAGE])
def test_vorige_seite_steht_nicht_in_der_fehlerseite(request_page, status, previous):
    response = request_page(_logged_in_client(), HTTP_REFERER=previous)

    assert response.status_code == status
    page = response.content.decode()
    assert "4711" not in page
    assert "erika" not in page.lower()
    assert "fremd.example" not in page


# Szenario 3: Die Prüfung im Browser braucht die vorige Seite des Tools; fremde schickt er nie mit.
def test_browser_schickt_die_vorige_seite_nur_innerhalb_des_tools_mit():
    response = Client().get("/anmelden/")

    assert response["Referrer-Policy"] == "same-origin"


# Entschiedene Bausteine stehen im Bausteinkatalog (#176, docs/gestaltung.md)
@pytest.mark.bausteinkatalog
def test_katalog_zeigt_die_knoepfe_der_fehlerseite():
    response = _logged_in_client().get("/bausteine/")

    assert response.status_code == 200
    root = parse_html(response.content.decode())
    section = _all(root, lambda e: e.name == "section" and _attr(e, "aria-labelledby") == "h-fehlerseite")
    assert len(section) == 1, "kein Abschnitt „Knöpfe der Fehlerseite“ im Katalog"
    back = _link(section[0], "Zurück")
    assert _attr(back, "hidden") is None, "im Katalog steht „Zurück“ immer sichtbar als Beispiel"
    assert _attr(_link(section[0], "Zur Startseite"), "href")
