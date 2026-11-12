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

from access.rights import MANAGE, NAME_ONLY, READ, Rights, alphabetical, child_kind, listed, unit_label
from accounts.models import display_name
from persons import texts as person_texts
from roles.models import LEAD_ROLE, LEADS_IN_UNITS, RoleKind
from units import texts
from units.models import Kind, Unit

# Die Kennung des Knopfs „Verwaltete Person anlegen“; dorthin führt sein Dialog zurück (#117).
ADD_MANAGED_ID = "verwaltete-person-anlegen"
# Was unter jeder Ebene hängt, für „… hat noch keine …“ (A11); ein Bund mit Ringen bekommt Ringe.
CHILDREN_WORD = {Kind.TROOP: texts.GROUPS, Kind.RING: texts.TROOPS, Kind.ASSOCIATION: texts.TROOPS}


@dataclass(frozen=True)
class Mark:
    """Kleine Marke an einer Organisation (A23) oder einer Leitung (A16): Text und Art für die Farbe."""

    text: str
    kind: str


@dataclass
class Lead:
    """Eine Leitung oder Person in einer Liste: Name, Fahrtenname, Rollen, die Mail nur, wo erlaubt.

    Leitungen haben genau eine Rolle (`role`). Personen im Abschnitt „Personen“ (#285) haben
    keine, eine oder mehrere Leitungsrollen (`role_names`), z. B. „Stammesleitung Stamm Walhall“.
    """

    name: str
    extra: str
    role: str
    mail: str
    locked: bool
    is_self: bool
    # Der Knopf rechts, nur wo die Person Leitungen entfernen darf: „Entfernen“ oder beim eigenen Eintrag „Rolle abgeben“ (#191).
    remove_href: str | None = None
    remove_label: str = ""
    role_names: list[str] = field(default_factory=list)
    # Bei Personen im Abschnitt „Personen“ der Knopf „Austragen“, nur wo die Person austragen darf (#286).
    expel_href: str | None = None
    expel_label: str = texts.EXPEL_BUTTON
    # Davor der Knopf „Verschieben“, nur wo die Person verschieben darf (#287).
    move_href: str | None = None
    move_label: str = texts.MOVE_BUTTON
    # Eine verwaltete Person (#117): Marke „verwaltet“ und der Knopf „Bearbeiten“ mit seiner Kennung, zu
    # der der Dialog danach zurückführt.
    managed: bool = False
    edit_href: str | None = None
    edit_label: str = person_texts.EDIT_BUTTON
    edit_id: str = ""

    @property
    def shown_roles(self) -> list[str]:
        """Die Rollenmarken unter dem Namen: bei Personen ihre Leitungsrollen, bei Leitungen die eine Rolle."""
        return self.role_names or ([self.role] if self.role else [])

    @property
    def locked_mark(self) -> Mark | None:
        """Die Marke „gesperrt“; nur Verwaltende bekommen gesperrte Leitungen überhaupt zu sehen (Frage B)."""
        return Mark(texts.MARK_LOCKED, "gesperrt") if self.locked else None

    @property
    def managed_mark(self) -> Mark | None:
        """Die Marke „verwaltet“ bei einer verwalteten Person im Abschnitt „Personen“ (#117)."""
        return Mark(person_texts.MARK_MANAGED, "verwaltet") if self.managed else None

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
    # Der Abschnitt „Personen“ (#285): None auf der Leseseite, sonst die direkten Mitglieder.
    persons: list[Lead] | None = None
    persons_count: str = ""
    persons_empty: str = ""
    # Der Knopf „Person mit Konto aufnehmen“, nur wo die Person aufnehmen darf (PK-17, PK-26, EH-18).
    admit_href: str | None = None
    admit_label: str = texts.ADMIT_TITLE
    # Daneben „Verwaltete Person anlegen“, nur wo die Person anlegen darf (VP-01, VP-17, EH-18; #117).
    add_managed_href: str | None = None
    add_managed_label: str = person_texts.ADD_TITLE
    add_managed_id: str = ADD_MANAGED_ID
    # Der Knopf „… anlegen“ unter „Organisationen darunter“, nur wo die Person anlegen darf (#95).
    create_href: str | None = None
    create_label: str = ""
    # Der Stift oben rechts im Kopf, nur wo die Person umbenennen darf; er öffnet „… bearbeiten“ (#95).
    edit_href: str | None = None
    edit_label: str = ""


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


def _user_by_name(user) -> tuple:
    """Personen wie Leitungen nach Nachnamen, dann Vornamen; ohne Namen am Ende, nach dem Benutzernamen."""
    return (not user.last_name, alphabetical(user.last_name), alphabetical(user.first_name), user.username)


