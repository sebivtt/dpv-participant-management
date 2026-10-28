"""Adressen des Tools.

Öffentlich, also ohne Login erreichbar, sind nur die Login-Seiten (accounts/views.py).
Alles andere schützt LoginRequiredMiddleware; der Rundumtest in tests/test_login.py prüft das.
"""

from django.urls import path, register_converter

from access.keys import KEY_CONVERTER, KeyConverter
from accounts import views as accounts_views
from core.views import building_blocks, organisation, organisation_unit, profile, profile_scout_name, start

# Eigene Fehlerseite statt der von Django: ohne technische Einzelheiten, mit Fehlernummer (#6).
handler500 = "core.errors.server_error"

# Einträge stehen in Adressen nur mit ihrer zufälligen Kennung: path("person/<key:person>/", …) (#64).
register_converter(KeyConverter, KEY_CONVERTER)

urlpatterns = [
    path("", start, name="start"),
    path("profil/", profile, name="profile"),
    path("profil/fahrtenname/", profile_scout_name, name="profile_scout_name"),
    path("organisation/", organisation, name="organisation"),
    path("organisation/<key:unit>/", organisation_unit, name="organisation_unit"),
    path("bausteine/", building_blocks, name="building_blocks"),
    path("anmelden/", accounts_views.login_page, name="account_login"),
    path("abmelden/", accounts_views.logout, name="account_logout"),
    # Die Namen erwartet allauth; es baut damit die Adressen für Start und Rückkehr des Logins.
    path("anmelden/<str:provider_id>/start/", accounts_views.keycloak_login, name="openid_connect_login"),
    path("anmelden/<str:provider_id>/zurueck/", accounts_views.keycloak_callback, name="openid_connect_callback"),
]
