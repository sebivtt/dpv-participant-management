"""Tests für „nicht gefunden“ statt „kein Zugriff“ und zufällige Kennungen in Adressen (#64, BER-01).

Regel (Klärung von #64 am 22.10.2026): Eine Adresse mit Kennung eines Eintrags zeigt ohne Recht
dieselbe Antwort wie ein Eintrag, den es nicht gibt (404); eine Adresse ohne Kennung, also ein
ganzer Bereich, zeigt ohne Recht „kein Zugriff“ (403). Das gilt auch für Formulare und für
jemanden, der ein Recht mitten in der Arbeit verliert.

Die Tests nutzen Testadressen in `tests/urls.py`, die so gebaut sind, wie Seiten es müssen:
Einträge nur über die zentrale Rechteprüfung (`request.rights`). Verglichen wird die ganze Antwort:
Statuscode, Inhalt Byte für Byte und alle Kopfzeilen. Ausgenommen ist nur der Wert des
Formularschutzes (CSRF) auf Seiten mit Formular: Django verschlüsselt ihn bei jeder Antwort neu,
auch bei zwei gleichen Aufrufen. Die Fehlerseiten haben kein Formular, dort ist nichts
ausgenommen. Im Vergleich der Formulare fehlen außerdem die Login-Adressen: Sie antworten ohne
Login, nehmen keine Einträge und schicken bei jedem Aufruf neue Zufallswerte für Keycloak.
Alle Namen sind erfunden.
"""

import logging
import re

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test.utils import CaptureQueriesContext
from django.test import Client

from access.keys import KEY_ALPHABET, KEY_LENGTH, KEY_PATTERN, has_key, is_key, new_key
from roles.models import Role
from tests.keycloak_fake import login
from tests.test_rechtepruefung import member, remove
from tests import test_rechtepruefung
from tests.test_rollen import BY, give, person, unit
from tests.test_rundumtest import ALL, PUBLIC, _example_address
from units.models import Unit

# Dieselben Einheiten und Personen wie in tests/test_rechtepruefung.py.
org = test_rechtepruefung.org

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls")]

R = Role.Kind
U = Unit.Kind
# Eine Kennung in der richtigen Form, die zu keinem Eintrag gehört.
MISSING = "a" * KEY_LENGTH
NOT_FOUND_TEXT = "Diese Seite gibt es nicht."
NO_ACCESS_TEXT = "Dafür fehlt dir die Berechtigung."
# Der Formularschutz, der bei jeder Antwort anders aussieht (siehe oben), und seit #100 die Kennung des Formulars
# „Veranstaltung erstellen“ gegen den Doppelklick (VG8): Sie ist bei jedem Öffnen neu und verrät nichts über Einträge.
CSRF_VALUE = re.compile(rb'(name="(?:csrfmiddlewaretoken|creation_key)" value=")[^"]*"')