def _managed_by_name(entry) -> tuple:
    """Verwaltete Personen in derselben Ordnung wie Personen mit Konto; sie haben immer einen Nachnamen (#117)."""
    return (False, alphabetical(entry.last_name), alphabetical(entry.first_name), "")


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
            **self._structure_buttons(unit),
            **self._persons_section(unit, access),
        )

    def _structure_buttons(self, unit: Unit) -> dict:
        """Die Knöpfe zum Anlegen und Bearbeiten, je nur wo die Rechteprüfung es erlaubt (#95)."""
        rights = self.rights
        kind = child_kind(unit)
        return {
            "create_href": reverse("organisation_create", args=[unit.key]) if rights.may_create(unit) else None,
            "create_label": texts.CREATE_TITLE[kind] if kind else "",
            "edit_href": reverse("organisation_edit", args=[unit.key]) if rights.may_rename(unit) else None,
            "edit_label": texts.EDIT_TITLE % {"unit": unit_label(unit)},
        }

    def _persons_section(self, unit: Unit, access: str) -> dict:
        """Der Abschnitt „Personen“ nur im eigenen Bereich; auf der Leseseite gibt es ihn nicht (#285, U1).

        Personen mit Konto und verwaltete Personen stehen gemischt, alle nach Nachname, dann Vorname;
        die Zahl im Kopf zählt alle (#117, Frage 2). Ohne Personen steht der Satz aus N7, der zweite Satz
        nur, wo die Person dort anlegen darf.
        """
        if access != MANAGE:
            return {}
        may = {"expel": self.rights.may_expel(unit), "move": self.rights.may_move(unit)}
        may_add = self.rights.may_add_managed(unit)
        people = [(_user_by_name(user), self._person(user, unit, **may)) for user in self.rights.members(unit)]
        people += [(_managed_by_name(entry), self._managed(entry, unit)) for entry in self.rights.managed_in(unit)]
        persons = [lead for _order, lead in sorted(people, key=lambda pair: pair[0])]
        empty = str(person_texts.NOBODY_YET)
        if may_add:
            empty = f"{empty} {person_texts.NOBODY_YET_ADD}"
        return {
            "persons": persons,
            "persons_count": texts.PERSONS_COUNT % {"count": len(persons)},
            "persons_empty": empty,
            "admit_href": reverse("organisation_admit", args=[unit.key]) if self.rights.may_admit(unit) else None,
            "add_managed_href": reverse("organisation_add_managed", args=[unit.key]) if may_add else None,
        }

    @staticmethod
    def _managed(entry, unit: Unit) -> Lead:
        """Eine verwaltete Person im Abschnitt „Personen“: wie eine Person mit Konto, ohne Mail und Geburtsdatum (#117).

        Mit der Marke „verwaltet“ und dem Knopf „Bearbeiten“; den hat, wer den Abschnitt sieht, denn
        sehen und bearbeiten gehen zusammen im ganzen Bereich (VP-02).
        """
        full_name = f"{entry.first_name} {entry.last_name}"
        return Lead(
            name=entry.scout_name or full_name,
            extra=full_name if entry.scout_name else "",
            role="",
            mail="",
            locked=False,
            is_self=False,
            managed=True,
            edit_href=reverse("organisation_edit_managed", args=[unit.key, entry.key]),
            edit_id=edit_anchor(entry),
        )

    def _person(self, user, unit: Unit, expel: bool, move: bool) -> Lead:
        """Eine Person im Abschnitt „Personen“ mit ihren Leitungsrollen von der Gruppe bis zum Bund (#65 N1).

        Mit den Knöpfen „Verschieben“ und „Austragen“, wo die Person das darf, auch beim eigenen
        Eintrag (#286, #287).
        """
        full_name = " ".join(part for part in (user.first_name, user.last_name) if part)
        leads = sorted(user.lead_roles, key=lambda role: (LEADS_IN_UNITS.index(role.kind), alphabetical(role.unit.name)))
        return Lead(
            name=user.scout_name or full_name or user.username,
            extra=full_name if user.scout_name else "",
            role="",
            role_names=[str(texts.ROLE_AT % {"role": role.get_kind_display(), "unit": unit_label(role.unit)}) for role in leads],
            mail=user.email,
            locked=not user.is_active,
            is_self=user.pk == self.user.pk,
            expel_href=reverse("organisation_expel", args=[unit.key, user.key]) if expel else None,
            move_href=reverse("organisation_move", args=[unit.key, user.key]) if move else None,
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


def _ending_lines(endings: list[dict], own: bool) -> list[str]:
    """Die Sätze der Vorschau zu den Rollen, die enden, und zur letzten Leitung (#286, wie #191)."""
    if not endings:
        return []
    roles = [str(texts.ROLE_OF % {"role": entry["role"].get_kind_display(), "unit": unit_label(entry["role"].unit)})
             for entry in endings]
    lines = [str((texts.ENDING_OWN_ROLES if own else texts.ENDING_ROLES) % {"roles": listed(roles)})]
    for entry in endings:
        if not entry["last"]:
            continue
        unit = entry["role"].unit
        values = {"unit": unit.name, "role": entry["role"].get_kind_display()}
        if unit.kind == Kind.ASSOCIATION:
            lines.append(str(texts.LAST_ASSOCIATION_LEAD % values))
        elif entry["cover"] is None:
            lines.append(str(texts.LAST_LEAD_NOBODY % values))
        else:
            cover = entry["cover"]
            lines.append(str(texts.LAST_LEAD_COVERED % {**values, "cover": texts.COVER_NAME[cover.kind] % {"unit": cover.name}}))
    return lines


def _choice(name: str, legend: str, options: list[tuple[str, str, list[str]]], chosen: str = "") -> dict:
    """Die Daten für den Baustein „Auswahl im Dialog“ (#286): je Möglichkeit Wert, Beschriftung und Vorschau.

    `chosen` ist der Wert, der gewählt bleiben soll, etwa nach einer Ablehnung (#287); ohne ihn oder
    mit einem Wert, den es nicht gibt, ist die erste Möglichkeit gewählt.
    """
    values = [value for value, _label, _lines in options]
    chosen = chosen if chosen in values else ""
    return {"name": name, "legend": legend, "chosen": chosen,
            "options": [{"value": value, "label": label, "lines": lines, "checked": value == chosen}
                        for value, label, lines in options]}


def expulsion_dialog(unit: Unit, shown: dict, action: str) -> dict:
    """Der Dialog „… austragen?“ aus dem, was `Rights.expulsion()` liefert (PK-21, #65 Frage 11 und 17).

    Titel ist die Frage; darunter die Wahl mit ihrer Vorschau (Baustein „Auswahl im Dialog“); der rote
    Knopf „Austragen“ schickt die Wahl mit.
    """
    person, place = shown["person"], unit_label(unit)
    options = []
    for option in shown["options"]:
        values = {"person": person, "unit": place}
        if option["target"] is None:
            label, first = texts.EXPEL_NONE % values, texts.EXPEL_PREVIEW_NONE % values
        else:
            values["target"] = unit_label(option["target"])
            label, first = texts.EXPEL_UP % values, texts.EXPEL_PREVIEW_UP % values
        lines = [str(first), *_ending_lines(option["endings"], own=False), str(texts.REGISTRATIONS_STAY)]
        options.append((option["value"], str(label), lines))
    return {
        "title": texts.EXPEL_QUESTION % {"person": person, "unit": place},
        "close_href": reverse("organisation_unit", args=[unit.key]),
        "confirm_action": action,
        "confirm_label": texts.EXPEL_BUTTON,
        "form_id": "f-dialog",
        "choice": _choice("wahl", str(texts.EXPEL_LEGEND % {"person": person}), options),
    }


def move_dialog(unit: Unit, shown: dict, action: str, notice: str = "", chosen: str = "") -> dict:
    """Der Dialog „Verschieben“ aus dem, was `Rights.moving()` liefert (PK-19, Zielbild aus #285).

    Titel „Verschieben“, darunter wer aus welcher Organisation; die Wahl der Organisationen direkt
    darunter ist der Baustein „Auswahl im Dialog“ ohne Vorschau, der Knopf „Verschieben“ ist blau
    (Sebastian bei der Umsetzung, 10.11.2026: „1a und 2a“). `notice` ist eine Ablehnung, die im
    Dialog an der Stelle der Handlung steht (PK-25, #186); dann bleibt das abgelehnte Ziel `chosen`
    gewählt (Sebastian, 10.11.2026: „Ja, gewählt lassen“).
    """
    options = [(target.key, unit_label(target), []) for target in shown["targets"]]
    return {
        "title": texts.MOVE_TITLE,
        "subtitle": texts.MOVE_FROM % {"person": shown["person"], "unit": unit_label(unit)},
        "lines": [texts.MOVE_QUESTION],
        "close_href": reverse("organisation_unit", args=[unit.key]),
        "confirm_action": action,
        "confirm_label": texts.MOVE_BUTTON,
        "confirm_primary": True,
        "form_id": "f-dialog",
        "choice": _choice("ziel", str(texts.MOVE_QUESTION), options, chosen=chosen),
        "notice": notice,
    }


def edit_anchor(entry) -> str:
    """Die Kennung des Knopfs „Bearbeiten“ einer verwalteten Person; dorthin führt ihr Dialog zurück (#117)."""
    return f"bearbeiten-{entry.key}"


def managed_dialog(unit: Unit, form, action: str, entry=None, hidden: tuple = (), conflict: str = "") -> dict:
    """Der Dialog „Verwaltete Person anlegen“ oder, mit `entry`, „… bearbeiten“ (#117, Zielbild).

    Darunter „in … · ohne Konto, verwaltet“, die vier Felder und der dunkelblaue Knopf „Anlegen“ oder
    „Speichern“; einen Knopf zum Löschen gibt es nicht (N5, #118). × und „Abbrechen“ führen zur Seite
    zurück, mit der Kennung des Knopfs, der den Dialog geöffnet hat, in der Adresse; dort bekommt er den
    Fokus wieder. `hidden` sind die versteckten Felder (Kennung des Dialogs oder Stand), `conflict`
    der Satz, wenn inzwischen jemand anderes gespeichert hat (MG6).
    """
    back = f"{reverse('organisation_unit', args=[unit.key])}#{edit_anchor(entry) if entry else ADD_MANAGED_ID}"
    return {
        "title": person_texts.EDIT_TITLE % {"person": entry.display_name} if entry else person_texts.ADD_TITLE,
        "subtitle": person_texts.IN_UNIT % {"unit": unit_label(unit)},
        "close_href": back,
        "confirm_action": action,
        "confirm_label": person_texts.SAVE_BUTTON if entry else person_texts.ADD_BUTTON,
        "confirm_primary": True,
        "form_id": "f-dialog",
        # Die Meldungen am Feld kommen vom Tool, nicht als Blase des Browsers (MG1, MG4).
        "novalidate": True,
        "person_form": form,
        "hidden": list(hidden),
        "conflict": conflict,
    }


def create_dialog(parent: Unit, form, action: str) -> dict:
    """Der Dialog „… anlegen“ (#95): Titel nach der Art, darunter wo, das Feld „Name“ und der blaue Knopf „Anlegen“.

    Die Art kommt aus `child_kind()`, also aus der Adresse. Eine Ablehnung steht als Fehler am Feld (OG1, OG3).
    """
    return {
        "title": texts.CREATE_TITLE[child_kind(parent)],
        "subtitle": texts.CREATE_IN % {"unit": unit_label(parent)},
        "close_href": reverse("organisation_unit", args=[parent.key]),
        "confirm_action": action,
        "confirm_label": texts.CREATE_BUTTON,
        "confirm_primary": True,
        "form_id": "f-dialog",
        "form": form,
    }


def edit_dialog(unit: Unit, form, action: str, rings: list[Unit] | None, rings_switch: bool, ring_key: str = "",
                rings_on: bool = False, ring_notice: str = "", shown_name: str | None = None,
                shown_ring: str | None = None) -> dict:
    """Der Dialog „… bearbeiten“ (#95; Sebastian bei der Vorschau, 11.11.2026): alles an einem Ort.

    Das Textfeld „Name“ für jede Leitung, die umbenennen darf; mit `rings` (nur die Bundesleitung,
    beim Stamm) die Wahl des Rings als „Auswahl im Dialog“ ohne Vorschau, der jetzige gewählt, bei
    einem Stamm ohne Ring zuerst „ohne Ring (bisher)“; mit `rings_switch` (nur die Bundesleitung,
    beim Bund) der Schalter „Hat Ringe“, nach dem Einschalten gesperrt. `ring_key` und `rings_on`
    halten nach einer Ablehnung die Eingabe fest; `ring_notice` steht dann unter der Wahl.
    Versteckt geht mit, was der Dialog beim ersten Öffnen gezeigt hat (`shown_name`, `shown_ring`,
    sonst der jetzige Stand), damit nur Geändertes gespeichert wird (OG4).
    """
    dialog = {
        "title": texts.EDIT_TITLE % {"unit": unit_label(unit)},
        "close_href": reverse("organisation_unit", args=[unit.key]),
        "confirm_action": action,
        "confirm_label": texts.SAVE_BUTTON,
        "confirm_primary": True,
        "form_id": "f-dialog",
        "form": form,
        "notice": ring_notice,
        "hidden": [("name_vorher", unit.name if shown_name is None else shown_name)],
    }
    if rings is not None:
        now = unit.parent.key if unit.parent.kind == Kind.RING else ""
        dialog["hidden"].append(("ring_vorher", now if shown_ring is None else shown_ring))
        options = [] if now else [("", str(texts.NO_RING_YET), [])]
        options += [(ring.key, unit_label(ring), []) for ring in rings]
        dialog["choice"] = _choice("ring", str(texts.RING_LABEL), options, chosen=ring_key or now)
        dialog["choice"]["legend_shown"] = True
    if rings_switch:
        dialog["switch"] = {"name": "hat_ringe", "value": "an", "title": texts.HAS_RINGS_TITLE,
                            "checked": unit.has_rings or rings_on, "locked": unit.has_rings,
                            "text": texts.HAS_RINGS_LOCKED if unit.has_rings else texts.HAS_RINGS_OFF}
    return dialog


def rings_question(bund: Unit, action: str, name: str, shown_name: str | None = None) -> dict:
    """Die Rückfrage aus O8, bevor „hat Ringe“ eingeschaltet wird (#95, EH-23).

    Sie trägt den Namen aus dem Dialog weiter und, was der Dialog beim Öffnen gezeigt hat (OG4).
    """
    return {
        "title": texts.INTRODUCE_RINGS_QUESTION % {"unit": bund.name},
        "lines": [str(line) for line in texts.INTRODUCE_RINGS_LINES],
        "close_href": reverse("organisation_unit", args=[bund.key]),
        "confirm_action": action,
        "confirm_label": texts.INTRODUCE_RINGS_BUTTON,
        "confirm_primary": True,
        "hidden": [("name", name), ("name_vorher", bund.name if shown_name is None else shown_name),
                   ("hat_ringe", "an"), ("bestaetigt", "ja")],
    }


def exit_dialog(membership, options: list[dict], action: str) -> dict:
    """Der Dialog „Austreten“ auf „Mein Profil“ aus dem, was `Rights.exit_options()` liefert (EP-06).

    Die Wahl nennt die Ebenen der eigenen Kette; die Organisation der Mitgliedschaft geht als
    verstecktes Feld mit, damit eine inzwischen geänderte Mitgliedschaft „nicht gefunden“ ist (PG3).
    """
    found = []
    for option in options:
        values = {"unit": unit_label(option["level"])}
        if option["target"] is None:
            label, first = texts.EXIT_NONE % values, texts.EXIT_PREVIEW_NONE % values
        else:
            values["target"] = unit_label(option["target"])
            label, first = texts.EXIT_UP % values, texts.EXIT_PREVIEW_UP % values
        lines = [str(first), *_ending_lines(option["endings"], own=True), str(texts.OWN_REGISTRATIONS_STAY)]
        found.append((option["level"].key, str(label), lines))
    return {
        "title": texts.EXIT_TITLE,
        "close_href": reverse("profile"),
        "confirm_action": action,
        "confirm_label": texts.EXIT_BUTTON,
        "form_id": "f-dialog",
        "hidden": [("von", membership.unit.key)],
        "choice": _choice("ebene", str(texts.EXIT_LEGEND), found),
    }


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


def admission(entries: list[dict], unit: Unit) -> tuple[list[Hit], tuple[str, str] | None]:
    """Treffer und Meldung im Dialog „Person aufnehmen“ aus den Treffern der Rechteprüfung (#285).

    Aufnehmen lässt sich nur, wer noch nirgends Mitglied ist; nur sie stehen mit dem Knopf
    „Aufnehmen“ in der Liste, ohne Organisation darunter. Wer im eigenen Bereich oder als die
    Person selbst schon Mitglied ist, bekommt „… ist schon Mitglied in …“ (PG5); wer außerhalb
    Mitglied ist, den Satz ohne die Organisation (PK-18, PK-16). Ob es klappt, entscheidet erst
    `Rights.admit()`.
    """
    found, notice = [], None
    for entry in entries:
        name = display_name(entry["first_name"], entry["last_name"], entry["scout_name"]) or entry["username"]
        if entry["unit_label"]:
            notice = notice or ("info", str(texts.ALREADY_MEMBER % {"person": name, "unit": entry["unit_label"]}))
        elif entry["elsewhere"]:
            notice = notice or ("warning", str(texts.OTHER_ORGANISATION))
        else:
            full_name = _full_name(entry)
            found.append(Hit(key=entry["key"], name=entry["scout_name"] or full_name or entry["username"],
                             extra=full_name if entry["scout_name"] else "", place="", note="", warning="", hint=""))
    return found, notice


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
