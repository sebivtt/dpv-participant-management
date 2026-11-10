"""Tests für Konten ohne Zuordnung (#9; PK-06, EH-07, RO-08, dazu EP-01 und EP-03 als Gegenprobe).

Die Kürzel S1 bis G4 verweisen auf Sebastians Szenarien vom 27.10.2026 im Issue #9 (Kommentar
„Szenarien (27.10.2026)“). V4 und V5 (Veranstaltungen, Anmeldungen) prüfen #100 und #101. Wie in
#90 und #64 prüfen die Tests die zentrale Rechteprüfung und die Testadressen in `tests/urls.py`, dazu
Startseite und „Mein Profil“, die einzigen Seiten, die ein Konto ohne Zuordnung heute öffnet.

Der Hinweis richtet sich nach „weder Mitgliedschaft noch Rolle“, nicht nach „Zuordnung“: Ein
Admin ohne Mitgliedschaft sieht ihn nicht (Klärung vom 27.10.2026, Frage 2). Alle Namen sind
erfunden; Personen und Einheiten stammen aus tests/test_rechtepruefung.py.
"""

import pytest
from django.test import Client

from access.rights import Rights
from roles.models import Role
from tests import test_rechtepruefung
from tests.test_gestaltung import _tree
from tests.test_meldungen import assert_is, kind, notice_with, notices, visible
from tests.test_nicht_gefunden import NO_ACCESS_TEXT, answers, assert_like_missing, person_address
from tests.test_rechtepruefung import leads_seen, remove, seen
from tests.test_rollen import give

# Dieselben Einheiten und Personen wie in tests/test_rechtepruefung.py: Otto ist `ohne`, Finn
# `falke`, Anton `adler_kind`, Fiete `falken_leitung`, Vera `verbandsleitung`, Tom `team`.
org = test_rechtepruefung.org

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls")]

R = Role.Kind
PAGES = ("/", "/profil/")
HINT_NAME = "Ergänze deinen Namen in deinem DPV-Konto und melde dich danach neu an."
HINT_NO_ORG_BOLD = "Du bist noch keiner Organisation zugeordnet."
HINT_NO_ORG = (
    f"{HINT_NO_ORG_BOLD} Wende dich an die Leitung deiner Gruppe oder deines Stammes, damit sie dich aufnimmt."
)
# Was Otto nirgends sehen darf: andere Personen, Einheiten und Leitungen (V1 bis V3).
FOREIGN_WORDS = ("Finn", "Anton", "Fiete", "Wanda", "Bruno", "Sippe Falken", "Walhall", "Boreas", "Zugvögel", "Adler")


