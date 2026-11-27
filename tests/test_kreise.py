"""Tests für Kreise: anlegen, einladen und beitreten (#381, Teil A von #141; GRP-01, GRP-02, BER-01, BER-03).

Die Kennungen A1 bis A6, AV1 bis AV7 und AG1 bis AG5 verweisen auf die Szenarien vom 17.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/381#issuecomment-6945396247), die Wortlaute auf den Text
von #381 und das Zielbild `docs/zielbilder/kreise.html`. Personen wie in den Szenarien, alle erfunden: Tom
(DPV-Veranstaltungsteam), Finn (Mitglied der Sippe Falken), Wanda (Stammesleitung Walhall), Svea (Mitglied im Bund
Mosaik), Anton und Wilma (Mitglieder in Boreas), Wiebke (Mitglied der Meute Wölfe), Otto (Konto ohne Zuordnung), Vera
(Verbandsleitung), Max (Admin). Jedes Konto war schon einmal angemeldet und hat eine bestätigte Mail (#251). Geprüft
wird, was beim Browser ankommt, und was danach in der Datenbank steht. Wie die Seiten am PC und am Handy bedienbar sind,
prüft `rauchtests/test_kreise.py`.
"""

import hashlib
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.utils import timezone

from access.rights import Rights
from accounts.models import AccountSearch
from circles.models import Circle, CircleInvitation, CircleMember
from roles.models import Role
from tests.query_limit import assert_queries_do_not_grow
from tests.test_anmeldungen import start_support
from tests.test_benennen import LIMIT_TEXT, _one_after_the_other, dialog_of, hits, notices, searched, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import NO_ACCESS_TEXT, assert_like_missing
from tests.test_organisation import client_for, nav_labels, page_tree, unit_address
from tests.test_rechtepruefung import remove
from tests.test_rollen import build_org, give, person

R = Role.Kind
User = get_user_model()
pytestmark = pytest.mark.django_db

LIST = "/kreise/"
CREATE = "/kreise/anlegen/"
NAV = "Kreise"
DESCRIPTION = "Wir planen das Vorbereitungstreffen des DPV im Frühjahr 2028."
NO_INVITATIONS = "Du hast keine offenen Einladungen."
NONE_YET = "Du bist noch in keinem Kreis. Mit „Kreis anlegen“ oben bildest du zum Beispiel ein Planungsteam."
NO_ACCOUNT = ("Kein Konto gefunden. Prüfe die Schreibweise der Mail oder des Benutzernamens. Die Person muss sich schon "
              "einmal im Tool angemeldet haben.")


# ---------- Personen und Hilfen ----------


def build_people() -> SimpleNamespace:
    """Die Organisationen aus `build_org()` und die Personen der Szenarien, jedes Konto schon angemeldet."""
    o = build_org()
    people = {
        "tom": ("tom.probst", "Tom", "Probst", "Rabe", R.EVENT_TEAM, o.dpv),
        "finn": ("finn.muster", "Finn", "Muster", "Flink", R.MEMBER, o.falken),
        "wanda": ("wanda.beispiel", "Wanda", "Beispiel", "Wirbelwind", R.MEMBER, o.walhall),
        "svea": ("svea.beispiel", "Svea", "Beispiel", "Möwe", R.MEMBER, o.kueste),
        "anton": ("anton.testmann", "Anton", "Testmann", "Ameise", R.MEMBER, o.boreas),
        "wilma": ("wilma.musterfrau", "Wilma", "Musterfrau", "", R.MEMBER, o.boreas),
        "wiebke": ("wiebke.woelfe", "Wiebke", "Wölfe", "", R.MEMBER, o.woelfe),
        "otto": ("otto.ohnezu", "Otto", "Ohnezu", "", None, None),
        "vera": ("vera.verband", "Vera", "Verband", "", R.FEDERATION_LEAD, o.dpv),
    }
    for name, (username, first, last, scout, kind, where) in people.items():
        user = person(username, first, last)
        user.scout_name, user.email = scout, f"{username}@example.org"
        user.save()
        if kind:
            give(user, kind, where)
        setattr(o, name, user)
    give(o.wanda, R.TROOP_LEAD, o.walhall)
    o.max = person("max.admin", "Max", "Admin")
    o.max.email = "max.admin@example.org"
    o.max.save()
    give(o.max, R.ADMIN)
    User.objects.update(last_login=timezone.now())
    for user in User.objects.exclude(email=""):
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    for name in vars(o):
        value = getattr(o, name)
        if isinstance(value, User):
            value.refresh_from_db()
    return o


@pytest.fixture
def org():
    return build_people()


def circle_of(manager, name: str = "Planungsteam", description: str = DESCRIPTION, members=(), invited=()):
    """Ein Kreis, wie ihn das Tool nach dem Anlegen durch `manager` speichert, mit Mitgliedern und Einladungen."""
    found = Circle.objects.create(name=name, description=description)
    CircleMember.objects.create(circle=found, user=manager, manages=True)
    for user in members:
        CircleMember.objects.create(circle=found, user=user)
    for user in invited:
        CircleInvitation.objects.create(circle=found, user=user, invited_by=manager)
    return found


@pytest.fixture
def planungsteam(org):
    """Toms „Planungsteam“: Svea ist Mitglied und verwaltet nicht, Anton und Wilma sind eingeladen."""
    return circle_of(org.tom, members=[org.svea], invited=[org.anton, org.wilma])


