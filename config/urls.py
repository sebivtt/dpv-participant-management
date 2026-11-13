"""Adressen des Tools.

Öffentlich, also ohne Login erreichbar, sind nur die Login-Seiten (accounts/views.py).
Alles andere schützt LoginRequiredMiddleware; der Rundumtest in tests/test_rundumtest.py prüft das.
"""

from django.urls import path, register_converter

from access.keys import KEY_CONVERTER, KeyConverter
from accounts import views as accounts_views
from core.views import (
    building_blocks,
    event_create,
    event_edit,
    event_page,
    events,
    federation_appoint,
    federation_appoint_lead,
    federation_remove,
    federation_search,
    federation_search_lead,
    organisation,
    organisation_add_managed,
    organisation_admit,
    organisation_admit_search,
    organisation_appoint,
    organisation_create,
    organisation_delete_managed,
    organisation_edit,
    organisation_edit_managed,
    organisation_expel,
    organisation_expel_managed,
    organisation_move,
    organisation_move_managed,
    organisation_remove,
    organisation_remove_displayed,
    organisation_search,
    organisation_suggestions,
    organisation_support,
    organisation_unit,
    profile,
    profile_leave,
    profile_leave_team,
    profile_scout_name,
    start,
    support_end,
)

# Eigene Fehlerseite statt der von Django: ohne technische Einzelheiten, mit Fehlernummer (#6).
handler500 = "core.errors.server_error"

# Einträge stehen in Adressen nur mit ihrer zufälligen Kennung: path("person/<key:person>/", …) (#64).
register_converter(KeyConverter, KEY_CONVERTER)

urlpatterns = [
    path("", start, name="start"),
    path("profil/", profile, name="profile"),
    path("profil/fahrtenname/", profile_scout_name, name="profile_scout_name"),
    path("profil/team-abgeben/", profile_leave_team, name="profile_leave_team"),
    path("profil/austreten/", profile_leave, name="profile_leave"),
    path("organisation/", organisation, name="organisation"),
    # Seite „Verband“ der Verbandsleitung (#94): der Verband mit seiner Kennung, die Rolle im Verband fest in der
    # Adresse, nie als frei wählbarer Teil.
    *(
        entry
        for slug in ("verbandsleitung", "team")
        for entry in (
            path(f"organisation/verband/<key:unit>/{slug}/benennen/", federation_appoint, {"role": slug},
                 name=f"federation_appoint_{slug}"),
            path(f"organisation/verband/<key:unit>/{slug}/benennen/suchen/", federation_search, {"role": slug},
                 name=f"federation_search_{slug}"),
        )
    ),
    path("organisation/verband/bund/<key:unit>/benennen/", federation_appoint_lead, name="federation_appoint_lead"),
    path("organisation/verband/bund/<key:unit>/benennen/suchen/", federation_search_lead, name="federation_search_lead"),
    path("organisation/verband/entfernen/<key:role>/", federation_remove, name="federation_remove"),
    path("organisation/<key:unit>/", organisation_unit, name="organisation_unit"),
    path("organisation/<key:unit>/benennen/", organisation_appoint, name="organisation_appoint"),
    path("organisation/<key:unit>/benennen/suchen/", organisation_search, name="organisation_search"),
    path("organisation/<key:unit>/benennen/vorschlaege/", organisation_suggestions, name="organisation_suggestions"),
    path("organisation/<key:unit>/entfernen/<key:role>/", organisation_remove, name="organisation_remove"),
    # Angezeigte Leitungsrollen verwalteter Personen (#99): eigene Adresse neben der für Rollen mit Konto.
    path("organisation/<key:unit>/entfernen-anzeige/<key:role>/", organisation_remove_displayed,
         name="organisation_remove_displayed"),
    path("organisation/<key:unit>/aufnehmen/", organisation_admit, name="organisation_admit"),
    path("organisation/<key:unit>/aufnehmen/suchen/", organisation_admit_search, name="organisation_admit_search"),
    path("organisation/<key:unit>/austragen/<key:person>/", organisation_expel, name="organisation_expel"),
    path("organisation/<key:unit>/verschieben/<key:person>/", organisation_move, name="organisation_move"),
    path("organisation/<key:unit>/anlegen/", organisation_create, name="organisation_create"),
    path("organisation/<key:unit>/bearbeiten/", organisation_edit, name="organisation_edit"),
    # Verwaltete Personen (#117): Anlegen und Bearbeiten als Dialoge mit eigener Adresse, die Organisation aus der Adresse.
    path("organisation/<key:unit>/verwaltete-person/anlegen/", organisation_add_managed, name="organisation_add_managed"),
    path("organisation/<key:unit>/verwaltete-person/<key:person>/bearbeiten/", organisation_edit_managed,
         name="organisation_edit_managed"),
    # Verschieben, Austragen und Löschen verwalteter Personen (#118), wie die Dialoge oben mit eigener Adresse.
    path("organisation/<key:unit>/verwaltete-person/<key:person>/verschieben/", organisation_move_managed,
         name="organisation_move_managed"),
    path("organisation/<key:unit>/verwaltete-person/<key:person>/austragen/", organisation_expel_managed,
         name="organisation_expel_managed"),
    path("organisation/<key:unit>/verwaltete-person/<key:person>/loeschen/", organisation_delete_managed,
         name="organisation_delete_managed"),
    # Support-Zugang der Admins (#92): Starten an der Seite der Organisation, Beenden im Balken auf jeder Seite.
    path("organisation/<key:unit>/support-zugang/", organisation_support, name="organisation_support"),
    path("support-zugang/beenden/", support_end, name="support_end"),
    # Veranstaltungen (#100, Probe in P2): Liste, „Veranstaltung erstellen“, Seite und „… bearbeiten“ je Veranstaltung.
    path("veranstaltungen/", events, name="events"),
    path("veranstaltungen/erstellen/", event_create, name="event_create"),
    path("veranstaltungen/<key:event>/", event_page, name="event_page"),
    path("veranstaltungen/<key:event>/bearbeiten/", event_edit, name="event_edit"),
    path("bausteine/", building_blocks, name="building_blocks"),
    path("anmelden/", accounts_views.login_page, name="account_login"),
    path("abmelden/", accounts_views.logout, name="account_logout"),
    # Die Namen erwartet allauth; es baut damit die Adressen für Start und Rückkehr des Logins.
    path("anmelden/<str:provider_id>/start/", accounts_views.keycloak_login, name="openid_connect_login"),
    path("anmelden/<str:provider_id>/zurueck/", accounts_views.keycloak_callback, name="openid_connect_callback"),
]