def client_for(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def answer(response) -> tuple:
    """Alles, was beim Browser ankommt: Statuscode, Inhalt und Kopfzeilen; nur Formularschutz und Kennung des Formulars sind gleichgesetzt."""
    content = CSRF_VALUE.sub(rb'\1..."', response.content)
    return response.status_code, content, sorted(response.headers.items())


def answers(user, address: str, form: dict | None = None) -> list[tuple]:
    """Die Antworten auf jedem Weg: lesend und als Formular."""
    form = form or {"name": "Gekapert", "unit": MISSING}
    found = []
    for method, data in (("get", None), ("post", form)):
        found.append(answer(getattr(client_for(user), method)(address, data or {})))
    return found


# Ein ganzes Stück einer Adresse in der Form einer Kennung.
KEY_IN_ADDRESS = re.compile(rf"(?<=/){KEY_PATTERN}(?=/|$)")


def with_missing_keys(address: str) -> str:
    """Dieselbe Adresse, jede Kennung darin ersetzt durch eine, zu der es keinen Eintrag gibt."""
    return KEY_IN_ADDRESS.sub(MISSING, address)


def assert_like_missing(user, address_for) -> None:
    """Die Adresse eines vorhandenen Eintrags antwortet wie die eines Eintrags, den es nicht gibt."""
    shown, missing = answers(user, address_for), answers(user, with_missing_keys(address_for))
    assert shown == missing
    for status, content, _headers in shown:
        assert status == 404
        assert NOT_FOUND_TEXT in content.decode()


def person_address(entry, suffix: str = "") -> str:
    return f"/test/person/{entry.key}/{suffix}"


def test_vergleichsadresse_ersetzt_genau_die_kennungen():
    """Befund der unabhängigen Prüfung zu #156: früher ersetzte der Baustein das vierte Stück der Adresse, egal was dort stand."""
    first, second = new_key(), new_key()

    assert with_missing_keys(f"/person/{first}/") == f"/person/{MISSING}/"
    assert with_missing_keys(f"/einheit/{first}/person/{second}/") == f"/einheit/{MISSING}/person/{MISSING}/"
    assert with_missing_keys(f"/test/person/{first}/entfernen/") == f"/test/person/{MISSING}/entfernen/"
    assert with_missing_keys("/test/nummer/verstecktes-feld/") == "/test/nummer/verstecktes-feld/"


# Personen (BER-01, Grund 1 und 2): Wer eine Person nicht sieht, erfährt nicht, dass es sie gibt


@pytest.mark.rechtematrix("PK-02")
def test_berechtigte_leitung_erreicht_die_person_ueber_ihre_kennung(org):
    """Gegenprobe: Die Stammesleitung sieht ein Mitglied einer Gruppe ihres Stammes, auf jedem Weg."""
    for status, content, _headers in answers(org.walhall_leitung, person_address(org.falke)):
        assert status == 200
        assert content.decode() == "Finn Falke"


def test_jede_person_erreicht_sich_selbst_ueber_ihre_kennung(org):
    """Gegenprobe zu PK-05 und PK-06 (BER-01, Grund 1)."""
    for user in (org.falke, org.ohne):
        statuses = {status for status, _content, _headers in answers(user, person_address(user))}
        assert statuses == {200}


@pytest.mark.rechtematrix("PK-04")
@pytest.mark.wie_nicht_vorhanden("test/person/<key:key>/")
def test_person_ausserhalb_des_bereichs_ist_nicht_gefunden_wie_eine_nicht_vorhandene(org):
    """Die Stammesleitung von Walhall bei einem Kind der Zugvögel."""
    assert_like_missing(org.walhall_leitung, person_address(org.adler_kind))


@pytest.mark.rechtematrix("PK-04")
def test_gruppenleitung_bei_einer_anderen_gruppe_ihres_stammes_ist_nicht_gefunden(org):
    assert_like_missing(org.falken_leitung, person_address(org.wolf))


@pytest.mark.rechtematrix("PK-04")
def test_leitung_ueber_der_kette_ist_als_person_nicht_gefunden(org):
    """Name und Rolle der Bundesleitung sieht die Stammesleitung (RO-01), die Person selbst nicht."""
    assert_like_missing(org.walhall_leitung, person_address(org.bundesleitung))


@pytest.mark.rechtematrix("PK-05")
def test_mitglied_findet_keine_andere_person_auch_nicht_in_der_eigenen_einheit(org):
    neighbour = member("fine.falke", org.falken)

    assert_like_missing(org.falke, person_address(neighbour))
    assert_like_missing(org.falke, person_address(org.wolf))


@pytest.mark.rechtematrix("PK-06")
def test_konto_ohne_zuordnung_findet_keine_andere_person(org):
    assert_like_missing(org.ohne, person_address(org.falke))


@pytest.mark.rechtematrix("PK-07")
def test_verbandsleitung_findet_keine_person_der_buende(org):
    assert_like_missing(org.verbandsleitung, person_address(org.falke))
    assert_like_missing(org.verbandsleitung, person_address(org.bundesleitung))


@pytest.mark.rechtematrix("PK-07")
def test_dpv_veranstaltungsteam_findet_keine_person_der_buende(org):
    assert_like_missing(org.team, person_address(org.falke))


@pytest.mark.rechtematrix("PK-08")
def test_admin_ohne_support_zugang_findet_keine_person(org):
    give(org.max, R.ADMIN)

    assert_like_missing(org.max, person_address(org.falke))


# Aktionen an sichtbaren Einträgen: Fehlt das Recht für die Aktion, gilt dieselbe Regel


@pytest.mark.rechtematrix("PK-21")
def test_leitung_der_eigenen_einheit_erreicht_das_austragen(org):
    """Gegenprobe zu PK-22: Die Gruppenleitung der Falken bei einem Mitglied der Falken."""
    statuses = {status for status, _content, _headers in answers(org.falken_leitung, person_address(org.falke, "entfernen/"))}

    assert statuses == {200}


@pytest.mark.rechtematrix("PK-22")
@pytest.mark.wie_nicht_vorhanden("test/person/<key:key>/entfernen/")
def test_austragen_eines_sichtbaren_mitglieds_einer_gruppe_darunter_ist_nicht_gefunden(org):
    """Die Stammesleitung sieht Finn (PK-02), darf ihn aber nicht austragen; die Gruppe hat eine Leitung."""
    assert_like_missing(org.walhall_leitung, person_address(org.falke, "entfernen/"))


@pytest.mark.rechtematrix("EH-18")
def test_einspringende_leitung_erreicht_die_einheit_ohne_leitung(org):
    """Gegenprobe zu EH-19: Ohne Gruppenleitung springt die Stammesleitung für die Falken ein."""
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)

    statuses = {status for status, _content, _headers in answers(org.walhall_leitung, f"/test/einheit/{org.falken.key}/")}

    assert statuses == {200}


