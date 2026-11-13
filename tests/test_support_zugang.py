"""Tests für den Support-Zugang der Admins und das Protokoll der Admin-Zugriffe (#92, BER-02).

Die Kennungen S1 bis S8, SA1 bis SA3, SV1 bis SV8, SG1 bis SG6 und U1 bis U4 verweisen auf die
Szenarien vom 12.11.2026, Fassung nach dem Zielbild
(https://github.com/sebivtt/dpv-participant-management/issues/92#issuecomment-6819688970), die
Wortlaute auf den Text von #92 und die Nachklärung N1 bis N4b. Personen wie in den Tests zu #285 und
#117 (`tests/test_personen.py`, `tests/test_verwaltete_personen.py`): Wanda heißt „Wirbelwind“, Fiete
„Funke“, Finn „Flink“; die Meute Wölfe hat hier keine Leitung mit Konto. Max ist Admin ohne andere
Rolle, Alma Admin und Gruppenleitung der Sippe Adler. Namen, Fahrtennamen und Mails sind erfunden.
"""

import io
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import DatabaseError, connection, transaction
from django.test import Client
from django.utils import timezone

from access.rights import Rights
from persons.models import ManagedPerson
from roles.models import AdminAccess, Role, RoleChange
from tests import test_personen
from tests.test_benennen import appoint, dialog_of, notices, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, nodes, page_tree, unit_address
from tests.test_personen import admit, find, membership_of
from tests.test_rollen import BY, give, person
from tests.test_verwaltete_personen import edit_address, managed, open_edit, save
from units.models import Unit

R = Role.Kind
A = AdminAccess.Action
D = AdminAccess.Detail
pytestmark = pytest.mark.django_db
User = get_user_model()
BERLIN = ZoneInfo("Europe/Berlin")

base_org = test_personen.base_org
org_189 = test_personen.org_189
org_190 = test_personen.org_190
personen_org = test_personen.org

END_ADDRESS = "/support-zugang/beenden/"
START_LABEL = "Support-Zugang starten"
EXPIRED = "Dein Support-Zugang für Stamm Walhall ist nach 60 Minuten abgelaufen."
UNSAVED = "Was du gerade abgeschickt hast, ist nicht gespeichert."
NOT_YOURSELF = "Im Support-Zugang kannst du dir selbst keine Rolle geben."
CHOOSE_REASON = "Bitte wähle einen Anlass."
REASONS = [
    ("lead_request", "Anfrage einer Leitung"),
    ("debugging", "Fehlersuche"),
    ("data_subject", "Anfrage einer betroffenen Person (Auskunft, Berichtigung)"),
    ("other", "Sonstiges"),
]


@pytest.fixture
def clock(monkeypatch):
    """Die Uhr des Servers, gestellt auf den 12.11.2026, 13:35 Uhr; `clock["now"]` lässt sich vorstellen."""
    state = {"now": datetime(2026, 11, 12, 13, 35, tzinfo=BERLIN)}
    monkeypatch.setattr(timezone, "now", lambda: state["now"])
    return state


@pytest.fixture
def org(personen_org, clock):
    """Die Personen aus #285, dazu Alma, Lena und Ole; die Meute Wölfe ohne Leitung mit Konto (S5)."""
    org = personen_org
    Role.objects.get(user=org.woelfe_leitung, kind=R.GROUP_LEAD, unit=org.woelfe).delete(by=BY)
    org.alma = person("alma.admin", "Alma", "Admin")
    give(org.alma, R.ADMIN)
    give(org.alma, R.GROUP_LEAD, org.adler)
    org.alma.email = "alma.admin@example.org"
    org.alma.last_login = timezone.now()
    org.alma.save()
    EmailAddress.objects.create(user=org.alma, email=org.alma.email, verified=True, primary=True)
    org.lena = managed("Lena", "Probe", org.falken, scout_name="Kiwi", born=date(2015, 5, 14))
    org.ole = managed("Ole", "Probe", org.adler, born=date(2016, 2, 29))
    return org


# ---------- Hilfen ----------


def support_address(where) -> str:
    return f"{unit_address(where)}support-zugang/"


def start(user, where, reason="lead_request", client=None):
    """„Support-Zugang starten“ im Dialog mit dem gewählten Anlass, wie der dunkelblaue Knopf es abschickt."""
    data = {} if reason is None else {"anlass": reason}
    return (client or client_for(user)).post(support_address(where), data)


def end(user, client=None):
    """„beenden“ im Balken."""
    return (client or client_for(user)).post(END_ADDRESS)


def log() -> list[tuple]:
    """Das Protokoll der Admin-Zugriffe in seiner Reihenfolge: Art, Zusatz, Admin und Bereich."""
    return [(entry.action, entry.detail, entry.actor_name, entry.unit_name)
            for entry in AdminAccess.objects.order_by("id")]


def follow(response, client) -> Client:
    """Die Seite nach der Weiterleitung."""
    assert response.status_code == 302, response.status_code
    return client.get(response["Location"])


