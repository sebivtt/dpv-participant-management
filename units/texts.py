"""Meldungen zu den Einheiten (#88), übersetzbar (NFA-02).

Nach außen heißen Einheiten „Organisation“ (Nachklärung P2 vom 22.10.2026, Frage 7); die
Meldungen nennen deshalb immer die Ebene (Verband, Bund, Ring, Stamm, Gruppe), nie „Einheit“.
"""

from django.utils.translation import gettext_lazy

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
