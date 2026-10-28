"""Was die Seite „Organisation“ zeigt: die Gliederung des eigenen Bundes und die Seite je Organisation (#189).

Wer was sieht, entscheidet allein die zentrale Rechteprüfung (`request.rights`, #90): wie weit die
Person eine Einheit sieht (`unit_access()`), welche Leitungen (`leads()`) und wessen Mail
(`persons()`). Dieses Modul liest Personendaten nur über sie und ordnet sie für die Vorlagen.
Alles wird bei jedem Aufruf neu berechnet, nichts gespeichert: Der nächste Klick zeigt den neuen
Stand (A20). Gliederung und Seite brauchen gleich viele Abfragen, egal wie groß der Bund ist.
"""

from dataclasses import dataclass, field

from django.db.models import Q
from django.urls import reverse

from access.rights import MANAGE, NAME_ONLY, READ, Rights, alphabetical
from roles.models import LEADS_IN_UNITS, UNIT_KINDS, Role
from units import texts
from units.models import Kind, Unit

# Die Leitungsrolle jeder Ebene, z. B. Stamm → Stammesleitung.
LEAD_ROLE = {unit_kind: Role.Kind(role) for role in LEADS_IN_UNITS for unit_kind in UNIT_KINDS[role]}
# Was unter jeder Ebene hängt, für „… hat noch keine …“ (A11); ein Bund mit Ringen bekommt Ringe.
CHILDREN_WORD = {Kind.TROOP: texts.GROUPS, Kind.RING: texts.TROOPS, Kind.ASSOCIATION: texts.TROOPS}


@dataclass(frozen=True)
class Mark:
    """Kleine Marke an einer Organisation (A23) oder einer Leitung (A16): Text und Art für die Farbe."""

    text: str
    kind: str


@dataclass
class Lead:
    """Eine Leitung auf der Seite einer Organisation: Name, Fahrtenname und Rolle, die Mail nur, wo erlaubt."""

    name: str
    extra: str
    role: str
    mail: str
    locked: bool
    is_self: bool

    @property
    def locked_mark(self) -> Mark | None:
        """Die Marke „gesperrt“; nur Verwaltende bekommen gesperrte Leitungen überhaupt zu sehen (Frage B)."""
        return Mark(texts.MARK_LOCKED, "gesperrt") if self.locked else None

    @property
    def initial(self) -> str:
        """Der Anfangsbuchstabe im Kreis, wie in der Kopfzeile mit Name."""
        return self.name[:1].upper()


@dataclass
class Node:
    """Eine Organisation in der Gliederung mit ihren Organisationen darunter."""

    unit: Unit
    kind: str
    access: str
    href: str | None
    mark: Mark | None
    leads: str
    current: bool
    children: list["Node"] = field(default_factory=list)
    folded: list["Node"] = field(default_factory=list)


@dataclass
class Tile:
    """Eine Organisation unter „Organisationen darunter“ als Rollenkachel: klein die Art, groß der Name, darunter die Leitung.

    Anklickbar nur, soweit sie es in der Gliederung ist; ohne Zugriff grau und nur mit Namen.
    """

    label: str
    org: str
    href: str | None
    way: str
    mark: Mark | None


@dataclass
class Page:
    """Die Seite einer Organisation, zum Verwalten oder nur zum Lesen."""

    unit: Unit
    access: str
    path: list[tuple[str, str | None]]
    kind_line: str
    mark: Mark | None
    leads: list[Lead]
    notice: str
    tiles: list[Tile] | None
    empty: str


def short_name(entry: dict) -> str:
    """Wie eine Leitung in der Gliederung heißt: Fahrtenname, sonst Vor- und Nachname, sonst Benutzername (A21)."""
    return entry["scout_name"] or _full_name(entry) or entry["username"]