def start_button(root):
    """Der Knopf „Support-Zugang starten“ im Kopf der Organisationsseite, oder None."""
    heads = _all(root, lambda e: "a-orga-kopf" in _classes(e))
    if not heads:
        return None
    links = [link for link in _by_tag(_one(heads), "a") if _visible_text(link) == START_LABEL]
    return _one(links) if links else None


def bar(root):
    """Der Balken „Support-Zugang … aktiv bis …“, oder None."""
    found = _all(root, lambda e: "a-supportbalken" in _classes(e))
    return _one(found) if found else None


def sections(root) -> list[str]:
    """Die Abschnitte der Organisationsseite unter dem Kopf, nach ihrer Überschrift."""
    return [_attr(entry, "aria-labelledby") for entry in _by_tag(root, "section")
            if (_attr(entry, "aria-labelledby") or "").startswith("h-") and _attr(entry, "aria-labelledby") != "menue-unten-titel"]


def fixed_notices(root) -> list[tuple[str, str]]:
    """Feste Meldungen oben auf der Seite: Art (Klasse) und sichtbarer Text, ohne kurze Meldungen."""
    return [(" ".join(_classes(entry)), _visible_text(entry))
            for entry in _all(root, lambda e: "a-meldung" in _classes(e) and _attr(e, "data-kurz") is None)]


def page_text(user, where, client=None) -> str:
    response = (client or client_for(user)).get(unit_address(where))
    assert response.status_code == 200
    return _visible_text(_tree(response))


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("SZ-01", "SZ-06", "EH-06", "EH-08")
def test_s1_max_sieht_alle_buende_nur_mit_namen(org):
    root = page_tree(org.max, "/organisation/")

    shown = nodes(root)
    for name in ("Pfadfinderbund Boreas", "Walhall", "Sippe Falken", "Zugvögel", "DPBM Mosaik", "Leuchtturm"):
        assert name in shown, name
        assert shown[name]["leads"] == ""
        assert shown[name]["href"] is not None
    assert "Wirbelwind" not in _visible_text(root)
    # Wie im Zielbild steht neben der Überschrift „alle Bünde“ statt der Namen.
    head = _one(_all(root, lambda e: "a-gliederung-kopf" in _classes(e)))
    assert _visible_text(head) == "Gliederung alle Bünde"


@pytest.mark.rechtematrix("SZ-01", "SZ-06", "PK-08", "EH-06")
def test_s1_auf_walhall_steht_nur_der_kopf_mit_dem_knopf(org):
    root = page_tree(org.max, unit_address(org.walhall))

    button = start_button(root)
    assert button is not None
    assert _attr(button, "href") == support_address(org.walhall)
    assert {"btn", "btn-verschieben"} <= set(_classes(button))
    # Schild-Symbol vor der Beschriftung (N4).
    assert _attr(_one(_by_tag(button, "use")), "href") == "#i-schild"
    assert sections(root) == []
    text = _visible_text(root)
    for hidden in ("Wirbelwind", "Wiesel", "Wilma", "wanda.walhall@example.org", "Leitungen", "Personen"):
        assert hidden not in text, hidden


def test_s1_der_dialog_nennt_die_organisation_und_hat_keinen_anlass_vorgewaehlt(org):
    response = client_for(org.max).get(support_address(org.walhall))

    dialog = dialog_of(_tree(response))
    assert _visible_text(_one(_by_tag(dialog, "h2"))) == "Support-Zugang für Stamm Walhall starten"
    assert ("Du siehst und änderst danach höchstens 60 Minuten lang, was die Leitung von Stamm Walhall darf. "
            "Jeder Schritt kommt ins Protokoll.") in _visible_text(dialog)
    radios = _by_tag(dialog, "input", type="radio")
    labels = [_visible_text(_one(_by_tag(dialog, "label", **{"for": _attr(entry, "id")}))) for entry in radios]
    assert [(_attr(entry, "value"), label) for entry, label in zip(radios, labels, strict=True)] == REASONS
    assert all(_attr(entry, "checked") is None for entry in radios)
    assert "Anlass" in _visible_text(dialog)
    assert not _by_tag(dialog, "textarea")
    assert not _by_tag(dialog, "input", type="text")
    button = _one(_by_tag(dialog, "button", type="submit"))
    assert _visible_text(button) == START_LABEL
    assert "btn-primary" in _classes(button)
    assert "Abbrechen" in _visible_text(dialog)
    assert AdminAccess.objects.count() == 0


