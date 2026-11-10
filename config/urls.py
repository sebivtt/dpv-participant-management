"""Adressen des Tools.

Öffentlich, also ohne Login erreichbar, sind nur die Login-Seiten (accounts/views.py).
Alles andere schützt LoginRequiredMiddleware; der Rundumtest in tests/test_rundumtest.py prüft das.
"""

from django.urls import path, register_converter

from access.keys import KEY_CONVERTER, KeyConverter
from accounts import views as accounts_views
from core.views import (
    building_blocks,
    federation_appoint,
    federation_appoint_lead,
    federation_remove,
    federation_search,
    federation_search_lead,
    organisation,
    organisation_admit,
    organisation_admit_search,
    organisation_appoint,
    organisation_remove,
    organisation_search,
    organisation_suggestions,
    organisation_unit,
    profile,
    profile_leave_team,
    profile_scout_name,
    start,
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
    path("organisation/<key:unit>/aufnehmen/", organisation_admit, name="organisation_admit"),
    path("organisation/<key:unit>/aufnehmen/suchen/", organisation_admit_search, name="organisation_admit_search"),
    path("bausteine/", building_blocks, name="building_blocks"),
    path("anmelden/", accounts_views.login_page, name="account_login"),
    path("abmelden/", accounts_views.logout, name="account_logout"),
    # Die Namen erwartet allauth; es baut damit die Adressen für Start und Rückkehr des Logins.
    path("anmelden/<str:provider_id>/start/", accounts_views.keycloak_login, name="openid_connect_login"),
    path("anmelden/<str:provider_id>/zurueck/", accounts_views.keycloak_callback, name="openid_connect_callback"),
]
