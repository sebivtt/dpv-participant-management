"""Befehl für den eigenen Rechner und die Testumgebung: erfundene Testdaten anlegen (#103, DSG-08).

Jeder Lauf leert die Datenbank bis auf die Konten, auch alle Protokolle, und legt dieselben erfundenen
Daten neu an: Verband, Bünde, Ring, Stämme, Gruppen, Rollen und verwaltete Personen. Was genau, steht
im Text von #103 und in der Besetzung des Kommentars „Szenarien (12.11.2026)“ dort. Er läuft nur,
wenn die Einstellungen ausdrücklich „lokal“ (`LOCAL_ENVIRONMENT`) oder „Testumgebung“
(`TEST_ENVIRONMENT`) sagen; sonst bricht er ab, bevor er etwas löscht.

- **Lokal** legt er jedes Konto der Besetzung im Tool an, mit der festen Keycloak-Kennung aus
  `dev/keycloak/dpv-realm.json` (#199). Der erste Login landet so im Konto aus dem Befehl.
- **In der Testumgebung** legt er keine Konten an. Rollen bekommen nur die vier Konten aus #62, und
  nur, wenn sie sich schon einmal angemeldet haben; gefunden über den Benutzernamen wie beim Befehl
  `admin` (#89). Wer fehlt, steht am Ende in der Ausgabe.

Alles läuft über die normalen Wege des Tools, damit die Regeln greifen und das Protokoll wie im echten
Ablauf entsteht: Einheiten und Rollen einzeln mit `save(by=SERVER_COMMAND)`, verwaltete Personen über
die zentrale Rechteprüfung, angelegt und bestätigt von der Leitung, die das auch im Tool dürfte. Wer vor
dem Lauf Admin ist, wird es danach wieder, mit neuem Eintrag im Protokoll. Alles geschieht in einer
Transaktion: Scheitert etwas, bleibt die Datenbank, wie sie war.

Beispiel:
    python manage.py testdata
"""

import json
from datetime import date

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction

from access.keys import new_key
from access.rights import Rights
from core import texts
from core.actors import SERVER_COMMAND
from persons.models import ManagedPerson
from roles.models import LEADS_IN_UNITS, Role, RoleKind
from units.models import Kind, Unit

REALM_FILE = settings.BASE_DIR / "dev" / "keycloak" / "dpv-realm.json"
# Unter diesem Namen speichert allauth die Verknüpfung mit Keycloak (config/settings.py).
PROVIDER = settings.SOCIALACCOUNT_PROVIDERS["openid_connect"]["APPS"][0]["provider_id"]

# Die Einheiten in der Reihenfolge des Anlegens: Art, Name, Einheit darüber, „hat Ringe“.
UNITS = (
    (Kind.FEDERATION, "DPV", None, False),
    (Kind.ASSOCIATION, "Pfadfinderbund Boreas", "DPV", False),
    (Kind.TROOP, "Walhall", "Pfadfinderbund Boreas", False),
    (Kind.GROUP, "Sippe Falken", "Walhall", False),
    (Kind.GROUP, "Meute Wölfe", "Walhall", False),
    (Kind.TROOP, "Zugvögel", "Pfadfinderbund Boreas", False),
    (Kind.GROUP, "Sippe Kraniche", "Zugvögel", False),
    (Kind.ASSOCIATION, "Bund Nordstern", "DPV", True),
    (Kind.RING, "Küste", "Bund Nordstern", False),
    (Kind.TROOP, "Leuchtturm", "Küste", False),
    (Kind.GROUP, "Sippe Möwen", "Leuchtturm", False),
)

# Die Besetzung: Benutzername, Rolle, Organisation. Wer eine Leitung bekommt, wird dort zugleich Mitglied
# (#89). Namen und Mails stehen nicht hier, sondern bei den Konten in Keycloak (`REALM_FILE`).
CAST = (
    ("verbandsleitung", RoleKind.FEDERATION_LEAD, "DPV"),
    ("veranstaltungsteam", RoleKind.EVENT_TEAM, "DPV"),
    ("ohne.nachname", RoleKind.ASSOCIATION_LEAD, "Pfadfinderbund Boreas"),
    ("erika.testfrau", RoleKind.TROOP_LEAD, "Walhall"),
    ("mitglied.walhall", RoleKind.MEMBER, "Walhall"),
    ("gruppenleitung.falken", RoleKind.GROUP_LEAD, "Sippe Falken"),
    ("mitglied.falken", RoleKind.MEMBER, "Sippe Falken"),
    ("gruppenleitung.woelfe", RoleKind.GROUP_LEAD, "Meute Wölfe"),
    ("max.testmann", RoleKind.TROOP_LEAD, "Zugvögel"),
    ("gruppenleitung.kraniche", RoleKind.GROUP_LEAD, "Sippe Kraniche"),
    ("bundesleitung.nordstern", RoleKind.ASSOCIATION_LEAD, "Bund Nordstern"),
    ("ringleitung.kueste", RoleKind.RING_LEAD, "Küste"),
    ("stammesleitung.leuchtturm", RoleKind.TROOP_LEAD, "Leuchtturm"),
    ("gruppenleitung.moewen", RoleKind.GROUP_LEAD, "Sippe Möwen"),
    ("ohne.name", None, None),  # Konto ohne Einheit und Rolle (#9)
    ("admin", RoleKind.ADMIN, None),
)
# Die vier Konten aus #62, die es auch im Test-Realm des DPV gibt; nur sie bekommen in der Testumgebung eine Rolle.
SERVER_ACCOUNTS = ("erika.testfrau", "max.testmann", "ohne.nachname", "ohne.name")