@pytest.mark.rechtematrix("EH-19")
@pytest.mark.wie_nicht_vorhanden("test/einheit/<key:key>/")
def test_leitung_darueber_ist_bei_einer_einheit_mit_leitung_nicht_gefunden(org):
    assert_like_missing(org.walhall_leitung, f"/test/einheit/{org.falken.key}/")


@pytest.mark.rechtematrix("EH-27")
def test_verbandsleitung_ist_bei_einem_bund_ohne_leitung_nicht_gefunden(org):
    remove(org.bundesleitung, R.ASSOCIATION_LEAD, org.boreas)

    assert_like_missing(org.verbandsleitung, f"/test/einheit/{org.boreas.key}/")


# Gegenprobe Byte für Byte: kaputte und alte Kennungen, „kein Zugriff“ an einer Adresse mit Kennung


def test_kaputte_kennungen_und_alte_nummern_sind_nicht_gefunden_wie_eine_nicht_vorhandene(org):
    """Auch die laufende Nummer eines sichtbaren Eintrags führt nicht mehr zu ihm."""
    missing = answers(org.walhall_leitung, f"/test/person/{MISSING}/")
    for broken in (str(org.falke.pk), org.falke.key.upper(), org.falke.key + "a", org.falke.key[:-1], "1; DROP", "%00"):
        assert answers(org.walhall_leitung, f"/test/person/{broken}/") == missing, broken
    assert answers(org.walhall_leitung, "/gibt-es-nicht/") == missing


@pytest.mark.wie_nicht_vorhanden("test/person/<key:key>/kein-zugriff/")
def test_kein_zugriff_an_einer_adresse_mit_kennung_wird_nicht_gefunden(org):
    """Meldet eine Seite mit Kennung fälschlich „kein Zugriff“, macht die zentrale Stelle „nicht gefunden“ daraus."""
    assert_like_missing(org.walhall_leitung, person_address(org.falke, "kein-zugriff/"))


def tool_log(caplog) -> list[str]:
    """Die Zeilen, die das Tool selbst ins Log schreibt; Djangos eigene verwirft es (config/settings.py)."""
    return [record.getMessage() for record in caplog.records if record.name == "core.errors"]


def test_log_unterscheidet_fremde_und_nicht_vorhandene_eintraege_nicht(org, caplog):
    """Auch das Log zeigt nur das Muster der Adresse, nie, ob es den Eintrag gibt (#6)."""
    with caplog.at_level(logging.WARNING, logger="core.errors"):
        answers(org.walhall_leitung, person_address(org.adler_kind))
    foreign = tool_log(caplog)
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="core.errors"):
        answers(org.walhall_leitung, f"/test/person/{MISSING}/")

    assert foreign == tool_log(caplog)
    assert foreign and all(org.adler_kind.key not in line for line in foreign)


