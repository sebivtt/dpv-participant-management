"""Massendaten für den Leistungstest am Ende jeder Phase (#104, NFA-05): Zusatz `--mass-data` am Befehl `testdata`.

Legt im Bund Boreas zusätzlich `TROOPS` erfundene Probestämme mit je `GROUPS_PER_TROOP` Gruppen an und
verteilt darauf `PERSONS` erfundene Personen, gemischt mit und ohne Konto. Der Probestamm 01 hat `OUTLIER`
direkte Personen, als Ausreißer weit über jedem echten Stamm; die übrigen verteilen sich gleichmäßig. Jede
Probe-Organisation bekommt eine Leitung aus ihren eigenen Mitgliedern, damit Gliederung und Seiten wie im
Betrieb aussehen. Was genau, steht im Text von #104 und in den Szenarien dort.

Anders als der Rest des Befehls schreibt der Zusatz in einem Rutsch, an `save()` und der zentralen
Rechteprüfung vorbei (`bulk_create`), also ohne die Prüfungen beim Speichern und ohne Einträge in den
Protokollen (docs/entscheidungen.md, 13.11.2026, #104); einzeln gespeichert bräuchte jeder Lauf ein Vielfaches
der Zeit. Die Daten sind so gebaut, dass sie die Regeln trotzdem einhalten: eindeutige Namen, Leitungen auf
dem Pfad ihrer Mitgliedschaft, keine Person im Verband.

Die erfundenen Konten (`probe.0001` usw.) sind mit keinem Keycloak-Konto verknüpft und haben kein Passwort;
anmelden kann sich mit ihnen niemand. Damit die Suche bei „Person aufnehmen“ sie über die genaue Mail findet,
haben sie eine bestätigte Mail und einen Zeitpunkt des letzten Logins, wie Konten, die sich schon einmal
angemeldet haben. Sie bleiben wie alle Konten über Läufe hinweg stehen; der nächste Lauf nimmt sie wieder.
Jeder Lauf ergibt dieselben Daten, nur die zufälligen Kennungen für Adressen sind neu.

Seit dem Ende von P2 (#369) dazu die erfundene Veranstaltung `EVENT` mit allen Personen: je Probestamm eine
Anmeldung, abgegeben von seiner Stammesleitung, mit den Personen des Stamms und seiner Gruppen (#369, Frage 2).
Leitung der Veranstaltung ist die Bundesleitung Boreas; fehlt sie (in der Testumgebung vor ihrem ersten Login),
hat die Veranstaltung keine Leitung, und die Anmeldungen gibt es trotzdem. Auch sie entstehen in einem Rutsch,
an `Registration.create()` vorbei; wer darin steht, dürfte die Stammesleitung auch im Tool anmelden (ANM-01).

Erweitern am Ende einer Phase (#145): Was neue Seiten mit Personen oder Anmeldungen brauchen, kommt als
weitere Funktion hierher und wird in `create()` aufgerufen.
"""

from datetime import UTC, date, datetime, timedelta

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import CommandError

from core import texts
from events.models import Event, RegisteredPerson, Registration, copy_of
from persons.models import ManagedPerson
from roles.models import Role, RoleKind
from units.models import Kind, Unit

# Wie viele erfundene Probestämme, Gruppen je Stamm und Personen; eine Organisation hat `OUTLIER` direkte Personen.
TROOPS = 40
GROUPS_PER_TROOP = 5
PERSONS = 5000
OUTLIER = 500
# Zwei von fünf Personen haben ein Konto, die anderen sind verwaltete Personen (etwa Kinder).
ACCOUNT_SHARE = 2

