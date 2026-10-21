"""Seiten der App „core“."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def start(request: HttpRequest) -> HttpResponse:
    """Startseite. Zeigt vorerst nur, dass das Tool läuft; mit #5 kommt sie hinter den Login."""
    return render(request, "core/start.html")