def circle_address(entry) -> str:
    return f"{LIST}{entry.key}/"


def invite_address(entry) -> str:
    return f"{circle_address(entry)}einladen/"


def search_address(entry) -> str:
    return f"{invite_address(entry)}suchen/"


def withdraw_address(entry, invitation) -> str:
    return f"{circle_address(entry)}einladungen/{invitation.key}/zuruecknehmen/"


def accept_address(invitation) -> str:
    return f"{LIST}einladungen/{invitation.key}/annehmen/"


def decline_address(invitation) -> str:
    return f"{LIST}einladungen/{invitation.key}/ablehnen/"


def invitation_of(circle, user) -> CircleInvitation:
    return CircleInvitation.objects.get(circle=circle, user=user)


def open_create(user, client=None):
    """Öffnet „Kreis anlegen“; gibt den Dialog und die Kennung des Dialogs zurück."""
    response = (client or client_for(user)).get(CREATE)
    assert response.status_code == 200, response.status_code
    found = dialog_of(_tree(response))
    return found, _attr(_one(_by_tag(found, "input", name="creation_key")), "value")


def create(user, client=None, **values):
    """Füllt „Kreis anlegen“ aus und klickt auf „Kreis anlegen“."""
    client = client or client_for(user)
    _found, creation_key = open_create(user, client=client)
    return client.post(CREATE, {"name": "Planungsteam", "description": DESCRIPTION, **values,
                                "creation_key": creation_key})


def search(user, circle, text: str, client=None):
    """„Suchen“ im Dialog „Person einladen“; gibt den Dialog der Antwort zurück."""
    response = (client or client_for(user)).post(search_address(circle), {"suche": text})
    assert response.status_code == 200, response.status_code
    return dialog_of(_tree(response))


def invite(user, circle, target, client=None):
    """„Einladen“ neben einem Treffer, wie der Knopf es abschickt."""
    return (client or client_for(user)).post(invite_address(circle), {"person": target.key})


def section(root, heading_id: str):
    return _one(_by_tag(root, "section", aria_labelledby=heading_id))


def my_circles(user) -> list[str]:
    """Die Einträge unter „Meine Kreise“ mit ihrem sichtbaren Text, in ihrer Reihenfolge."""
    root = section(page_tree(user, LIST), "h-meine-kreise")
    return [_visible_text(entry) for entry in _all(root, lambda e: "a-eintrag" in _classes(e))]


def invitations_shown(user) -> list[str]:
    """Die Einladungen unter „Einladungen“ mit ihrem sichtbaren Text."""
    root = section(page_tree(user, LIST), "h-einladungen")
    return [_visible_text(entry) for entry in _all(root, lambda e: "a-einladung" in _classes(e))]


def members_shown(user, circle) -> list[str]:
    root = section(page_tree(user, circle_address(circle)), "h-mitglieder")
    return [_visible_text(entry) for entry in _all(root, lambda e: "a-leitung" in _classes(e) and e.name == "li")]


def pending_shown(user, circle) -> list[str]:
    root = section(page_tree(user, circle_address(circle)), "h-offene-einladungen")
    return [_visible_text(entry) for entry in _all(root, lambda e: "a-leitung" in _classes(e) and e.name == "li")]


def start_hints(user) -> list[str]:
    root = page_tree(user, "/")
    return [_visible_text(entry) for entry in _all(root, lambda e: "a-meldung" in _classes(e))
            if "Einladung in einen Kreis" in _visible_text(entry)]


def members_of(circle) -> set[tuple[str, bool]]:
    return set(CircleMember.objects.filter(circle=circle).values_list("user__username", "manages"))


def invited_to(circle) -> set[str]:
    return set(CircleInvitation.objects.filter(circle=circle).values_list("user__username", flat=True))


def field_errors(root) -> dict[str, str]:
    """Die Fehler am Feld je Feld, auch am mehrzeiligen Textfeld „Beschreibung“."""
    found = {}
    for block in _all(root, lambda e: "a-textfeld" in _classes(e)):
        errors = _all(block, lambda e: "invalid-feedback" in _classes(e))
        if errors:
            field = (_by_tag(block, "input") + _by_tag(block, "textarea"))[0]
            found[_attr(field, "name")] = _visible_text(_one(errors))
    return found


def assert_no_access(response) -> None:
    assert response.status_code == 403, response.status_code
    assert NO_ACCESS_TEXT in response.content.decode()


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("KR-01", "KR-02")
def test_a1_tom_legt_das_planungsteam_an_und_verwaltet_es(org):
    client = client_for(org.tom)
    assert NAV in nav_labels(page_tree(org.tom, "/"))
    root = page_tree(org.tom, LIST)
    assert _text(_one(_by_tag(root, "h1"))) == "Kreise"
    assert NO_INVITATIONS in _visible_text(section(root, "h-einladungen"))
    assert NONE_YET in _visible_text(section(root, "h-meine-kreise"))
    button = _one(_all(section(root, "h-meine-kreise"), lambda e: "a-flaeche-aktion" in _classes(e)))
    assert (_visible_text(button), _attr(button, "href")) == ("Kreis anlegen", CREATE)

    found, _key = open_create(org.tom, client=client)
    assert _text(_one(_by_tag(found, "h2"))) == "Kreis anlegen"
    assert "Nur Mitglieder sehen den Kreis. Du verwaltest ihn." in _visible_text(found)
    assert [_attr(field, "name") for field in _by_tag(found, "input") + _by_tag(found, "textarea")
            if _attr(field, "type") != "hidden"] == ["name", "description"]

    response = create(org.tom, client=client)

    created = Circle.objects.get()
    assert (created.name, created.description) == ("Planungsteam", DESCRIPTION)
    assert members_of(created) == {("tom.probst", True)}
    assert response.status_code == 302
    assert response.url == circle_address(created)
    page = client.get(response.url)
    assert short_notices(page) == ["Der Kreis „Planungsteam“ ist angelegt."]
    assert _text(_one(_by_tag(_tree(page), "h1"))) == "Planungsteam"
    assert my_circles(org.tom) == ["Planungsteam 1 Mitglied Verwaltend"]


