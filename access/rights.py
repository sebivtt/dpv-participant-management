"""Die zentrale Rechteprüfung: wer welche Personen und Leitungen sieht und wo jemand Leitung ist (#90).

Grundlage sind BER-01 (geschlossene Liste der Gründe, Personendaten zu sehen), ROL-02
(einspringende Leitung) und `docs/rechtematrix.md`. Jede Seite fragt `request.rights`; keine
Seite liest Personen- oder Anmeldedaten selbst aus der Datenbank (`CONTRIBUTING.md`,
Abschnitt 4; der Rundumtest meldet Verstöße).

Was gebaut ist, zeigt die Spalte „Stand“ in `docs/rechtematrix.md`. Weitere Gründe und Aktionen
kommen mit ihren Seiten an diese Stelle (Protokoll der Nachklärung von #90 vom 25.10.2026).

Rollen und Einheiten werden beim ersten Bedarf einer Anfrage einmal geladen und mit der Anfrage
verworfen. Einen Zwischenspeicher über Anfragen hinweg gibt es nicht: Wer eine Rolle verliert
oder nicht mehr einspringt, verliert die Rechte beim nächsten Klick (Entscheidung vom 24.10.2026,
F4.6). Fehlt eine Angabe (kein Login, keine Mitgliedschaft, keine Einheit), ist das Ergebnis
immer „verboten“ (F4.3).

Wie eine Seite „verboten“ zeigt, regelt diese Stelle für alle Seiten (#64, Auslegung von BER-01):
Einträge holt eine Seite mit ihrer zufälligen Kennung über `entry()` oder `person()`; ohne Recht
ist der Eintrag „nicht gefunden“ (404), genau wie einer, den es nicht gibt. Einen ganzen Bereich
ohne Kennung in der Adresse öffnet sie über `require_section()`; ohne Recht heißt es „kein
Zugriff“ (403). Meldet eine Seite an einer Adresse mit Kennung trotzdem „kein Zugriff“, macht
`RightsMiddleware` „nicht gefunden“ daraus.
"""

import math
import unicodedata
from collections.abc import Callable
from datetime import timedelta
from functools import cached_property

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import (
    BooleanField,
    CharField,
    Exists,
    ExpressionWrapper,
    F,
    Model,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Value,
)
from django.db.models.functions import Concat
from django.http import Http404
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

from access.keys import has_key, is_key
from accounts.models import AccountSearch, display_name
from persons import texts as person_texts
from persons.models import EDITABLE_FIELDS, ManagedPerson
from roles.models import LEAD_ROLE, LEADS_IN_UNITS, Role, after_leaving, leads_off_path, on_path
from units import texts as unit_texts
from units.models import Kind as UnitKind
from units.models import Unit

R = Role.Kind
# Wen die Verbandsleitung als Leitung sieht (RO-05): Bundesleitungen, Verbandsleitungen und das
# DPV-Veranstaltungsteam, im ganzen Verband.
SEEN_BY_FEDERATION_LEAD = (R.ASSOCIATION_LEAD, R.FEDERATION_LEAD, R.EVENT_TEAM)
# Was über eine Leitung nach BER-01, Grund 3 sichtbar ist: Name, Fahrtenname und Rolle, nie die
# Mail (#136, B2; #111). Den vollen Namen daraus bildet `accounts.models.display_name()`; ohne Namen
# zeigen Seiten den Benutzernamen wie „Mein Profil“ (#189, A12). Interne Nummern von Konto und
# Einheit gibt die Liste nicht heraus, damit keine auf eine Seite gerät (#156); Seiten ordnen die
# Leitungen über die Kennungen von Konto und Einheit zu (#189), die Knöpfe zum Entfernen nennen die
# Kennung der Rolle (#191). `locked` kennzeichnet ein im Tool gesperrtes Konto; solche Leitungen
# stehen nur in der Liste, wer sie entfernen darf (#189, Frage B).
LEAD_FIELDS = ("kind",)
LEAD_NAMES = {
    "first_name": F("user__first_name"),
    "last_name": F("user__last_name"),
    "scout_name": F("user__scout_name"),
    "username": F("user__username"),
    "user_key": F("user__key"),
    "unit_name": F("unit__name"),
    "unit_key": F("unit__key"),
    "role_key": F("key"),
    "locked": ExpressionWrapper(Q(user__is_active=False), output_field=BooleanField()),
}
# Vorschläge beim Tippen erst ab so vielen Zeichen und höchstens so viele (PK-09, Frage 10 aus #93).
SUGGESTION_MIN = 3
SUGGESTION_MOST = 10
# Zeichen, die in anderen Suchen für „beliebig“ stehen; allein gesucht zeigen sie nichts (PK-15).
WILDCARDS = frozenset("*%_")
# Suchlimit für „Suchen“ über die genaue Mail oder den Benutzernamen (PK-24, Frage D aus #93).
SEARCH_LIMIT = 20
SEARCH_WINDOW = timedelta(minutes=60)
# Wie weit eine Leitung eine Einheit auf der Seite „Organisation“ sieht (#189).
MANAGE = "manage"  # im eigenen Bereich: Seite mit Mails, wo sie die Person sieht
READ = "read"  # auf der Kette nach oben: Seite nur lesen
NAME_ONLY = "name"  # sonst im eigenen Bund: nur der Name in der Gliederung
# Die Wahl beim Austragen (#286, #65 Frage 17): „hoch“ heißt danach direkt zur Organisation darüber,
# „ganz“ heißt danach keiner Organisation mehr; der Wert sagt, ob die Person ganz ausgetragen wird.
EXPEL_CHOICES = {"hoch": False, "ganz": True}


