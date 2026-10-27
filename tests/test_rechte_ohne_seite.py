"""Tests für die Verbote, für die es im Tool keine Seite gibt (#90; EP-09, RO-19, PR-01, PR-03, TD-01).

Diese Zeilen der Rechtematrix gelten, weil keine Adresse das Verbotene tut. Die Tests rufen
deshalb jede Adresse des Tools auf, wie der Rundumtest: mit und ohne htmx, lesend und mit einem
manipulierten Formular, angemeldet als Mitglied, Leitung, Verbandsleitung, Admin, Konto ohne
Zuordnung und als Person mit vielen Rollen zugleich (#136, A17: je Fall). Danach muss die
Datenbank unverändert sein, und keine Antwort darf zeigen, was niemand im Tool sieht. Kommt eine
Adresse dazu, prüfen die Tests sie mit. Als erlaubten Fall prüfen sie die Gegenprobe: Der
vorgesehene Weg (erster Login, Befehl auf dem Server, Schreiben ins Protokoll) geht weiter.

Das Muster „nach dem verbotenen Versuch steht in der Datenbank noch dasselbe“ stammt aus
`backend/tests/test_zugriffsschutz.py` im alten Repo (sebivtt/scout-participant-management, Stand
9df4513); übernommen ist die Prüfung, nicht der Code, der dort an Veranstaltungen hing.
"""

import io
import re

import pytest
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.db import connection
from django.test import Client

from roles.models import Role, RoleChange
from tests.keycloak_fake import login
from tests.test_rollen import BY, build_org, give
from tests import urls as test_urls
from access.keys import has_key
from tests.test_rundumtest import ALL, EXAMPLE_KEY, _all_patterns, _example_address
from units.models import Unit, UnitChange

pytestmark = pytest.mark.django_db

R = Role.Kind
User = get_user_model()

# Was zuerst vergeben war und nur noch im Protokoll steht (alter Name von Person und Einheit).
OLD_PERSON_NAME = "Ronja Altname"
OLD_UNIT_NAME = "Sippe Altname"
KEYCLOAK_DETAIL = "nur-im-login-baustein-7f3q9"


# Auffällige Nummern für Konten und Einheiten, damit die Suche nach Nummern sie sicher erkennt (#156).
# Kennungen enthalten nur die Ziffern 2 bis 7, nie 0 oder 1; eine Nummer mit 0 und 1 kann also nie
# Teil einer Kennung sein.
FIRST_USER_NUMBER = 7000001
FIRST_UNIT_NUMBER = 7100001