@pytest.mark.rechtematrix("KR-01", "KR-02")
def test_a1_ebenso_legt_finn_ohne_leitungsrolle_den_sippenrat_an(org):
    for user in (org.finn, org.wanda, org.vera, org.svea):
        assert NAV in nav_labels(page_tree(user, "/")), user.username

        assert create(user, name=f"Sippenrat von {user.first_name}").status_code == 302, user.username

        created = Circle.objects.get(name=f"Sippenrat von {user.first_name}")
        assert members_of(created) == {(user.username, True)}
        assert my_circles(user) == [f"Sippenrat von {user.first_name} 1 Mitglied Verwaltend"]


@pytest.mark.rechtematrix("KR-06", "KR-07", "KR-08", "KR-10", "PK-13", "PK-14", "PK-24")
def test_a2_tom_findet_svea_ueber_mail_und_benutzernamen_und_laedt_sie_ein(org):
    circle = circle_of(org.tom)
    client = client_for(org.tom)
    root = page_tree(org.tom, circle_address(circle))
    button = _one(_all(section(root, "h-mitglieder"), lambda e: "a-flaeche-aktion" in _classes(e)))
    assert (_visible_text(button), _attr(button, "href")) == ("Person einladen", invite_address(circle))
    found = dialog_of(page_tree(org.tom, invite_address(circle)))
    assert _text(_one(_by_tag(found, "h2"))) == "Person einladen"
    assert "in Planungsteam" in _visible_text(found)

    for text in ("svea.beispiel@example.org", "svea.beispiel", "SVEA.Beispiel@Example.org"):
        shown = hits(search(org.tom, circle, text, client=client))
        assert list(shown) == ["Möwe"], text
        assert shown["Möwe"]["text"] == "Möwe (Svea Beispiel) Einladen", text
        assert shown["Möwe"]["key"] == org.svea.key

    response = invite(org.tom, circle, org.svea, client=client)

    assert response.status_code == 302
    assert response.url == circle_address(circle)
    assert short_notices(client.get(response.url)) == ["Möwe (Svea Beispiel) ist eingeladen."]
    assert invited_to(circle) == {"svea.beispiel"}
    assert members_of(circle) == {("tom.probst", True)}
    assert pending_shown(org.tom, circle) == ["Möwe (Svea Beispiel) Zurücknehmen"]


@pytest.mark.rechtematrix("KR-04", "KR-09")
def test_a3_svea_sieht_den_hinweis_nimmt_an_und_ist_mitglied(org):
    circle = circle_of(org.tom, invited=[org.svea])
    client = client_for(org.svea)
    hints = start_hints(org.svea)
    assert hints == ["Einladung in einen Kreis Rabe (Tom Probst) lädt dich in den Kreis „Planungsteam“ "
                     "ein. Zur Einladung"]
    link = _one([a for a in _by_tag(page_tree(org.svea, "/"), "a") if _visible_text(a) == "Zur Einladung"])
    assert _attr(link, "href") == LIST
    # Ein Knopf statt eines Links im Text (Vorschau, Sebastian, 27.11.2026).
    assert {"btn", "btn-zart"} <= set(_classes(link))
    assert invitations_shown(org.svea) == [f"Planungsteam Rabe (Tom Probst) lädt dich ein. {DESCRIPTION} Ablehnen Annehmen"]

    response = client.post(accept_address(invitation_of(circle, org.svea)))

    assert response.status_code == 302
    assert response.url == circle_address(circle)
    assert short_notices(client.get(response.url)) == ["Du bist jetzt Mitglied von „Planungsteam“."]
    assert members_of(circle) == {("tom.probst", True), ("svea.beispiel", False)}
    assert invited_to(circle) == set()
    assert start_hints(org.svea) == []
    assert invitations_shown(org.svea) == []
    assert my_circles(org.svea) == ["Planungsteam 2 Mitglieder"]


@pytest.mark.rechtematrix("KR-03", "KR-05", "KR-10")
def test_a4_svea_sieht_alle_mitglieder_mit_name_und_fahrtenname(org, planungsteam):
    CircleMember.objects.create(circle=planungsteam, user=org.wilma)
    root = page_tree(org.svea, circle_address(planungsteam))

    assert _text(_one(_by_tag(root, "h1"))) == "Planungsteam"
    assert DESCRIPTION in _visible_text(_one(_all(root, lambda e: "a-kopf" in _classes(e))))
    assert members_shown(org.svea, planungsteam) == [
        "Rabe (Tom Probst) Verwaltend",
        "Möwe (Svea Beispiel) · das bist du",
        "Wilma Musterfrau",
    ]
    assert "3 Mitglieder" in _visible_text(section(root, "h-mitglieder"))


