"""Texte zu Kreisen (#381), übersetzbar (NFA-02).

Wortlaute aus dem Text von #381, den Szenarien vom 17.11.2026 und, für kurze Meldungen und Sätze in Rückfragen, aus dem
Zielbild `docs/zielbilder/kreise.html` (Nachklärung vom 17.11.2026).
"""

from django.utils.translation import gettext_lazy, ngettext_lazy

# Seitenleiste und Seite „Kreise“
NAV = gettext_lazy("Kreise")
INVITATIONS = gettext_lazy("Einladungen")
NO_INVITATIONS = gettext_lazy("Du hast keine offenen Einladungen.")
MY_CIRCLES = gettext_lazy("Meine Kreise")
NONE_YET = gettext_lazy("Du bist noch in keinem Kreis. Mit „Kreis anlegen“ oben bildest du zum Beispiel ein Planungsteam.")
MANAGING = gettext_lazy("Verwaltend")
MEMBER_COUNT = ngettext_lazy("%(count)s Mitglied", "%(count)s Mitglieder", "count")

# Kreis anlegen
CREATE_TITLE = gettext_lazy("Kreis anlegen")
CREATE_SUBTITLE = gettext_lazy("Nur Mitglieder sehen den Kreis. Du verwaltest ihn.")
NAME_LABEL = gettext_lazy("Name")
NAME_EMPTY = gettext_lazy("Bitte gib dem Kreis einen Namen.")
NAME_TOO_LONG = gettext_lazy("Der Name darf höchstens 60 Zeichen lang sein.")
DESCRIPTION_LABEL = gettext_lazy("Beschreibung")
DESCRIPTION_TOO_LONG = gettext_lazy("Die Beschreibung darf höchstens 500 Zeichen lang sein.")
CREATED = gettext_lazy("Der Kreis „%(circle)s“ ist angelegt.")

# Seite eines Kreises
MEMBERS = gettext_lazy("Mitglieder")
OPEN_INVITATIONS = gettext_lazy("Offene Einladungen")
NO_OPEN_INVITATIONS = gettext_lazy("Keine offenen Einladungen.")
ONLY_MANAGERS = gettext_lazy("Nur Verwaltende sehen offene Einladungen.")
INVITATION_TITLE = gettext_lazy("Einladung")
INVITED_HINT = gettext_lazy("Wer im Kreis ist, siehst du, sobald du die Einladung annimmst.")

# Person einladen
INVITE_TITLE = gettext_lazy("Person einladen")
INVITE_IN = gettext_lazy("in %(circle)s")
SEARCH_LABEL = gettext_lazy("Mail oder Benutzername")
SEARCH_HELP = gettext_lazy("Die Person muss sich schon einmal im Tool angemeldet haben. Gefunden wird sie nur über die "
                           "genaue Mail oder den genauen Benutzernamen. Sie wird erst Mitglied, wenn sie die Einladung "
                           "annimmt.")
NO_ACCOUNT = gettext_lazy("Kein Konto gefunden. Prüfe die Schreibweise der Mail oder des Benutzernamens. Die Person muss "
                          "sich schon einmal im Tool angemeldet haben.")
HITS_TITLE = gettext_lazy("Gefunden")
INVITE_BUTTON = gettext_lazy("Einladen")
YOURSELF = gettext_lazy("Das bist du.")
ALREADY_MEMBER = gettext_lazy("%(name)s ist schon Mitglied.")
ALREADY_INVITED = gettext_lazy("%(name)s ist schon eingeladen.")
NO_ASSIGNMENT = gettext_lazy("%(name)s gehört noch keiner Organisation an und kann deshalb noch nicht eingeladen werden.")
INVITED = gettext_lazy("%(name)s ist eingeladen.")

# Zurücknehmen, Annehmen, Ablehnen
WITHDRAW_BUTTON = gettext_lazy("Zurücknehmen")
WITHDRAW_TITLE = gettext_lazy("Einladung an %(name)s zurücknehmen?")
WITHDRAW_TEXT = gettext_lazy("Die Einladung verschwindet. Du kannst die Person später wieder einladen.")
WITHDRAWN = gettext_lazy("Die Einladung an %(name)s ist zurückgenommen.")
INVITES_YOU = gettext_lazy("%(name)s lädt dich ein.")
ACCEPT_BUTTON = gettext_lazy("Annehmen")
DECLINE_BUTTON = gettext_lazy("Ablehnen")
ACCEPTED = gettext_lazy("Du bist jetzt Mitglied von „%(circle)s“.")
DECLINED = gettext_lazy("Du hast die Einladung in „%(circle)s“ abgelehnt.")
GONE = gettext_lazy("Diese Einladung gibt es nicht mehr.")

# Hinweis auf der Startseite (GRP-02): je offene Einladung einer
START_TITLE = gettext_lazy("Einladung in einen Kreis")
START_TEXT = gettext_lazy("%(name)s lädt dich in den Kreis „%(circle)s“ ein.")
START_LINK = gettext_lazy("Zur Einladung")