def number_from(model, first: int) -> None:
    """Die nächsten Einträge von `model` bekommen Nummern ab `first`.

    PostgreSQL nimmt den Zähler beim Zurückrollen des Tests nicht zurück; spätere Tests zählen
    deshalb von dort weiter, was keinem Test schadet.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT setval(pg_get_serial_sequence(%s, 'id'), %s, false)", [model._meta.db_table, first])


@pytest.fixture
def org():
    """Einheiten und Rollen; Erika hat viele Rollen zugleich, auch Admin, die übrigen je eine."""
    number_from(User, FIRST_USER_NUMBER)
    number_from(Unit, FIRST_UNIT_NUMBER)
    o = build_org()
    give(o.erika, R.ASSOCIATION_LEAD, o.boreas)
    give(o.erika, R.TROOP_LEAD, o.walhall)
    give(o.erika, R.FEDERATION_LEAD, o.dpv)
    give(o.erika, R.ADMIN)
    give(o.max, R.MEMBER, o.falken)
    o.lead = User.objects.create(username="zora.zugvogel", first_name="Zora", last_name="Zugvogel")
    give(o.lead, R.TROOP_LEAD, o.zugvoegel)
    o.federation_lead = User.objects.create(username="vera.verband", first_name="Vera", last_name="Verband")
    give(o.federation_lead, R.FEDERATION_LEAD, o.dpv)
    o.admin = User.objects.create(username="ada.admin", first_name="Ada", last_name="Admin")
    give(o.admin, R.ADMIN)
    o.without = User.objects.create(username="otto.ohne", first_name="Otto", last_name="Ohne")
    o.everyone = [o.max, o.lead, o.federation_lead, o.admin, o.without, o.erika]
    # Einträge in beiden Protokollen, deren Namen danach nur noch dort stehen.
    o.ronja = User.objects.create(username="ronja.test", first_name="Ronja", last_name="Altname")
    give(o.ronja, R.MEMBER, o.woelfe)
    o.ronja.last_name = "Neuname"
    o.ronja.save()
    o.falken.name = OLD_UNIT_NAME
    o.falken.save(by=BY)
    o.falken.name = "Sippe Falken"
    o.falken.save(by=BY)
    SocialAccount.objects.create(user=o.max, provider="keycloak", uid="nur-test-1", extra_data={"x": KEYCLOAK_DETAIL})
    return o


def manipulated_form(org) -> dict:
    """Felder, mit denen jemand ein Konto, eine Rolle oder ein Login-Datum anzulegen versucht."""
    return {
        "username": "gekapert",
        "email": "gekapert@example.org",
        "first_name": "Gekapert",
        "user": org.max.pk,
        "user_id": org.max.pk,
        "person": org.max.pk,
        "kind": R.ADMIN,
        "role": R.ADMIN,
        "unit": org.falken.pk,
        "is_superuser": "on",
        "is_staff": "on",
        "uid": "gekapert",
        "provider": "keycloak",
        "delete": "1",
        "id": org.max.pk,
        "pk": org.max.pk,
        # Seit #64 stehen Einträge mit ihrer zufälligen Kennung in Adressen und Formularen.
        "key": org.max.key,
        "person_key": org.max.key,
        "unit_key": org.falken.key,
    }


def every_attempt(org, patterns=ALL, keys=()):
    """Ruft jede Adresse auf viele Arten auf, jedes Mal frisch angemeldet, als jede Person aus `org.everyone`.

    Gibt jede Adresse mit ihrem Namen und alle Antworten zurück. `patterns` ist nur für die
    Gegenproben mit Testadressen anders. Mit `keys` kommt in Adressen mit Kennung außer der
    erfundenen Kennung auch jede dieser echten Kennungen, damit die Seiten auch mit einem
    gefundenen Eintrag antworten.
    """
    form = manipulated_form(org)
    for pattern, entry in patterns:
        example = _example_address(pattern)
        addresses = [example, *(example.replace(EXAMPLE_KEY, key) for key in keys)] if has_key(pattern) else [example]
        for address in addresses:
            yield entry.name, address, _attempts(address, form, org)


def _attempts(address: str, form: dict, org) -> list:
    """Alle Antworten auf eine Adresse: lesend, per htmx, mit Formular, für jede Person aus `org.everyone`."""
    responses = []
    for user in org.everyone:
        for method, data, htmx in (
            ("get", None, False),
            ("get", None, True),
            ("get", form, False),
            ("post", form, False),
            ("post", form, True),
        ):
            client = Client()
            client.force_login(user)
            headers = {"HX-Request": "true"} if htmx else {}
            call = getattr(client, method)
            responses.append(call(address, data or {}, headers=headers))
    return responses


def snapshot(model, *fields) -> list:
    return sorted(model.objects.values_list(*fields), key=repr)


def page_texts(org) -> list[tuple[str, str]]:
    return [
        (address, response.content.decode(errors="replace"))
        for _name, address, responses in every_attempt(org)
        for response in responses
    ]


# EP-09: Konten im Tool anlegen oder löschen


@pytest.mark.rechtematrix("EP-09")
def test_keine_adresse_legt_ein_konto_an_oder_loescht_eines(org):
    before = snapshot(User, "pk", "username", "email", "is_superuser", "is_staff")

    list(every_attempt(org))

    assert snapshot(User, "pk", "username", "email", "is_superuser", "is_staff") == before


@pytest.mark.rechtematrix("EP-09", "TD-01")
def test_konto_entsteht_beim_ersten_login(client, keycloak):
    """Gegenprobe zu EP-09 und TD-01: Der Login legt Konto und Verknüpfung mit Keycloak an."""
    assert not User.objects.filter(username="erika.testfrau").exists()

    login(client)

    user = User.objects.get(username="erika.testfrau")
    assert SocialAccount.objects.filter(user=user).exists()
    assert Session.objects.exists()


# RO-19: Rolle Admin im Tool vergeben oder entfernen


@pytest.mark.rechtematrix("RO-19")
def test_keine_adresse_vergibt_oder_entfernt_die_rolle_admin(org):
    before = snapshot(Role, "user_id", "kind", "unit_id")

    list(every_attempt(org))

    assert snapshot(Role, "user_id", "kind", "unit_id") == before
    admins = sorted(Role.objects.filter(kind=R.ADMIN).values_list("user__username", flat=True))
    assert admins == ["ada.admin", "erika.testfrau"]


@pytest.mark.rechtematrix("RO-19")
def test_admin_wird_per_befehl_auf_dem_server_ernannt(org):
    """Gegenprobe zu RO-19: der vorgesehene Weg bis ADM-01."""
    call_command("admin", "grant", "max.testmann", stdout=io.StringIO())

    assert Role.objects.filter(user=org.max, kind=R.ADMIN).exists()


# PR-01 und PR-03: die Protokolle im Tool ansehen


@pytest.mark.rechtematrix("PR-01")
def test_keine_adresse_zeigt_das_protokoll_der_rollenaenderungen(org):
    assert RoleChange.objects.filter(person_name=OLD_PERSON_NAME).exists()

    shown = [address for address, text in page_texts(org) if OLD_PERSON_NAME in text]

    assert shown == []


@pytest.mark.rechtematrix("PR-01")
def test_rollenaenderungen_werden_weiter_ins_protokoll_geschrieben(org):
    """Gegenprobe zu PR-01: In P2 wird das Protokoll nur geschrieben (W4)."""
    before = RoleChange.objects.count()

    give(org.max, R.GROUP_LEAD, org.falken)

    assert RoleChange.objects.count() == before + 1


@pytest.mark.rechtematrix("PR-03")
def test_keine_adresse_zeigt_das_protokoll_der_strukturaenderungen(org):
    assert UnitChange.objects.filter(new_value=OLD_UNIT_NAME).exists()

    shown = [address for address, text in page_texts(org) if OLD_UNIT_NAME in text]

    assert shown == []


@pytest.mark.rechtematrix("PR-03")
def test_strukturaenderungen_werden_weiter_ins_protokoll_geschrieben(org):
    """Gegenprobe zu PR-03."""
    before = UnitChange.objects.count()

    org.woelfe.name = "Meute Füchse"
    org.woelfe.save(by=BY)

    assert UnitChange.objects.count() == before + 1


# TD-01: technische Daten des Logins


LOGIN_TABLES = [
    (SocialAccount, ("pk", "user_id", "provider", "uid", "extra_data")),
    (SocialApp, ("pk", "provider", "client_id")),
    (SocialToken, ("pk", "account_id")),
    (EmailAddress, ("pk", "user_id", "email", "verified", "primary")),
    (EmailConfirmation, ("pk", "email_address_id")),
    (Group, ("pk", "name")),
    (Permission, ("pk", "codename")),
    (ContentType, ("pk", "app_label", "model")),
]


@pytest.mark.rechtematrix("TD-01")
def test_keine_adresse_aendert_die_technischen_daten_des_logins(org):
    before = {model: snapshot(model, *fields) for model, fields in LOGIN_TABLES}

    list(every_attempt(org))

    assert {model: snapshot(model, *fields) for model, fields in LOGIN_TABLES} == before


@pytest.mark.rechtematrix("TD-01")
def test_keine_adresse_zeigt_die_technischen_daten_des_logins(org):
    shown = [address for address, text in page_texts(org) if KEYCLOAK_DETAIL in text or "nur-test-1" in text]

    assert shown == []


@pytest.mark.rechtematrix("TD-01")
def test_keine_adresse_zeigt_oder_aendert_eine_fremde_sitzung(org):
    """Sitzungen anderer bleiben unberührt, auch beim Abmelden über ein manipuliertes Formular."""
    other = Client()
    other.force_login(org.max)
    key = other.session.session_key
    stored = Session.objects.get(session_key=key).session_data

    for _name, address, responses in every_attempt(org):
        for response in responses:
            assert key not in response.content.decode(errors="replace"), address
        assert Session.objects.get(session_key=key).session_data == stored, address


# Keine Seite zeigt eine interne Nummer (#156, Lücke L2 aus #64)

DIGITS = re.compile(r"\d+")


def internal_numbers() -> set[str]:
    """Die Nummern aller Konten und Einheiten."""
    return {str(number) for model in (User, Unit) for number in model.objects.values_list("pk", flat=True)}


def numbers_shown(response, numbers: set[str]) -> set[str]:
    """Interne Nummern in der Antwort: in Links, angehängten Parametern, Formularfeldern (auch `hx-vals`), im Text, in den Kopfzeilen (z. B. einer Weiterleitung) und in Cookies.

    Gesucht wird jede ganze Zahl der Antwort; eine Jahreszahl oder eine längere Zahl, die eine
    Nummer nur enthält, ist kein Treffer. Verschlüsselte oder umkodierte Nummern (z. B. Base64)
    findet die Suche nicht; die bleiben Sache der unabhängigen Prüfung.
    """
    headers = " ".join(f"{name}: {value}" for name, value in response.headers.items())
    cookies = " ".join(cookie.OutputString() for cookie in response.cookies.values())
    text = " ".join((response.content.decode(errors="replace"), headers, cookies))
    return set(DIGITS.findall(text)) & numbers


def pages_with_numbers(org, patterns=ALL) -> list[tuple[str, str]]:
    """Adressen mit den Nummern, die sie zeigen; Adressen mit Kennung auch mit jeder echten Kennung aufgerufen."""
    numbers = internal_numbers()
    keys = [key for model in (User, Unit) for key in model.objects.values_list("key", flat=True)]
    return sorted(
        {
            (address, number)
            for _name, address, responses in every_attempt(org, patterns, keys)
            for response in responses
            for number in numbers_shown(response, numbers)
        }
    )


def test_konten_und_einheiten_haben_auffaellige_nummern(org):
    """Sonst fände die Suche Nummern wie 1 oder 12 überall und bewiese nichts."""
    numbers = [int(number) for number in internal_numbers()]

    assert numbers
    assert min(numbers) >= FIRST_USER_NUMBER


def test_keine_antwort_enthaelt_eine_interne_nummer(org):
    """V6 und S7: keine Nummer einer Person oder Einheit, weder in Links noch in Formularfeldern noch im Text."""
    assert pages_with_numbers(org) == []


@pytest.mark.urls("tests.urls")
@pytest.mark.parametrize("name", ["number_in_link", "number_in_hidden_field", "number_in_hx_vals", "number_in_redirect", "number_in_cookie"])
def test_seite_mit_interner_nummer_macht_die_suche_rot(org, name):
    """Gegenprobe zu V6: Link mit `?einheit=`, verstecktes Feld, `hx-vals`, Weiterleitung und Cookie mit der Nummer der Falken."""
    patterns = [(pattern, entry) for pattern, entry in _all_patterns(test_urls.urlpatterns) if entry.name == name]

    assert {number for _address, number in pages_with_numbers(org, patterns)} == {str(org.falken.pk)}


@pytest.mark.urls("tests.urls")
def test_kennungen_und_andere_zahlen_machen_die_suche_nicht_rot(org):
    """G2 und S7: Kennung im Link und im Formularfeld, Jahreszahl und kleine Zahlen sind keine Nummern."""
    patterns = [(pattern, entry) for pattern, entry in _all_patterns(test_urls.urlpatterns) if entry.name == "without_number"]

    assert len(patterns) == 1
    assert pages_with_numbers(org, patterns) == []


@pytest.mark.urls("tests.urls")
def test_seite_mit_kennung_die_eine_nummer_zeigt_macht_die_suche_rot(org):
    """Gegenprobe zu V6 für Seiten mit Kennung: Gesucht wird auch mit echten Kennungen, nicht nur mit „nicht gefunden“."""
    patterns = [(pattern, entry) for pattern, entry in _all_patterns(test_urls.urlpatterns) if entry.name == "number_of_person"]

    found = {number for _address, number in pages_with_numbers(org, patterns)}

    assert {str(user.pk) for user in org.everyone} <= found