# Die verwalteten Personen je Organisation: Vorname, Nachname, Geburtsdatum, Fahrtenname. Erkennbar erfunden
# an den Nachnamen; eine feste Liste statt eines Pakets, damit jeder Lauf dieselben Daten ergibt (#103).
MANAGED = {
    "Walhall": (("Paul", "Probe", "2012-09-03", ""),),
    "Sippe Falken": (
        ("Lena", "Probe", "2015-05-14", "Kiwi"),
        ("Jonas", "Muster", "2014-02-11", ""),
        ("Mila", "Muster", "2015-08-23", "Igel"),
        ("Emil", "Probe", "2014-11-30", ""),
        ("Ida", "Muster", "2015-03-07", ""),
    ),
    "Meute Wölfe": (
        ("Theo", "Probe", "2017-01-19", ""),
        ("Lotte", "Muster", "2016-06-02", "Maus"),
        ("Anton", "Muster", "2017-10-12", ""),
        ("Frieda", "Probe", "2016-04-25", ""),
    ),
    "Sippe Kraniche": (
        ("Ole", "Probe", "2014-07-15", "Luchs"),
        ("Greta", "Muster", "2013-12-01", ""),
        ("Henri", "Muster", "2014-05-09", ""),
        ("Clara", "Probe", "2013-09-28", ""),
    ),
    "Sippe Möwen": (
        ("Lotta", "Probe", "2015-07-07", ""),
        ("Karl", "Muster", "2014-01-16", "Fuchs"),
        ("Nele", "Muster", "2015-10-04", ""),
        ("Moritz", "Probe", "2014-03-21", ""),
    ),
}

# Was zu den Konten gehört und deshalb stehen bleibt: das Konto, seine Verknüpfung mit Keycloak, seine
# Mail-Liste und seine Anmeldung, dazu Djangos eigene Verzeichnisse. Alles andere leert jeder Lauf, auch
# Tabellen, die spätere Issues dazubringen (#101, #102).
KEPT = (EmailAddress, SocialAccount, SocialToken, SocialApp, Session, ContentType, Permission, Group)


class Command(BaseCommand):
    """Leert die Datenbank bis auf die Konten und legt die erfundenen Testdaten neu an."""

    help = "Erfundene Testdaten anlegen; leert dafür die Datenbank bis auf die Konten. Nur lokal und in der Testumgebung."

    def handle(self, *args, **options):
        local = _allowed_environment()
        realm = _realm() if local else {}
        notes = []
        with transaction.atomic():
            admins = list(get_user_model().objects.filter(roles__kind=RoleKind.ADMIN).order_by("username"))
            _clear()
            units = _units()
            accounts, missing = _local_accounts(realm) if local else _server_accounts()
            for username, kind, unit in CAST:
                if kind is not None and username in accounts:
                    Role(user=accounts[username], kind=kind, unit=units.get(unit)).save(by=SERVER_COMMAND)
            for user in admins:
                # Wer laut Besetzung ohnehin Admin ist, hat die Rolle schon wieder.
                if not Role.objects.filter(user=user, kind=RoleKind.ADMIN).exists():
                    Role(user=user, kind=RoleKind.ADMIN).save(by=SERVER_COMMAND)
            without_creator = _managed(units, accounts)
        if admins:
            notes.append(texts.ADMINS_KEPT % {"usernames": ", ".join(user.username for user in admins)})
        if missing:
            message = texts.USERNAME_TAKEN if local else texts.LOG_IN_FIRST
            notes.append(message % {"usernames": ", ".join(missing)})
        if without_creator:
            notes.append(texts.NO_CREATOR % {"units": ", ".join(without_creator)})
        counts = {"units": len(units), "roles": Role.objects.count(), "managed": ManagedPerson.objects.count()}
        self.stdout.write(texts.DONE % counts)
        for note in notes:
            self.stdout.write(note)


def _allowed_environment() -> bool:
    """Ob der Befehl lokal läuft (True) oder in der Testumgebung (False); sonst Abbruch, bevor etwas gelöscht ist."""
    if settings.TEST_ENVIRONMENT:
        return False
    if settings.LOCAL_ENVIRONMENT:
        return True
    raise CommandError(texts.NOT_ALLOWED)


