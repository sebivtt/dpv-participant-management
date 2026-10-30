"""Meldungen zu den Einheiten (#88), übersetzbar (NFA-02).

Nach außen heißen Einheiten „Organisation“ (Nachklärung P2 vom 22.10.2026, Frage 7); die
Meldungen nennen deshalb immer die Ebene (Verband, Bund, Ring, Stamm, Gruppe), nie „Einheit“.
"""

from django.utils.translation import gettext_lazy, ngettext_lazy

# Regeln beim Speichern
NAME_EMPTY = gettext_lazy("Der Name darf nicht leer sein.")
FEDERATION_HAS_NO_PARENT = gettext_lazy("Über dem Verband gibt es nichts.")
ASSOCIATION_PARENT = gettext_lazy("Ein Bund hängt am Verband.")
RING_PARENT = gettext_lazy("Ein Ring hängt an einem Bund.")
TROOP_PARENT = gettext_lazy("Ein Stamm hängt an einem Ring oder direkt an einem Bund.")
GROUP_PARENT = gettext_lazy("Eine Gruppe hängt an einem Stamm.")
KIND_FIXED = gettext_lazy("Die Ebene lässt sich nachträglich nicht ändern.")
STAYS_IN_ASSOCIATION = gettext_lazy("Ein Ring oder Stamm bleibt in seinem Bund.")
ONLY_ASSOCIATION_HAS_RINGS = gettext_lazy("Nur ein Bund hat Ringe.")
RINGS_SWITCHED_OFF = gettext_lazy(
    "Im Bund „%(association)s“ ist „hat Ringe“ ausgeschaltet. Ringe gibt es nur in einem Bund mit Ringen."
)
NEW_TROOP_NEEDS_RING = gettext_lazy("Im Bund „%(association)s“ hängt jeder neue Stamm in einem Ring.")
STILL_HAS_RINGS = gettext_lazy(
    "Der Bund „%(association)s“ hat noch Ringe. „Hat Ringe“ lässt sich erst ausschalten, wenn er keinen Ring mehr hat."
)
FEDERATION_EXISTS = gettext_lazy("Es gibt schon einen Verband: „%(name)s“.")
ASSOCIATION_EXISTS = gettext_lazy("Den Bund „%(name)s“ gibt es schon.")
RING_EXISTS = gettext_lazy("Im Bund „%(association)s“ gibt es schon den Ring „%(name)s“.")
TROOP_EXISTS = gettext_lazy("Im Bund „%(association)s“ gibt es schon den Stamm „%(name)s“.")
GROUP_EXISTS = gettext_lazy("Im Stamm „%(troop)s“ gibt es schon die Gruppe „%(name)s“.")

# Protokoll der Strukturänderungen (#131)
LOGGED_GROUP_IN_TROOP = gettext_lazy("%(unit)s (%(troop)s)")
# Alter und neuer Wert von „hat Ringe“
SWITCH_ON = gettext_lazy("ein")
SWITCH_OFF = gettext_lazy("aus")
LOG_LOCKED = gettext_lazy("Einträge im Protokoll der Strukturänderungen lassen sich nicht ändern oder löschen.")

# Befehle für Admins
NO_FEDERATION = gettext_lazy("Es gibt noch keinen Verband.")
CREATE_FEDERATION_FIRST = gettext_lazy("Es gibt noch keinen Verband. Lege ihn zuerst mit „federation create“ an.")
FEDERATION_CREATED = gettext_lazy("Den Verband „%(name)s“ gibt es jetzt.")
FEDERATION_RENAMED = gettext_lazy("Der Verband heißt jetzt „%(name)s“.")
ASSOCIATION_CREATED = gettext_lazy("Den Bund „%(name)s“ gibt es jetzt.")
RINGS_ON_AT_CREATION = gettext_lazy("„Hat Ringe“ ist eingeschaltet.")
ASSOCIATION_RENAMED = gettext_lazy("Der Bund „%(old)s“ heißt jetzt „%(new)s“.")
ASSOCIATION_UNKNOWN = gettext_lazy("Den Bund „%(name)s“ gibt es nicht.")
RINGS_NOW_ON = gettext_lazy("Im Bund „%(name)s“ ist „hat Ringe“ jetzt eingeschaltet.")
RINGS_NOW_OFF = gettext_lazy("Im Bund „%(name)s“ ist „hat Ringe“ jetzt ausgeschaltet.")
LIST_FEDERATION = gettext_lazy("Verband: %(name)s")
LIST_ASSOCIATIONS = gettext_lazy("Bünde:")
LIST_NO_ASSOCIATIONS = gettext_lazy("Bünde: noch keine")
LIST_WITH_RINGS = gettext_lazy("  %(name)s (hat Ringe)")
LIST_WITHOUT_RINGS = gettext_lazy("  %(name)s (ohne Ringe)")