def test_wer_ein_recht_verliert_sieht_beim_naechsten_klick_nicht_gefunden(org):
    """#90: keine eigene Meldung, wenn eine Rolle mitten in der Arbeit endet."""
    address = person_address(org.falke)
    assert {status for status, _content, _headers in answers(org.walhall_leitung, address)} == {200}

    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)

    assert_like_missing(org.walhall_leitung, address)


# Ganze Bereiche ohne Kennung: „kein Zugriff“


def test_ganzer_bereich_ohne_recht_zeigt_kein_zugriff(org):
    for user in (org.falke, org.ohne, org.verbandsleitung, org.team):
        for status, content, _headers in answers(user, "/test/leitungen/"):
            assert status == 403
            assert NO_ACCESS_TEXT in content.decode()


@pytest.mark.rechtematrix("RO-08")
def test_admin_ohne_support_zugang_sieht_beim_bereich_leitungen_kein_zugriff(org):
    """V5 (#156, Lücke L1 aus #64): Max öffnet den Bereich „Leitungen“."""
    give(org.max, R.ADMIN)

    for status, content, _headers in answers(org.max, "/test/leitungen/"):
        assert status == 403
        assert NO_ACCESS_TEXT in content.decode()


def test_ganzer_bereich_mit_recht_ist_erreichbar(org):
    """Gegenprobe."""
    statuses = {status for status, _content, _headers in answers(org.walhall_leitung, "/test/leitungen/")}

    assert statuses == {200}


def test_wer_das_recht_fuer_einen_bereich_verliert_sieht_kein_zugriff(org):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)

    statuses = {status for status, _content, _headers in answers(org.falken_leitung, "/test/leitungen/")}

    assert statuses == {403}


# Verbote ohne Seite (EP-09, RO-19, PR-01, PR-03, TD-01): Formulare mit echten und nicht
# vorhandenen Kennungen ergeben auf jeder Adresse des Tools dieselbe Antwort


def same_answers_for_real_and_missing_keys(org, real: dict) -> None:
    """Ruft jede Adresse des Tools mit Login als viele Personen auf, einmal mit echten, einmal mit erfundenen Kennungen.

    Steht in einer Adresse eine Kennung (`<key:…>`), kommt dort in beiden Fällen dieselbe echte hinein,
    die erste Kennung aus `real`, bei Personen-Adressen also womöglich die einer Einheit; verglichen
    werden dann nur die Formulare mit echten gegen erfundene Kennungen. Seit #189 gibt es Seiten mit
    Kennung, die eine Leitung mit der echten Kennung sehen darf, und seit #190 solche, an die sie
    Formulare schicken darf (Suchen bei Sippe Falken für Wanda). Dass eine Adresse ohne Recht wie
    eine erfundene antwortet, prüfen die Tests „wie nicht vorhanden“ je Adresse.
    """
    missing = dict.fromkeys(real, MISSING)
    give(org.max, R.ADMIN)
    users = (org.falke, org.walhall_leitung, org.verbandsleitung, org.max, org.ohne)
    for pattern, entry in ALL:
        if entry.name in PUBLIC:
            continue
        address = _example_address(pattern)
        with_real = address.replace(MISSING, next(iter(real.values()))) if has_key(pattern) else address
        # Nur das Formular (der letzte Weg von answers()), wenn die Adresse eine Kennung hat.
        forms_only = slice(1, None) if has_key(pattern) else slice(None)
        compared = with_real if has_key(pattern) else address
        for user in users:
            shown, expected = answers(user, with_real, real), answers(user, compared, missing)
            assert shown[forms_only] == expected[forms_only], (pattern, user.username)


@pytest.mark.alle_adressen
@pytest.mark.rechtematrix("EP-09")
def test_konto_loeschen_mit_echter_kennung_antwortet_wie_mit_erfundener(org):
    same_answers_for_real_and_missing_keys(org, {"key": org.falke.key, "user": org.falke.key, "delete": org.falke.key})


@pytest.mark.alle_adressen
@pytest.mark.rechtematrix("RO-19")
def test_rolle_admin_mit_echter_kennung_antwortet_wie_mit_erfundener(org):
    same_answers_for_real_and_missing_keys(org, {"person": org.falke.key, "admin": org.falke.key})