@pytest.mark.rechtematrix("KR-10")
def test_a4_mail_organisation_und_offene_einladungen_sieht_svea_nicht(org, planungsteam):
    text = client_for(org.svea).get(circle_address(planungsteam)).content.decode()

    for hidden in ("@example.org", "Pfadfinderbund Boreas", "Küste", "DPBM Mosaik", "Ameise", "Anton", "Offene Einladungen",
                   "Person einladen", "Zurücknehmen"):
        assert hidden not in text, hidden


@pytest.mark.rechtematrix("KR-08", "KR-09")
def test_a5_anton_lehnt_ab_und_tom_kann_ihn_erneut_einladen(org, planungsteam):
    client = client_for(org.anton)

    response = client.post(decline_address(invitation_of(planungsteam, org.anton)))

    assert response.status_code == 302
    assert response.url == LIST
    assert short_notices(client.get(LIST)) == ["Du hast die Einladung in „Planungsteam“ abgelehnt."]
    assert invited_to(planungsteam) == {"wilma.musterfrau"}
    assert ("anton.testmann", False) not in members_of(planungsteam)
    assert invitations_shown(org.anton) == []
    assert pending_shown(org.tom, planungsteam) == ["Wilma Musterfrau Zurücknehmen"]
    # Ablehnen ist still: Tom sieht keinen Hinweis dazu, kann Anton aber erneut einladen.
    assert "abgelehnt" not in _visible_text(page_tree(org.tom, circle_address(planungsteam)))
    assert invite(org.tom, planungsteam, org.anton).status_code == 302
    assert invited_to(planungsteam) == {"anton.testmann", "wilma.musterfrau"}


@pytest.mark.rechtematrix("KR-08")
def test_a6_tom_nimmt_die_einladung_an_wilma_zurueck(org, planungsteam):
    client = client_for(org.tom)
    address = withdraw_address(planungsteam, invitation_of(planungsteam, org.wilma))
    links = _by_tag(section(page_tree(org.tom, circle_address(planungsteam)), "h-offene-einladungen"), "a")
    assert address in [_attr(link, "href") for link in links]
    found = dialog_of(page_tree(org.tom, address))
    assert _text(_one(_by_tag(found, "h2"))) == "Einladung an Wilma Musterfrau zurücknehmen?"
    assert "Die Einladung verschwindet. Du kannst die Person später wieder einladen." in _visible_text(found)

    response = client.post(address)

    assert response.status_code == 302
    assert response.url == circle_address(planungsteam)
    assert short_notices(client.get(response.url)) == ["Die Einladung an Wilma Musterfrau ist zurückgenommen."]
    assert invited_to(planungsteam) == {"anton.testmann"}
    assert invitations_shown(org.wilma) == []
    assert start_hints(org.wilma) == []


# ---------- Verboten ----------


@pytest.mark.rechtematrix("KR-01", "KR-02")
def test_av1_otto_und_max_haben_keinen_punkt_und_legen_nichts_an(org):
    for user in (org.otto, org.max):
        assert NAV not in nav_labels(page_tree(user, "/")), user.username
        assert_no_access(client_for(user).get(LIST))
        assert_no_access(client_for(user).get(CREATE))
        response = client_for(user).post(CREATE, {"name": "Gekapert", "description": "", "creation_key": "a" * 20})
        assert_no_access(response)
    assert not Circle.objects.exists()


@pytest.mark.rechtematrix("KR-02")
def test_av1_auch_im_support_zugang_legt_max_keinen_kreis_an(org):
    start_support(org.max, org.falken)
    client = client_for(org.max)

    assert NAV not in nav_labels(page_tree(org.max, "/"))
    assert_no_access(client.get(LIST))
    assert_no_access(client.post(CREATE, {"name": "Gekapert", "description": "", "creation_key": "a" * 20}))
    assert not Circle.objects.exists()


@pytest.mark.rechtematrix("KR-02", "KR-08")
def test_av2_tom_findet_otto_kann_ihn_aber_nicht_einladen(org):
    circle = circle_of(org.tom)

    shown = hits(search(org.tom, circle, "otto.ohnezu@example.org"))

    assert shown == {"Otto Ohnezu": {
        "text": "Otto Ohnezu Otto Ohnezu gehört noch keiner Organisation an und kann deshalb noch nicht eingeladen "
                "werden.", "button": False, "key": None}}
    response = invite(org.tom, circle, org.otto)
    assert response.status_code == 200
    assert notices(dialog_of(_tree(response))) == [
        "Otto Ohnezu gehört noch keiner Organisation an und kann deshalb noch nicht eingeladen werden."]
    assert invited_to(circle) == set()


@pytest.mark.rechtematrix("KR-05")
def test_av3_leitungen_verbandsleitung_und_admin_finden_finns_sippenrat_nicht(org):
    sippenrat = circle_of(org.finn, name="Sippenrat", description="")
    for user in (org.wanda, org.vera, org.max, org.tom):
        assert_like_missing(user, circle_address(sippenrat))
    for user in (org.wanda, org.vera, org.tom):
        assert my_circles(user) == []
        assert "Sippenrat" not in client_for(user).get(LIST).content.decode()


@pytest.mark.wie_nicht_vorhanden("kreise/<key:circle>/")
@pytest.mark.rechtematrix("KR-05")
def test_av3_auch_im_support_zugang_fuer_die_falken_sieht_max_den_sippenrat_nicht(org):
    sippenrat = circle_of(org.finn, name="Sippenrat", description="")
    start_support(org.max, org.falken)

    assert_like_missing(org.max, circle_address(sippenrat))