# Seite „Organisation“ (#189); Namen von Organisationen ohne Anführungszeichen wie in den Szenarien
MARK_COVERS = gettext_lazy("Du springst ein")
MARK_READ = gettext_lazy("nur lesen")
MARK_LOCKED = gettext_lazy("gesperrt")
# Der Knopf oben am Handy: zurück zur Gliederung, für die Verbandsleitung zur Seite „Verband“ (#218).
BACK_TO_OUTLINE = gettext_lazy("Gliederung")
BACK_TO_FEDERATION = gettext_lazy("Verband")
LEADS_LINE = gettext_lazy("%(role)s: %(names)s")
LOCKED_NAME = gettext_lazy("%(name)s (gesperrt)")
NO_LEAD_SHORT = gettext_lazy("keine %(role)s")
NO_LEAD = gettext_lazy("%(unit)s hat keine %(role)s.")
NO_LEAD_COVERED = gettext_lazy(
    "%(unit)s hat keine %(role)s. Bis eine benannt ist, springt die %(cover_role)s von %(cover)s ein."
)
# Am Satzanfang mit der Art, damit es wie ein ganzer Satz klingt (Sebastian, 28.10.2026, #189).
WITH_KIND = {
    "association": gettext_lazy("Der Bund %(unit)s"),
    "ring": gettext_lazy("Der Ring %(unit)s"),
    "troop": gettext_lazy("Der Stamm %(unit)s"),
    "group": gettext_lazy("Die Gruppe %(unit)s"),
}
KIND_IN = gettext_lazy("%(kind)s in %(parent)s")
NOTHING_BELOW = gettext_lazy("%(unit)s hat noch keine %(children)s.")
GROUPS = gettext_lazy("Gruppen")
TROOPS = gettext_lazy("Stämme")
RINGS = gettext_lazy("Ringe")

# Leitung benennen (#190), Wortlaut nach den Szenarien und den Entscheidungen bei der Umsetzung
APPOINT_TITLE = gettext_lazy("%(role)s benennen")
APPOINT_FOR = gettext_lazy("für %(unit)s")
SUGGESTIONS_TITLE = gettext_lazy("Vorschläge aus deinem Bereich")
NO_SUGGESTIONS = gettext_lazy(
    "Keine Vorschläge aus deinem Bereich. Mit „Suchen“ findest du andere über die genaue Mail oder den Benutzernamen."
)
HITS_TITLE = gettext_lazy("Treffer")
ELSEWHERE = gettext_lazy("schon woanders Mitglied")
NOWHERE = gettext_lazy("noch nirgends Mitglied")
BECOMES_MEMBER = gettext_lazy("Mit dem Benennen wird die Person Mitglied von %(unit)s.")
NO_ACCOUNT = gettext_lazy("Kein Konto gefunden. Die Person muss sich zuerst einmal im Tool anmelden.")
SEARCH_LIMIT = ngettext_lazy(
    "Du hast in kurzer Zeit sehr oft gesucht. Bitte versuche es in %(minutes)s Minute noch einmal.",
    "Du hast in kurzer Zeit sehr oft gesucht. Bitte versuche es in %(minutes)s Minuten noch einmal.",
    "minutes",
)
NOT_YOURSELF = gettext_lazy("Dir selbst kannst du keine Rolle geben. Das kann eine andere Leitung von %(unit)s oder darüber.")
MEMBER_ELSEWHERE = gettext_lazy(
    "Diese Person gehört schon zu einer anderen Organisation und kann hier keine Leitung werden. Sie kann bei ihrer "
    "bisherigen Leitung den Wechsel veranlassen."
)
NOT_ON_PATH = gettext_lazy("%(person)s ist Mitglied in %(unit)s und kann deshalb keine Leitung bei %(target)s sein.")
ALREADY_LEAD = gettext_lazy("%(person)s ist schon %(role)s von %(unit)s.")
APPOINTED = gettext_lazy("%(person)s ist jetzt %(role)s von %(unit)s.")
# Das Ziel mit seiner Art davor, z. B. „Stamm Zugvögel“ (Sebastian, 28.10.2026, bei der Umsetzung von #190).
KIND_AND_NAME = {
    "association": gettext_lazy("Bund %(unit)s"),
    "ring": gettext_lazy("Ring %(unit)s"),
    "troop": gettext_lazy("Stamm %(unit)s"),
    "group": gettext_lazy("Gruppe %(unit)s"),
}