@pytest.mark.alle_adressen
@pytest.mark.rechtematrix("PR-01")
def test_protokoll_der_rollen_mit_echter_kennung_antwortet_wie_mit_erfundener(org):
    same_answers_for_real_and_missing_keys(org, {"person": org.falke.key, "id": org.falke.key})


@pytest.mark.alle_adressen
@pytest.mark.rechtematrix("PR-03")
def test_protokoll_der_einheiten_mit_echter_kennung_antwortet_wie_mit_erfundener(org):
    same_answers_for_real_and_missing_keys(org, {"unit": org.falken.key, "einheit": org.falken.key})


@pytest.mark.alle_adressen
@pytest.mark.rechtematrix("TD-01")
def test_login_daten_mit_echter_kennung_antworten_wie_mit_erfundener(org):
    same_answers_for_real_and_missing_keys(org, {"user": org.falke.key, "pk": org.falke.key})


# Die Kennung selbst


def test_konten_und_einheiten_haben_eine_kennung_in_der_vorgesehenen_form(org):
    keys = [*(user.key for user in (org.falke, org.ohne, org.verbandsleitung)), org.dpv.key, org.falken.key]

    assert all(is_key(key) for key in keys)
    assert all(len(key) == KEY_LENGTH and set(key) <= set(KEY_ALPHABET) for key in keys)
    assert len(set(keys)) == len(keys)


def test_kennung_verraet_weder_anzahl_noch_reihenfolge(org):
    """Nacheinander angelegte Einträge haben Kennungen ohne Reihenfolge; zufällig sortiert wären 30 nur einmal in 10^32 Fällen.

    Mehr als fünf gleiche Anfänge aus drei Zeichen kommen bei 30 zufälligen Kennungen praktisch nie vor
    (im Mittel 0,01 gleiche Paare).
    """
    users = [person(f"kim.folge{number}", "Kim", f"Folge{number}") for number in range(30)]
    groups = [unit(U.GROUP, f"Sippe {number}", org.walhall) for number in range(30)]
    for entries in (users, groups):
        keys = [entry.key for entry in entries]
        assert keys not in (sorted(keys), sorted(keys, reverse=True))
        # Gezählte Kennungen begännen alle gleich; zufällige teilen die ersten drei Zeichen fast nie.
        assert len({key[:3] for key in keys}) >= 25


def test_kennung_nutzt_das_ganze_alphabet():
    """Alle 32 Zeichen kommen vor; eine Kennung mit weniger Zeichen wäre leichter zu erraten."""
    seen = set("".join(new_key() for _ in range(300)))

    assert seen == set(KEY_ALPHABET)


def test_kennung_aendert_sich_beim_speichern_nicht(org):
    before = (org.falke.key, org.falken.key)

    org.falke.last_name = "Neuname"
    org.falke.save()
    org.falken.name = "Sippe Habichte"
    org.falken.save(by=BY)
    org.falke.refresh_from_db()
    org.falken.refresh_from_db()

    assert (org.falke.key, org.falken.key) == before


@pytest.mark.parametrize("value", [None, "", 17, MISSING.upper(), MISSING[:-1], MISSING + "a", "a" * 19 + "1", "a" * 19 + "-"])
def test_falsche_form_ist_keine_kennung(value):
    assert not is_key(value)


def test_erster_login_legt_das_konto_mit_kennung_an(client, keycloak):
    """Gegenprobe: Login, Startseite und Abmelden gehen weiter; das neue Konto hat eine Kennung."""
    login(client)

    created = get_user_model().objects.get(username="erika.testfrau")
    assert is_key(created.key)
    assert client.get("/").status_code == 200
    assert client.post("/abmelden/").status_code == 200  # seit #280 die kurze Seite mit Formular an Keycloak


@pytest.mark.django_db(transaction=True)
def test_vorhandene_eintraege_bekommen_bei_der_migration_je_eine_kennung():
    """Konten und Einheiten, die es vor #64 gab (Testumgebung), bekommen je eine eigene Kennung."""
    before = [("accounts", "0001_initial"), ("units", "0002_unit_change")]
    executor = MigrationExecutor(connection)
    executor.migrate(before)
    old = executor.loader.project_state(before).apps
    for number in range(3):
        old.get_model("accounts", "User").objects.create(username=f"alt.konto{number}")
    old_unit = old.get_model("units", "Unit")
    federation = old_unit.objects.create(kind=U.FEDERATION, name="DPV")
    old_unit.objects.create(kind=U.ASSOCIATION, name="Bund Alt", parent=federation)

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    keys = [*get_user_model().objects.values_list("key", flat=True), *Unit.objects.values_list("key", flat=True)]
    assert len(keys) == 5
    assert all(is_key(key) for key in keys)
    assert len(set(keys)) == 5