@pytest.mark.wie_nicht_vorhanden("kreise/<key:circle>/einladen/")
@pytest.mark.rechtematrix("KR-06", "KR-07", "KR-08", "PK-14")
def test_av4_svea_als_mitglied_hat_weder_suche_noch_einladen(org, planungsteam):
    root = page_tree(org.svea, circle_address(planungsteam))
    assert "Person einladen" not in _visible_text(root)
    assert not _all(section(root, "h-mitglieder"), lambda e: "a-flaeche-aktion" in _classes(e))

    assert_like_missing(org.svea, invite_address(planungsteam))
    assert invited_to(planungsteam) == {"anton.testmann", "wilma.musterfrau"}


@pytest.mark.wie_nicht_vorhanden("kreise/<key:circle>/einladen/suchen/")
@pytest.mark.rechtematrix("KR-06", "KR-07")
def test_av4_svea_sucht_auch_ueber_die_direkte_adresse_nicht(org, planungsteam):
    assert_like_missing(org.svea, search_address(planungsteam))
    assert not AccountSearch.objects.filter(user=org.svea).exists()
    response = client_for(org.svea).post(invite_address(planungsteam), {"person": org.finn.key})
    assert response.status_code == 404
    assert invited_to(planungsteam) == {"anton.testmann", "wilma.musterfrau"}


@pytest.mark.wie_nicht_vorhanden("kreise/<key:circle>/einladungen/<key:invitation>/zuruecknehmen/")
@pytest.mark.rechtematrix("KR-07", "KR-08")
def test_av4_svea_nimmt_keine_einladung_zurueck(org, planungsteam):
    assert_like_missing(org.svea, withdraw_address(planungsteam, invitation_of(planungsteam, org.anton)))
    assert invited_to(planungsteam) == {"anton.testmann", "wilma.musterfrau"}


@pytest.mark.rechtematrix("KR-03", "KR-04")
def test_av5_anton_sieht_als_eingeladener_nur_die_einladung(org, planungsteam):
    root = page_tree(org.anton, circle_address(planungsteam))

    # Seit der Vorschau (Sebastian, 27.11.2026): die Seite des Kreises mit Name und Beschreibung im Kopf und darunter
    # der Fläche „Einladung“ zum Annehmen oder Ablehnen wie auf der Seite „Kreise“, statt einer Seite „Einladung“.
    assert _text(_one(_by_tag(root, "h1"))) == "Planungsteam"
    head = _one(_all(root, lambda e: "a-kopf" in _classes(e)))
    assert " ".join(_visible_text(head).split()) == f"Kreise Planungsteam Planungsteam {DESCRIPTION}"
    assert _visible_text(section(root, "h-einladung")) == (
        "Einladung Planungsteam Rabe (Tom Probst) lädt dich ein. Ablehnen Annehmen Wer im Kreis ist, siehst du, "
        "sobald du die Einladung annimmst.")
    text = client_for(org.anton).get(circle_address(planungsteam)).content.decode()
    for hidden in ("Möwe", "Svea", "Wilma", "Mitglieder"):
        assert hidden not in text, hidden


@pytest.mark.wie_nicht_vorhanden("kreise/einladungen/<key:invitation>/annehmen/")
@pytest.mark.rechtematrix("KR-04", "KR-05", "KR-09")
def test_av6_wiebke_nimmt_mit_antons_einladung_nicht_an(org, planungsteam):
    assert_like_missing(org.wiebke, accept_address(invitation_of(planungsteam, org.anton)))
    assert members_of(planungsteam) == {("tom.probst", True), ("svea.beispiel", False)}
    assert invited_to(planungsteam) == {"anton.testmann", "wilma.musterfrau"}
    assert invitations_shown(org.wiebke) == []
    assert start_hints(org.wiebke) == []


@pytest.mark.wie_nicht_vorhanden("kreise/einladungen/<key:invitation>/ablehnen/")
@pytest.mark.rechtematrix("KR-09")
def test_av6_wiebke_lehnt_antons_einladung_nicht_ab(org, planungsteam):
    assert_like_missing(org.wiebke, decline_address(invitation_of(planungsteam, org.anton)))
    assert invited_to(planungsteam) == {"anton.testmann", "wilma.musterfrau"}


@pytest.mark.rechtematrix("KR-05")
def test_av6_die_kennung_eines_fremden_kreises_ist_nicht_gefunden(org, planungsteam):
    sippenrat = circle_of(org.finn, name="Sippenrat", description="")

    assert_like_missing(org.tom, circle_address(sippenrat))
    assert_like_missing(org.tom, invite_address(sippenrat))
    assert_like_missing(org.tom, withdraw_address(sippenrat, invitation_of(planungsteam, org.anton)))


@pytest.mark.rechtematrix("KR-06")
def test_av7_unbestaetigte_mail_und_teil_einer_mail_finden_nichts(org):
    circle = circle_of(org.tom)
    EmailAddress.objects.filter(user=org.finn).update(verified=False)

    for text in ("finn.muster@example.org", "svea.beispiel@example", "svea", "Möwe", "Svea Beispiel", "%", "*"):
        dialog = search(org.tom, circle, text)
        assert hits(dialog) == {}, text
    assert notices(search(org.tom, circle, "finn.muster@example.org")) == [NO_ACCOUNT]


