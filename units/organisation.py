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
from roles.models import LEAD_ROLE, LEADS_IN_UNITS, RoleKind
from units import texts
from units.models import Kind, Unit

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
    # Der Knopf rechts, nur wo die Person Leitungen entfernen darf: „Entfernen“ oder beim eigenen Eintrag „Rolle abgeben“ (#191).
    remove_href: str | None = None
    remove_label: str = ""

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
    # Der Knopf „… benennen“, nur wo die Person Leitungen benennen darf (#190).
    appoint_href: str | None = None
    appoint_label: str = ""
    # Der Knopf oben am Handy, immer zu „Organisation“ (#218).
    back_label: str = texts.BACK_TO_OUTLINE


@dataclass
class Hit:
    """Ein Vorschlag oder Treffer im Dialog „… benennen“ (#190): Name, wo die Person Mitglied ist, und was geht.

    `place` nennt die Organisation nur im eigenen Bereich, sonst „schon woanders Mitglied“ oder
    „noch nirgends Mitglied“ (PK-16). Den Knopf „Benennen“ gibt es nur ohne `note` (bei sich
    selbst) und ohne `warning` (schon woanders Mitglied); `hint` steht als Satz darunter.
    """

    key: str
    name: str
    extra: str
    place: str
    note: str
    warning: str
    hint: str

    @property
    def initial(self) -> str:
        return self.name[:1].upper()


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

    def visible_leads(self, unit: Unit, without_locked: bool = False) -> list[dict]:
        """Die Leitungen, die die Person bei dieser Organisation sieht; gesperrte nur im eigenen Bereich (Frage B).

        `without_locked` lässt auch dort gesperrte Leitungen weg, etwa in den Kacheln einer
        Leseseite, die nie gesperrte Leitungen zeigt (EH-28, unabhängige Prüfung).
        """
        access = self.access(unit)
        if access not in (MANAGE, READ):
            return []
        show_locked = access == MANAGE and not without_locked
        return [entry for entry in self.leads.get(unit.key, []) if show_locked or not entry["locked"]]

    def leads_line(self, unit: Unit, without_locked: bool = False) -> str:
        """Die Zeile in der Gliederung, z. B. „Stammesleitung: Wirbelwind, Wiesel“ (A21); ohne Zugriff leer."""
        if self.access(unit) not in (MANAGE, READ):
            return ""
        role = LEAD_ROLE[unit.kind].label
        names = [
            texts.LOCKED_NAME % {"name": short_name(entry)} if entry["locked"] else short_name(entry)
            for entry in self.visible_leads(unit, without_locked)
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
        children = self.children.get(unit.pk, [])
        tiles = None if unit.kind == Kind.GROUP else [self._tile(child, without_locked=access == READ) for child in children]
        path = [(entry.name, self.href(entry)) for entry in self._above(unit)]
        back_label = texts.BACK_TO_OUTLINE
        if self.rights.is_federation_lead():
            # Für die Verbandsleitung führt „Organisation“ zur Seite „Verband“; deshalb steht der
            # Verband als erste Ebene im Pfad, und der Knopf am Handy heißt danach (#218).
            federation = Unit.objects.filter(kind=Kind.FEDERATION).first()
            if federation is not None:
                path.insert(0, (federation.name, reverse("organisation")))
            back_label = texts.BACK_TO_FEDERATION
        return Page(
            unit=unit,
            access=access,
            path=path,
            kind_line=kind_line,
            mark=self.mark(unit),
            leads=self._leads_of(unit, access),
            notice=self._notice(unit),
            tiles=tiles,
            empty=self._empty(unit) if tiles == [] else "",
            appoint_href=reverse("organisation_appoint", args=[unit.key]) if self.rights.may_appoint(unit) else None,
            appoint_label=texts.APPOINT_TITLE % {"role": LEAD_ROLE[unit.kind].label},
            back_label=back_label,
        )

    def _leads_of(self, unit: Unit, access: str) -> list[Lead]:
        entries = self.visible_leads(unit)
        mails = {}
        if access == MANAGE and entries:
            # Die Mail nur, wenn die Person sie nach BER-01 ohnehin sieht (A8, A9); die Leseseite nie.
            keys = [entry["user_key"] for entry in entries]
            mails = dict(self.rights.persons().filter(key__in=keys).values_list("key", "email"))
        role = LEAD_ROLE[unit.kind].label
        may_remove = self.rights.may_appoint(unit)
        found = []
        for entry in entries:
            full_name = _full_name(entry)
            is_self = entry["user_key"] == self.user.key
            found.append(Lead(
                name=entry["scout_name"] or full_name or entry["username"],
                extra=full_name if entry["scout_name"] else "",
                role=role,
                mail=mails.get(entry["user_key"], ""),
                locked=entry["locked"],
                is_self=is_self,
                remove_href=reverse("organisation_remove", args=[unit.key, entry["role_key"]]) if may_remove else None,
                remove_label=texts.GIVE_UP_BUTTON if is_self else texts.REMOVE_BUTTON,
            ))
        return found

    def removal(self, unit: Unit, shown: dict, action: str) -> dict:
        """Der Dialog zum Entfernen oder Abgeben aus dem, was `Rights.removal()` liefert (C1 bis C6, N6).

        Titel ist die Frage; darunter beim Abgeben, was man verliert, und bei der letzten Leitung,
        wer danach einspringt, mit „Trotzdem entfernen?“ oder „Trotzdem abgeben?“ am Ende.
        """
        values = {"person": shown["person"], "role": shown["role"], "unit": unit.name}
        lines = []
        if shown["is_self"]:
            title = texts.GIVE_UP_QUESTION % values
            lines.append(texts.GIVE_UP_LOSES % values)
        else:
            title = texts.REMOVE_QUESTION % values
        if shown["last"]:
            cover = self.units.get(shown["cover"])
            if unit.kind == Kind.ASSOCIATION:
                sentence = texts.LAST_ASSOCIATION_LEAD % values
            elif cover is None:
                sentence = texts.LAST_LEAD_NOBODY % values
            else:
                sentence = texts.LAST_LEAD_COVERED % {**values, "cover": texts.COVER_NAME[cover.kind] % {"unit": cover.name}}
            anyway = texts.ANYWAY_GIVE_UP if shown["is_self"] else texts.ANYWAY_REMOVE
            lines.append(f"{sentence} {anyway}")
        return {
            "title": title,
            "lines": lines,
            "close_href": reverse("organisation_unit", args=[unit.key]),
            "confirm_action": action,
            "confirm_label": texts.GIVE_UP_BUTTON if shown["is_self"] else texts.REMOVE_BUTTON,
        }

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

    def _tile(self, unit: Unit, without_locked: bool) -> Tile:
        mark = self.mark(unit)
        covers = mark is not None and mark.kind == "ein"
        return Tile(
            label=unit.get_kind_display(),
            org=unit.name,
            href=self.href(unit),
            way="" if covers else self.leads_line(unit, without_locked),
            mark=mark if covers else None,
        )


def hits(entries: list[dict], unit: Unit, kind: str | None = None) -> list[Hit]:
    """Vorschläge oder Treffer aus der Rechteprüfung für den Dialog „… benennen“ der Einheit `unit` (#190).

    Bei sich selbst steht statt des Knopfs, wer einen benennen kann (RO-12): eine andere Leitung
    der eigenen Organisation oder darüber. Wer außerhalb des eigenen Bereichs schon Mitglied ist,
    bekommt den Satz aus BV1 statt des Knopfs, ohne dass die Organisation genannt wird (PK-16).

    Mit `kind` ist es der Dialog der Verbandsleitung auf der Seite „Verband“ (#94): Bei sich selbst
    steht, dass eine andere Verbandsleitung benennt; wer schon woanders Mitglied ist, behält den
    Knopf, weil die Rolle trotzdem auf ihrem Pfad liegen kann (V5); ob sie das tut, sagt erst das
    Benennen, ohne die Organisation zu nennen (VV3). Mitglied wird nur, wer Bundesleitung wird.
    """
    found = []
    for entry in entries:
        full_name = _full_name(entry)
        note = warning = hint = ""
        if entry["is_self"]:
            note = texts.NOT_YOURSELF_FEDERATION if kind else texts.NOT_YOURSELF % {"unit": entry["unit_name"] or unit.name}
        elif entry["elsewhere"] and not kind:
            warning = texts.MEMBER_ELSEWHERE
        elif not entry["unit_name"] and not entry["elsewhere"] and kind in (None, RoleKind.ASSOCIATION_LEAD):
            hint = texts.BECOMES_MEMBER % {"unit": unit.name}
        if entry["elsewhere"]:
            place = texts.ELSEWHERE
        else:
            place = entry["unit_name"] or texts.NOWHERE
        found.append(Hit(
            key=entry["key"],
            name=entry["scout_name"] or full_name or entry["username"],
            extra=full_name if entry["scout_name"] else "",
            place=place,
            note=note,
            warning=warning,
            hint=hint,
        ))
    return found


@dataclass
class Association:
    """Ein Bund auf der Seite „Verband“: Name, Bundesleitungen und was die Verbandsleitung dort tun kann (#94)."""

    unit: Unit
    href: str | None
    leads: list[Lead]
    notice: str
    appoint_href: str


# Kurze Namen der Rollen im Verband für Adressen, z. B. „/organisation/verband/team/benennen/“.
FEDERATION_SLUGS = {"verbandsleitung": RoleKind.FEDERATION_LEAD, "team": RoleKind.EVENT_TEAM}
SLUG_OF = {kind: slug for slug, kind in FEDERATION_SLUGS.items()}


class Federation:
    """Die Seite „Verband“ der Verbandsleitung: Verbandsleitung, DPV-Veranstaltungsteam und Bünde (#94).

    Personen erscheinen nur nach BER-01, Grund 3: Name, Fahrtenname und Rolle der Bundesleitungen,
    Verbandsleitungen und Teammitglieder aus `Rights.leads()`, nie eine Mail. Ringe, Stämme und
    Gruppen stehen nicht da (EH-05). Ein Bund ist nur anklickbar, wenn sich seine Seite für die
    Person öffnet, also wenn sie dort selbst Leitung ist, auch unterhalb des Bundes (F2 vom
    30.10.2026), ohne Marke „Deine Rolle: Bundesleitung“ (Nachklärung M1 zu #218). Gesperrte
    Konten stehen mit der Marke „gesperrt“ da, weil die Verbandsleitung sie entfernen darf (wie
    #189, Frage B; F3 vom 30.10.2026).
    """

    def __init__(self, rights: Rights, user) -> None:
        self.rights = rights
        self.user = user
        self.federation = Unit.objects.filter(kind=Kind.FEDERATION).first()
        self.leads: dict[tuple[str, str], list[dict]] = {}
        for entry in sorted(rights.leads(), key=_by_name):
            self.leads.setdefault((entry["kind"], entry["unit_key"]), []).append(entry)

    def _people(self, kind: str, unit: Unit | None) -> list[Lead]:
        if unit is None:
            return []
        found = []
        for entry in self.leads.get((kind, unit.key), []):
            full_name = _full_name(entry)
            is_self = entry["user_key"] == self.user.key
            found.append(Lead(
                name=entry["scout_name"] or full_name or entry["username"],
                extra=full_name if entry["scout_name"] else "",
                role=RoleKind(kind).label,
                mail="",
                locked=entry["locked"],
                is_self=is_self,
                remove_href=reverse("federation_remove", args=[entry["role_key"]]),
                remove_label=texts.GIVE_UP_BUTTON if is_self else texts.REMOVE_BUTTON,
            ))
        return found

    def federation_leads(self) -> list[Lead]:
        return self._people(RoleKind.FEDERATION_LEAD, self.federation)

    def team(self) -> list[Lead]:
        return self._people(RoleKind.EVENT_TEAM, self.federation)

    def associations(self) -> list[Association]:
        """Alle Bünde nach dem Alphabet, je mit ihren Bundesleitungen; ohne Bundesleitung mit Konto ein Satz (VG3)."""
        bunds = sorted(Unit.objects.filter(kind=Kind.ASSOCIATION), key=lambda entry: alphabetical(entry.name))
        role = RoleKind.ASSOCIATION_LEAD.label
        return [Association(
            unit=bund,
            href=reverse("organisation_unit", args=[bund.key]) if self.rights.opens_unit(bund) else None,
            leads=self._people(RoleKind.ASSOCIATION_LEAD, bund),
            notice="" if self.rights.has_lead(bund) else str(texts.NO_LEAD % {"unit": bund.name, "role": role}),
            appoint_href=reverse("federation_appoint_lead", args=[bund.key]),
        ) for bund in bunds]

    def removal(self, role, shown: dict, action: str) -> dict:
        """Der Dialog zum Entfernen oder Abgeben auf der Seite „Verband“, mit den Wortlauten aus #191 (V7, V9)."""
        close = reverse("organisation")
        anyway = texts.ANYWAY_GIVE_UP if shown["is_self"] else texts.ANYWAY_REMOVE
        label = texts.GIVE_UP_BUTTON if shown["is_self"] else texts.REMOVE_BUTTON
        lines = []
        if role.kind == RoleKind.ASSOCIATION_LEAD:
            values = {"person": shown["person"], "role": shown["role"], "unit": role.unit.name}
            title = (texts.GIVE_UP_QUESTION if shown["is_self"] else texts.REMOVE_QUESTION) % values
            if shown["is_self"]:
                lines.append(texts.GIVE_UP_LOSES % values)
            if shown["last"]:
                lines.append(f"{texts.LAST_ASSOCIATION_LEAD % values} {anyway}")
        else:
            questions = texts.FEDERATION_GIVE_UP_QUESTION if shown["is_self"] else texts.FEDERATION_REMOVE_QUESTION
            title = questions[role.kind] % {"person": shown["person"]}
            if shown["last"] and role.kind == RoleKind.FEDERATION_LEAD:
                lines.append(f"{texts.LAST_FEDERATION_LEAD} {anyway}")
        return {"title": title, "lines": lines, "close_href": close, "confirm_action": action, "confirm_label": label}


def federation_done(role, shown: dict) -> str:
    """Die kurze Meldung nach dem Entfernen oder Abgeben auf der Seite „Verband“ (wie C13)."""
    if role.kind == RoleKind.ASSOCIATION_LEAD:
        values = {**shown, "unit": role.unit.name}
        return str((texts.GAVE_UP if shown["is_self"] else texts.REMOVED) % values)
    done = texts.FEDERATION_GAVE_UP if shown["is_self"] else texts.FEDERATION_REMOVED
    return str(done[role.kind] % shown)