def client_for(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def open_page(client: Client, address: str):
    response = client.get(address)
    assert response.status_code == 200, (address, response.status_code)
    return _tree(response)


def has_hint(client: Client, address: str) -> bool:
    return any(HINT_NO_ORG_BOLD in visible(notice) for notice in notices(open_page(client, address)))


# S1, S2: Was Otto darf


@pytest.mark.rechtematrix("EP-01", "PK-06")
def test_s1_otto_sieht_sein_eigenes_profil_ohne_mitgliedschaft_und_rolle(org):
    """Gegenprobe zu PK-06: Sich selbst sieht Otto, über die Rechteprüfung, die Testadresse und „Mein Profil“."""
    org.ohne.email = "otto.ohne@example.org"
    org.ohne.save()

    assert seen(org.ohne) == {"otto.ohne"}
    assert {status for status, _content, _headers in answers(org.ohne, person_address(org.ohne))} == {200}
    content = client_for(org.ohne).get("/profil/").content.decode()
    for value in ("Otto", "Ohne", "otto.ohne", "otto.ohne@example.org"):
        assert value in content
    assert "Mitgliedschaft" not in content
    assert "a-rollenkacheln" not in content


@pytest.mark.rechtematrix("EP-03")
def test_s2_otto_traegt_seinen_fahrtennamen_ein(org):
    client = client_for(org.ohne)

    response = client.post("/profil/fahrtenname/", {"scout_name": "Kauz"})

    assert response.status_code == 302
    org.ohne.refresh_from_db()
    assert org.ohne.scout_name == "Kauz"


# H1 bis H5: der Hinweis auf Startseite und „Mein Profil“


@pytest.mark.parametrize("address", PAGES)
def test_h1_otto_sieht_den_hinweis_als_warnmeldung(org, address):
    notice = notice_with(open_page(client_for(org.ohne), address), HINT_NO_ORG_BOLD)

    assert_is(notice, "warning")
    assert visible(notice) == HINT_NO_ORG


def test_h2_mitglied_sieht_den_hinweis_nicht(org):
    client = client_for(org.falke)

    for address in PAGES:
        assert not has_hint(client, address), address


def test_h3_admin_ohne_mitgliedschaft_sieht_den_hinweis_nicht(org):
    give(org.max, R.ADMIN)
    client = client_for(org.max)

    for address in PAGES:
        assert not has_hint(client, address), address


def test_h4_verbandsleitung_und_veranstaltungsteam_ohne_mitgliedschaft_sehen_den_hinweis_nicht(org):
    for user in (org.verbandsleitung, org.team):
        client = client_for(user)
        for address in PAGES:
            assert not has_hint(client, address), (user.username, address)


@pytest.mark.parametrize("address", PAGES)
def test_h5_ohne_nachnamen_zuerst_der_hinweis_zum_namen_dann_dieser(org, address):
    org.ohne.last_name = ""
    org.ohne.save()

    warnings = [n for n in notices(open_page(client_for(org.ohne), address)) if kind(n) == "warning"]

    assert [visible(n) for n in warnings] == [HINT_NAME, HINT_NO_ORG]


# V1 bis V3: Was Otto nicht sieht, auch über direkte Adressen und manipulierte Formulare


@pytest.mark.rechtematrix("PK-06")
def test_v1_otto_findet_weder_finn_noch_anton(org):
    """Fremde Kennungen antworten auf jedem Weg genau wie eine erfundene (#64)."""
    assert seen(org.ohne) == {"otto.ohne"}
    assert_like_missing(org.ohne, person_address(org.falke))
    assert_like_missing(org.ohne, person_address(org.adler_kind))


@pytest.mark.rechtematrix("EH-07")
def test_v2_otto_erreicht_keine_einheit_ueber_ihre_kennung(org):
    """Weder über die Adresse noch über einen angehängten Parameter oder ein Formularfeld."""
    assert_like_missing(org.ohne, f"/test/einheit/{org.falken.key}/")
    client = client_for(org.ohne)
    for method in ("get", "post"):
        response = getattr(client, method)("/test/einheit/", {"einheit": org.falken.key})
        assert response.status_code == 404, method
        assert "Sippe Falken" not in response.content.decode()


@pytest.mark.rechtematrix("EH-07")
def test_v2_otto_sieht_keinen_namen_einer_einheit(org):
    """Auch nicht über die Liste der Leitungen, in der jede Leitung mit ihrer Einheit steht."""
    assert list(Rights(org.ohne).leads()) == []
    assert list(Rights(org.ohne).own_roles()) == []


@pytest.mark.rechtematrix("RO-08")
def test_v3_otto_sieht_keine_leitungen_und_beim_bereich_kein_zugriff(org):
    assert leads_seen(org.ohne) == set()
    for status, content, _headers in answers(org.ohne, "/test/leitungen/"):
        assert status == 403
        assert NO_ACCESS_TEXT in content.decode()


@pytest.mark.rechtematrix("RO-08")
def test_v3_admin_ohne_support_zugang_sieht_keine_leitungen(org):
    """Eigener Fall der Zeile RO-08 (#136, A17): Max ist Admin ohne Mitgliedschaft."""
    give(org.max, R.ADMIN)

    assert leads_seen(org.max) == set()
    assert list(Rights(org.max).leads()) == []


@pytest.mark.rechtematrix("PK-06", "EH-07", "RO-08")
def test_v1_bis_v3_startseite_und_profil_zeigen_nichts_fremdes_auch_mit_fremden_kennungen(org):
    """Angehängte Kennungen und Formulare ändern an den beiden Seiten nichts."""
    client = client_for(org.ohne)
    data = {"person": org.falke.key, "einheit": org.falken.key, "scout_name": "Kauz"}
    for address in PAGES:
        for method in ("get", "post"):
            response = getattr(client, method)(address, data, follow=True)
            assert response.status_code == 200, (address, method)
            content = response.content.decode()
            for word in FOREIGN_WORDS:
                assert word not in content, (address, method, word)


# G1 bis G4: Rechte entstehen und enden mit Mitgliedschaft und Rolle, beim nächsten Klick


@pytest.mark.rechtematrix("EH-07", "RO-08")
def test_g1_mit_mitgliedschaft_ist_der_hinweis_weg_und_otto_sieht_fiete(org):
    """Gegenprobe zu EH-07 und RO-08; das Aufnehmen selbst baut #285, hier wird die Mitgliedschaft direkt angelegt."""
    client = client_for(org.ohne)
    assert has_hint(client, "/")

    give(org.ohne, R.MEMBER, org.falken)

    for address in PAGES:
        assert not has_hint(client, address), address
    assert ("Fiete", R.GROUP_LEAD) in leads_seen(org.ohne)
    assert "Sippe Falken" in client.get("/profil/").content.decode()


def test_g2_als_gruppenleitung_eingesetzt_wird_otto_mitglied_und_der_hinweis_ist_weg(org):
    client = client_for(org.ohne)

    give(org.ohne, R.GROUP_LEAD, org.adler)

    assert Role.objects.filter(user=org.ohne, kind=R.MEMBER, unit=org.adler).exists()
    for address in PAGES:
        assert not has_hint(client, address), address


@pytest.mark.rechtematrix("RO-08")
def test_g3_ohne_mitgliedschaft_erscheint_bei_finn_der_hinweis_und_fiete_ist_weg(org):
    client = client_for(org.falke)
    assert ("Fiete", R.GROUP_LEAD) in leads_seen(org.falke)

    remove(org.falke, R.MEMBER, org.falken)

    for address in PAGES:
        assert has_hint(client, address), address
    assert leads_seen(org.falke) == set()
    assert seen(org.falke) == {"finn.falke"}


@pytest.mark.rechtematrix("RO-08")
def test_g4_admin_mit_mitgliedschaft_sieht_keinen_hinweis_aber_fiete(org):
    give(org.max, R.ADMIN)
    give(org.max, R.MEMBER, org.falken)
    client = client_for(org.max)

    for address in PAGES:
        assert not has_hint(client, address), address
    assert ("Fiete", R.GROUP_LEAD) in leads_seen(org.max)