@pytest.mark.rechtematrix("KR-06", "PK-24")
def test_av7_die_21_suche_zeigt_das_suchlimit_mit_den_suchen_als_leitung_zusammen(org):
    circle = circle_of(org.wanda, name="Stammesrat")
    # Zehn Suchen als Stammesleitung im Dialog „… benennen“, neun für den Kreis.
    for _ in range(10):
        assert client_for(org.wanda).post(f"{unit_address(org.walhall)}benennen/suchen/",
                                          {"suche": "niemand@example.org"}).status_code == 200
    searched(org.wanda, *([1] * 9))
    assert "Kein Konto gefunden" in _visible_text(search(org.wanda, circle, "niemand@example.org"))

    dialog = search(org.wanda, circle, "svea.beispiel@example.org")

    assert notices(dialog) == [LIMIT_TEXT.format('59 Minuten')]
    assert hits(dialog) == {}
    assert AccountSearch.objects.filter(user=org.wanda).count() == 20


# ---------- Grenzfälle ----------


@pytest.mark.rechtematrix("KR-08")
def test_ag1_schon_mitglied_schon_eingeladen_oder_man_selbst_satz_statt_knopf(org, planungsteam):
    shown = {
        text: hits(search(org.tom, planungsteam, text))
        for text in ("svea.beispiel@example.org", "anton.testmann", "tom.probst@example.org")
    }

    assert shown["svea.beispiel@example.org"]["Möwe"]["text"] == "Möwe (Svea Beispiel) Möwe ist schon Mitglied."
    assert shown["anton.testmann"]["Ameise"]["text"] == "Ameise (Anton Testmann) Ameise ist schon eingeladen."
    assert shown["tom.probst@example.org"]["Rabe"]["text"] == "Rabe (Tom Probst) Das bist du."
    assert not any(entry["button"] for found in shown.values() for entry in found.values())
    for target in (org.svea, org.anton, org.tom):
        assert invite(org.tom, planungsteam, target).status_code == 200
    assert invited_to(planungsteam) == {"anton.testmann", "wilma.musterfrau"}
    assert members_of(planungsteam) == {("tom.probst", True), ("svea.beispiel", False)}


def test_ag2_name_pflicht_und_grenzen_mit_fehler_am_feld(org):
    cases = [
        ({"name": "   "}, {"name": "Bitte gib dem Kreis einen Namen."}),
        ({"name": "x" * 61}, {"name": "Der Name darf höchstens 60 Zeichen lang sein."}),
        ({"description": "x" * 501}, {"description": "Die Beschreibung darf höchstens 500 Zeichen lang sein."}),
    ]
    for values, errors in cases:
        response = create(org.tom, **values)
        assert response.status_code == 200, values
        assert field_errors(dialog_of(_tree(response))) == errors, values
    assert not Circle.objects.exists()


def test_ag2_leerzeichen_am_rand_weg_grenzen_genau_und_gleiche_namen_erlaubt(org):
    assert create(org.tom, name="  Planungsteam  ", description="  Kurz.  ").status_code == 302
    assert create(org.tom, name="Planungsteam", description="").status_code == 302
    assert create(org.tom, name="y" * 60, description="z" * 500).status_code == 302

    assert sorted(Circle.objects.values_list("name", "description")) == [
        ("Planungsteam", ""), ("Planungsteam", "Kurz."), ("y" * 60, "z" * 500)]


def test_ag3_doppelt_abgeschickt_bleibt_es_bei_einem_kreis(org):
    client = client_for(org.tom)
    _found, creation_key = open_create(org.tom, client=client)
    form = {"name": "Planungsteam", "description": "", "creation_key": creation_key}

    first, second = client.post(CREATE, form), client.post(CREATE, form)

    created = Circle.objects.get()
    assert first.url == second.url == circle_address(created)
    assert members_of(created) == {("tom.probst", True)}


def test_ag3_die_kennung_eines_fremden_formulars_ist_nicht_gefunden(org):
    sippenrat = circle_of(org.finn, name="Sippenrat")

    response = client_for(org.tom).post(CREATE, {"name": "X", "description": "", "creation_key": sippenrat.creation_key})

    assert response.status_code == 404
    assert Circle.objects.count() == 1
    assert members_of(sippenrat) == {("finn.muster", True)}


@pytest.mark.django_db(transaction=True)
def test_ag3_gleichzeitig_abgeschickt_bleibt_es_bei_einem_kreis():
    o = build_people()
    values = {"name": "Planungsteam", "description": ""}

    results = _one_after_the_other(lambda: Rights(o.tom).create_circle(values, "b" * 20),
                                   lambda: Rights(o.tom).create_circle(values, "b" * 20))

    assert len(results) == 2
    assert results[0].pk == results[1].pk
    assert Circle.objects.count() == 1
    assert CircleMember.objects.count() == 1


@pytest.mark.rechtematrix("KR-09")
def test_ag4_nach_dem_zuruecknehmen_wird_anton_nicht_mitglied(org, planungsteam):
    """Anton hat „Kreise“ offen, Tom nimmt zurück, dann klickt Anton „Annehmen“: der Satz statt „nicht gefunden“.

    Unabhängige Prüfung, M2; Sebastian (27.11.2026): „Satz statt ‚nicht gefunden‘“. Bis dahin prüfte dieser Test
    „nicht gefunden“, das AG4 nicht entsprach.
    """
    invitation = invitation_of(planungsteam, org.anton)
    client = client_for(org.anton)
    assert "Annehmen" in client.get(LIST).content.decode()
    client_for(org.tom).post(withdraw_address(planungsteam, invitation))

    for address in (accept_address(invitation), decline_address(invitation)):
        response = client.post(address)
        assert (response.status_code, response.url) == (302, LIST), address
        assert notices(_tree(client.get(LIST))) == ["Diese Einladung gibt es nicht mehr."], address
    assert ("anton.testmann", False) not in members_of(planungsteam)


