"""Die Rollenformulare mit eingeschaltetem Formularschutz (CSRF), wie im echten Browser (#326, S3; RO-10, RO-15, RO-20).

Die übrigen Tests zu Benennen, Entfernen und Rolle abgeben schicken ihre Formulare ohne Formularschutz ab; der
Test-Browser von Django schaltet ihn sonst ab. Dass ein Formular ohne Formularschutz abgelehnt wird, prüft
`tests/test_fehlerseiten.py`. Hier öffnet ein Browser mit eingeschaltetem Formularschutz jede Seite, nimmt das
Formular von dort, mit allen Feldern, die die Seite mitschickt, und schickt es ab. Fehlt in einem Formular der
Formularschutz oder passt er nicht zur Seite, wird der Test rot. Personen und Einheiten wie in
`tests/test_rechte_ohne_seite.py`; alle Namen sind erfunden.
"""

import pytest
from allauth.account.models import EmailAddress
from django.test import Client
from django.utils import timezone

from roles.models import Role
from tests.test_gestaltung import _attr, _by_tag, _tree
from tests.test_rollen import build_org, give, person

pytestmark = pytest.mark.django_db
R = Role.Kind

ORGANISATION = "/organisation/"


@pytest.fixture
def org():
    """Zora leitet die Zugvögel, Vera und Erika sind Verbandsleitung; Paul (Sippe Adler) und Otto waren schon angemeldet."""
    o = build_org()
    o.zora = person("zora.zugvogel", "Zora", "Zugvogel")
    give(o.zora, R.MEMBER, o.zugvoegel)
    give(o.zora, R.TROOP_LEAD, o.zugvoegel)
    o.vera = person("vera.verband", "Vera", "Verband")
    give(o.vera, R.FEDERATION_LEAD, o.dpv)
    give(o.erika, R.FEDERATION_LEAD, o.dpv)
    o.paul = person("paul.probe", "Paul", "Probe")
    give(o.paul, R.MEMBER, o.adler)
    o.otto = person("otto.ohne", "Otto", "Ohne")
    for user in (o.paul, o.otto):
        user.email = f"{user.username}@example.org"
        user.last_login = timezone.now()
        user.save()
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    return o


def browser(user) -> Client:
    """Ein Browser mit eingeschaltetem Formularschutz, angemeldet als `user`."""
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    return client


def link_on(client: Client, page: str, address: str) -> str:
    """Öffnet `page` und gibt den Link zu `address` zurück; fehlt er, ist der Test rot."""
    # Ein Link darf eine Sprungmarke tragen, etwa „…/benennen/#abschnitt-leitungen“.
    links = [(_attr(link, "href") or "").split("#")[0] for link in _by_tag(_tree(client.get(page)), "a")]
    assert address in links, f"kein Link zu {address} auf {page}"
    return address


def submit(client: Client, page_response, action: str, person=None, **fields):
    """Schickt das Formular mit dem Ziel `action` von der Seite ab, mit allen Feldern, die die Seite mitgibt.

    Mit `person` das Formular, das diese Person benennt (je Treffer ein eigenes Formular); `fields` sind die Felder,
    die die Person selbst ausfüllt, etwa der Suchbegriff.
    """
    forms = [form for form in _by_tag(_tree(page_response), "form", method="post") if (_attr(form, "action") or "").split("#")[0] == action]
    data_of = [
        {_attr(field, "name"): _attr(field, "value") or "" for field in _by_tag(form, "input") if _attr(field, "name")}
        for form in forms
    ]
    if person is not None:
        data_of = [data for data in data_of if data.get("person") == person.key]
    assert len(data_of) == 1, f"{len(data_of)} statt genau einem Formular an {action}"
    data = data_of[0]
    assert data.get("csrfmiddlewaretoken"), f"Formular an {action} ohne Formularschutz"
    return client.post(action, {**data, **fields})


def assert_done(response, address: str) -> None:
    """Gelungen: zurück zur Seite, nicht „Ungültige Anfrage“ (403) wegen des Formularschutzes."""
    assert response.status_code == 302, response.status_code
    assert response["Location"].split("#")[0] == address


@pytest.mark.rechtematrix("RO-10", "RO-15", "RO-20")
def test_rollenformulare_gelingen_mit_eingeschaltetem_formularschutz(org):
    """S3: Zora benennt eine Gruppenleitung und entfernt sie, Vera benennt eine Bundesleitung und entfernt eine
    Verbandsleitung, Zora legt ihre eigene Rolle nieder; jedes Formular von seiner Seite aus."""
    # Zora benennt Paul als Gruppenleitung der Sippe Adler (RO-10).
    zora = browser(org.zora)
    adler = f"{ORGANISATION}{org.adler.key}/"
    appoint = link_on(zora, adler, f"{adler}benennen/")
    found = submit(zora, zora.get(appoint), f"{appoint}suchen/", suche="paul.probe")
    assert_done(submit(zora, found, appoint, person=org.paul), adler)
    paul_lead = Role.objects.get(user=org.paul, kind=R.GROUP_LEAD, unit=org.adler)

    # Zora entfernt Paul wieder (RO-15).
    remove = link_on(zora, adler, f"{adler}entfernen/{paul_lead.key}/")
    assert_done(submit(zora, zora.get(remove), remove), adler)
    assert not Role.objects.filter(pk=paul_lead.pk).exists()

    # Vera benennt Otto als Bundesleitung von Boreas (RO-11).
    vera = browser(org.vera)
    appoint = link_on(vera, ORGANISATION, f"/organisation/verband/bund/{org.boreas.key}/benennen/")
    found = submit(vera, vera.get(appoint), f"{appoint}suchen/", suche="otto.ohne@example.org")
    assert_done(submit(vera, found, appoint, person=org.otto), ORGANISATION)
    assert Role.objects.filter(user=org.otto, kind=R.ASSOCIATION_LEAD, unit=org.boreas).exists()

    # Vera entfernt Erika als Verbandsleitung (RO-15).
    erika_lead = Role.objects.get(user=org.erika, kind=R.FEDERATION_LEAD)
    remove = link_on(vera, ORGANISATION, f"/organisation/verband/entfernen/{erika_lead.key}/")
    assert_done(submit(vera, vera.get(remove), remove), ORGANISATION)
    assert not Role.objects.filter(pk=erika_lead.pk).exists()

    # Zora legt ihre Stammesleitung nieder (RO-20).
    zugvoegel = f"{ORGANISATION}{org.zugvoegel.key}/"
    own = Role.objects.get(user=org.zora, kind=R.TROOP_LEAD)
    remove = link_on(zora, zugvoegel, f"{zugvoegel}entfernen/{own.key}/")
    response = submit(zora, zora.get(remove), remove)
    assert response.status_code == 302, response.status_code
    assert not Role.objects.filter(pk=own.pk).exists()
    assert Role.objects.filter(user=org.zora, kind=R.MEMBER, unit=org.zugvoegel).exists()