# Leitung entfernen und Rolle abgeben (#191), Wortlaut nach den Szenarien C1 bis C13 und Sebastians
# Antworten bei der Umsetzung vom 28.10.2026
REMOVE_BUTTON = gettext_lazy("Entfernen")
GIVE_UP_BUTTON = gettext_lazy("Rolle abgeben")
REMOVE_QUESTION = gettext_lazy("%(person)s als %(role)s von %(unit)s entfernen?")
GIVE_UP_QUESTION = gettext_lazy("Deine Rolle als %(role)s von %(unit)s abgeben?")
GIVE_UP_LOSES = gettext_lazy("Du verlierst damit sofort den Zugriff auf die Personen von %(unit)s.")
LAST_LEAD_COVERED = gettext_lazy(
    "Danach hat %(unit)s keine %(role)s mehr. Bis eine neue benannt ist, springt die Leitung von %(cover)s ein."
)
# Für eine Gruppe, einen Stamm oder Ring, wenn bis zum Bund niemand Leitung ist (Antwort 2).
LAST_LEAD_NOBODY = gettext_lazy("Danach hat %(unit)s keine %(role)s mehr, und niemand springt ein.")
LAST_ASSOCIATION_LEAD = gettext_lazy(
    "Danach hat %(unit)s keine %(role)s mehr, und niemand springt ein. Eine neue %(role)s kann nur die "
    "Verbandsleitung benennen."
)
ANYWAY_REMOVE = gettext_lazy("Trotzdem entfernen?")
ANYWAY_GIVE_UP = gettext_lazy("Trotzdem abgeben?")
# Wer einspringt, wie in C1, C5 und C6: „Stamm Walhall“, „Ring Küste“, ein Bund nur mit seinem Namen.
COVER_NAME = {
    "association": gettext_lazy("%(unit)s"),
    "ring": KIND_AND_NAME["ring"],
    "troop": KIND_AND_NAME["troop"],
}
REMOVED = gettext_lazy("%(person)s ist nicht mehr %(role)s von %(unit)s.")
GAVE_UP = gettext_lazy("Du bist nicht mehr %(role)s von %(unit)s.")

# Seite „Verband“ der Verbandsleitung (#94), Wortlaute nach dem Issue und den Szenarien V1 bis VG4
APPOINT_FEDERATION_LEAD = gettext_lazy("Verbandsleitung benennen")
APPOINT_TEAM = gettext_lazy("Teammitglied benennen")
APPOINT_FOR_TEAM = gettext_lazy("für das DPV-Veranstaltungsteam")
APPOINT_FOR_FEDERATION = gettext_lazy("für den Verband")
NOT_YOURSELF_FEDERATION = gettext_lazy("Dir selbst kannst du keine Rolle geben. Das kann eine andere Verbandsleitung.")
FEDERATION_APPOINTED = {
    "association_lead": APPOINTED,
    "federation_lead": gettext_lazy("%(person)s ist jetzt Verbandsleitung."),
    "event_team": gettext_lazy("%(person)s ist jetzt im DPV-Veranstaltungsteam."),
}
FEDERATION_ALREADY = {
    "association_lead": ALREADY_LEAD,
    "federation_lead": gettext_lazy("%(person)s ist schon Verbandsleitung."),
    "event_team": gettext_lazy("%(person)s ist schon im DPV-Veranstaltungsteam."),
}
FEDERATION_REMOVE_QUESTION = {
    "federation_lead": gettext_lazy("%(person)s als Verbandsleitung entfernen?"),
    "event_team": gettext_lazy("%(person)s aus dem DPV-Veranstaltungsteam entfernen?"),
}
FEDERATION_GIVE_UP_QUESTION = {
    "federation_lead": gettext_lazy("Deine Rolle als Verbandsleitung abgeben?"),
    "event_team": gettext_lazy("Deine Rolle im DPV-Veranstaltungsteam abgeben?"),
}
FEDERATION_REMOVED = {
    "federation_lead": gettext_lazy("%(person)s ist nicht mehr Verbandsleitung."),
    "event_team": gettext_lazy("%(person)s ist nicht mehr im DPV-Veranstaltungsteam."),
}
FEDERATION_GAVE_UP = {
    "federation_lead": gettext_lazy("Du bist nicht mehr Verbandsleitung."),
    "event_team": gettext_lazy("Du bist nicht mehr im DPV-Veranstaltungsteam."),
}
LAST_FEDERATION_LEAD = gettext_lazy("Danach gibt es keine Verbandsleitung mehr. Eine neue kann nur ein Admin benennen.")