@pytest.mark.rechtematrix("KR-09")
def test_ag4_doppelt_auf_annehmen_geklickt_fuehrt_zur_seite_des_kreises(org, planungsteam):
    """Unabhängige Prüfung, M2: Die zweite Antwort zeigt, dass Anton schon Mitglied ist, statt „nicht gefunden“."""
    invitation = invitation_of(planungsteam, org.anton)
    client = client_for(org.anton)
    client.get(LIST)

    first, second = client.post(accept_address(invitation)), client.post(accept_address(invitation))

    assert first.url == second.url == circle_address(planungsteam)
    assert ("anton.testmann", False) in members_of(planungsteam)


def test_m1_zeilenumbrueche_der_beschreibung_zaehlen_einmal(org):
    """Unabhängige Prüfung, M1: Der Browser schickt Umbrüche als zwei Zeichen; gezählt und gespeichert wird einer."""
    response = create(org.tom, description="a\r\n" * 249 + "aa")

    assert response.status_code == 302
    assert Circle.objects.get().description == "a\n" * 249 + "aa"


def test_g1_unter_der_sperre_gesperrtes_konto_wird_nicht_eingeladen(org, monkeypatch):
    """Unabhängige Prüfung, G1: Wird das Konto zwischen Suche und Sperre gesperrt, entsteht keine Einladung."""
    circle = circle_of(org.tom)
    original = Rights._lock_with

    def locked_meanwhile(self, other):
        User.objects.filter(pk=other).update(is_active=False)
        return original(self, other)

    monkeypatch.setattr(Rights, "_lock_with", locked_meanwhile)

    assert Rights(org.tom).invite(circle.key, org.finn.key) == (False, NO_ACCOUNT)
    assert invited_to(circle) == set()


@pytest.mark.django_db(transaction=True)
@pytest.mark.rechtematrix("KR-09")
def test_ag4_tom_nimmt_zurueck_waehrend_anton_annimmt():
    o = build_people()
    circle = circle_of(o.tom, invited=[o.anton])
    invitation = invitation_of(circle, o.anton)

    results = _one_after_the_other(lambda: Rights(o.tom).withdraw(circle.key, invitation.key),
                                   lambda: Rights(o.anton).answer_invitation(invitation.key, accept=True))

    assert sorted(map(str, results)) == ["(None, 'Diese Einladung gibt es nicht mehr.')",
                                         "Die Einladung an Ameise (Anton Testmann) ist zurückgenommen."]
    assert members_of(circle) == {("tom.probst", True)}
    assert invited_to(circle) == set()


@pytest.mark.django_db(transaction=True)
def test_ag4_anton_nimmt_an_waehrend_tom_zuruecknimmt():
    o = build_people()
    circle = circle_of(o.tom, invited=[o.anton])
    invitation = invitation_of(circle, o.anton)

    results = _one_after_the_other(lambda: Rights(o.anton).answer_invitation(invitation.key, accept=True)[1],
                                   lambda: Rights(o.tom).withdraw(circle.key, invitation.key))

    assert sorted(results) == ["Diese Einladung gibt es nicht mehr.", "Du bist jetzt Mitglied von „Planungsteam“."]
    assert members_of(circle) == {("tom.probst", True), ("anton.testmann", False)}


def test_ag4_die_meldung_steht_auf_der_seite_kreise(org, planungsteam, monkeypatch):
    """Verschwindet die Einladung zwischen Prüfung und Sperre, steht „Diese Einladung gibt es nicht mehr.“ auf „Kreise“."""
    invitation = invitation_of(planungsteam, org.anton)
    original = Rights.invitation
    seen = []

    def gone_meanwhile(self, key):
        # Die Prüfung in der Seite findet die Einladung noch; danach nimmt Tom sie zurück.
        if seen:
            return seen[0]
        seen.append(original(self, key))
        CircleInvitation.objects.filter(pk=seen[0].pk).delete()
        return seen[0]

    monkeypatch.setattr(Rights, "invitation", gone_meanwhile)
    client = client_for(org.anton)

    response = client.post(accept_address(invitation))

    assert response.status_code == 302
    assert response.url == LIST
    assert notices(_tree(client.get(LIST))) == ["Diese Einladung gibt es nicht mehr."]
    assert ("anton.testmann", False) not in members_of(planungsteam)


@pytest.mark.rechtematrix("KR-02", "KR-09")
def test_ag5_anton_hat_die_zuordnung_verloren_und_annehmen_wird_abgelehnt(org, planungsteam):
    invitation = invitation_of(planungsteam, org.anton)
    remove(org.anton, R.MEMBER, org.boreas)

    response = client_for(org.anton).post(accept_address(invitation))

    assert response.status_code == 404
    assert ("anton.testmann", False) not in members_of(planungsteam)
    assert NAV not in nav_labels(page_tree(org.anton, "/"))
    assert start_hints(org.anton) == []