def _by_name(entry: dict) -> tuple:
    """Leitungen nach Nachnamen, dann Vornamen; ohne Namen am Ende, nach dem Benutzernamen."""
    return (not entry["last_name"], alphabetical(entry["last_name"]), alphabetical(entry["first_name"]),
            entry["username"])


def _full_name(entry: dict) -> str:
    return " ".join(part for part in (entry["first_name"], entry["last_name"]) if part)


class Organisation:
    """Gliederung und Seiten für die Person einer Anfrage; Grundlage sind ihre Rechte."""

    def __init__(self, rights: Rights, user) -> None:
        self.rights = rights
        self.user = user
        bunds = rights.associations
        found = Unit.objects.filter(Q(pk__in=bunds) | Q(association__in=bunds) | Q(parent__association__in=bunds))
        self.units = {entry.pk: entry for entry in found}
        self.children: dict[int, list[Unit]] = {}
        for entry in sorted(self.units.values(), key=lambda entry: alphabetical(entry.name)):
            if entry.parent_id in self.units:
                self.children.setdefault(entry.parent_id, []).append(entry)
        self.leads: dict[str, list[dict]] = {}
        for entry in sorted(rights.leads(), key=_by_name):
            if entry["kind"] in LEADS_IN_UNITS:
                self.leads.setdefault(entry["unit_key"], []).append(entry)

    # Bausteine

    def access(self, unit: Unit) -> str | None:
        return self.rights.unit_access(unit)

    def href(self, unit: Unit) -> str | None:
        """Die Adresse der Seite, wenn sie sich öffnet; sonst ist die Organisation nicht anklickbar (RO-04)."""
        if self.access(unit) in (MANAGE, READ):
            return reverse("organisation_unit", args=[unit.key])
        return None

    def mark(self, unit: Unit) -> Mark | None:
        """„Du springst ein“ oder „nur lesen“; sonst keine Marke (A23).

        Die eigene Rolle trägt keine Marke: Sie steht bei den Leitungen mit „das bist du“
        (Sebastian, 28.10.2026, am Vorschlag zu #189).
        """
        access = self.access(unit)
        if access == READ:
            return Mark(texts.MARK_READ, "lesen")
        if access == MANAGE and self.rights.covers(unit):
            return Mark(texts.MARK_COVERS, "ein")
        return None

    def visible_leads(self, unit: Unit) -> list[dict]:
        """Die Leitungen, die die Person bei dieser Organisation sieht; gesperrte nur im eigenen Bereich (Frage B)."""
        access = self.access(unit)
        if access not in (MANAGE, READ):
            return []
        return [entry for entry in self.leads.get(unit.key, []) if access == MANAGE or not entry["locked"]]

    def leads_line(self, unit: Unit) -> str:
        """Die Zeile in der Gliederung, z. B. „Stammesleitung: Wirbelwind, Wiesel“ (A21); ohne Zugriff leer."""
        if self.access(unit) not in (MANAGE, READ):
            return ""
        role = LEAD_ROLE[unit.kind].label
        names = [
            texts.LOCKED_NAME % {"name": short_name(entry)} if entry["locked"] else short_name(entry)
            for entry in self.visible_leads(unit)
        ]
        if not names:
            return texts.NO_LEAD_SHORT % {"role": role}
        return texts.LEADS_LINE % {"role": role, "names": ", ".join(names)}

    # Gliederung

    def start_unit(self) -> Unit:
        """Die Organisation, die neben der Gliederung zuerst steht: die oberste, die die Person leitet."""
        led = [entry for entry in self.units.values() if self.rights.leads_itself(entry)]
        return min(led, key=lambda entry: (len(self._above(entry)), alphabetical(entry.name)))

    def outline(self, current: Unit) -> list[Node]:
        """Der ganze eigene Bund (EH-01); ohne Zugriff nur der Name, immer zugeklappt (A22)."""
        bunds = [entry for entry in self.units.values() if entry.kind == Kind.ASSOCIATION]
        return [self._node(entry, current) for entry in sorted(bunds, key=lambda entry: alphabetical(entry.name))]

    def _node(self, unit: Unit, current: Unit) -> Node:
        node = Node(
            unit=unit,
            kind=unit.get_kind_display(),
            access=self.access(unit),
            href=self.href(unit),
            mark=self.mark(unit),
            leads=self.leads_line(unit),
            current=unit.pk == current.pk,
        )
        for child in self.children.get(unit.pk, []):
            target = node.folded if self.access(child) == NAME_ONLY and self.access(unit) != NAME_ONLY else node.children
            target.append(self._node(child, current))
        return node

    def _above(self, unit: Unit) -> list[Unit]:
        """Die Einheiten darüber bis zum Bund, von oben nach unten."""
        found = []
        parent = self.units.get(unit.parent_id)
        while parent is not None:
            found.append(parent)
            parent = self.units.get(parent.parent_id)
        return found[::-1]

    # Seite einer Organisation

    def page(self, unit: Unit) -> Page:
        """Die Seite: Kopf mit Pfad und Marke, „Leitungen“, bei allen außer Gruppen „Organisationen darunter“."""
        access = self.access(unit)
        parent = self.units.get(unit.parent_id)
        kind_line = unit.get_kind_display()
        if parent is not None:
            kind_line = texts.KIND_IN % {"kind": kind_line, "parent": parent.name}
        tiles = None if unit.kind == Kind.GROUP else [self._tile(child) for child in self.children.get(unit.pk, [])]
        return Page(
            unit=unit,
            access=access,
            path=[(entry.name, self.href(entry)) for entry in self._above(unit)],
            kind_line=kind_line,
            mark=self.mark(unit),
            leads=self._leads_of(unit, access),
            notice=self._notice(unit),
            tiles=tiles,
            empty=self._empty(unit) if tiles == [] else "",
        )

    def _leads_of(self, unit: Unit, access: str) -> list[Lead]:
        entries = self.visible_leads(unit)
        mails = {}
        if access == MANAGE and entries:
            # Die Mail nur, wenn die Person sie nach BER-01 ohnehin sieht (A8, A9); die Leseseite nie.
            keys = [entry["user_key"] for entry in entries]
            mails = dict(self.rights.persons().filter(key__in=keys).values_list("key", "email"))
        role = LEAD_ROLE[unit.kind].label
        found = []
        for entry in entries:
            full_name = _full_name(entry)
            found.append(Lead(
                name=entry["scout_name"] or full_name or entry["username"],
                extra=full_name if entry["scout_name"] else "",
                role=role,
                mail=mails.get(entry["user_key"], ""),
                locked=entry["locked"],
                is_self=entry["user_key"] == self.user.key,
            ))
        return found

    def _notice(self, unit: Unit) -> str:
        """Der Satz ohne Leitung (A10, A14); gesperrte Leitungen zählen nicht (A16)."""
        if self.rights.has_lead(unit):
            return ""
        values = {"unit": texts.WITH_KIND[unit.kind] % {"unit": unit.name}, "role": LEAD_ROLE[unit.kind].label}
        cover = self.units.get(self.rights.covering_unit(unit))
        if cover is None:
            return texts.NO_LEAD % values
        return texts.NO_LEAD_COVERED % {**values, "cover_role": LEAD_ROLE[cover.kind].label, "cover": cover.name}

    def _empty(self, unit: Unit) -> str:
        word = texts.RINGS if unit.kind == Kind.ASSOCIATION and unit.has_rings else CHILDREN_WORD[unit.kind]
        return texts.NOTHING_BELOW % {"unit": unit.name, "children": word}

    def _tile(self, unit: Unit) -> Tile:
        mark = self.mark(unit)
        covers = mark is not None and mark.kind == "ein"
        return Tile(
            label=unit.get_kind_display(),
            org=unit.name,
            href=self.href(unit),
            way="" if covers else self.leads_line(unit),
            mark=mark if covers else None,
        )
