"""Adressen des Tools."""

from django.urls import path

from core.views import start

# Eigene Fehlerseite statt der von Django: ohne technische Einzelheiten, mit Fehlernummer (#6).
handler500 = "core.errors.server_error"

urlpatterns = [
    path("", start, name="start"),
]