def _realm() -> dict[str, dict]:
    """Die erfundenen Konten aus der Datei des lokalen Keycloak, nach Benutzername."""
    try:
        users = json.loads(REALM_FILE.read_text(encoding="utf-8"))["users"]
    except FileNotFoundError as error:
        raise CommandError(texts.REALM_MISSING % {"path": REALM_FILE}) from error
    return {user["username"]: user for user in users}


def _clear() -> None:
    """Leert alle Tabellen außer denen der Konten, auch die Protokolle, und zählt die Nummern neu ab 1.

    Das Leeren in einem Schritt (TRUNCATE) lassen die Sperren der Protokolle zu; Ändern und Löschen
    einzelner Einträge lehnen sie weiter ab, im Programm und in der Datenbank (#91, #92, #131).
    """
    kept = {get_user_model(), *KEPT}
    tables = [model._meta.db_table for model in apps.get_models() if model not in kept and model._meta.managed]
    # Die Datenbank prüft Verweise erst am Ende der Transaktion; leeren lässt sie eine Tabelle nur ohne noch
    # offene Prüfung. Offen ist eine, wenn in derselben Transaktion schon geschrieben wurde, etwa in Tests.
    connection.check_constraints()
    with connection.cursor() as cursor:
        for statement in connection.ops.sql_flush(no_style(), tables, reset_sequences=True):
            cursor.execute(statement)


def _units() -> dict[str, Unit]:
    """Legt die Einheiten einzeln an, damit jede Regel und das Protokoll der Strukturänderungen greifen."""
    created = {}
    for kind, name, parent, has_rings in UNITS:
        unit = Unit(kind=kind, name=name, parent=created.get(parent), has_rings=has_rings)
        unit.save(by=SERVER_COMMAND)
        created[name] = unit
    return created


def _local_accounts(realm: dict[str, dict]) -> tuple[dict, list[str]]:
    """Die Konten der Besetzung lokal: verknüpft über die feste Keycloak-Kennung, fehlende neu angelegt.

    Gehört der Benutzername schon einem Konto mit anderer Kennung, bleibt es unberührt und ohne Rolle;
    verknüpft wird nie über den Benutzernamen (#5). Solche Benutzernamen kommen als zweiter Wert zurück.
    """
    users = get_user_model().objects
    found, taken = {}, []
    for username, _kind, _unit in CAST:
        entry = realm[username]
        linked = SocialAccount.objects.filter(provider=PROVIDER, uid=entry["id"]).select_related("user").first()
        if linked is not None:
            found[username] = linked.user
            continue
        if users.filter(username__iexact=username).exists():
            taken.append(username)
            continue
        user = users.create_user(
            username=username,
            email=entry.get("email") or "",
            first_name=entry.get("firstName") or "",
            last_name=entry.get("lastName") or "",
        )
        SocialAccount(user=user, provider=PROVIDER, uid=entry["id"]).save()
        found[username] = user
    return found, taken


def _server_accounts() -> tuple[dict, list[str]]:
    """Die vier Konten aus #62 in der Testumgebung, nur wenn sie sich schon angemeldet haben.

    Als zweiter Wert kommen die zurück, die sich zuerst anmelden müssen, um ihre Rolle zu bekommen; das
    Konto ohne Rolle (`ohne.name`) gehört nie dazu.
    """
    users = get_user_model().objects
    found = {username: users.filter(username=username).first() for username in SERVER_ACCOUNTS}
    with_role = {username for username, kind, _unit in CAST if kind is not None}
    missing = [name for name, user in found.items() if user is None and name in with_role]
    return {name: user for name, user in found.items() if user}, missing


def _managed(units: dict[str, Unit], accounts: dict) -> list[str]:
    """Legt die verwalteten Personen an wie im Tool: durch die Leitung, die es dort darf, mit ihrer Einwilligung (#98).

    Das ist die Leitung der Organisation selbst oder, ohne Leitung mit Konto dort, die einspringende darüber
    (VP-01, EH-18). Gibt es keine, etwa in der Testumgebung, bleibt die Organisation ohne verwaltete
    Personen; ihre Namen kommen zurück.
    """
    leads = [accounts[username] for username, kind, _unit in CAST if kind in LEADS_IN_UNITS and username in accounts]
    without_creator = []
    for name, persons in MANAGED.items():
        unit = units[name]
        creator = next((Rights(lead) for lead in leads if Rights(lead).may_add_managed(unit)), None)
        if creator is None:
            without_creator.append(name)
            continue
        for first_name, last_name, born, scout_name in persons:
            values = {"first_name": first_name, "last_name": last_name, "birth_date": date.fromisoformat(born),
                      "scout_name": scout_name, "consent": True}
            creator.add_managed(unit, values, new_key())
    return without_creator