class Rights:
    """Was eine Person sehen darf und wo sie Leitung ist, für genau eine Anfrage.

    Für jede Anfrage entsteht ein neues Objekt (`RightsMiddleware`); es merkt sich die Rollen
    nur für diese Anfrage. Mehrere Rollen zählen zusammen: Die Person darf alles, was eine davon
    erlaubt (#90). Admins bekommen hier keine Rechte; ihr Weg ist der Support-Zugang (#92).
    """

    def __init__(self, user) -> None:
        # Ohne gespeichertes, aktives Konto gibt es keine Rechte, auch nicht auf sich selbst.
        valid = user is not None and getattr(user, "pk", None) is not None and getattr(user, "is_active", False)
        self.user = user if valid else None

    # Was einmal pro Anfrage aus der Datenbank kommt

    @cached_property
    def _own_roles(self) -> list[tuple[str, int | None]]:
        if self.user is None:
            return []
        return list(Role.objects.filter(user_id=self.user.pk).values_list("kind", "unit_id"))

    @cached_property
    def _tree(self) -> dict[int, tuple[int | None, str]]:
        """Jede Einheit mit der Einheit darüber und ihrer Ebene."""
        return {pk: (parent, kind) for pk, parent, kind in Unit.objects.values_list("pk", "parent_id", "kind")}

    @cached_property
    def _children(self) -> dict[int, list[int]]:
        children: dict[int, list[int]] = {}
        for pk, (parent, _kind) in self._tree.items():
            if parent is not None:
                children.setdefault(parent, []).append(pk)
        return children

    @cached_property
    def _units_with_lead(self) -> frozenset[int]:
        """Einheiten mit mindestens einer Leitung mit Konto (ROL-02).

        Jede Rolle gehört zu einem Konto; angezeigte Leitungsrollen verwalteter Personen
        (#99) stehen nicht in dieser Tabelle und zählen deshalb nie (VP-16). Ein im Tool
        gesperrtes Konto zählt nicht, sonst hätte niemand in der Einheit Rechte (Sebastian,
        25.10.2026, Kommentar in #90).
        """
        leads = Role.objects.filter(kind__in=LEADS_IN_UNITS, user__is_active=True)
        return frozenset(leads.values_list("unit_id", flat=True))

    # Bausteine

    @cached_property
    def _led(self) -> frozenset[int]:
        """Die Einheiten, die die Person selbst leitet (Gruppe, Stamm, Ring oder Bund)."""
        return frozenset(unit for kind, unit in self._own_roles if kind in LEADS_IN_UNITS and unit is not None)

    @cached_property
    def _membership(self) -> int | None:
        return next((unit for kind, unit in self._own_roles if kind == R.MEMBER), None)

    @cached_property
    def area(self) -> frozenset[int]:
        """Der Bereich: die geleiteten Einheiten mit allen Einheiten darunter (BER-01, Grund 2)."""
        found: set[int] = set()
        for unit in self._led:
            found |= self._below(unit)
        return frozenset(found)

    @cached_property
    def chain(self) -> frozenset[int]:
        """Die Kette nach oben: ab der Mitgliedschaft und ab jeder geleiteten Einheit bis zum Bund (#150, C3)."""
        starts = set(self._led)
        if self._membership is not None:
            starts.add(self._membership)
        found: set[int] = set()
        for unit in starts:
            found |= self._above(unit)
        return frozenset(found)

    @cached_property
    def _covered(self) -> frozenset[int]:
        """Einheiten ohne Leitung mit Konto, für die die Person einspringt (ROL-02, EH-18).

        Von jeder geleiteten Einheit nach unten: Jede Einheit ohne Leitung gehört dazu und
        ebenso, was darunter wieder ohne Leitung ist. Eine Einheit mit Leitung beendet den Weg;
        für die Einheiten darunter springt dann diese Leitung ein. Nach oben springt niemand
        ein: Für einen Bund ohne Bundesleitung gibt es keine einspringende Leitung, auch nicht
        die Verbandsleitung, deren Rolle nicht zu den Leitungen in Einheiten zählt (EH-27).
        """
        found: set[int] = set()
        pending = [child for unit in self._led for child in self._children.get(unit, [])]
        while pending:
            unit = pending.pop()
            if unit in self._units_with_lead or unit in found:
                continue
            found.add(unit)
            pending.extend(self._children.get(unit, []))
        return frozenset(found)

    def _below(self, unit: int) -> set[int]:
        found = {unit}
        pending = list(self._children.get(unit, []))
        while pending:
            child = pending.pop()
            found.add(child)
            pending.extend(self._children.get(child, []))
        return found

    def _above(self, unit: int | None) -> set[int]:
        """Die Einheit und alle darüber, ohne den Verband."""
        found = set()
        while unit is not None and unit in self._tree:
            parent, kind = self._tree[unit]
            if kind == UnitKind.FEDERATION:
                break
            found.add(unit)
            unit = parent
        return found

    # Personen (BER-01, Grund 1 und 2)

    def persons(self) -> QuerySet:
        """Die Konten, deren Personendaten die Person sieht: sich selbst und die Mitglieder ihres Bereichs.

        Gefiltert wird in der Datenbank, damit auch große Bünde schnell bleiben (#104). Leitungen,
        die außerhalb des Bereichs Mitglied sind, gehören nicht dazu; von ihnen sieht man nur, was
        `leads()` zeigt (RO-03, Beispiel Berta).
        """
        users = get_user_model().objects
        if self.user is None:
            return users.none()
        members = Role.objects.filter(kind=R.MEMBER, unit_id__in=self.area).values("user_id")
        return users.filter(Q(pk=self.user.pk) | Q(pk__in=members))

    def person(self, key) -> object:
        """Ein Konto aus `persons()` über seine Kennung; ohne Recht „nicht gefunden“ wie bei einer Kennung ohne Eintrag (#64)."""
        return self.entry(self.persons(), key)

    # Wie Seiten „verboten“ zeigen (#64)

    def entry(self, entries: QuerySet, key, allowed: Callable[[Model], bool] | None = None) -> Model:
        """Der Eintrag mit dieser Kennung aus `entries`, den Einträgen, die die Person sehen darf.

        Ohne Recht ist das Ergebnis immer „nicht gefunden“ (404), genau wie bei einer Kennung, zu
        der es keinen Eintrag gibt, und bei einer Kennung in falscher Form: Gibt es den Eintrag,
        aber nicht in `entries`, oder sagt `allowed` für die gewünschte Aktion „nein“, erfährt
        niemand, dass es ihn gibt. Laufende Nummern nimmt die Stelle nicht an. Das gilt auch, wenn
        eine Seite einen Eintrag über einen angehängten Parameter oder ein Formularfeld wählt, z. B.
        aus einer Auswahlliste (#156); die Zugehörigkeit eines neuen Eintrags kommt trotzdem aus der
        Adresse (`CONTRIBUTING.md`, Abschnitt 4).
        """
        if self.user is None or not is_key(key):
            raise Http404
        found = entries.filter(key=key).first()
        if found is None or (allowed is not None and not allowed(found)):
            raise Http404
        return found

    def require_section(self, allowed: bool) -> None:
        """Öffnet einen ganzen Bereich des Tools ohne Kennung in der Adresse, z. B. „Organisation“ (#93).

        Ohne Recht „kein Zugriff“ (403): Welche Bereiche es gibt, ist kein Geheimnis, der Code ist
        öffentlich. Adressen mit Kennung prüfen über `entry()`; meldet eine von ihnen trotzdem
        „kein Zugriff“, zeigt `RightsMiddleware` „nicht gefunden“.

        Seiten melden „kein Zugriff“ nur so oder mit `PermissionDenied`, nie mit einer selbst
        gebauten Antwort mit Status 403: Die erkennt `RightsMiddleware` nicht, und an einer
        Adresse mit Kennung verriete sie, dass es den Eintrag gibt.
        """
        if self.user is None or not allowed:
            raise PermissionDenied

    # Seite „Organisation“ (#189)

    def sees_organisation(self) -> bool:
        """Gliederung und Seiten der Einheiten unter „Organisation“: jede Leitung von Gruppe bis Bund (EH-08).

        Mitglieder ohne Leitungsrolle, Konten ohne Zuordnung, das DPV-Veranstaltungsteam, die
        Verbandsleitung ohne weitere Rolle und Admins öffnen keine Einheit (EH-09; Admins mit #92,
        Mitglieder mit #134). Den Menüpunkt hat zusätzlich die Verbandsleitung (`sees_menu()`, #94).
        Endet die letzte Leitungsrolle, fehlt beides beim nächsten Klick.
        """
        return bool(self._led)

    @cached_property
    def associations(self) -> frozenset[int]:
        """Die eigenen Bünde: die Bünde auf der Kette nach oben (EH-01). Andere Bünde erscheinen nie (EH-03)."""
        return frozenset(unit for unit in self.chain if self._tree[unit][1] == UnitKind.ASSOCIATION)

    def unit_access(self, unit: Unit | None) -> str | None:
        """Wie weit die Person eine Einheit auf der Seite „Organisation“ sieht, oder None (#189).

        `MANAGE` im eigenen Bereich (RO-03), `READ` auf der Kette nach oben (RO-01, Frage C),
        `NAME_ONLY` für den Rest des eigenen Bundes (EH-01, RO-04), sonst nichts: andere Bünde
        und der Verband (EH-03, N7). Ohne Leitungsrolle immer nichts, auch auf der eigenen Kette
        (EH-09, AV9).
        """
        if unit is None or not self.sees_organisation() or unit.pk not in self._tree:
            return None
        if unit.pk in self.area:
            return MANAGE
        if unit.pk in self.chain:
            return READ
        if self._association_of(unit.pk) in self.associations:
            return NAME_ONLY
        return None

    def opens_unit(self, unit: Unit | None) -> bool:
        """Öffnet sich die Seite dieser Einheit, zum Verwalten oder nur zum Lesen (#189)?"""
        return self.unit_access(unit) in (MANAGE, READ)

    def leads_itself(self, unit: Unit | None) -> bool:
        """Leitet die Person diese Einheit selbst? Die Übersicht zeigt am PC die oberste solche Einheit (#189)."""
        return unit is not None and unit.pk in self._led

    def has_lead(self, unit: Unit | None) -> bool:
        """Hat die Einheit eine Leitung mit Konto? Gesperrte Konten zählen nicht (EH-18, #189, A16)."""
        return unit is not None and unit.pk in self._units_with_lead

    def covering_unit(self, unit: Unit | None) -> int | None:
        """Die nächste Einheit darüber mit Leitung, deren Leitung für `unit` einspringt; sonst None (ROL-02).

        Für einen Bund springt niemand ein (EH-27), ebenso nicht, wenn bis zum Bund keine
        Einheit eine Leitung hat. Gibt die interne Nummer zurück; Seiten zeigen nur den Namen.
        """
        if unit is None or self.has_lead(unit) or unit.pk not in self._tree:
            return None
        return self._lead_above(unit.pk)

    def _lead_above(self, unit: int, without: frozenset[int] = frozenset()) -> int | None:
        """Die nächste Einheit über `unit` mit Leitung mit Konto, ohne den Verband; sonst None.

        Einheiten in `without` zählen als ohne Leitung, etwa weil ihre letzte Leitung gerade endet (#286).
        """
        parent = self._tree[unit][0]
        while parent is not None and self._tree[parent][1] != UnitKind.FEDERATION:
            if parent in self._units_with_lead and parent not in without:
                return parent
            parent = self._tree[parent][0]
        return None

    def _association_of(self, unit: int) -> int | None:
        while unit is not None and unit in self._tree:
            parent, kind = self._tree[unit]
            if kind == UnitKind.ASSOCIATION:
                return unit
            unit = parent
        return None

    def own_roles(self) -> list[Role]:
        """Die eigenen Rollen der Person für „Mein Profil“, mit ihren Einheiten (EP-01, ORG-05).

        Zuerst die Mitgliedschaft, dann die Leitungsrollen von der Gruppe bis zum Bund, danach
        Verbandsleitung, DPV-Veranstaltungsteam und Admin; dieselbe Rolle mehrmals nach dem
        Namen der Einheit (Szenarien vom 25.10.2026 in #96). Die Einheiten darüber bis zum
        Verband sind vorab geladen, damit `Unit.names_above()` keine eigenen Abfragen braucht.
        Jeder Aufruf liest frisch: Eine geänderte Rolle erscheint beim nächsten Klick.
        """
        if self.user is None:
            return []
        roles = Role.objects.filter(user_id=self.user.pk).select_related("unit__parent__parent__parent__parent")
        order = list(R)
        return sorted(roles, key=lambda role: (order.index(role.kind), alphabetical(role.unit.name if role.unit else "")))

    def is_federation_lead(self) -> bool:
        """Ist die Person Verbandsleitung? Dann öffnet „Organisation“ die Seite „Verband“ (EH-08, #94)."""
        return any(kind == R.FEDERATION_LEAD for kind, _unit in self._own_roles)

    def sees_menu(self) -> bool:
        """Menüpunkt und Bereich „Organisation“: Leitungen von Gruppe bis Bund und die Verbandsleitung (EH-08, EH-09)."""
        return self.sees_organisation() or self.is_federation_lead()

    def has_roles(self) -> bool:
        """Hat die Person eine Mitgliedschaft oder irgendeine Rolle? Ohne beides steht der Hinweis „keiner Organisation zugeordnet“ (#9).

        Der Hinweis richtet sich bewusst nicht nach „Zuordnung“ (BER-03): Admins ohne
        Mitgliedschaft wissen, warum sie keiner Organisation angehören (Klärung von #9 vom
        27.10.2026, Frage 2). Nutzt die Rollen, die die Anfrage ohnehin einmal lädt.
        """
        return bool(self._own_roles)

    # Leitungen benennen (#190)

    def may_appoint(self, unit: Unit | None) -> bool:
        """Darf die Person in dieser Einheit Leitungen benennen (RO-10, RO-11, EH-18)?

        Das ist genau ihr Bereich: die Bundesleitung im ganzen Bund, die Ringleitung in ihrem
        Ring, die Stammesleitung in ihrem Stamm und dessen Gruppen, weitere Leitungen derselben
        Einheit. Wo sie einspringt, liegt ohnehin in ihrem Bereich. Auf der Kette nach oben sieht sie
        nur lesend (EH-28); Verbandsleitung, Mitglieder und Admins ohne Leitungsrolle haben keinen
        Bereich (RO-14, RO-17).
        """
        return unit is not None and self.sees_organisation() and unit.pk in self.area

    def suggestions(self, text: str) -> list[dict]:
        """Vorschläge beim Tippen: Personen mit Konto im eigenen Bereich nach Namen (PK-09, PK-10).

        Erst ab `SUGGESTION_MIN` Zeichen, höchstens `SUGGESTION_MOST`, gesucht in Vorname,
        Nachname, beidem zusammen und Fahrtenname, ohne Groß- und Kleinschreibung. Konten ohne
        Zuordnung und Personen außerhalb des Bereichs findet niemand über den Namen (PK-10 bis
        PK-12), gesperrte Konten erscheinen nicht (BV11). „%“ und „_“ stehen hier für sich selbst.
        """
        text = text.strip()
        if not self.sees_organisation() or len(text) < SUGGESTION_MIN:
            return []
        named = self.persons().filter(is_active=True).annotate(
            full_name=Concat("first_name", Value(" "), "last_name", output_field=CharField())
        )
        matches = (Q(first_name__icontains=text) | Q(last_name__icontains=text) | Q(full_name__icontains=text)
                   | Q(scout_name__icontains=text))
        found = named.filter(matches).order_by("last_name", "first_name", "username")[:SUGGESTION_MOST]
        return self._hits(list(found))

    def find_accounts(self, text: str) -> list[dict]:
        """Konten über die genaue bestätigte Mail oder den genauen Benutzernamen, ohne Groß- und Kleinschreibung (PK-13).

        Bestätigt heißt: Keycloak hat die Mail beim letzten Login des Kontos als bestätigt gemeldet
        (`EmailAddress.verified`, #251). Eine unbestätigte Mail zeigt dasselbe wie kein Konto. Ein
        Suchbegriff mit @ zählt nur als Mail, nie als Benutzername; sonst fände ein Benutzername, der
        wie eine fremde Mail aussieht, das Konto an der Mail vorbei.

        Für Leitungen von Gruppe bis Bund und für die Verbandsleitung (#94); eine Namenssuche hat
        die Verbandsleitung nicht, `suggestions()` gibt ihr nichts (PK-12).

        Nur Konten, die sich schon einmal angemeldet haben und nicht gesperrt sind; ein gesperrtes
        Konto zeigt dasselbe wie keines, damit die Suche keine Sperre verrät (BV11). Ein Teil einer
        Mail findet nichts, und eine Liste aller Konten gibt es nicht (PK-15): Verglichen wird auf
        Gleichheit, Platzhalter wie „%“ gelten als Zeichen. Den Treffer zeigt die Seite ohne die
        Organisation, wenn er außerhalb des eigenen Bereichs liegt (PK-16). Das Suchlimit zählt
        `count_search()`, nicht diese Stelle.
        """
        text = text.strip()
        if not self.sees_menu() or not text or set(text) <= WILDCARDS:
            return []
        accounts = get_user_model().objects.filter(is_active=True, last_login__isnull=False)
        if "@" in text:
            confirmed = EmailAddress.objects.filter(user=OuterRef("pk"), email__iexact=text, verified=True)
            found = accounts.filter(Exists(confirmed))
        else:
            found = accounts.filter(username__iexact=text)
        found = found.order_by("username")
        return self._hits(list(found[:SUGGESTION_MOST]))

    def _hits(self, users: list) -> list[dict]:
        """Was Vorschläge und Treffer zeigen dürfen: Kennung, Namen und wo die Person Mitglied ist (PK-16).

        `unit_name` und `unit_label` stehen nur bei Mitgliedern des eigenen Bereichs und bei der Person selbst;
        sonst sagt `elsewhere` nur, dass sie schon woanders Mitglied ist. Interne Nummern gibt die
        Liste nicht heraus (#156).
        """
        memberships = dict(
            Role.objects.filter(kind=R.MEMBER, user_id__in=[user.pk for user in users]).values_list("user_id", "unit_id")
        )
        units = {entry.pk: entry for entry in Unit.objects.filter(pk__in=memberships.values())}
        found = []
        for user in users:
            unit = memberships.get(user.pk)
            is_self = user.pk == self.user.pk
            shown = unit is not None and (unit in self.area or is_self)
            found.append({
                "key": user.key,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "scout_name": user.scout_name,
                "username": user.username,
                "unit_name": units[unit].name if shown else "",
                # Mit der Art davor wie beim Aufnehmen, z. B. „Stamm Walhall“ (#285); nur, wo auch der Name steht.
                "unit_label": unit_label(units[unit]) if shown else "",
                "elsewhere": unit is not None and not shown,
                "is_self": is_self,
            })
        return found

    def count_search(self) -> int:
        """Zählt eine Suche fürs Suchlimit; 0 heißt erlaubt und gezählt, sonst die Minuten bis zur nächsten (PK-24).

        Höchstens `SEARCH_LIMIT` Suchen in `SEARCH_WINDOW`, Mail und Benutzername zusammen. Eine
        abgewiesene Suche zählt nicht. Die Minuten reichen, bis die älteste gezählte Suche aus der
        Zeitspanne fällt, aufgerundet und mindestens 1; dann geht genau eine Suche wieder. Gleichzeitige
        Suchen derselben Person laufen nacheinander, weil das Konto bis zum Ende gesperrt ist (BV13).
        Einträge, die älter als die Zeitspanne sind, löscht jede Suche für alle Personen, damit nicht mehr
        gespeichert ist als nötig.
        """
        if self.user is None:
            return 0
        with transaction.atomic():
            list(get_user_model().objects.select_for_update().filter(pk=self.user.pk).values_list("pk"))
            now = timezone.now()
            # Alte Einträge aller Personen, damit auch von jemandem, der nie wieder sucht, nichts liegen bleibt.
            AccountSearch.objects.filter(searched_at__lte=now - SEARCH_WINDOW).delete()
            searches = AccountSearch.objects.filter(user_id=self.user.pk)
            times = list(searches.order_by("-searched_at").values_list("searched_at", flat=True)[:SEARCH_LIMIT])
            if len(times) >= SEARCH_LIMIT:
                wait = times[-1] + SEARCH_WINDOW - now
                return max(1, math.ceil(wait.total_seconds() / 60))
            AccountSearch.objects.create(user_id=self.user.pk, searched_at=now)
            return 0

    def appoint(self, unit: Unit, person_key) -> tuple[bool, str]:
        """Benennt eine Person als Leitung der Einheit; gibt zurück, ob es geklappt hat, und die Meldung.

        Ohne Recht in dieser Einheit oder mit einer Kennung, die keine erreichbare Person nennt
        (gesperrt, nie angemeldet und nicht im eigenen Bereich), ist das Ergebnis „nicht gefunden“.
        Abgelehnt mit Meldung wird, wer sich selbst benennen will (RO-12), wer dort schon Leitung
        ist (BV3), wer außerhalb des eigenen Bereichs schon Mitglied ist (BV1, ohne die
        Organisation zu nennen) und wer die Rolle danach nicht auf seinem Leitungspfad hätte (BV2,
        #89). Wer noch nirgends Mitglied ist, wird Mitglied der Einheit (B7, B8). Die Rolle gilt
        sofort und steht im Protokoll (#91). Gleichzeitige Benennungen derselben Person laufen
        nacheinander, weil ihr Konto bis zum Ende gesperrt ist; die zweite sieht „schon …“ (BV12).
        Gesperrt ist auch das eigene Konto, und das Recht wird unter der Sperre noch einmal geprüft:
        Wer gerade als Leitung entfernt wird, benennt danach niemanden mehr (#191).
        """
        if not self.may_appoint(unit) or not is_key(person_key):
            raise Http404
        users = get_user_model().objects
        kind = LEAD_ROLE[unit.kind]
        with transaction.atomic():
            found = users.filter(key=person_key).values_list("pk", flat=True).first()
            if found is None:
                raise Http404
            me = self._lock_with(found)
            fresh = Rights(me)
            if not fresh.may_appoint(unit):
                raise Http404
            reachable = Q(last_login__isnull=False) | Q(pk__in=fresh.persons().values("pk"))
            target = users.filter(reachable, pk=found, is_active=True).first()
            if target is None:
                raise Http404
            values = {"person": display_name(target.first_name, target.last_name, target.scout_name) or target.username,
                      "role": kind.label, "unit": unit.name}
            roles = Role.objects.filter(user_id=target.pk)
            membership = roles.filter(kind=R.MEMBER).select_related("unit").first()
            if target.pk == me.pk:
                own = membership.unit.name if membership else unit.name
                return False, str(unit_texts.NOT_YOURSELF % {"unit": own})
            if roles.filter(kind=kind, unit_id=unit.pk).exists():
                return False, str(unit_texts.ALREADY_LEAD % values)
            if membership is not None and membership.unit_id not in fresh.area:
                return False, str(unit_texts.MEMBER_ELSEWHERE)
            try:
                Role(user=target, kind=kind, unit=unit).save(by=me)
            except ValidationError as error:
                if error.error_list[0].code != "outside_path":
                    raise
                target_name = unit_texts.KIND_AND_NAME[unit.kind] % {"unit": unit.name}
                return False, str(unit_texts.NOT_ON_PATH % {**values, "unit": membership.unit.name, "target": target_name})
        return True, str(unit_texts.APPOINTED % values)

    def _lock_with(self, other: int):
        """Sperrt das eigene Konto und das Konto `other` bis zum Ende der Transaktion, immer nach Nummer geordnet.

        Die feste Reihenfolge verhindert, dass sich zwei Anfragen gegenseitig blockieren, etwa wenn
        Wanda und Willi sich gleichzeitig entfernen (CV5). Gibt das eigene Konto frisch aus der
        Datenbank zurück, also auch eine inzwischen gesetzte Sperre: Für ein gesperrtes Konto gibt
        `Rights` keine Rechte. Gibt es das Konto nicht mehr, ist das Ergebnis None, ebenso ohne Rechte.
        """
        users = get_user_model().objects.select_for_update().filter(pk__in={self.user.pk, other}).order_by("pk")
        return {user.pk: user for user in users}.get(self.user.pk)

    # Personen einer Organisation und „Person aufnehmen“ (#285, Teil 1 von #65)

    def members(self, unit: Unit | None) -> list:
        """Die direkten Mitglieder einer Organisation im eigenen Bereich, mit ihren Leitungsrollen (#65, Frage 8).

        Nur Personen, deren Daten die Person ohnehin sieht (`persons()`, BER-01, Grund 2); außerhalb
        des eigenen Bereichs, auch auf der Kette nach oben, ist die Liste leer. Mitglieder der
        Organisationen darunter stehen auf deren Seite. Die Leitungsrollen jeder Person stehen in
        `lead_roles`, mit ihren Organisationen vorab geladen, damit die Liste nicht je Person die
        Datenbank fragt (PG8). Gesperrte Konten stehen dabei, wie gesperrte Leitungen (#189, Frage B).
        """
        if unit is None or not self.sees_organisation() or unit.pk not in self.area:
            return []
        direct = Role.objects.filter(kind=R.MEMBER, unit_id=unit.pk).values("user_id")
        leads = Prefetch("roles", queryset=Role.objects.filter(kind__in=LEADS_IN_UNITS).select_related("unit"),
                         to_attr="lead_roles")
        return list(self.persons().filter(pk__in=direct).prefetch_related(leads))

    def may_admit(self, unit: Unit | None) -> bool:
        """Darf die Person in diese Organisation Personen mit Konto aufnehmen (PK-17, PK-26, EH-18)?

        Nur die Leitung der Organisation selbst und, solange dort keine Leitung mit Konto ist, die
        einspringende Leitung darüber (`leads_unit()`); in Organisationen darunter nicht. Die
        Verbandsleitung, das DPV-Veranstaltungsteam, Mitglieder und Admins leiten keine
        Organisation und nehmen niemanden auf (PK-23). Die automatische Mitgliedschaft beim
        Benennen als Leitung (#89) läuft über `appoint()`, nicht hier.
        """
        return unit is not None and self.leads_unit(unit)

    def admit(self, unit: Unit, person_key) -> tuple[bool, str]:
        """Nimmt eine Person mit Konto als Mitglied der Organisation auf; gibt zurück, ob es geklappt hat, und die Meldung.

        Ohne Recht in dieser Organisation oder mit einer Kennung, die keine erreichbare Person nennt
        (gesperrt, nie angemeldet und nicht im eigenen Bereich), ist das Ergebnis „nicht gefunden“.
        Wer schon Mitglied ist, bekommt im eigenen Bereich „… ist schon Mitglied in …“ (PG5),
        außerhalb einen Satz ohne die Organisation (PK-18, PK-16). Die Person muss nicht zustimmen;
        die Mitgliedschaft gilt sofort und steht im Protokoll (#91). Niemand nimmt sich selbst auf
        (EP-08); eine Leitung ist ohnehin schon Mitglied. Gleichzeitige Aufnahmen derselben Person
        laufen nacheinander, weil ihr Konto bis zum Ende gesperrt ist: Die zweite sieht die erste
        Mitgliedschaft (PG4). Das Recht wird unter der Sperre noch einmal geprüft, wie bei `appoint()`.
        """
        if not self.may_admit(unit) or not is_key(person_key):
            raise Http404
        users = get_user_model().objects
        with transaction.atomic():
            found = users.filter(key=person_key).values_list("pk", flat=True).first()
            if found is None:
                raise Http404
            me = self._lock_with(found)
            fresh = Rights(me)
            if not fresh.may_admit(unit):
                raise Http404
            reachable = Q(last_login__isnull=False) | Q(pk__in=fresh.persons().values("pk"))
            target = users.filter(reachable, pk=found, is_active=True).first()
            if target is None:
                raise Http404
            name = display_name(target.first_name, target.last_name, target.scout_name) or target.username
            membership = Role.objects.filter(user_id=target.pk, kind=R.MEMBER).select_related("unit").first()
            if membership is not None:
                if membership.unit_id in fresh.area or target.pk == me.pk:
                    return False, str(unit_texts.ALREADY_MEMBER % {"person": name, "unit": unit_label(membership.unit)})
                return False, str(unit_texts.OTHER_ORGANISATION)
            if target.pk == me.pk:
                raise Http404
            Role(user=target, kind=R.MEMBER, unit=unit).save(by=me)
        return True, str(unit_texts.ADMITTED % {"person": name, "unit": unit_label(unit)})

    # Austragen und Austreten (#286, Teil 2 von #65)

    def may_expel(self, unit: Unit | None) -> bool:
        """Darf die Person Mitglieder dieser Organisation austragen (PK-21, PK-22, EH-18, EH-19)?

        Wie beim Aufnehmen nur die Leitung der Organisation selbst und, solange dort keine Leitung
        mit Konto ist, die einspringende Leitung darüber; in Organisationen darunter mit eigener
        Leitung nicht. Verbandsleitung, DPV-Veranstaltungsteam, Mitglieder und Admins leiten keine
        Organisation und tragen niemanden aus (PK-23). Auch sich selbst darf die Leitung austragen
        (Sebastian bei der Umsetzung von #286, 10.11.2026).
        """
        return unit is not None and self.leads_unit(unit)

    def _expellable(self, unit: Unit, person_key) -> Role:
        """Die Mitgliedschaft der Person mit dieser Kennung direkt in `unit`, wenn die Person dort austragen darf.

        Sonst „nicht gefunden“, auch für ein Mitglied einer Organisation darunter und für eine Person,
        die gerade ausgetragen wurde oder ausgetreten ist (PG3).
        """
        if not self.may_expel(unit) or not is_key(person_key):
            raise Http404
        found = self.person(person_key)
        membership = Role.objects.filter(user_id=found.pk, kind=R.MEMBER, unit_id=unit.pk).select_related(
            "user", "unit__parent").first()
        if membership is None:
            raise Http404
        return membership

    def expulsion(self, unit: Unit, person_key) -> dict:
        """Was der Dialog „Austragen“ zeigt; ohne Recht „nicht gefunden“ (PK-21, #65 Frage 11 und 17).

        `person` ist der Name wie in der Liste, `options` die Wahlmöglichkeiten in der Reihenfolge des
        Dialogs: „hoch“ (direkt zur Organisation darüber, nicht beim Bund) und „ganz“ (keiner
        Organisation mehr). Je Möglichkeit `target`, die Organisation danach oder None, und `endings`,
        die Leitungsrollen, die dabei enden (`_endings()`). Ändert nichts.
        """
        membership = self._expellable(unit, person_key)
        user = membership.user
        options = []
        for choice, entirely in EXPEL_CHOICES.items():
            if not entirely and unit.kind == UnitKind.ASSOCIATION:
                continue
            options.append({"value": choice, "target": after_leaving(unit, entirely),
                            "endings": self._endings(membership, unit, entirely)})
        return {"person": display_name(user.first_name, user.last_name, user.scout_name) or user.username,
                "options": options}

    def expel(self, unit: Unit, person_key, choice: str) -> str:
        """Trägt ein Mitglied der Organisation aus; gibt die kurze Meldung zurück (PK-21).

        `choice` ist „hoch“ oder „ganz“ aus `EXPEL_CHOICES`; beim Bund gibt es nur „ganz“. Jede andere
        Wahl, ohne Recht, mit einer fremden Kennung oder wenn die Mitgliedschaft schon nicht mehr in
        dieser Organisation besteht, ist das Ergebnis „nicht gefunden“, und nichts ändert sich. Es enden
        die Leitungsrollen aus `Role.ending_leads()`, jede mit Eintrag im Protokoll (#91); eine Nachricht
        gibt es nicht. Gesperrt sind das eigene Konto und das der Person, dann wird das Recht unter der
        Sperre noch einmal geprüft: Von gleichzeitigen Änderungen an derselben Mitgliedschaft gelingt
        genau eine, die zweite sieht „nicht gefunden“ (PG3).
        """
        if self.user is None or choice not in EXPEL_CHOICES or not is_key(person_key):
            raise Http404
        entirely = EXPEL_CHOICES[choice]
        if not entirely and unit.kind == UnitKind.ASSOCIATION:
            raise Http404
        with transaction.atomic():
            owner = get_user_model().objects.filter(key=person_key).values_list("pk", flat=True).first()
            if owner is None:
                raise Http404
            me = self._lock_with(owner)
            membership = Rights(me)._expellable(unit, person_key)
            user = membership.user
            name = display_name(user.first_name, user.last_name, user.scout_name) or user.username
            if not membership.leave(unit, by=me, entirely=entirely):
                raise Http404
        return str(unit_texts.EXPELLED % {"person": name, "unit": unit_label(unit)})

    # Verschieben (#287, Teil 3 von #65)

    def may_move(self, unit: Unit | None) -> bool:
        """Darf die Person Mitglieder dieser Organisation in eine Organisation direkt darunter verschieben (PK-19)?

        Wie beim Austragen nur die Leitung der Organisation selbst und, solange dort keine Leitung mit
        Konto ist, die einspringende Leitung darüber (PK-20, EH-18, EH-19); nur dort, wo es eine
        Organisation darunter gibt, also nie bei einer Gruppe (PV5). Auch sich selbst darf die Leitung
        so verschieben (EP-10, #65 Frage 6). Alle ohne Leitungsrolle verschieben niemanden (PK-23).
        """
        return unit is not None and self.leads_unit(unit) and bool(self._children.get(unit.pk))

    def _movable(self, unit: Unit, person_key) -> Role:
        """Die Mitgliedschaft der Person mit dieser Kennung direkt in `unit`, wenn die Person dort verschieben darf.

        Sonst „nicht gefunden“, auch für ein Mitglied einer Organisation darunter oder darüber und für
        eine Person, die gerade verschoben oder ausgetragen wurde.
        """
        if not self.may_move(unit) or not is_key(person_key):
            raise Http404
        found = self.person(person_key)
        membership = Role.objects.filter(user_id=found.pk, kind=R.MEMBER, unit_id=unit.pk).select_related(
            "user", "unit__parent").first()
        if membership is None:
            raise Http404
        return membership

    @staticmethod
    def move_targets(unit: Unit) -> list[Unit]:
        """Die Organisationen direkt unter `unit`, nach dem Alphabet: die einzigen Ziele beim Verschieben (PK-20)."""
        return sorted(Unit.objects.filter(parent_id=unit.pk).select_related("parent"),
                      key=lambda entry: alphabetical(unit_label(entry)))

    def moving(self, unit: Unit, person_key) -> dict:
        """Was der Dialog „Verschieben“ zeigt; ohne Recht „nicht gefunden“ (PK-19, PK-20).

        `person` ist der Name wie in der Liste, `targets` die Organisationen direkt darunter. Ändert nichts.
        """
        user = self._movable(unit, person_key).user
        return {"person": display_name(user.first_name, user.last_name, user.scout_name) or user.username,
                "targets": self.move_targets(unit)}

    def move(self, unit: Unit, person_key, target_key) -> tuple[bool, str]:
        """Verschiebt ein Mitglied von `unit` in eine Organisation direkt darunter; gibt zurück, ob es geklappt hat, und die Meldung.

        Das Ziel kommt nur aus den Organisationen direkt unter `unit` (PK-20, PV9); jedes andere Ziel,
        ohne Recht, mit einer fremden Kennung oder wenn die Mitgliedschaft schon nicht mehr in `unit`
        besteht, ist „nicht gefunden“, und nichts ändert sich. Läge danach eine Leitungsrolle der
        Person nicht mehr auf ihrem Pfad, lehnt das Tool ab und nennt die Rollen (PK-25, #65 N4);
        Leitungsrollen enden beim Verschieben nie. Der Wechsel steht im Protokoll (#91). Gesperrt sind
        das eigene Konto und das der Person, dann wird das Recht unter der Sperre noch einmal geprüft:
        Von gleichzeitigen Änderungen an derselben Mitgliedschaft gelingt genau eine.
        """
        if self.user is None or not is_key(person_key) or not is_key(target_key):
            raise Http404
        with transaction.atomic():
            owner = get_user_model().objects.filter(key=person_key).values_list("pk", flat=True).first()
            if owner is None:
                raise Http404
            me = self._lock_with(owner)
            membership = Rights(me)._movable(unit, person_key)
            target = next((entry for entry in self.move_targets(unit) if entry.key == target_key), None)
            if target is None:
                raise Http404
            user = membership.user
            name = display_name(user.first_name, user.last_name, user.scout_name) or user.username
            blocking = membership.leads_outside(target)
            if blocking:
                roles = [str(unit_texts.ROLE_OF % {"role": lead.get_kind_display(), "unit": unit_label(lead.unit)})
                         for lead in blocking]
                text = unit_texts.MOVE_ROLE_DOES_NOT_FIT if len(roles) == 1 else unit_texts.MOVE_ROLES_DO_NOT_FIT
                return False, str(text % {"person": name, "roles": listed(roles), "target": unit_label(target)})
            membership.unit = target
            membership.save(by=me)
        return True, str(unit_texts.MOVED % {"person": name, "unit": unit_label(target)})

    def own_membership(self) -> Role | None:
        """Die eigene Mitgliedschaft, frisch gelesen, mit den Organisationen darüber; sonst None (EP-06)."""
        if self.user is None:
            return None
        return Role.objects.filter(user_id=self.user.pk, kind=R.MEMBER).select_related(
            "unit__parent__parent__parent__parent").first()

    def exit_options(self) -> tuple[Role, list[dict]] | None:
        """Was der Dialog „Austreten“ zeigt: die eigene Mitgliedschaft und die Ebenen der eigenen Kette (EP-06).

        Von der eigenen Organisation bis zum Bund, je mit `level`, `target` (die Organisation danach
        oder None) und `endings` wie beim Austragen. Ohne Mitgliedschaft None. Ändert nichts.
        """
        membership = self.own_membership()
        if membership is None:
            return None
        return membership, [{"level": level, "target": after_leaving(level, False),
                             "endings": self._endings(membership, level, False)} for level in _chain_of(membership)]

    def leave_own(self, level_key, from_key) -> str:
        """Tritt aus `level_key` aus, einer Organisation der eigenen Kette; gibt die kurze Meldung zurück (EP-06).

        Austreten gilt nur für die angemeldete Person: Die Mitgliedschaft kommt nie aus der Anfrage
        (EP-07). `from_key` ist die Organisation der Mitgliedschaft, wie der Dialog sie gezeigt hat;
        hat sie sich inzwischen geändert, etwa weil eine Leitung die Person gerade ausgetragen hat, ist
        das Ergebnis „nicht gefunden“, und nichts ändert sich (PG3). Eine Ebene außerhalb der eigenen
        Kette, auch eine manipulierte, ist ebenso „nicht gefunden“ (PG6). Urheber im Protokoll ist die
        Person selbst.
        """
        if self.user is None or not is_key(level_key) or not is_key(from_key):
            raise Http404
        with transaction.atomic():
            me = self._lock_with(self.user.pk)
            membership = Rights(me).own_membership()
            if membership is None or membership.unit.key != from_key:
                raise Http404
            level = next((entry for entry in _chain_of(membership) if entry.key == level_key), None)
            if level is None or not membership.leave(level, by=me):
                raise Http404
        return str(unit_texts.LEFT % {"unit": unit_label(level)})

    def _endings(self, membership: Role, left: Unit, entirely: bool) -> list[dict]:
        """Die Leitungsrollen, die enden, wenn `membership` `left` verlässt, für die Vorschau (ROL-01, #191).

        Je Rolle `role` (die Rolle selbst) und `last`: Danach hat ihre Organisation keine Leitung mit
        Konto mehr; gesperrte Leitungen zählen dabei nicht, wie beim Entfernen (C12). Dann nennt
        `cover` die Organisation, deren Leitung einspringt, oder None (EH-18, EH-27); Organisationen,
        die durch dieselbe Änderung ihre letzte Leitung verlieren, springen dabei nicht ein.
        """
        ending = membership.ending_leads(left, entirely)
        found = []
        for role in ending:
            others = Role.objects.filter(unit_id=role.unit_id, kind=role.kind, user__is_active=True)
            found.append({"role": role, "last": not others.exclude(pk=role.pk).exists()})
        emptied = frozenset(entry["role"].unit_id for entry in found if entry["last"])
        for entry in found:
            cover = self._lead_above(entry["role"].unit_id, without=emptied) if entry["last"] else None
            entry["cover"] = Unit.objects.get(pk=cover) if cover is not None else None
        return found

    # Verwaltete Personen (#117, PER-02)

    def _managed_entries(self) -> QuerySet:
        """Die verwalteten Personen, die die Person sieht und bearbeiten darf: alle im eigenen Bereich (VP-02).

        Wie bei Personen mit Konto (BER-01, Grund 2): die Gruppenleitung in ihrer Gruppe, die
        Stammesleitung im ganzen Stamm, Ring- und Bundesleitung alles darunter. Ohne Leitungsrolle von
        Gruppe bis Bund keine, also auch nicht die Verbandsleitung, das DPV-Veranstaltungsteam,
        Mitglieder, Konten ohne Zuordnung und Admins (VP-06). Wer eine Person angelegt hat, zählt nicht
        (VP-05, #89). Gefiltert wird in der Datenbank, wie bei `persons()`.
        """
        if not self.sees_organisation():
            return ManagedPerson.objects.none()
        return ManagedPerson.objects.filter(unit_id__in=self.area)

    def managed_in(self, unit: Unit | None) -> list[ManagedPerson]:
        """Die direkten verwalteten Personen einer Organisation im eigenen Bereich; sonst keine (#117, Frage 1).

        Die einer Organisation darunter stehen auf deren Seite. Eine Abfrage, egal wie viele es sind (MG9).
        """
        if unit is None:
            return []
        return list(self._managed_entries().filter(unit_id=unit.pk))

    def may_add_managed(self, unit: Unit | None) -> bool:
        """Darf die Person in dieser Organisation eine verwaltete Person anlegen (VP-01, VP-17, EH-18)?

        Wie beim Aufnehmen nur die Leitung der Organisation selbst und, solange dort keine Leitung mit
        Konto ist, die einspringende Leitung darüber (`leads_unit()`); in Organisationen darunter nicht.
        Im Verband nie (#88); dort leitet ohnehin niemand eine Organisation.
        """
        return unit is not None and unit.kind != UnitKind.FEDERATION and self.leads_unit(unit)

    def managed_person(self, unit: Unit, person_key) -> ManagedPerson:
        """Eine verwaltete Person direkt in `unit` über ihre Kennung; ohne Recht „nicht gefunden“ (VP-03).

        Eine Person, die zu einer anderen Organisation gehört, ist hier ebenso „nicht gefunden“, auch
        im eigenen Bereich: Die Organisation der Adresse muss stimmen (MV4). Kennungen von Personen mit
        Konto finden hier nie etwas (MV5).
        """
        return self.entry(self._managed_entries().filter(unit_id=unit.pk), person_key)

    def add_managed(self, unit: Unit, values: dict, creation_key) -> str:
        """Legt eine verwaltete Person in `unit` an; gibt die kurze Meldung zurück, leer, wenn es sie schon gibt (VP-01).

        `values` sind die geprüften Angaben aus `ManagedPersonForm`; die Organisation kommt nur aus der
        Adresse (MV4). `creation_key` ist die Kennung des Dialogs: Schickt jemand denselben Dialog zweimal
        ab, etwa mit einem Doppelklick, auch gleichzeitig, bleibt es bei einer Person, und die zweite
        Antwort hat keine Meldung (MG7). Ohne Recht oder mit einer Kennung in falscher Form „nicht
        gefunden“. Gesperrt ist das eigene Konto, und das Recht wird darunter frisch geprüft: Endet das
        Einspringen, während der Dialog offen ist, wird niemand angelegt (MW3).

        Ohne `values["consent"]` legt es niemanden an (DSG-02, #98). Die Bestätigung trägt das eigene Konto
        und die Uhrzeit des Servers, nie Angaben aus dem Formular (VP-11), und steht in derselben Zeile wie
        die Person: Beides wird zusammen gespeichert oder gar nicht (EG1).
        """
        if not self.may_add_managed(unit) or not is_key(creation_key):
            raise Http404
        if values.get("consent") is not True:
            raise ValidationError(person_texts.CONSENT_MISSING, code="consent")
        with transaction.atomic():
            me = self._lock_with(self.user.pk)
            if not Rights(me).may_add_managed(unit):
                raise Http404
            if ManagedPerson.objects.filter(creation_key=creation_key).exists():
                return ""
            created = ManagedPerson(unit=unit, creation_key=creation_key, consent_by=me, consent_at=timezone.now(),
                                    **{name: values[name] for name in EDITABLE_FIELDS})
            try:
                with transaction.atomic():
                    created.save()
            except IntegrityError:
                # Derselbe Dialog wurde gleichzeitig ein zweites Mal abgeschickt (MG7).
                if ManagedPerson.objects.filter(creation_key=creation_key).exists():
                    return ""
                raise
        return str(person_texts.ADDED % {"person": created.display_name, "unit": unit_label(unit)})

    def edit_managed(self, unit: Unit, person_key, values: dict, version) -> tuple[bool, ManagedPerson, str]:
        """Speichert die Angaben einer verwalteten Person; gibt zurück, ob es geklappt hat, die Person und die Meldung (VP-02).

        `version` ist der Stand, den der Dialog beim Öffnen gezeigt hat. Hat inzwischen jemand anderes
        gespeichert, wird nichts überschrieben: Das Ergebnis ist „nicht geklappt“ mit der Person, wie sie
        jetzt ist, und dem Satz „… wurde inzwischen von jemand anderem geändert. …“ (MG6). Ohne Recht, mit
        einer fremden Kennung oder einer Person einer anderen Organisation „nicht gefunden“ (VP-03, MV4,
        MV5). Gesperrt sind das eigene Konto und die Person, und das Recht wird darunter frisch geprüft:
        Wer gerade als Leitung entfernt wurde, speichert nichts mehr, auch im schon offenen Dialog (MW1,
        VP-04); von zwei gleichzeitigen Änderungen gelingt genau eine.
        """
        if self.user is None or not is_key(person_key):
            raise Http404
        with transaction.atomic():
            me = self._lock_with(self.user.pk)
            fresh = Rights(me)
            entry = fresh.entry(fresh._managed_entries().filter(unit_id=unit.pk).select_for_update(), person_key)
            if str(entry.version) != str(version):
                return False, entry, str(person_texts.CHANGED_MEANWHILE % {"person": entry.display_name})
            for name in EDITABLE_FIELDS:
                setattr(entry, name, values[name])
            entry.version += 1
            entry.save()
        return True, entry, str(person_texts.SAVED % {"person": entry.display_name})

    # Leitungen entfernen und die eigene Rolle abgeben (#191)

    def may_remove(self, role: Role) -> bool:
        """Darf die Person diese Rolle entfernen oder, wenn es ihre eigene ist, abgeben (RO-10, RO-11, RO-20)?

        Nur Leitungsrollen von Gruppe bis Bund in ihrem Bereich, also genau dort, wo sie benennen
        darf (`may_appoint()`), auch bei gesperrten Konten (RO-21). Die eigenen Leitungsrollen liegen
        immer im eigenen Bereich. Mitgliedschaften, Verbandsleitung, DPV-Veranstaltungsteam und Admin
        entfernt diese Stelle nie (CV3, CV8, RO-18, RO-19).
        """
        return role.kind in LEADS_IN_UNITS and self.sees_organisation() and role.unit_id in self.area

    def _removable(self, unit: Unit, role_key) -> Role:
        """Die Rolle mit dieser Kennung in genau dieser Einheit, wenn die Person sie entfernen darf; sonst „nicht gefunden“ (CV3)."""
        return self.entry(Role.objects.filter(unit_id=unit.pk).select_related("user"), role_key, allowed=self.may_remove)

    def removal(self, unit: Unit, role_key) -> dict:
        """Was die Bestätigung zum Entfernen oder Abgeben zeigt (C1 bis C6, C11, C12).

        `person` ist der Name wie in der Meldung nach dem Benennen, `is_self` sagt, ob es die eigene
        Rolle ist. `last` heißt: Danach hat die Einheit keine Leitung mit Konto mehr; gesperrte
        Leitungen zählen dabei nicht (C12). Dann nennt `cover` die interne Nummer der Einheit,
        deren Leitung einspringt, oder None (EH-18, EH-27); Seiten zeigen nur ihren Namen.
        """
        return self._describe(self._removable(unit, role_key))

    def _describe(self, role: Role) -> dict:
        user = role.user
        others = Role.objects.filter(unit_id=role.unit_id, kind=role.kind, user__is_active=True).exclude(pk=role.pk)
        last = not others.exists()
        return {
            "person": display_name(user.first_name, user.last_name, user.scout_name) or user.username,
            "is_self": user.pk == self.user.pk,
            "role": role.get_kind_display(),
            "last": last,
            "cover": self._lead_above(role.unit_id) if last else None,
        }

    def remove(self, unit: Unit, role_key) -> str:
        """Entfernt die Leitungsrolle oder gibt die eigene ab; gibt die kurze Meldung zurück (C13).

        Ohne Recht, mit einer fremden Kennung oder wenn die Rolle schon entfernt ist, ist das Ergebnis
        „nicht gefunden“, und nichts ändert sich. Die Mitgliedschaft bleibt immer (C7, CV8, #89). Die
        Änderung steht im Protokoll, eine Nachricht gibt es nicht (#91, ROL-04). Gesperrt sind das
        eigene Konto und das der Person mit der Rolle, dann wird das Recht unter der Sperre noch einmal
        geprüft: Entfernen sich zwei Leitungen gleichzeitig gegenseitig, gelingt nur die erste
        Änderung (CV5); entfernen zwei dieselbe Leitung, sieht die zweite „nicht gefunden“ (CV6).
        """
        if self.user is None or not is_key(role_key):
            raise Http404
        with transaction.atomic():
            owner = Role.objects.filter(key=role_key).values_list("user_id", flat=True).first()
            if owner is None:
                raise Http404
            me = self._lock_with(owner)
            fresh = Rights(me)
            role = fresh._removable(unit, role_key)
            shown = fresh._describe(role)
            role.delete(by=me)
        values = {**shown, "unit": unit.name}
        return str((unit_texts.GAVE_UP if shown["is_self"] else unit_texts.REMOVED) % values)

    # Organisationen anlegen und bearbeiten (#95, ORG-06)

    def may_create(self, parent: Unit | None) -> bool:
        """Darf die Person unter `parent` eine Organisation anlegen (EH-10 bis EH-13, EH-18, EH-19)?

        Gruppen in jedem Stamm des eigenen Bereichs: die Stammesleitung, die Ringleitung im ganzen
        Ring, die Bundesleitung im ganzen Bund. Stämme in einem Ring nur die Leitung des Rings
        selbst oder, solange er keine Leitung mit Konto hat, die einspringende Bundesleitung. Ringe
        und, in einem Bund ohne Ringe, Stämme nur die Bundesleitung. Unter einer Gruppe und im
        Verband entsteht nichts; Verbandsleitung, Team, Mitglieder und Admins leiten keine Organisation.
        """
        kind = child_kind(parent)
        if kind is None or not self.sees_organisation():
            return False
        if kind == UnitKind.GROUP:
            return parent.pk in self.area
        if parent.kind == UnitKind.RING:
            return self.leads_unit(parent)
        return parent.pk in self._led

    def create(self, parent: Unit, name: str) -> tuple[bool, str]:
        """Legt unter `parent` eine Organisation der Art aus `child_kind()` an; gibt zurück, ob es geklappt hat, und die Meldung.

        Art und Organisation darüber kommen nur aus der Adresse, nie aus dem Formular (OV1, OV4).
        Ohne Recht „nicht gefunden“. Gibt es den Namen dort schon, nennt die Meldung die vorhandene
        Organisation (OG1, OG2); legen zwei gleichzeitig denselben Namen an, entsteht genau eine.
        Das Anlegen steht im Protokoll der Strukturänderungen (#131). Gesperrt sind das eigene Konto,
        der Bund und die Organisation darüber, dann wird das Recht frisch geprüft.
        """
        if not self.may_create(parent):
            raise Http404
        with transaction.atomic():
            me = self._lock_with(self.user.pk)
            # Erst den Bund sperren, dann das Recht prüfen: Ein gleichzeitiger Ringwechsel ist danach
            # entweder schon gespeichert oder wartet (unabhängige Prüfung, Befund 2).
            parent = self._lock_structure(parent)
            if not Rights(me).may_create(parent):
                raise Http404
            created = Unit(kind=child_kind(parent), name=name, parent=parent)
            refused = _saved_or_reason(created, me)
        if refused:
            return False, refused
        return True, str(unit_texts.CREATED % {"unit": unit_label(created)})

    def may_rename(self, unit: Unit | None) -> bool:
        """Darf die Person diese Organisation umbenennen (EH-14, EH-15, EH-20)?

        Jede Leitung ihre eigene Organisation und alle darunter, die Bundesleitung auch ihren Bund;
        also genau der eigene Bereich. Den Verband und fremde Bünde benennt niemand im Tool um.
        """
        return unit is not None and self.sees_organisation() and unit.pk in self.area

    def rename(self, unit: Unit, name: str) -> tuple[bool, str]:
        """Benennt eine Organisation um; gibt zurück, ob es geklappt hat, und die Meldung (EH-14). Wie `edit()`."""
        return _done_or_refused(self.edit(unit, name=name))

    def may_change_ring(self, troop: Unit | None) -> bool:
        """Darf die Person diesen Stamm einem Ring zuordnen oder in einen anderen Ring wechseln (EH-16, EH-17)?

        Nur die Bundesleitung des Bundes, nur in einem Bund mit Ringen und nur, wenn es einen
        anderen Ring gibt. Ringleitungen, Stammesleitungen und alle anderen nie.
        """
        if troop is None or troop.kind != UnitKind.TROOP or not self.sees_organisation():
            return False
        if troop.association_id not in self._led or not self.ring_targets(troop):
            return False
        return Unit.objects.filter(pk=troop.association_id, has_rings=True).exists()

    @staticmethod
    def rings_of(troop: Unit) -> list[Unit]:
        """Alle Ringe des Bundes eines Stammes nach dem Alphabet, der jetzige eingeschlossen: die Wahl im Dialog (#95)."""
        rings = Unit.objects.filter(kind=UnitKind.RING, parent_id=troop.association_id)
        return sorted(rings, key=lambda ring: alphabetical(ring.name))

    @staticmethod
    def ring_targets(troop: Unit) -> list[Unit]:
        """Die Ringe des Bundes außer dem jetzigen, nach dem Alphabet: die einzigen Ziele (EH-16, EH-26)."""
        rings = Unit.objects.filter(kind=UnitKind.RING, parent_id=troop.association_id).exclude(pk=troop.parent_id)
        return sorted(rings, key=lambda ring: alphabetical(ring.name))

    def change_ring(self, troop: Unit, ring_key) -> tuple[bool, str]:
        """Ordnet einen Stamm einem Ring zu oder wechselt ihn; gibt zurück, ob es geklappt hat, und die Meldung (EH-16). Wie `edit()`."""
        if not is_key(ring_key):
            raise Http404
        return _done_or_refused(self.edit(troop, ring_key=ring_key))

    def may_introduce_rings(self, unit: Unit | None) -> bool:
        """Darf die Person für diesen Bund „hat Ringe“ einschalten (EH-23, EH-24)? Nur die eigene Bundesleitung, nur einmal."""
        return (unit is not None and unit.kind == UnitKind.ASSOCIATION and not unit.has_rings
                and self.sees_organisation() and unit.pk in self._led)

    def edit(self, unit: Unit, name: str | None = None, ring_key: str | None = None, rings_on: bool = False) -> dict:
        """Speichert den Dialog „… bearbeiten“: Name, Ring und „hat Ringe“, alles zusammen oder nichts (#95).

        Ohne Recht, die Organisation umzubenennen, ist das Ergebnis „nicht gefunden“ (EH-15). Ändert
        die Anfrage etwas, das die Person nicht ändern darf, etwa den Ring als Ringleitung oder „hat
        Ringe“ in einem fremden Bund, ebenso, und nichts ändert sich (OV6, OV8). `None` und ein
        ausgeschalteter Schalter heißen „bleibt“; ausschalten lässt sich „hat Ringe“ nie (EH-25). Als
        Ring zählen nur `ring_targets()` und der jetzige Ring; „" heißt ohne Ring und geht nur, solange
        der Stamm keinen hat (EH-26, OV9).

        Gelesen und das Recht geprüft wird unter der Sperre (Konto, Bund, Organisation) frisch,
        geschrieben nur, was sich ändert (OG4). Gibt `{"messages": [...], "errors": {...}}` zurück: je Änderung die kurze
        Meldung, bei einer Ablehnung je Feld („name“, „ring“) der Grund; dann ist nichts gespeichert,
        auch nicht die übrigen Änderungen.
        """
        if not self.may_rename(unit) or (ring_key not in (None, "") and not is_key(ring_key)):
            raise Http404
        with transaction.atomic():
            me = self._lock_with(self.user.pk)
            current = self._lock_structure(unit)
            fresh = Rights(me)
            if not fresh.may_rename(current):
                raise Http404
            target = fresh._ring_target(current, ring_key)
            if rings_on and not current.has_rings and not fresh.may_introduce_rings(current):
                raise Http404
            saved = transaction.savepoint_create()
            result = _apply_edit(current, me, name, target, rings_on and not current.has_rings)
            if result["errors"]:
                transaction.savepoint_rollback(saved)
        return result

    def _ring_target(self, troop: Unit, ring_key: str | None) -> Unit | None:
        """Der neue Ring aus der Anfrage, oder None, wenn er bleibt; ohne Recht oder fremd „nicht gefunden“."""
        if ring_key is None or troop.kind != UnitKind.TROOP:
            if ring_key not in (None, ""):
                raise Http404
            return None
        now = troop.parent.key if troop.parent.kind == UnitKind.RING else ""
        if ring_key == now:
            return None
        if not self.may_change_ring(troop):
            raise Http404
        target = next((ring for ring in self.ring_targets(troop) if ring.key == ring_key), None)
        if target is None:
            raise Http404
        return target

    def _lock_structure(self, unit: Unit) -> Unit:
        """Sperrt den Bund der Organisation und dann sie selbst; gibt sie frisch zurück (#95).

        Dieselbe Reihenfolge wie beim Speichern einer Rolle oder Einheit: Konten, Bund, Einheit.
        """
        bund = self._association_of(unit.pk)
        if bund is not None:
            list(Unit.objects.select_for_update().filter(pk=bund).values_list("pk"))
        list(Unit.objects.select_for_update().filter(pk=unit.pk).values_list("pk"))
        return Unit.objects.select_related("parent").get(pk=unit.pk)

    # Seite „Verband“ der Verbandsleitung (#94)

    def appoint_in_federation(self, kind: str, unit: Unit, person_key) -> tuple[bool, str, dict]:
        """Benennt als Verbandsleitung eine Bundesleitung, Verbandsleitung oder ein Teammitglied (RO-15).

        Gibt zurück, ob es geklappt hat, die Meldung und die Werte für sie. `unit` ist der Bund
        (Bundesleitung) oder der Verband (Verbandsleitung, DPV-Veranstaltungsteam); passt beides
        nicht zusammen, ist das Ergebnis „nicht gefunden“, ebenso ohne Rolle Verbandsleitung und für
        Konten, die nie angemeldet oder gesperrt sind. Abgelehnt mit Meldung wird, wer sich selbst
        benennen will (RO-12, RO-16), wer die Rolle schon hat und wer als Bundesleitung nicht auf
        seinem Leitungspfad läge (#89), ohne dessen Organisation zu nennen (PK-16). Gesperrt sind
        das eigene Konto und das der Person; das Recht wird unter der Sperre noch einmal geprüft, wie
        bei `appoint()`.
        """
        if not self._federation_target(kind, unit) or not is_key(person_key):
            raise Http404
        users = get_user_model().objects
        with transaction.atomic():
            found = users.filter(key=person_key).values_list("pk", flat=True).first()
            if found is None:
                raise Http404
            me = self._lock_with(found)
            if not Rights(me).is_federation_lead():
                raise Http404
            target = users.filter(pk=found, is_active=True, last_login__isnull=False).first()
            if target is None:
                raise Http404
            values = {"person": display_name(target.first_name, target.last_name, target.scout_name) or target.username,
                      "role": Role.Kind(kind).label, "unit": unit.name}
            if target.pk == me.pk:
                return False, str(unit_texts.NOT_YOURSELF_FEDERATION), values
            if Role.objects.filter(user_id=target.pk, kind=kind, unit_id=unit.pk).exists():
                return False, str(unit_texts.FEDERATION_ALREADY[kind] % values), values
            try:
                Role(user=target, kind=kind, unit=unit).save(by=me)
            except ValidationError as error:
                if error.error_list[0].code not in ("outside_path", "second_membership"):
                    raise
                return False, str(unit_texts.MEMBER_ELSEWHERE), values
        return True, str(unit_texts.FEDERATION_APPOINTED[kind] % values), values

    def _federation_target(self, kind: str, unit: Unit | None) -> bool:
        """Passt die Rolle zur Organisation, und darf die Person dort als Verbandsleitung benennen?"""
        if unit is None or not self.is_federation_lead():
            return False
        if kind == R.ASSOCIATION_LEAD:
            return unit.kind == UnitKind.ASSOCIATION
        return kind in (R.FEDERATION_LEAD, R.EVENT_TEAM) and unit.kind == UnitKind.FEDERATION

    def may_remove_in_federation(self, role: Role) -> bool:
        """Darf die Person diese Rolle auf der Seite „Verband“ entfernen oder, wenn es ihre ist, abgeben (RO-15, RO-20)?

        Nur als Verbandsleitung und nur Bundesleitungen, Verbandsleitungen und Mitglieder des
        DPV-Veranstaltungsteams, auch mit gesperrtem Konto. Leitungen von Ringen, Stämmen und
        Gruppen, Mitgliedschaften und Admin nie (RO-17, RO-19).
        """
        return role.kind in SEEN_BY_FEDERATION_LEAD and self.is_federation_lead()

    def _removable_in_federation(self, role_key) -> Role:
        roles = Role.objects.filter(kind__in=SEEN_BY_FEDERATION_LEAD).select_related("user", "unit")
        return self.entry(roles, role_key, allowed=self.may_remove_in_federation)

    def removal_in_federation(self, role_key) -> tuple[Role, dict]:
        """Die Rolle und was die Bestätigung zeigt, wie `removal()`; ohne Recht „nicht gefunden“."""
        role = self._removable_in_federation(role_key)
        return role, self._describe(role)

    def remove_in_federation(self, role_key) -> tuple[Role, dict]:
        """Entfernt die Rolle auf der Seite „Verband“ oder gibt die eigene ab; gibt Rolle und Beschreibung zurück.

        Wie `remove()`: ohne Recht oder wenn die Rolle schon weg ist „nicht gefunden“; gleichzeitiges
        gegenseitiges Entfernen gelingt nur einmal (VG1), weil beide Konten gesperrt und die Rechte
        danach frisch geprüft werden. Die Mitgliedschaft einer Bundesleitung bleibt (#89).
        """
        if self.user is None or not is_key(role_key):
            raise Http404
        with transaction.atomic():
            owner = Role.objects.filter(key=role_key).values_list("user_id", flat=True).first()
            if owner is None:
                raise Http404
            me = self._lock_with(owner)
            fresh = Rights(me)
            role = fresh._removable_in_federation(role_key)
            shown = fresh._describe(role)
            role.delete(by=me)
        return role, shown

    def own_team_role(self) -> Role | None:
        """Die eigene Rolle im DPV-Veranstaltungsteam, frisch gelesen; sonst None (RO-20, „Mein Profil“)."""
        if self.user is None:
            return None
        return Role.objects.filter(user_id=self.user.pk, kind=R.EVENT_TEAM).first()

    def leave_team(self) -> bool:
        """Gibt die eigene Rolle im DPV-Veranstaltungsteam ab; False, wenn es keine (mehr) gibt (RO-20)."""
        if self.user is None:
            return False
        with transaction.atomic():
            me = self._lock_with(self.user.pk)
            role = Rights(me).own_team_role()
            if role is None:
                return False
            role.delete(by=me)
        return True

    # Leitungen (BER-01, Grund 3)

    def leads(self) -> QuerySet:
        """Name und Rolle der Leitungen, die die Person sieht, ohne Mail (RO-01 bis RO-03, RO-05).

        Das sind die Leitungen der Einheiten auf ihrer Kette nach oben und in ihrem Bereich, für
        die Verbandsleitung außerdem Bundesleitungen, Verbandsleitungen und das
        DPV-Veranstaltungsteam. Jeder Eintrag enthält nur die Felder aus `LEAD_FIELDS` und `LEAD_NAMES`.

        Leitungen mit im Tool gesperrtem Konto stehen nur dabei, wo die Person Leitungen entfernen
        darf, also in ihrem Bereich (RO-10, RO-11), gekennzeichnet mit `locked`; alle anderen
        erfahren nichts von der Sperre (#189, Frage B). Die Verbandsleitung sieht außerdem
        gesperrte Bundesleitungen, Verbandsleitungen und Mitglieder des DPV-Veranstaltungsteams,
        wie vor #189; gesperrte Leitungen von Ringen, Stämmen und Gruppen außerhalb ihres Bereichs
        nicht mehr. Was sie davon zeigt, regelt die Seite „Verband“ (#94).
        """
        if self.user is None:
            return Role.objects.none().values(*LEAD_FIELDS, **LEAD_NAMES)
        seen = Q(kind__in=LEADS_IN_UNITS, unit_id__in=self.chain | self.area)
        locked_seen = Q(unit_id__in=self.area)
        if any(kind == R.FEDERATION_LEAD for kind, _unit in self._own_roles):
            seen |= Q(kind__in=SEEN_BY_FEDERATION_LEAD)
            locked_seen |= Q(kind__in=SEEN_BY_FEDERATION_LEAD)
        leads = Role.objects.filter(seen).exclude(Q(user__is_active=False) & ~locked_seen)
        order = ("unit__name", "kind", "user__last_name", "user__first_name", "user__username")
        return leads.order_by(*order).values(*LEAD_FIELDS, **LEAD_NAMES)

    # Leitung einer Einheit

    def covers(self, unit: Unit | None) -> bool:
        """Springt die Person für diese Einheit ein, weil sie keine Leitung mit Konto hat (EH-18)?"""
        return unit is not None and unit.pk in self._covered

    def leads_unit(self, unit: Unit | None) -> bool:
        """Hat die Person in dieser Einheit die Rechte einer Leitung, selbst oder einspringend?

        Rechte, die nur die Leitung der Einheit selbst hat, hat die Leitung darüber nur dann,
        wenn sie einspringt (EH-19).
        """
        return unit is not None and (unit.pk in self._led or unit.pk in self._covered)

    def leads_unit_of(self, person) -> bool:
        """Ist die Person Leitung der eigenen Einheit von `person`, selbst oder einspringend (PK-21, PK-22)?"""
        if person is None or getattr(person, "pk", None) is None:
            return False
        membership = Role.objects.filter(user_id=person.pk, kind=R.MEMBER).select_related("unit").first()
        return membership is not None and self.leads_unit(membership.unit)


