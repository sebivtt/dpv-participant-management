"""Adressen des Tools."""

from django.urls import path

from core.views import start

urlpatterns = [
    path("", start, name="start"),
]
