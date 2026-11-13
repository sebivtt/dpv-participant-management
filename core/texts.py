"""Meldungen des Befehls für Testdaten (#103), übersetzbar (NFA-02)."""

from django.utils.translation import gettext_lazy

NOT_ALLOWED = gettext_lazy(
    "Der Befehl läuft nur lokal oder in der Testumgebung. Die Einstellungen sagen weder das eine noch das "
    "andere; es wurde nichts gelöscht. Auf dem eigenen Rechner: LOCAL_ENVIRONMENT=1 in die Umgebungsdatei "
    "eintragen (README.md)."
)
REALM_MISSING = gettext_lazy(
    "Die Datei mit den erfundenen Konten fehlt (%(path)s). Es wurde nichts gelöscht."
)
DONE = gettext_lazy(
    "Testdaten angelegt: %(units)s Organisationen, %(roles)s Rollen und %(managed)s verwaltete Personen. "
    "Alle Daten außer den Konten wurden vorher gelöscht, auch die Protokolle."
)
ADMINS_KEPT = gettext_lazy("Wieder Admin wie vor dem Lauf: %(usernames)s.")
LOG_IN_FIRST = gettext_lazy(
    "Ohne Rolle, weil noch nie im Tool angemeldet: %(usernames)s. Diese Konten müssen sich zuerst einmal "
    "anmelden; danach den Befehl erneut ausführen."
)
USERNAME_TAKEN = gettext_lazy(
    "Ohne Rolle, weil der Benutzername im Tool schon zu einem Konto mit anderer Keycloak-Kennung gehört: "
    "%(usernames)s. Der Befehl übernimmt nie ein Konto über den Benutzernamen; abhilft „Lokale Datenbank neu "
    "anlegen“ im README."
)
NO_CREATOR = gettext_lazy(
    "Ohne verwaltete Personen, weil dort niemand mit Konto sie anlegen darf: %(units)s."
)
