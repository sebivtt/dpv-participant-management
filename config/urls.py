"""Adressen des Tools.

Öffentlich, also ohne Login erreichbar, sind nur die Login-Seiten (accounts/views.py).
Alles andere schützt LoginRequiredMiddleware; der Rundumtest in tests/test_login.py prüft das.
"""

from django.urls import path

from accounts import views as accounts_views
from core.views import pattern_library, start

# Eigene Fehlerseite statt der von Django: ohne technische Einzelheiten, mit Fehlernummer (#6).
handler500 = "core.errors.server_error"

urlpatterns = [
    path("", start, name="start"),
    path("muster/", pattern_library, name="pattern_library"),
    path("anmelden/", accounts_views.login_page, name="account_login"),
    path("abmelden/", accounts_views.logout, name="account_logout"),
    # Die Namen erwartet allauth; es baut damit die Adressen für Start und Rückkehr des Logins.
    path("anmelden/<str:provider_id>/start/", accounts_views.keycloak_login, name="openid_connect_login"),
    path("anmelden/<str:provider_id>/zurueck/", accounts_views.keycloak_callback, name="openid_connect_callback"),
]