# Nummern in Parametern und Formularfeldern (#156, Lücke L2 aus #64)


def answers_with_parameter(user, value: str) -> list[tuple]:
    """Die Antworten der Testseite, die die Einheit aus `?einheit=` oder dem Formularfeld `einheit` nimmt."""
    found = []
    for method, address, data in (
        ("get", f"/test/einheit/?einheit={value}", None),
        ("post", "/test/einheit/", {"einheit": value}),
    ):
        found.append(answer(getattr(client_for(user), method)(address, data or {})))
    return found


def test_einheit_aus_parameter_oder_formularfeld_mit_nummer_ist_nicht_gefunden_wie_eine_erfundene_kennung(org):
    """V7: Auch die Gruppenleitung der Falken erreicht ihre Einheit nicht über deren Nummer."""
    for user in (org.falken_leitung, org.walhall_leitung):
        by_number = answers_with_parameter(user, str(org.falken.pk))
        assert by_number == answers_with_parameter(user, MISSING)
        for status, content, _headers in by_number:
            assert status == 404
            assert NOT_FOUND_TEXT in content.decode()


def test_einheit_aus_parameter_oder_formularfeld_mit_kennung_ist_erreichbar(org):
    """Gegenprobe zu V7: Mit der Kennung der Falken antwortet die Testseite der Gruppenleitung."""
    for status, content, _headers in answers_with_parameter(org.falken_leitung, org.falken.key):
        assert status == 200
        assert content.decode() == "geleitet: Sippe Falken"


# Gleich viele Datenbankabfragen (#156, Lücke L4 aus #64)


def query_counts(user, address: str) -> list[int]:
    """Die Zahl der Datenbankabfragen je Weg: lesend und als Formular."""
    counts = []
    for method, data in (("get", None), ("post", {"name": "Gekapert"})):
        client = client_for(user)
        with CaptureQueriesContext(connection) as queries:
            getattr(client, method)(address, data or {})
        counts.append(len(queries))
    return counts


@pytest.mark.rechtematrix("PK-04")
def test_fremder_und_nicht_vorhandener_eintrag_loesen_gleich_viele_abfragen_aus(org):
    """V9: Wanda bei Anton, den sie nicht sehen darf, und bei einer erfundenen Kennung; gezählt wird, nicht gemessen."""
    for suffix in ("", "entfernen/"):
        foreign = query_counts(org.walhall_leitung, person_address(org.adler_kind, suffix))
        missing = query_counts(org.walhall_leitung, f"/test/person/{MISSING}/{suffix}")
        assert foreign == missing, suffix
        assert all(foreign)


@pytest.mark.rechtematrix("PK-22")
def test_sichtbarer_eintrag_ohne_recht_zur_aktion_darf_eine_abfrage_mehr_ausloesen(org):
    """G1: Wanda sieht Finn, darf ihn aber nicht austragen (Protokoll, Frage 2).

    Hier darf eine Abfrage mehr anfallen, die Antwort ist trotzdem genau gleich „nicht gefunden“.
    """
    shown = query_counts(org.walhall_leitung, person_address(org.falke, "entfernen/"))
    missing = query_counts(org.walhall_leitung, f"/test/person/{MISSING}/entfernen/")

    assert all(more >= fewer for more, fewer in zip(shown, missing, strict=True))
    assert_like_missing(org.walhall_leitung, person_address(org.falke, "entfernen/"))


@pytest.mark.wie_nicht_vorhanden("test/nummer/<key:key>/")
def test_testseite_mit_nummer_einer_fremden_person_ist_nicht_gefunden(org):
    """Die Testseite für die Suche nach Nummern hält sich selbst an „nicht gefunden“ (Prüfung aus V8)."""
    assert_like_missing(org.walhall_leitung, f"/test/nummer/{org.adler_kind.key}/")