# Was unter jeder Ebene angelegt wird (#95); unter einem Bund hängt es an „hat Ringe“ (#88).
CHILD_KINDS = {UnitKind.RING: UnitKind.TROOP, UnitKind.TROOP: UnitKind.GROUP}


def child_kind(parent: Unit | None) -> str | None:
    """Die Art einer neuen Organisation unter `parent`: im Bund Ringe oder Stämme, im Ring Stämme, im Stamm Gruppen."""
    if parent is None:
        return None
    if parent.kind == UnitKind.ASSOCIATION:
        return UnitKind.RING if parent.has_rings else UnitKind.TROOP
    return CHILD_KINDS.get(parent.kind)


def _saved_or_reason(unit: Unit, by, **options) -> str:
    """Speichert die Organisation; gibt bei Ablehnung den Grund für die Seite zurück, sonst einen leeren Text.

    Gibt es den Namen schon, nennt der Grund die vorhandene Organisation wie in OG1; das gilt
    auch, wenn die Datenbank einen gleichzeitig angelegten gleichen Namen ablehnt.
    """
    try:
        with transaction.atomic():
            unit.save(by=by, **options)
    except ValidationError as error:
        other = unit.clashing()
        if other is None:
            return " ".join(error.messages)
        if other.kind == UnitKind.ASSOCIATION:
            # Andere Bünde sieht eine Leitung nicht (EH-03); die Meldung nennt deshalb nur den eigenen Namen.
            return str(unit_texts.NAME_TAKEN[other.kind] % {"name": unit.name})
        place = unit.parent.name if unit.kind == UnitKind.GROUP else other.association.name
        return str(unit_texts.NAME_TAKEN[other.kind] % {"name": other.name, "place": place})
    return ""