FIRST_NAMES = (
    "Ada", "Ben", "Cleo", "Dario", "Ella", "Finn", "Gesa", "Hugo", "Ilka", "Jan", "Kira", "Lasse", "Malu", "Nico",
    "Olga", "Pit", "Rike", "Sami", "Tilda", "Uwe", "Vera", "Wanja", "Xenia", "Yara", "Zoe", "Arne", "Bea", "Carl",
    "Dina", "Eik", "Fee", "Gero", "Hanna", "Ivo", "Juna", "Kalle", "Lia", "Mats", "Nova", "Ole",
)
LAST_NAMES = ("Probe", "Muster")
SCOUT_NAMES = ("Dachs", "Eule", "Falke", "Hummel", "Krähe", "Lerche", "Otter", "Wiesel")
# Feste Zeitpunkte statt der Uhr, damit jeder Lauf dieselben Daten ergibt.
LAST_LOGIN = datetime(2026, 1, 1, tzinfo=UTC)
CONSENT_AT = datetime(2026, 1, 1, tzinfo=UTC)
FIRST_BIRTH_DATE = date(2008, 1, 1)
# Die erfundene Veranstaltung mit allen Personen (#369); die Anmeldungen kommen im Abstand einer Minute.
EVENT = {"name": "Probe-Bundeslager 2028", "start": date(2028, 7, 20), "end": date(2028, 7, 29)}
FIRST_REGISTRATION_AT = datetime(2027, 11, 1, tzinfo=UTC)


def create(association: Unit, consent_by) -> dict:
    """Legt die Massendaten im Bund `association` an und gibt zurück, wie viel.

    `consent_by` ist das Konto, das die Einwilligung der verwalteten Personen bestätigt hat, die Bundesleitung;
    ohne sie bleibt die Angabe leer. Lehnt mit `CommandError` ab, bevor etwas geschrieben ist, wenn ein
    Benutzername der erfundenen Konten einem Konto gehört, das mit Keycloak verknüpft ist: Es bekäme sonst
    Rollen in den Probestämmen.
    """
    usernames = [username(number) for number in range(PERSONS) if has_account(number)]
    linked = SocialAccount.objects.filter(user__username__in=usernames).values_list("user__username", flat=True)
    if linked:
        raise CommandError(texts.MASS_DATA_TAKEN % {"usernames": ", ".join(sorted(linked))})
    units = _units(association)
    accounts = _accounts(usernames)
    roles, people, leads = _persons(units, accounts, consent_by)
    registrations = _registrations(units, people, leads, consent_by)
    return {"units": len(units), "accounts": len(accounts), "managed": PERSONS - len(accounts), "roles": roles,
            "event": EVENT["name"], "registrations": registrations}


def username(number: int) -> str:
    """Der Benutzername der Person mit dieser laufenden Nummer, z. B. „probe.0001“."""
    return f"probe.{number + 1:04d}"


def has_account(number: int) -> bool:
    """Ob die Person mit dieser laufenden Nummer ein Konto hat."""
    return number % 5 < ACCOUNT_SHARE


def _units(association: Unit) -> list[Unit]:
    """Die Probestämme und ihre Gruppen, jeder Stamm gefolgt von seinen Gruppen; der erste ist der Ausreißer."""
    troops = Unit.objects.bulk_create([
        Unit(kind=Kind.TROOP, name=f"Probestamm {number:02d}", parent=association, association=association)
        for number in range(1, TROOPS + 1)
    ])
    groups = Unit.objects.bulk_create([
        Unit(kind=Kind.GROUP, name=f"Probegruppe {number}", parent=troop)
        for troop in troops for number in range(1, GROUPS_PER_TROOP + 1)
    ])
    ordered = []
    for index, troop in enumerate(troops):
        ordered += [troop, *groups[index * GROUPS_PER_TROOP:(index + 1) * GROUPS_PER_TROOP]]
    return ordered


def _accounts(usernames: list[str]) -> dict[str, object]:
    """Die erfundenen Konten nach Benutzername: vorhandene aus einem früheren Lauf wieder, fehlende neu.

    Namen, Mail und Mail-Liste setzt jeder Lauf neu, damit das Ergebnis gleich ist, auch wenn sich ein Konto inzwischen
    geändert hätte.
    """
    users = get_user_model().objects
    numbers = {username(number): number for number in range(PERSONS)}
    found = {user.username: user for user in users.filter(username__in=usernames)}
    for name, user in found.items():
        user.first_name, user.last_name, user.email = _name(numbers[name]) + (f"{name}@example.org",)
        user.last_login, user.is_active = LAST_LOGIN, True
    users.bulk_update(found.values(), ["first_name", "last_name", "email", "last_login", "is_active"])
    new = []
    for name in usernames:
        if name not in found:
            first_name, last_name = _name(numbers[name])
            new.append(get_user_model()(username=name, first_name=first_name, last_name=last_name,
                                        email=f"{name}@example.org", last_login=LAST_LOGIN,
                                        password=make_password(None)))
    for user in users.bulk_create(new):
        found[user.username] = user
    # Die Mail-Liste ebenso: genau eine bestätigte Mail je Konto, damit die Suche es findet und nur darüber.
    EmailAddress.objects.filter(user__in=found.values()).delete()
    EmailAddress.objects.bulk_create([
        EmailAddress(user=found[name], email=found[name].email, verified=True, primary=True) for name in usernames
    ])
    return found