@pytest.mark.rechtematrix("SZ-01", "SZ-02", "PR-05", "PR-06")
def test_s2_max_startet_mit_anlass_und_sieht_den_balken(org):
    client = client_for(org.max)

    page = follow(start(org.max, org.walhall, client=client), client)

    root = _tree(page)
    assert short_notices(page) == ["Support-Zugang für Stamm Walhall gestartet."]
    shown = bar(root)
    assert shown is not None
    assert "Support-Zugang für Stamm Walhall aktiv bis 14:35" in _visible_text(shown)
    form = _one(_by_tag(shown, "form", method="post"))
    assert _attr(form, "action") == END_ADDRESS
    assert _visible_text(_one(_by_tag(form, "button"))) == "beenden"
    # Danach kommt die Seite von Walhall als „ansehen“ dazu (S3); hier zählt der Start.
    entry = AdminAccess.objects.get(action=A.STARTED)
    assert (entry.action, entry.detail, entry.actor_id, entry.actor_name) == (A.STARTED, D.LEAD_REQUEST, org.max.pk,
                                                                              "Max Admin")
    assert (entry.unit_id, entry.unit_kind, entry.unit_name) == (org.walhall.pk, Unit.Kind.TROOP, "Walhall")
    assert entry.at == datetime(2026, 11, 12, 13, 35, tzinfo=BERLIN)
    assert f"{entry.get_action_display()} · {entry.get_detail_display()}" == (
        "Support-Zugang gestartet · Anfrage einer Leitung")