def _apply_edit(unit: Unit, by, name: str | None, ring: Unit | None, rings_on: bool) -> dict:
    """Schreibt die Änderungen aus „… bearbeiten“ nacheinander, je nur ihr Feld; sammelt Meldungen und Gründe (#95).

    Nur innerhalb der Transaktion von `Rights.edit()`; bei einem Grund rollt sie alles zurück.
    """
    messages, errors = [], {}
    # Zuerst prüfen, ob der Ring passt, solange der Name noch der alte ist; sonst nennte die Meldung
    # einen Namen, der wegen der Ablehnung gar nicht gespeichert wird.
    blocking = leads_off_path(unit, ring) if ring is not None else []
    if blocking:
        errors["ring"] = " ".join(_off_path_sentence(membership, leads) for membership, leads in blocking)
    if name is not None and name.strip() != unit.name:
        old = unit_label(unit)
        unit.name = name
        refused = _saved_or_reason(unit, by, update_fields=["name"])
        if refused:
            errors["name"] = refused
        else:
            messages.append(str(unit_texts.RENAMED_TO % {"old": old, "new": unit_label(unit)}))
    if ring is not None and not errors:
        unit.parent = ring
        unit.save(update_fields=["parent"], by=by)
        messages.append(str(unit_texts.RING_CHANGED_TO % {"unit": unit_label(unit), "ring": unit_label(ring)}))
    if rings_on and not errors:
        unit.has_rings = True
        unit.save(update_fields=["has_rings"], by=by)
        messages.append(str(unit_texts.RINGS_INTRODUCED % {"unit": unit.name}))
    return {"messages": messages, "errors": errors}