@pytest.mark.django_db(transaction=True)
def test_ag5_verliert_anton_die_zuordnung_gleichzeitig_wird_er_nicht_mitglied():
    o = build_people()
    circle = circle_of(o.tom, invited=[o.anton])
    invitation = invitation_of(circle, o.anton)

    results = _one_after_the_other(lambda: remove(o.anton, R.MEMBER, o.boreas),
                                   lambda: _refused(lambda: Rights(o.anton).answer_invitation(invitation.key, True)))

    assert "abgelehnt" in results
    assert members_of(circle) == {("tom.probst", True)}


def _refused(action) -> str:
    from django.core.exceptions import PermissionDenied

    try:
        action()
    except PermissionDenied:
        return "abgelehnt"
    return "angenommen"


@pytest.mark.django_db(transaction=True)
def test_ag2_zwei_einladungen_gleichzeitig_ergeben_eine():
    o = build_people()
    circle = circle_of(o.tom)
    CircleMember.objects.filter(circle=circle).update(manages=True)
    CircleMember.objects.create(circle=circle, user=o.svea, manages=True)

    results = _one_after_the_other(lambda: Rights(o.tom).invite(circle.key, o.anton.key),
                                   lambda: Rights(o.svea).invite(circle.key, o.anton.key))

    assert sorted(done for done, _text in results) == [False, True]
    assert invited_to(circle) == {"anton.testmann"}


def test_kreis_anlegen_antwortet_ohne_uhrzeit_in_den_kopfzeilen(org):
    """Lauf auf GitHub für 9179830: „Expires“ mit der Uhrzeit ließ den Vergleich echter mit erfundenen Kennungen in
    tests/test_nicht_gefunden.py an einer Sekundengrenze scheitern. Wie bei „Veranstaltung erstellen“: nie zwischenspeichern,
    aber ohne Uhrzeit."""
    client = client_for(org.tom)
    _found, creation_key = open_create(org.tom, client=client)
    for response in (client.get(CREATE), client.post(CREATE, {"name": "", "creation_key": creation_key})):
        assert response.status_code == 200
        assert "Expires" not in response.headers
        assert "no-store" in response.headers["Cache-Control"]


# ---------- Wer den Menüpunkt hat, Listen ohne Abfragen je Eintrag ----------


def test_was_unveraendert_bleibt_ottos_startseite_und_die_suche_der_leitungen(org):
    """„Was bleibt unverändert?“: Ottos Startseite hat keinen Hinweis, Svea sucht als Mitglied keine Konten für Organisationen."""
    circle_of(org.tom, invited=[org.otto])
    assert start_hints(org.otto) == []
    assert Rights(org.svea).find_accounts("finn.muster@example.org") == []
    assert [entry["username"] for entry in Rights(org.wanda).find_accounts("finn.muster@example.org")] == ["finn.muster"]


def test_die_liste_meine_kreise_waechst_nicht_mit_den_abfragen(org):
    def create_entry(number: int) -> None:
        circle_of(org.tom, name=f"Kreis {number}", members=[org.svea], invited=[org.anton])
        found = circle_of(org.wilma, name=f"Einladung {number}")
        CircleInvitation.objects.create(circle=found, user=org.tom, invited_by=org.wilma)

    assert_queries_do_not_grow(create_entry, lambda: client_for(org.tom).get(LIST))


def test_die_seite_eines_kreises_waechst_nicht_mit_den_abfragen(org):
    circle = circle_of(org.tom)

    def create_entry(number: int) -> None:
        CircleMember.objects.create(circle=circle, user=person(f"mitglied.{number}", "Mia", f"Mitglied {number}"))
        CircleInvitation.objects.create(circle=circle, user=person(f"gast.{number}", "Gerd", f"Gast {number}"),
                                        invited_by=org.tom)

    assert_queries_do_not_grow(create_entry, lambda: client_for(org.tom).get(circle_address(circle)))


def test_die_startseite_waechst_nicht_mit_den_einladungen(org):
    def create_entry(number: int) -> None:
        found = circle_of(org.wilma, name=f"Kreis {number}")
        CircleInvitation.objects.create(circle=found, user=org.tom, invited_by=org.wilma)

    assert_queries_do_not_grow(create_entry, lambda: client_for(org.tom).get("/"))


def test_lesend_fuehren_annehmen_und_ablehnen_zur_seite_kreise(org, planungsteam):
    invitation = invitation_of(planungsteam, org.anton)
    for address in (accept_address(invitation), decline_address(invitation)):
        response = client_for(org.anton).get(address)
        assert (response.status_code, response.url) == (302, LIST)
    assert invited_to(planungsteam) == {"anton.testmann", "wilma.musterfrau"}


# ---------- Zielbild ----------

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "docs" / "zielbilder" / "kreise.html"
CHECKSUM = "99cc6465246f36f0f433d569d0e600a8ebc790d6d8f36d5559f0fa789cef36c9"


def test_zielbild_liegt_unveraendert_mit_eintrag_im_repo():
    readme = (ROOT / "docs" / "zielbilder" / "README.md").read_text()

    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == CHECKSUM
    section = readme.split("## Kreise", 1)
    assert len(section) == 2
    for must in (CHECKSUM, "17.11.2026", "Orientierung, keine Anforderung", "Abweichungen", "#381"):
        assert must in section[1].split("\n## ", 1)[0], must


def test_zielbild_laedt_nichts_von_fremden_servern():
    content = TARGET.read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)
