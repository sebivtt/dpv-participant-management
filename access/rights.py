"""Gerüst der zentralen Rechteprüfung (#90); die Regeln folgen."""

from django.contrib.auth import get_user_model
from django.http import Http404

from roles.models import Role


class Rights:
    """Gerüst: erlaubt noch nichts."""

    def __init__(self, user) -> None:
        self.user = user

    @property
    def area(self) -> frozenset[int]:
        return frozenset()

    @property
    def chain(self) -> frozenset[int]:
        return frozenset()

    def persons(self):
        return get_user_model().objects.none()

    def person(self, pk):
        raise Http404

    def leads(self):
        return Role.objects.none().values()

    def leads_unit(self, unit) -> bool:
        return False

    def covers(self, unit) -> bool:
        return False

    def leads_unit_of(self, person) -> bool:
        return False


def on_lead_path(person, unit) -> bool:
    return False


class RightsMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