def _done_or_refused(result: dict) -> tuple[bool, str]:
    """Aus dem Ergebnis von `Rights.edit()`: ob es geklappt hat, und die Meldungen oder Gründe als ein Text."""
    if result["errors"]:
        return False, " ".join(result["errors"].values())
    return True, " ".join(result["messages"])


def _off_path_sentence(membership: Role, leads: list[Role]) -> str:
    """Ein Satz je Person, deren Leitungsrollen nach einem Ringwechsel nicht mehr passen (OG5)."""
    user = membership.user
    roles = [str(unit_texts.ROLE_OF % {"role": lead.get_kind_display(), "unit": unit_label(lead.unit)}) for lead in leads]
    text = unit_texts.RING_CHANGE_ROLE_BLOCKS if len(roles) == 1 else unit_texts.RING_CHANGE_ROLES_BLOCK
    name = display_name(user.first_name, user.last_name, user.scout_name) or user.username
    return str(text % {"person": name, "roles": listed(roles), "unit": unit_label(membership.unit)})


def unit_label(unit: Unit) -> str:
    """Wie eine Organisation im Abschnitt „Personen“ und beim Aufnehmen heißt: „Stamm Walhall“, „Sippe Falken“ (#285)."""
    return str(unit_texts.MEMBER_UNIT_NAME[unit.kind] % {"unit": unit.name})


