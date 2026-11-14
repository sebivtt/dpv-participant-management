"""Sprungmarken zum Abschnitt einer Seite für Dialoge mit eigener Adresse (#220).

Jeder Dialog hat eine eigene Adresse (#190); Öffnen, Schließen und Speichern laden die Seite neu.
Ohne Skript springt die Seite dabei zum Abschnitt, in dem der Knopf steht, der den Dialog geöffnet
hat: Die Adressen des Dialogs (Knopf, ×, „Abbrechen“ und die Formulare) tragen dazu „#abschnitt-…“.
Nach dem Speichern leitet der Server ohne Sprungmarke weiter; der Browser behält dann die des
Formulars. Mit Skript merkt sich die Seite stattdessen, wie weit sie gerollt war, und entfernt diese
Sprungmarken vor dem Laden (core/static/core/app.js, „Stelle merken“). Steht der Knopf ganz oben auf
der Seite, braucht der Dialog keine. Die Abschnitte tragen die Kennung in ihrer Vorlage
(`id="abschnitt-…"`); tests/test_stelle_merken.py prüft beides zusammen.
"""

# Die Abschnitte, aus denen Dialoge geöffnet werden: Seite einer Organisation, „Mein Profil“, „Verband“
LEADS = "leitungen"
BELOW = "darunter"
PERSONS = "personen"
ROLES = "rollen"
FEDERATION_LEADS = "verbandsleitung"
TEAM = "team"


def association(unit) -> str:
    """Der Abschnitt eines Bundes auf der Seite „Verband“; davon gibt es dort mehrere."""
    return f"bund-{unit.key}"


def to_section(href: str, section: str | None) -> str:
    """Die Adresse `href` mit der Sprungmarke zum Abschnitt `section`; ohne Abschnitt unverändert."""
    return f"{href}#abschnitt-{section}" if section else href