def _persons(units: list[Unit], accounts: dict, consent_by) -> tuple[int, dict, dict]:
    """Verteilt die Personen: die ersten `OUTLIER` in den Ausreißer, die übrigen reihum auf alle anderen.

    Gibt zurück, wie viele Rollen entstanden sind, je Organisation ihre Personen (Konten und verwaltete Personen in
    der Reihenfolge des Anlegens) und je Organisation das Konto ihrer Leitung, alles nach der Nummer der Organisation.
    """
    others = units[1:]
    roles, managed, leads = [], [], {}
    people = {unit.pk: [] for unit in units}
    for number in range(PERSONS):
        unit = units[0] if number < OUTLIER else others[(number - OUTLIER) % len(others)]
        if has_account(number):
            user = accounts[username(number)]
            people[unit.pk].append(user)
            roles.append(Role(user=user, kind=RoleKind.MEMBER, unit=unit))
            # Das erste Mitglied mit Konto leitet die Organisation; die Leitung liegt so auf dem Pfad (#89).
            if unit.pk not in leads:
                kind = RoleKind.TROOP_LEAD if unit.kind == Kind.TROOP else RoleKind.GROUP_LEAD
                leads[unit.pk] = Role(user=user, kind=kind, unit=unit)
        else:
            first_name, last_name = _name(number)
            managed.append(ManagedPerson(
                first_name=first_name, last_name=last_name, unit=unit,
                birth_date=FIRST_BIRTH_DATE + timedelta(days=(number * 37) % 5000),
                scout_name=SCOUT_NAMES[number % len(SCOUT_NAMES)] if number % 7 == 0 else "",
                consent_by=consent_by, consent_at=CONSENT_AT,
            ))
            people[unit.pk].append(managed[-1])
    Role.objects.bulk_create([*roles, *leads.values()])
    # Die Datenbank gibt die neuen Nummern zurück; die Personen in `people` sind dieselben Objekte.
    ManagedPerson.objects.bulk_create(managed)
    return len(roles) + len(leads), people, {pk: role.user for pk, role in leads.items()}


def _registrations(units: list[Unit], people: dict, leads: dict, event_lead) -> int:
    """Die Veranstaltung `EVENT` und je Probestamm die Anmeldung seiner Leitung mit allen Personen des Stamms und seiner
    Gruppen, der Stamm zuerst (#369). Gibt zurück, wie viele Anmeldungen entstanden sind.

    Die Kopie der Angaben ist dieselbe wie beim Anmelden im Tool (`copy_of()` in `events/models.py`, A5).
    """
    event = Event.objects.create(**EVENT)
    if event_lead is not None:
        event.leads.add(event_lead)
    troops = [unit for unit in units if unit.kind == Kind.TROOP]
    registrations = Registration.objects.bulk_create([
        Registration(event=event, contact=leads[troop.pk], created_at=FIRST_REGISTRATION_AT + timedelta(minutes=index))
        for index, troop in enumerate(troops)
    ])
    entries = []
    for troop, registration in zip(troops, registrations, strict=True):
        members = [troop, *[unit for unit in units if unit.parent_id == troop.pk]]
        for person in [person for unit in members for person in people[unit.pk]]:
            entries.append(RegisteredPerson(registration=registration, **copy_of(person)))
    RegisteredPerson.objects.bulk_create(entries)
    return len(registrations)


def _name(number: int) -> tuple[str, str]:
    """Vor- und Nachname der Person mit dieser laufenden Nummer; Nachnamen nur „Probe“ oder „Muster“."""
    return FIRST_NAMES[number % len(FIRST_NAMES)], LAST_NAMES[(number // len(FIRST_NAMES)) % len(LAST_NAMES)]