def test_s2_der_balken_steht_auf_jeder_seite(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    for address in ("/", "/profil/", "/organisation/", unit_address(org.zugvoegel)):
        root = _tree(client.get(address))
        assert bar(root) is not None, address
        assert "aktiv bis 14:35" in _visible_text(bar(root)), address


def test_s2_im_zugang_kein_knopf_auf_walhall_und_darunter(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    assert start_button(_tree(client.get(unit_address(org.walhall)))) is None
    assert start_button(_tree(client.get(unit_address(org.falken)))) is None
    assert start_button(_tree(client.get(unit_address(org.zugvoegel)))) is not None


@pytest.mark.rechtematrix("SZ-03", "SZ-06", "PK-08")
def test_s3_im_zugang_sieht_max_walhall_wie_wanda_mit_protokoll_je_seite(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    walhall = page_text(org.max, org.walhall, client=client)
    falken = page_text(org.max, org.falken, client=client)

    assert "Wirbelwind" in walhall and "wilma.walhall@example.org" in walhall
    assert "Kiwi" in falken and "Flink" in falken
    assert sections(_tree(client.get(unit_address(org.walhall)))) == sections(page_tree(org.walhall_leitung,
                                                                                        unit_address(org.walhall)))
    assert log()[:3] == [
        (A.STARTED, D.LEAD_REQUEST, "Max Admin", "Walhall"),
        (A.VIEWED, "", "Max Admin", "Walhall"),
        (A.VIEWED, "", "Max Admin", "Walhall"),
    ]


@pytest.mark.rechtematrix("SZ-03", "SZ-05", "PK-13")
def test_s4_max_findet_otto_und_nimmt_ihn_auf(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    dialog = find(org.max, org.walhall, "otto.ohne@example.org", client=client)
    assert "Otto" in _visible_text(dialog)
    response = admit(org.max, org.walhall, org.ohne, client=client)

    assert response.status_code == 302
    assert membership_of(org.ohne) == "Walhall"
    assert log()[1:] == [
        (A.VIEWED, D.ACCOUNT_SEARCH, "Max Admin", "Walhall"),
        (A.CHANGED, "", "Max Admin", "Walhall"),
    ]
    change = RoleChange.objects.order_by("id").last()
    assert (change.actor_id, change.person_name, change.kind, change.unit_name, change.action) == (
        org.max.pk, "Otto Ohne", R.MEMBER, "Walhall", RoleChange.Action.GRANTED)


@pytest.mark.rechtematrix("SZ-03")
def test_s5_max_springt_in_der_meute_woelfe_ein_wie_wanda(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    root = _tree(client.get(unit_address(org.woelfe)))
    assert "Du springst ein" in _visible_text(root)
    assert admit(org.max, org.woelfe, org.ohne, client=client).status_code == 302
    assert membership_of(org.ohne) == "Meute Wölfe"


@pytest.mark.rechtematrix("SZ-01", "SZ-04")
def test_s6_beenden_nimmt_den_balken_und_die_rechte(org):
    client = client_for(org.max)
    follow(start(org.max, org.walhall, client=client), client)

    page = follow(end(org.max, client=client), client)

    root = _tree(page)
    assert short_notices(page) == ["Support-Zugang für Stamm Walhall beendet."]
    assert bar(root) is None
    walhall = _tree(client.get(unit_address(org.walhall)))
    assert sections(walhall) == []
    assert start_button(walhall) is not None
    assert log()[-1] == (A.ENDED, D.BUTTON, "Max Admin", "Walhall")


def test_s7_ein_neuer_start_beendet_den_alten(org):
    client = client_for(org.max)
    follow(start(org.max, org.walhall, client=client), client)

    page = follow(start(org.max, org.zugvoegel, reason="debugging", client=client), client)

    assert short_notices(page) == ["Support-Zugang für Stamm Walhall beendet. Support-Zugang für Stamm Zugvögel gestartet."]
    assert log() == [
        (A.STARTED, D.LEAD_REQUEST, "Max Admin", "Walhall"),
        (A.VIEWED, "", "Max Admin", "Walhall"),
        (A.ENDED, D.SWITCHED, "Max Admin", "Walhall"),
        (A.STARTED, D.DEBUGGING, "Max Admin", "Zugvögel"),
        (A.VIEWED, "", "Max Admin", "Zugvögel"),
    ]
    walhall = _tree(client.get(unit_address(org.walhall)))
    assert sections(walhall) == []
    assert "Support-Zugang für Stamm Zugvögel aktiv bis 14:35" in _visible_text(bar(walhall))


def test_s8_alma_eigene_rolle_kommt_nicht_ins_protokoll(org):
    client = client_for(org.alma)
    page_text(org.alma, org.adler, client=client)
    assert AdminAccess.objects.count() == 0

    start(org.alma, org.walhall, client=client)
    page_text(org.alma, org.walhall, client=client)
    page_text(org.alma, org.adler, client=client)

    assert log() == [
        (A.STARTED, D.LEAD_REQUEST, "Alma Admin", "Walhall"),
        (A.VIEWED, "", "Alma Admin", "Walhall"),
    ]


# ---------- Ablauf ----------


@pytest.mark.rechtematrix("SZ-04")
def test_sa1_nach_60_minuten_zeigt_der_naechste_klick_die_information(org, clock):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)
    clock["now"] += timedelta(minutes=61)

    response = client.get("/profil/")

    page = follow(response, client)
    root = _tree(page)
    assert response["Location"] == unit_address(org.walhall)
    shown = fixed_notices(root)
    assert len(shown) == 1
    assert "ist-info" in shown[0][0]
    assert shown[0][1].endswith(EXPIRED)
    assert bar(root) is None
    assert sections(root) == []
    ended = AdminAccess.objects.order_by("id").last()
    assert (ended.action, ended.detail) == (A.ENDED, D.EXPIRED)
    assert ended.at == datetime(2026, 11, 12, 14, 35, tzinfo=BERLIN)
    # Die Meldung steht nur einmal.
    assert fixed_notices(_tree(client.get(unit_address(org.walhall)))) == []


@pytest.mark.rechtematrix("SZ-04")
def test_sa1_bis_zum_ende_der_60_minuten_gilt_der_zugang(org, clock):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)
    clock["now"] += timedelta(minutes=59)

    assert "Wirbelwind" in page_text(org.max, org.walhall, client=client)


def test_sa2_nach_ablauf_wird_ein_abgeschicktes_formular_nicht_gespeichert(org, clock):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)
    _dialog, version = open_edit(org.max, org.falken, org.lena, client=client)
    clock["now"] += timedelta(minutes=61)

    response = save(org.max, org.falken, org.lena, version, client=client, first_name="Lenchen", last_name="Probe",
                    birth_date="2015-05-14", scout_name="Kiwi")

    root = _tree(follow(response, client))
    assert ManagedPerson.objects.get(pk=org.lena.pk).first_name == "Lena"
    warnings = [entry for entry in _all(root, lambda e: "ist-warnung" in _classes(e))]
    assert len(warnings) == 1
    assert _visible_text(_one(_all(warnings[0], lambda e: "a-meldung-titel" in _classes(e)))) == EXPIRED
    assert UNSAVED in _visible_text(warnings[0])
    assert A.CHANGED not in [entry[0] for entry in log()]


def test_sa3_abmelden_beendet_den_zugang(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    client.post("/abmelden/")

    assert log()[-1] == (A.ENDED, D.LOGOUT, "Max Admin", "Walhall")
    assert bar(_tree(client_for(org.max).get("/"))) is None


# ---------- Verboten ----------


ADDRESSES_IN_WALHALL = [
    "benennen/", "benennen/suchen/", "aufnehmen/", "aufnehmen/suchen/", "anlegen/", "bearbeiten/",
    "verwaltete-person/anlegen/",
]


@pytest.mark.rechtematrix("SZ-06", "PK-08")
def test_sv1_ohne_zugang_keine_personen_und_keine_leitungen(org):
    client = client_for(org.max)
    rights = Rights(org.max)

    for suffix in ADDRESSES_IN_WALHALL:
        assert client.get(f"{unit_address(org.walhall)}{suffix}").status_code == 404, suffix
        assert client.post(f"{unit_address(org.walhall)}{suffix}", {"person": org.ohne.key, "name": "X",
                                                                     "suche": "otto.ohne@example.org"}).status_code == 404, suffix
    assert client.post(f"{unit_address(org.walhall)}benennen/vorschlaege/", {"suche": "Wir"}).status_code == 404
    assert client.get(edit_address(org.falken, org.lena)).status_code == 404
    assert client.get(f"{unit_address(org.walhall)}austragen/{org.walhall_mitglied.key}/").status_code == 404
    assert client.get(f"{unit_address(org.walhall)}verschieben/{org.walhall_mitglied.key}/").status_code == 404
    assert set(rights.persons().values_list("username", flat=True)) == {"max.admin"}
    assert rights.managed_in(org.falken) == []
    assert rights.find_accounts("otto.ohne@example.org") == []
    assert list(rights.leads()) == []
    assert membership_of(org.ohne) is None
    assert AdminAccess.objects.count() == 0


@pytest.mark.rechtematrix("SZ-06")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/bearbeiten/")
def test_sv1_lenas_adresse_ist_ohne_zugang_wie_nicht_vorhanden(org):
    assert_like_missing(org.max, edit_address(org.falken, org.lena))


@pytest.mark.rechtematrix("SZ-03", "SZ-04")
def test_sv2_im_zugang_fuer_walhall_keine_personen_der_zugvoegel(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    assert_like_missing(org.max, edit_address(org.adler, org.ole))
    zugvoegel = _tree(client.get(unit_address(org.zugvoegel)))
    assert sections(zugvoegel) == []
    assert "Zora" not in _visible_text(zugvoegel)
    assert client.get(f"{unit_address(org.adler)}aufnehmen/").status_code == 404
    assert admit(org.max, org.adler, org.ohne, client=client).status_code == 404
    assert membership_of(org.ohne) is None


@pytest.mark.rechtematrix("SZ-02")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/support-zugang/")
def test_sv3_ohne_rolle_admin_startet_niemand_einen_zugang(org):
    for user in (org.walhall_leitung, org.falke, org.ohne, org.verbandsleitung, org.team):
        client = client_for(user)
        assert_like_missing(user, support_address(org.walhall))
        assert start(user, org.walhall, client=client).status_code == 404
        assert end(user, client=client).status_code == 403
    assert start_button(page_tree(org.walhall_leitung, unit_address(org.walhall))) is None
    assert AdminAccess.objects.count() == 0
    assert "Support-Zugang" not in _visible_text(page_tree(org.walhall_leitung, unit_address(org.walhall)))


@pytest.mark.rechtematrix("SZ-05")
def test_sv4_max_benennt_sich_im_zugang_nicht_selbst(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    response = appoint(org.max, org.walhall, org.max, client=client)
    assert NOT_YOURSELF in notices(dialog_of(_tree(response)))
    # Manipuliertes Formular mit weiteren Feldern und eine andere Organisation im Zugang.
    response = appoint(org.max, org.falken, org.max, client=client, unit=org.walhall.key, kind=R.TROOP_LEAD)
    assert NOT_YOURSELF in notices(dialog_of(_tree(response)))
    assert set(Role.objects.filter(user=org.max).values_list("kind", flat=True)) == {R.ADMIN}


@pytest.mark.rechtematrix("SZ-05")
def test_sv4_max_nimmt_sich_im_zugang_nicht_selbst_auf(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    for where in (org.walhall, org.woelfe):
        response = admit(org.max, where, org.max, client=client, person_key=org.max.key)
        assert NOT_YOURSELF in notices(dialog_of(_tree(response))), where
    # Auch eine Anfrage aus dem Skript, ohne vorher geöffneten Dialog.
    raw = Client()
    raw.force_login(org.max)
    response = raw.post(f"{unit_address(org.walhall)}aufnehmen/", {"person": org.max.key},
                        headers={"x-requested-with": "fetch"})
    assert NOT_YOURSELF in _visible_text(_tree(response))
    assert set(Role.objects.filter(user=org.max).values_list("kind", flat=True)) == {R.ADMIN}
    assert A.CHANGED not in [entry[0] for entry in log()]


@pytest.mark.rechtematrix("SZ-01", "EH-06")
def test_sv5_kein_zugang_fuer_den_verband(org):
    client = client_for(org.max)

    assert client.get(unit_address(org.dpv)).status_code == 404
    assert start(org.max, org.dpv, client=client).status_code == 404
    assert AdminAccess.objects.count() == 0
    assert START_LABEL not in _visible_text(page_tree(org.verbandsleitung, "/organisation/"))


def test_sv6_ohne_anlass_oder_mit_freiem_text_kein_zugang(org):
    client = client_for(org.max)

    for reason in (None, "", "Ich schau mal", "account_search", "expired"):
        response = start(org.max, org.walhall, reason=reason, client=client)
        assert response.status_code == 200, reason
        dialog = dialog_of(_tree(response))
        assert CHOOSE_REASON in notices(dialog), reason
    assert AdminAccess.objects.count() == 0
    assert bar(_tree(client.get("/"))) is None


def test_sv7_im_zugang_keine_gesundheitsangaben(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    text = page_text(org.max, org.falken, client=client)
    dialog, _version = open_edit(org.max, org.falken, org.lena, client=client)

    assert "Gesundheit" not in text
    assert "Gesundheit" not in _visible_text(dialog)


def entry_of(org) -> AdminAccess:
    """Ein Eintrag, wie ihn ein Start schreibt; direkt angelegt, damit die Sperre allein geprüft wird."""
    return AdminAccess.objects.create(at=timezone.now(), actor_id=org.max.pk, actor_name="Max Admin", action=A.STARTED,
                                      detail=D.LEAD_REQUEST, unit_id=org.walhall.pk, unit_kind=Unit.Kind.TROOP,
                                      unit_name="Walhall")


@pytest.mark.rechtematrix("PR-06")
def test_sv8_eintraege_lassen_sich_im_programm_nicht_aendern_oder_loeschen(org):
    entry = entry_of(org)

    entry.unit_name = "Anders"
    with pytest.raises(ValidationError):
        entry.save()
    with pytest.raises(ValidationError):
        entry.delete()
    assert log() == [(A.STARTED, D.LEAD_REQUEST, "Max Admin", "Walhall")]


@pytest.mark.rechtematrix("PR-06")
@pytest.mark.parametrize("change", ["update", "delete"])
def test_sv8_sammelaenderungen_scheitern_an_der_datenbank(org, change):
    entry_of(org)

    with pytest.raises(DatabaseError), transaction.atomic():
        if change == "update":
            AdminAccess.objects.update(unit_name="Anders")
        else:
            AdminAccess.objects.all().delete()
    assert log() == [(A.STARTED, D.LEAD_REQUEST, "Max Admin", "Walhall")]


@pytest.mark.rechtematrix("PR-06")
def test_sv8_aendern_per_sql_scheitert_an_der_datenbank(org):
    entry_of(org)

    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("UPDATE roles_adminaccess SET actor_name = 'Niemand'")
    assert log() == [(A.STARTED, D.LEAD_REQUEST, "Max Admin", "Walhall")]


# ---------- Grenzfälle ----------


def test_sg1_ohne_eintrag_keine_seite(org, monkeypatch):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    def broken(*args, **kwargs):
        raise DatabaseError("Protokoll nicht erreichbar")

    monkeypatch.setattr(AdminAccess, "save", broken)
    client.raise_request_exception = False
    response = client.get(unit_address(org.walhall))

    assert response.status_code == 500
    assert "Wirbelwind" not in response.content.decode()


def test_sg1_ohne_eintrag_keine_aenderung(org, monkeypatch):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)
    real_save = AdminAccess.save

    def broken(self, *args, **kwargs):
        if self.action == A.CHANGED:
            raise DatabaseError("Protokoll nicht erreichbar")
        return real_save(self, *args, **kwargs)

    monkeypatch.setattr(AdminAccess, "save", broken)
    client.raise_request_exception = False
    response = admit(org.max, org.walhall, org.ohne, client=client)

    assert response.status_code == 500
    assert membership_of(org.ohne) is None
    assert not RoleChange.objects.filter(person_name="Otto Ohne").exists()


@pytest.mark.rechtematrix("PK-24")
def test_sg2_suchen_im_zugang_zaehlen_zur_grenze(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    for number in range(20):
        dialog = find(org.max, org.walhall, f"niemand{number}@example.org", client=client)
        assert "Du hast in kurzer Zeit sehr oft gesucht" not in _visible_text(dialog)
    dialog = find(org.max, org.walhall, "otto.ohne@example.org", client=client)

    assert "Du hast in kurzer Zeit sehr oft gesucht. Bitte versuche es in 60 Minuten noch einmal." in notices(dialog)
    assert [entry for entry in log() if entry[1] == D.ACCOUNT_SEARCH] == [
        (A.VIEWED, D.ACCOUNT_SEARCH, "Max Admin", "Walhall")] * 20


def test_sg3_das_protokoll_enthaelt_keine_namen_von_personen_und_keinen_suchbegriff(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)
    page_text(org.max, org.falken, client=client)
    find(org.max, org.walhall, "otto.ohne@example.org", client=client)
    admit(org.max, org.walhall, org.ohne, client=client)
    _dialog, version = open_edit(org.max, org.falken, org.lena, client=client)
    save(org.max, org.falken, org.lena, version, client=client, first_name="Lena", last_name="Probe",
         birth_date="2015-05-15", scout_name="Kiwi")
    end(org.max, client=client)

    texts = " ".join(" ".join(str(value) for value in entry) for entry in
                     AdminAccess.objects.values_list("actor_name", "detail", "unit_name"))
    for name in ("Otto", "otto", "Lena", "Kiwi", "Probe", "Flink", "Finn", "Wanda", "Wirbelwind", "example.org", "2015"):
        assert name not in texts, name
    assert {entry.unit_name for entry in AdminAccess.objects.all()} == {"Walhall"}
    assert [field.name for field in AdminAccess._meta.get_fields()] == [
        "id", "at", "actor_id", "actor_name", "action", "detail", "unit_id", "unit_kind", "unit_name"]
    assert A.CHANGED in [entry[0] for entry in log()]


def test_sg4_notfall_loeschen_einer_leeren_organisation(org):
    empty = Unit(kind=Unit.Kind.GROUP, name="Sippe Irrtum", parent=org.walhall)
    empty.save(by=BY)

    call_command("emergency_delete", empty.key, stdout=io.StringIO())

    assert not Unit.objects.filter(pk=empty.pk).exists()
    entry = AdminAccess.objects.get()
    assert (entry.action, entry.actor_id, entry.actor_name, entry.unit_id, entry.unit_kind, entry.unit_name) == (
        A.DELETED, None, "Befehl auf dem Server", empty.pk, Unit.Kind.GROUP, "Sippe Irrtum (Walhall)")


@pytest.mark.parametrize("where", ["walhall", "falken", "adler_ohne_konten", "dpv", "unbekannt"])
def test_sg4_der_befehl_lehnt_organisationen_mit_inhalt_ab(org, where):
    """Walhall hat Gruppen darunter, die Falken Mitglieder; in der Sippe Adler steht nur noch Ole."""
    if where == "adler_ohne_konten":
        for role in Role.objects.filter(unit=org.adler).order_by("-kind"):
            if Role.objects.filter(pk=role.pk).exists():
                role.delete(by=BY)
        assert not Role.objects.filter(unit=org.adler).exists()
        target = org.adler.key
    elif where == "unbekannt":
        target = "x" * len(org.walhall.key)
    else:
        target = getattr(org, where).key

    with pytest.raises(CommandError):
        call_command("emergency_delete", target, stdout=io.StringIO())

    assert Unit.objects.filter(pk__in=[org.walhall.pk, org.falken.pk, org.adler.pk, org.dpv.pk]).count() == 4
    assert AdminAccess.objects.count() == 0


def test_sg5_doppelklick_ergibt_einen_zugang_und_einen_eintrag(org):
    client = client_for(org.max)

    first = start(org.max, org.walhall, client=client)
    second = start(org.max, org.walhall, client=client)

    assert first.status_code == 302 and second.status_code == 302
    assert log() == [(A.STARTED, D.LEAD_REQUEST, "Max Admin", "Walhall")]


@pytest.mark.django_db(transaction=True)
def test_sg5_gleichzeitig_abgeschickt_ergibt_einen_eintrag(clock):
    """Zwei gleichzeitige Starts derselben Person laufen nacheinander, weil ihr Konto gesperrt ist."""
    from tests.test_benennen import _one_after_the_other
    from tests.test_rollen import build_org

    o = build_org()
    admin = person("max.admin", "Max", "Admin")
    give(admin, R.ADMIN)

    results = _one_after_the_other(lambda: Rights(admin).start_support(o.walhall, "lead_request"),
                                   lambda: Rights(admin).start_support(o.walhall, "lead_request"))

    assert len(results) == 2
    assert AdminAccess.objects.filter(action=A.STARTED).count() == 1


@pytest.mark.rechtematrix("SZ-03", "SZ-04")
def test_sg6_ein_zugang_fuer_die_falken_gilt_nur_fuer_die_falken(org):
    client = client_for(org.max)
    start(org.max, org.falken, client=client)

    assert "Kiwi" in page_text(org.max, org.falken, client=client)
    walhall = _tree(client.get(unit_address(org.walhall)))
    assert "h-personen" not in sections(walhall)
    assert "Wilma" not in _visible_text(walhall)
    assert start_button(walhall) is not None
    assert client.get(f"{unit_address(org.walhall)}austragen/{org.walhall_mitglied.key}/").status_code == 404


# ---------- Was bleibt unverändert ----------


def test_u1_leitungen_arbeiten_ohne_eintraege(org):
    client = client_for(org.walhall_leitung)
    page_text(org.walhall_leitung, org.walhall, client=client)
    find(org.walhall_leitung, org.walhall, "otto.ohne@example.org", client=client)
    admit(org.walhall_leitung, org.walhall, org.ohne, client=client)

    assert membership_of(org.ohne) == "Walhall"
    assert AdminAccess.objects.count() == 0
    assert start_button(page_tree(org.walhall_leitung, unit_address(org.walhall))) is None


def test_u2_ohne_zugang_hat_der_admin_keine_rechte_einer_leitung(org):
    rights = Rights(org.max)

    assert not rights.may_admit(org.walhall)
    assert not rights.may_appoint(org.walhall)
    assert not rights.may_add_managed(org.walhall)
    assert not rights.may_create(org.walhall)
    assert rights.members(org.walhall) == []


def test_u3_aenderungen_im_zugang_stehen_im_protokoll_der_rollenaenderungen(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)
    before = RoleChange.objects.count()

    admit(org.max, org.walhall, org.ohne, client=client)

    assert RoleChange.objects.count() == before + 1
    assert RoleChange.objects.order_by("id").last().actor_name == "Max Admin"


def test_u4_fuer_andere_rollen_bleibt_die_seite_ohne_knopf_und_balken(org):
    for user, where in ((org.walhall_leitung, org.walhall), (org.falken_leitung, org.falken),
                        (org.bundesleitung, org.boreas)):
        root = page_tree(user, unit_address(where))
        assert start_button(root) is None
        assert bar(root) is None
        assert "h-leitungen" in sections(root)


@pytest.mark.rechtematrix("EP-04")
def test_im_zugang_aendert_max_nur_den_eigenen_fahrtennamen(org):
    """EP-04: Auch der Support-Zugang gibt kein Recht auf den Fahrtennamen anderer, auch nicht per manipuliertem Formular."""
    from tests.test_fahrtenname import foreign_fields
    from tests.test_fahrtenname import save as save_scout_name

    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    save_scout_name(org.max, "Gekapert", client=client, **foreign_fields(org.walhall_mitglied))

    assert User.objects.get(pk=org.walhall_mitglied.pk).scout_name == org.walhall_mitglied.scout_name
    assert User.objects.get(pk=org.max.pk).scout_name == "Gekapert"


# ---------- Befunde der unabhängigen Prüfung ----------


def test_befund1_kopfseite_mit_gliederung_aus_dem_zugang_kommt_ins_protokoll(org):
    """Die Gliederung zeigt im Zugang die Leitungen von Walhall, auch neben einer Seite nur mit dem Kopf."""
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    for address in (unit_address(org.mosaik), support_address(org.zugvoegel)):
        before = AdminAccess.objects.count()
        response = client.get(address)
        assert "Wirbelwind" in response.content.decode(), address
        assert log()[before:] == [(A.VIEWED, "", "Max Admin", "Walhall")], address


def test_befund1_gegenprobe_alma_auf_der_eigenen_sippe_ohne_eintrag(org):
    """S8 bleibt: Was Alma über die eigene Rolle sieht, kommt nicht ins Protokoll."""
    client = client_for(org.alma)
    start(org.alma, org.walhall, client=client)
    before = AdminAccess.objects.count()

    page_text(org.alma, org.adler, client=client)

    assert AdminAccess.objects.count() == before


def test_befund2_ablauf_beim_tippen_verschluckt_die_meldung_nicht(org, clock):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)
    clock["now"] += timedelta(minutes=61)

    client.post(f"{unit_address(org.walhall)}benennen/vorschlaege/", {"suche": "Wir"}, follow=True,
                headers={"Sec-Fetch-Dest": "empty"})
    root = _tree(client.get(unit_address(org.walhall)))

    assert [text for _classes_, text in fixed_notices(root) if text.endswith(EXPIRED)]


def test_befund3_beenden_nach_dem_loeschen_der_organisation(org):
    empty = Unit(kind=Unit.Kind.GROUP, name="Sippe Irrtum", parent=org.walhall)
    empty.save(by=BY)
    client = client_for(org.max)
    start(org.max, empty, client=client)
    call_command("emergency_delete", empty.key, stdout=io.StringIO())

    response = end(org.max, client=client)

    assert response.status_code == 302
    assert log()[-1][:2] == (A.ENDED, D.BUTTON)


def test_befund4_beenden_nach_ablauf_sagt_nicht_nicht_gespeichert(org, clock):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)
    clock["now"] += timedelta(minutes=61)

    root = _tree(follow(end(org.max, client=client), client))

    shown = fixed_notices(root)
    assert len(shown) == 1 and "ist-info" in shown[0][0]
    assert UNSAVED not in shown[0][1]


# ---------- Bausteine ----------


@pytest.mark.bausteinkatalog
def test_bausteinkatalog_zeigt_den_balken_den_zart_blauen_knopf_und_den_kopf_mit_knopf(org):
    root = page_tree(org.walhall_leitung, "/bausteine/")

    balken = _one(_by_tag(root, "section", aria_labelledby="h-supportbalken"))
    assert "Support-Zugang für Stamm Walhall aktiv bis 14:35" in _visible_text(bar(balken))
    assert _visible_text(_one(_by_tag(bar(balken), "button"))) == "beenden"
    knopf = _one(_by_tag(root, "section", aria_labelledby="h-knopfverschieben"))
    labels = [_visible_text(link) for link in _all(knopf, lambda e: "btn-verschieben" in _classes(e))]
    assert START_LABEL in labels and "Verschieben" in [label.split(":")[0] for label in labels]
    kopf = _one(_by_tag(root, "section", aria_labelledby="h-orgakopf"))
    assert START_LABEL in [_visible_text(link) for link in _all(kopf, lambda e: "btn-verschieben" in _classes(e))]


def test_der_balken_ist_dunkelblau_und_keine_meldung(org):
    client = client_for(org.max)
    start(org.max, org.walhall, client=client)

    shown = bar(_tree(client.get("/")))

    assert "a-meldung" not in _classes(shown)
    assert "a-testband" not in _classes(shown)
    assert _attr(_one(_by_tag(shown, "use")), "href") == "#i-schild"
