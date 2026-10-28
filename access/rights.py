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

import math
import unicodedata
from collections.abc import Callable
from datetime import timedelta
from functools import cached_property

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import BooleanField, CharField, ExpressionWrapper, F, Model, Q, QuerySet, Value
from django.db.models.functions import Concat
from django.http import Http404
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

from access.keys import has_key, is_key
from accounts.models import AccountSearch, display_name
from roles.models import LEAD_ROLE, LEADS_IN_UNITS, Role, on_path
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
        return self._lead_above(unit.pk)

    def _lead_above(self, unit: int) -> int | None:
        """Die nächste Einheit über `unit` mit Leitung mit Konto, ohne den Verband; sonst None."""
        parent = self._tree[unit][0]
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
        """Konten über die genaue Mail oder den genauen Benutzernamen, ohne Groß- und Kleinschreibung (PK-13).

        Nur Konten, die sich schon einmal angemeldet haben und nicht gesperrt sind; ein gesperrtes
        Konto zeigt dasselbe wie keines, damit die Suche keine Sperre verrät (BV11). Ein Teil einer
        Mail findet nichts, und eine Liste aller Konten gibt es nicht (PK-15): Verglichen wird auf
        Gleichheit, Platzhalter wie „%“ gelten als Zeichen. Den Treffer zeigt die Seite ohne die
        Organisation, wenn er außerhalb des eigenen Bereichs liegt (PK-16). Das Suchlimit zählt
        `count_search()`, nicht diese Stelle.
        """
        text = text.strip()
        if not self.sees_organisation() or not text or set(text) <= WILDCARDS:
            return []
        accounts = get_user_model().objects.filter(is_active=True, last_login__isnull=False)
        found = accounts.filter(Q(email__iexact=text) | Q(username__iexact=text)).order_by("username")
        return self._hits(list(found[:SUGGESTION_MOST]))

    def _hits(self, users: list) -> list[dict]:
        """Was Vorschläge und Treffer zeigen dürfen: Kennung, Namen und wo die Person Mitglied ist (PK-16).

        `unit_name` steht nur bei Mitgliedern des eigenen Bereichs und bei der Person selbst;
        sonst sagt `elsewhere` nur, dass sie schon woanders Mitglied ist. Interne Nummern gibt die
        Liste nicht heraus (#156).
        """
        memberships = dict(
            Role.objects.filter(kind=R.MEMBER, user_id__in=[user.pk for user in users]).values_list("user_id", "unit_id")
        )
        names = dict(Unit.objects.filter(pk__in=memberships.values()).values_list("pk", "name"))
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
                "unit_name": names[unit] if shown else "",
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

    # Leitungen entfernen und die eigene Rolle abgeben (#191)

    def may_remove(self, role: Role) -> bool:
        """Darf die Person diese Rolle entfernen oder, wenn es ihre eigene ist, abgeben (RO-10, RO-11, RO-20)?

        Nur Leitungsrollen von Gruppe bis Bund in ihrem Bereich, also genau dort, wo sie benennen
        darf (`may_appoint()`), auch bei gesperrten Konten (RO-21). Die eigenen Leitungsrollen liegen
        immer im eigenen Bereich. Mitgliedschaften, Verbandsleitung, DPV-Veranstaltungsteam und Admin
        entfernt diese Stelle nie (CV3, CV8, RO-18, RO-19); die Verbandsleitung kommt mit #94.
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
        nicht mehr. Was sie davon zeigt, entscheidet #94 mit ihrer Seite.
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
