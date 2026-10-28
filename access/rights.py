"""Die zentrale Rechteprüfung: wer welche Personen und Leitungen sieht und wo jemand Leitung ist (#90).

Grundlage sind BER-01 (geschlossene Liste der Gründe, Personendaten zu sehen), ROL-02
(einspringende Leitung) und `docs/rechtematrix.md`. Jede Seite fragt `request.rights`; keine
Seite liest Personen- oder Anmeldedaten selbst aus der Datenbank (`CONTRIBUTING.md`,
Abschnitt 4; der Rundumtest meldet Verstöße).

Gebaut sind die Gründe 1 bis 3 von BER-01 und die Bausteine Bereich, Kette nach oben,
Leitungspfad, einspringende Leitung und „Leitung der eigenen Einheit einer Person“. Die übrigen
Gründe und die einzelnen Aktionen kommen mit ihren Seiten an diese Stelle (#93, #100, #101, #92,
#65, #94, #95, #117, #118; Protokoll der Nachklärung von #90 vom 25.10.2026).

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

import unicodedata
from functools import cached_property

from collections.abc import Callable

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import BooleanField, ExpressionWrapper, F, Model, Q, QuerySet
from django.http import Http404
from django.utils.functional import SimpleLazyObject

from access.keys import has_key, is_key
from roles.models import LEADS_IN_UNITS, Role, on_path
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
# Leitungen über die Kennungen von Konto und Einheit zu (#189). `locked` kennzeichnet ein im Tool
# gesperrtes Konto; solche Leitungen stehen nur in der Liste, wer sie entfernen darf (#189, Frage B).
LEAD_FIELDS = ("kind",)
LEAD_NAMES = {
    "first_name": F("user__first_name"),
    "last_name": F("user__last_name"),
    "scout_name": F("user__scout_name"),
    "username": F("user__username"),
    "user_key": F("user__key"),
    "unit_name": F("unit__name"),
    "unit_key": F("unit__key"),
    "locked": ExpressionWrapper(Q(user__is_active=False), output_field=BooleanField()),
}
# Wie weit eine Leitung eine Einheit auf der Seite „Organisation“ sieht (#189).
MANAGE = "manage"  # im eigenen Bereich: Seite mit Mails, wo sie die Person sieht
READ = "read"  # auf der Kette nach oben: Seite nur lesen
NAME_ONLY = "name"  # sonst im eigenen Bund: nur der Name in der Gliederung


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
        """Menüpunkt und Bereich „Organisation“: jede Leitung von Gruppe bis Bund (EH-08).

        Mitglieder ohne Leitungsrolle, Konten ohne Zuordnung, das DPV-Veranstaltungsteam, die
        Verbandsleitung ohne weitere Rolle und Admins sehen ihn nicht (EH-09; Verbandsleitung mit
        #94, Admins mit #92, Mitglieder mit #134). Endet die letzte Leitungsrolle, fehlt er beim
        nächsten Klick.
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
        parent = self._tree[unit.pk][0]
        while parent is not None and self._tree[parent][1] != UnitKind.FEDERATION:
            if parent in self._units_with_lead:
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

    def has_roles(self) -> bool:
        """Hat die Person eine Mitgliedschaft oder irgendeine Rolle? Ohne beides steht der Hinweis „keiner Organisation zugeordnet“ (#9).

        Der Hinweis richtet sich bewusst nicht nach „Zuordnung“ (BER-03): Admins ohne
        Mitgliedschaft wissen, warum sie keiner Organisation angehören (Klärung von #9 vom
        27.10.2026, Frage 2). Nutzt die Rollen, die die Anfrage ohnehin einmal lädt.
        """
        return bool(self._own_roles)

    # Leitungen (BER-01, Grund 3)

    def leads(self) -> QuerySet:
        """Name und Rolle der Leitungen, die die Person sieht, ohne Mail (RO-01 bis RO-03, RO-05).

        Das sind die Leitungen der Einheiten auf ihrer Kette nach oben und in ihrem Bereich, für
        die Verbandsleitung außerdem Bundesleitungen, Verbandsleitungen und das
        DPV-Veranstaltungsteam. Jeder Eintrag enthält nur die Felder aus `LEAD_FIELDS` und `LEAD_NAMES`.

        Leitungen mit im Tool gesperrtem Konto stehen nur dabei, wo die Person Leitungen entfernen
        darf, also in ihrem Bereich (RO-10, RO-11), gekennzeichnet mit `locked`; alle anderen
        erfahren nichts von der Sperre (#189, Frage B). Was die Verbandsleitung davon sieht,
        entscheidet #94; bis dahin bleibt es für sie wie bisher.
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
