"""Meldungen zu den Rollen (#89), übersetzbar (NFA-02).

Nach außen heißen Einheiten „Organisation“ (Nachklärung P2 vom 22.10.2026, Frage 7). Die Namen
der Einheiten stehen in Anführungszeichen und ohne Artikel, weil sich ein Name wie „Zugvögel“
nicht automatisch beugen lässt („bei den Zugvögeln“).
"""

from django.utils.translation import gettext_lazy

# Rolle an der passenden Ebene
WRONG_LEVEL = {
    "member": gettext_lazy("Mitglied ist man in einer Gruppe, einem Stamm, einem Ring oder einem Bund, nie im Verband."),
    "group_lead": gettext_lazy("Eine Gruppenleitung gehört zu einer Gruppe."),
    "troop_lead": gettext_lazy("Eine Stammesleitung gehört zu einem Stamm."),
    "ring_lead": gettext_lazy("Eine Ringleitung gehört zu einem Ring."),
    "association_lead": gettext_lazy("Eine Bundesleitung gehört zu einem Bund."),
    "federation_lead": gettext_lazy("Die Verbandsleitung gehört zum Verband."),
    "event_team": gettext_lazy("Das DPV-Veranstaltungsteam gehört zum Verband."),
    "admin": gettext_lazy("Admin ist eine Rolle ohne Organisation."),
}
ROLE_FIXED = gettext_lazy("Bei einer Rolle lässt sich nur die Organisation einer Mitgliedschaft ändern.")

# Doppelte Rollen
ALREADY_ADMIN = gettext_lazy("%(person)s ist schon Admin.")
ALREADY_HAS_ROLE = gettext_lazy("%(person)s ist schon %(role)s in %(unit)s.")
SECOND_MEMBERSHIP = gettext_lazy(
    "%(person)s ist schon Mitglied in %(unit)s. Mitglied ist man in höchstens einer Organisation."
)

# Pfad von Mitgliedschaft und Leitung
OUTSIDE_PATH = gettext_lazy("%(person)s ist Mitglied in %(unit)s und kann deshalb keine Leitung in %(target)s sein.")
REMOVE_ROLE_FIRST = gettext_lazy("%(person)s ist noch %(roles)s. Diese Rolle muss zuerst entfernt werden.")
REMOVE_ROLES_FIRST = gettext_lazy("%(person)s ist noch %(roles)s. Diese Rollen müssen zuerst entfernt werden.")
# Austreten und Austragen (#65); Seiten prüfen vorher, die Meldungen sind die letzte Sicherung.
ONLY_MEMBERSHIP_LEAVES = gettext_lazy("Austreten geht nur aus einer Mitgliedschaft.")
NOT_IN_CHAIN = gettext_lazy("Austreten geht nur aus der eigenen Organisation oder einer darüber.")
ROLE_IN_UNIT = gettext_lazy("%(role)s in %(unit)s")
AND = gettext_lazy("und")

# Wie eine Einheit in Meldungen heißt; bei Gruppen mit dem Stamm, weil Gruppennamen sich oft wiederholen.
UNIT = gettext_lazy("„%(unit)s“")
GROUP_IN_TROOP = gettext_lazy("„%(unit)s“ (%(troop)s)")

# Protokoll der Rollenänderungen (#91); „Befehl auf dem Server“ steht in core/actors.py.
LOG_LOCKED = gettext_lazy("Einträge im Protokoll der Rollenänderungen lassen sich nicht ändern oder löschen.")

# Befehl für Admins
UNKNOWN_USERNAME = gettext_lazy(
    "Kein Konto mit diesem Benutzernamen. Die Person muss sich zuerst einmal im Tool anmelden."
)
ADMIN_GRANTED = gettext_lazy("%(username)s ist jetzt Admin.")
ADMIN_ALREADY = gettext_lazy("%(username)s ist schon Admin.")
ADMIN_REVOKED = gettext_lazy("%(username)s ist jetzt kein Admin mehr.")
NOT_ADMIN = gettext_lazy("%(username)s ist kein Admin.")

# Befehl für die Verbandsleitung (#94)
FEDERATION_LEAD_GRANTED = gettext_lazy("%(username)s ist jetzt Verbandsleitung.")
FEDERATION_LEAD_ALREADY = gettext_lazy("%(username)s ist schon Verbandsleitung.")
FEDERATION_LEAD_REVOKED = gettext_lazy("%(username)s ist jetzt keine Verbandsleitung mehr.")
NOT_FEDERATION_LEAD = gettext_lazy("%(username)s ist keine Verbandsleitung.")
