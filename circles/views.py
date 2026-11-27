"""Seiten der Kreise (#381): leeres Gerüst. Jede Adresse ist „nicht gefunden“, bis die Seiten gebaut sind."""

from django.http import Http404, HttpRequest, HttpResponse

from access.addresses import checks_rights

CIRCLE_ROWS = ("KR-01", "KR-02", "KR-03", "KR-04", "KR-05", "KR-07", "KR-08", "KR-10")
INVITE_ROWS = ("KR-02", "KR-05", "KR-06", "KR-07", "KR-08", "KR-10", "PK-13", "PK-14", "PK-24")
ANSWER_ROWS = ("KR-02", "KR-04", "KR-05", "KR-09")


@checks_rights(*CIRCLE_ROWS)
def circles(request: HttpRequest) -> HttpResponse:
    """Seite „Kreise“ (Gerüst)."""
    raise Http404


@checks_rights(*CIRCLE_ROWS)
def circle_create(request: HttpRequest) -> HttpResponse:
    """Dialog „Kreis anlegen“ (Gerüst)."""
    raise Http404


@checks_rights(*CIRCLE_ROWS)
def circle_page(request: HttpRequest, circle: str) -> HttpResponse:
    """Seite eines Kreises (Gerüst)."""
    raise Http404


@checks_rights(*INVITE_ROWS)
def circle_invite(request: HttpRequest, circle: str) -> HttpResponse:
    """Dialog „Person einladen“ (Gerüst)."""
    raise Http404


@checks_rights(*INVITE_ROWS)
def circle_search(request: HttpRequest, circle: str) -> HttpResponse:
    """„Suchen“ im Dialog „Person einladen“ (Gerüst)."""
    raise Http404


@checks_rights(*INVITE_ROWS)
def circle_withdraw(request: HttpRequest, circle: str, invitation: str) -> HttpResponse:
    """Einladung zurücknehmen (Gerüst)."""
    raise Http404


@checks_rights(*ANSWER_ROWS)
def circle_accept(request: HttpRequest, invitation: str) -> HttpResponse:
    """Einladung annehmen (Gerüst)."""
    raise Http404


@checks_rights(*ANSWER_ROWS)
def circle_decline(request: HttpRequest, invitation: str) -> HttpResponse:
    """Einladung ablehnen (Gerüst)."""
    raise Http404