def _chain_of(membership: Role) -> list[Unit]:
    """Die Organisationen, aus denen eine Mitgliedschaft austreten kann: ihre eigene und die darüber bis zum Bund (EP-06)."""
    found = []
    unit = membership.unit
    while unit is not None and unit.kind != UnitKind.FEDERATION:
        found.append(unit)
        unit = unit.parent
    return found


def listed(parts: list[str]) -> str:
    """„A“, „A und B“, „A, B und C“; für Meldungen, die mehrere Rollen nennen (#286, #287)."""
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} {unit_texts.AND} {parts[-1]}"


def alphabetical(name: str) -> str:
    """Schlüssel für die Sortierung nach dem Alphabet: Ä bei A, É bei E, ohne Groß- und Kleinschreibung.

    Python vergleicht sonst nach Zeichencode und stellt „Ährenfeld“ hinter „Zugvögel“.
    """
    without_marks = "".join(char for char in unicodedata.normalize("NFKD", name) if not unicodedata.combining(char))
    return without_marks.casefold()


def on_lead_path(person, unit: Unit | None) -> bool:
    """Liegt `unit` auf dem Leitungspfad von `person` (#89, ROL-01)? Ohne Mitgliedschaft nie."""
    if person is None or unit is None or getattr(person, "pk", None) is None:
        return False
    membership = Role.objects.filter(user_id=person.pk, kind=R.MEMBER).select_related("unit__parent").first()
    return membership is not None and on_path(membership.unit, unit)


class RightsMiddleware:
    """Gibt jeder Anfrage ihre eigenen Rechte als `request.rights`, erst beim ersten Zugriff geladen.

    Außerdem wird „kein Zugriff“ an einer Adresse mit Kennung zu „nicht gefunden“ (#64), damit
    keine Seite durch die Art der Fehlerseite verrät, dass es einen Eintrag gibt.
    """

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        request.rights = SimpleLazyObject(lambda: Rights(getattr(request, "user", None)))
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Macht aus „kein Zugriff“ einer Seite mit Kennung in der Adresse „nicht gefunden“ (#64)."""
        match = getattr(request, "resolver_match", None)
        if isinstance(exception, PermissionDenied) and match is not None and has_key(match.route):
            raise Http404 from exception
        return None
