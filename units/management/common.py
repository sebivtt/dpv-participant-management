"""Gemeinsames der Befehle für Verband und Bünde (#88)."""

from collections.abc import Iterator
from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.db.models import Value
from django.db.models.functions import Lower

from units import texts
from units.models import Kind, Unit


@contextmanager
def refuse_with_reason() -> Iterator[None]:
    """Macht aus einer Ablehnung beim Speichern eine Fehlermeldung des Befehls.

    Der Befehl endet dann mit Fehler und nennt nur den Grund in Alltagssprache, ohne Ablauf
    des Programms.
    """
    try:
        yield
    except ValidationError as error:
        raise CommandError(" ".join(error.messages)) from error


def federation() -> Unit | None:
    """Der Verband, falls es ihn schon gibt."""
    return Unit.objects.filter(kind=Kind.FEDERATION).first()


def association(name: str) -> Unit:
    """Der Bund mit diesem Namen, ohne Rücksicht auf Groß- und Kleinschreibung und Leerzeichen am Rand."""
    name = name.strip()
    found = (
        Unit.objects.alias(lowered_name=Lower("name"))
        .filter(kind=Kind.ASSOCIATION, lowered_name=Lower(Value(name)))
        .first()
    )
    if found is None:
        raise CommandError(texts.ASSOCIATION_UNKNOWN % {"name": name})
    return found
