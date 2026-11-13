"""Tests für die Probe „Wer eine Veranstaltung anlegt, ist ihre Leitung“ (#100, TEAM-01, BER-03).

Die Kennungen V1 bis V5, VV1 bis VV4 und VG1 bis VG9 verweisen auf die Szenarien vom 30.10.2026
(https://github.com/sebivtt/dpv-participant-management/issues/100#issuecomment-6522727393), die
Wortlaute auf den Text von #100. VG10 (Datumsfeld, Handy, nur Tastatur, wie am Handy tippen) prüft der
Rauchtest `rauchtests/test_veranstaltungen.py`. Personen wie in den Szenarien: Finn (Mitglied der Sippe
Falken), Fiete (Gruppenleitung Falken), Wanda (Stammesleitung Walhall), Vera (Verbandsleitung), Tom
(DPV-Veranstaltungsteam), Otto (Konto ohne Zuordnung), Max (nur Admin). Alle Namen sind erfunden.
Geprüft wird, was beim Browser ankommt, und was danach in der Datenbank steht.
"""

from datetime import date
from types import SimpleNamespace

import pytest
from django.core.exceptions import PermissionDenied

from access.rights import Rights
from events.models import Event
from roles.models import Role
from tests.test_benennen import _one_after_the_other, dialog_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import NO_ACCESS_TEXT, assert_like_missing
from tests.test_organisation import client_for, nav_labels, page_tree, unit_address
from tests.test_rechtepruefung import remove
from tests.test_rollen import build_org, give, person
from tests.query_limit import assert_queries_do_not_grow

R = Role.Kind
pytestmark = pytest.mark.django_db

LIST = "/veranstaltungen/"
CREATE = "/veranstaltungen/erstellen/"
NAV = "Veranstaltungen"
CREATE_LABEL = "Veranstaltung erstellen"
NONE_YET = "Du leitest noch keine Veranstaltung."
PROBELAGER = {"name": "Probelager 2027", "start": "2027-05-15", "end": "2027-05-17"}


# ---------- Personen und Hilfen ----------


def build_people() -> SimpleNamespace:
    """Die Organisationen aus `build_org()` und die Personen der Szenarien."""
    o = build_org()
    o.finn = person("finn.falke", "Finn", "Falke")
    give(o.finn, R.MEMBER, o.falken)
    o.fiete = person("fiete.falke", "Fiete", "Falke")
    give(o.fiete, R.MEMBER, o.falken)
    give(o.fiete, R.GROUP_LEAD, o.falken)
    o.wanda = person("wanda.walhall", "Wanda", "Walhall")
    give(o.wanda, R.MEMBER, o.walhall)
    give(o.wanda, R.TROOP_LEAD, o.walhall)
    o.vera = person("vera.verband", "Vera", "Verband")
    give(o.vera, R.FEDERATION_LEAD, o.dpv)
    o.tom = person("tom.team", "Tom", "Team")
    give(o.tom, R.EVENT_TEAM, o.dpv)
    o.otto = person("otto.ohne", "Otto", "Ohne")
    o.max = person("max.admin", "Max", "Admin")
    give(o.max, R.ADMIN)
    return o


@pytest.fixture
def org():
    return build_people()


def event_of(lead, name: str = "Probelager 2027", start: date = date(2027, 5, 15), end: date = date(2027, 5, 17)):
    """Eine Veranstaltung, wie das Tool sie nach dem Anlegen durch `lead` speichert."""
    found = Event.objects.create(name=name, start=start, end=end)
    found.leads.add(lead)
    return found


@pytest.fixture
def probelager(org):
    """Finns „Probelager 2027“, wie nach V1."""
    return event_of(org.finn)


def event_address(entry) -> str:
    return f"{LIST}{entry.key}/"


def edit_address(entry) -> str:
    return f"{event_address(entry)}bearbeiten/"


def open_create(user, client=None):
    """Öffnet „Veranstaltung erstellen“; gibt den Dialog und die Kennung des Formulars zurück."""
    response = (client or client_for(user)).get(CREATE)
    assert response.status_code == 200, response.status_code
    found = dialog_of(_tree(response))
    return found, _attr(_one(_by_tag(found, "input", name="creation_key")), "value")


def create(user, client=None, **values):
    """Füllt „Veranstaltung erstellen“ aus und klickt auf „Anlegen“."""
    client = client or client_for(user)
    _found, creation_key = open_create(user, client=client)
    return client.post(CREATE, {**PROBELAGER, **values, "creation_key": creation_key})


def open_edit(user, entry, client=None):
    response = (client or client_for(user)).get(edit_address(entry))
    assert response.status_code == 200, response.status_code
    return dialog_of(_tree(response))


def save(user, entry, client=None, **values):
    """Ändert im Dialog „… bearbeiten“ die Angaben und klickt auf „Speichern“."""
    shown = {"name": entry.name, "start": entry.start.isoformat(), "end": entry.end.isoformat()}
    return (client or client_for(user)).post(edit_address(entry), {**shown, **values})


def field_values(dialog) -> dict[str, str]:
    return {_attr(field, "name"): _attr(field, "value") or "" for field in _by_tag(dialog, "input")
            if _attr(field, "type") not in ("hidden",)}


def field_errors(root) -> dict[str, str]:
    """Die Fehler am Feld, je Feld (Baustein „Textfeld“ und „Datumsfeld“)."""
    found = {}
    for block in _all(root, lambda e: "a-textfeld" in _classes(e)):
        errors = _all(block, lambda e: "invalid-feedback" in _classes(e))
        if errors:
            found[_attr(_one(_by_tag(block, "input")), "name")] = _visible_text(_one(errors))
    return found


def listed(user) -> list[tuple[str, str]]:
    """Die Veranstaltungen in der Liste „Veranstaltungen“: Name und Zeitraum, in ihrer Reihenfolge."""
    root = page_tree(user, LIST)
    tiles = _all(root, lambda e: e.name == "li" and "a-orgakachel" in _classes(e))
    return [(_visible_text(_one(_all(tile, lambda e: "a-kachel-link" in _classes(e)))),
             _visible_text(_one(_all(tile, lambda e: "a-rollenmarke" in _classes(e))))) for tile in tiles]


def list_section(user):
    return _one(_by_tag(page_tree(user, LIST), "section", aria_labelledby="h-veranstaltungen"))


def create_button(user) -> str | None:
    """Die Adresse des Knopfs „Veranstaltung erstellen“ in der Liste, oder None."""
    links = [link for link in _by_tag(list_section(user), "a") if _visible_text(link) == CREATE_LABEL]
    return _attr(_one(links), "href") if links else None


def leads_of(entry) -> set[str]:
    return set(entry.leads.values_list("username", flat=True))


SCRIPT = {"HTTP_HX_REQUEST": "true", "HTTP_SEC_FETCH_DEST": "empty", "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def assert_no_access(response) -> None:
    """„Dafür fehlt dir die Berechtigung.“ (403, Entscheidung zu #64)."""
    assert response.status_code == 403, response.status_code
    assert NO_ACCESS_TEXT in response.content.decode()


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VA-01", "VA-02")
def test_v1_finn_legt_probelager_2027_an_und_leitet_es(org):
    client = client_for(org.finn)
    assert NAV in nav_labels(page_tree(org.finn, "/"))
    section = list_section(org.finn)
    assert NONE_YET in _visible_text(section)
    assert create_button(org.finn) == CREATE

    found, _key = open_create(org.finn, client=client)
    assert _text(_one(_by_tag(found, "h2"))) == CREATE_LABEL
    assert list(field_values(found)) == ["name", "start", "end"]
    assert [_attr(field, "type") for field in _by_tag(found, "input") if _attr(field, "name") in ("start", "end")] == [
        "date", "date"]
    assert [_visible_text(button) for button in _by_tag(found, "button")] == ["Anlegen"]

    response = create(org.finn, client=client)

    created = Event.objects.get()
    assert (created.name, created.start, created.end) == ("Probelager 2027", date(2027, 5, 15), date(2027, 5, 17))
    assert leads_of(created) == {"finn.falke"}
    assert response.status_code == 302
    assert response.url == event_address(created)
    page = client.get(response.url)
    assert short_notices(page) == ["Probelager 2027 ist angelegt. Du leitest diese Veranstaltung."]
    root = _tree(page)
    assert _text(_one(_by_tag(root, "h1"))) == "Probelager 2027"
    assert "15.05.2027 bis 17.05.2027" in _visible_text(root)
    assert listed(org.finn) == [("Probelager 2027", "15.05.2027 bis 17.05.2027")]
    assert NONE_YET not in _visible_text(list_section(org.finn))


@pytest.mark.rechtematrix("VA-01", "VA-05")
def test_v2_fiete_vera_und_tom_legen_ebenso_eine_veranstaltung_an(org):
    for user in (org.fiete, org.vera, org.tom, org.wanda):
        assert NAV in nav_labels(page_tree(user, "/")), user.username
        assert create_button(user) == CREATE, user.username

        response = create(user, name=f"Lager von {user.first_name}")

        assert response.status_code == 302, user.username
        assert leads_of(Event.objects.get(name=f"Lager von {user.first_name}")) == {user.username}
        assert listed(user) == [(f"Lager von {user.first_name}", "15.05.2027 bis 17.05.2027")]


@pytest.mark.rechtematrix("VA-02")
def test_v3_finn_aendert_das_ende_auf_den_18_mai(org, probelager):
    client = client_for(org.finn)
    root = page_tree(org.finn, event_address(probelager))
    pencil = _one(_all(root, lambda e: "a-stift" in _classes(e)))
    assert _attr(pencil, "href") == edit_address(probelager)
    assert _text(pencil) == "Probelager 2027 bearbeiten"

    found = open_edit(org.finn, probelager, client=client)
    assert _text(_one(_by_tag(found, "h2"))) == "Probelager 2027 bearbeiten"
    assert field_values(found) == {"name": "Probelager 2027", "start": "2027-05-15", "end": "2027-05-17"}
    assert [_visible_text(button) for button in _by_tag(found, "button")] == ["Speichern"]

    response = save(org.finn, probelager, client=client, end="2027-05-18")

    assert response.status_code == 302
    assert response.url == event_address(probelager)
    probelager.refresh_from_db()
    assert probelager.end == date(2027, 5, 18)
    assert leads_of(probelager) == {"finn.falke"}
    page = client.get(response.url)
    assert short_notices(page) == ["Die Angaben zu Probelager 2027 sind gespeichert."]
    assert "15.05.2027 bis 18.05.2027" in _visible_text(_tree(page))


@pytest.mark.rechtematrix("VA-02", "VA-05")
def test_v4_finn_verliert_die_zuordnung_und_leitet_seine_veranstaltung_weiter(org, probelager):
    remove(org.finn, R.MEMBER, org.falken)

    assert NAV in nav_labels(page_tree(org.finn, "/"))
    section = list_section(org.finn)
    assert create_button(org.finn) is None
    assert listed(org.finn) == [("Probelager 2027", "15.05.2027 bis 17.05.2027")]
    # Ohne Zuordnung auch kein Ersatztext für den Knopf: nur die Überschrift und die Veranstaltung.
    assert _visible_text(section) == "Veranstaltungen, die du leitest 15.05.2027 bis 17.05.2027 Probelager 2027"
    assert client_for(org.finn).get(event_address(probelager)).status_code == 200
    open_edit(org.finn, probelager)
    assert save(org.finn, probelager, end="2027-05-18").status_code == 302
    probelager.refresh_from_db()
    assert probelager.end == date(2027, 5, 18)
    # Anlegen geht ohne Zuordnung nicht mehr (VA-05).
    assert_no_access(client_for(org.finn).get(CREATE))


def test_v5_die_liste_ist_nach_beginn_sortiert_die_frueheste_zuerst(org):
    event_of(org.finn, "Herbstfahrt", date(2027, 10, 1), date(2027, 10, 3))
    event_of(org.finn, "Pfingstlager", date(2027, 5, 14), date(2027, 5, 17))
    event_of(org.finn, "Winterlager", date(2026, 12, 27), date(2026, 12, 30))

    assert [name for name, _period in listed(org.finn)] == ["Winterlager", "Pfingstlager", "Herbstfahrt"]


def test_ein_tag_steht_ohne_bis(org):
    """Ende gleich Beginn (VG4) steht in Liste und Seite nur mit einem Datum."""
    one_day = event_of(org.finn, "Stammestag", date(2027, 6, 5), date(2027, 6, 5))

    assert listed(org.finn) == [("Stammestag", "05.06.2027")]
    assert "05.06.2027" in _visible_text(page_tree(org.finn, event_address(one_day)))


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VA-01", "VA-05")
def test_vv1_otto_und_max_haben_keinen_punkt_und_legen_nichts_an(org):
    for user in (org.otto, org.max):
        client = client_for(user)
        assert NAV not in nav_labels(page_tree(user, "/")), user.username
        assert_no_access(client.get(CREATE))
        assert_no_access(client.get(CREATE, **SCRIPT))
        assert_no_access(client.post(CREATE, {**PROBELAGER, "creation_key": "b" * 20}))
        assert_no_access(client.post(CREATE, {**PROBELAGER, "creation_key": "b" * 20}, **SCRIPT))
        assert_no_access(client.get(LIST))
        with pytest.raises(PermissionDenied):
            Rights(user).create_event({"name": "Probelager 2027", "start": date(2027, 5, 15),
                                       "end": date(2027, 5, 17)}, "c" * 20)

    assert not Event.objects.exists()


@pytest.mark.rechtematrix("VA-05")
def test_vv1_auch_im_support_zugang_legt_max_nichts_an(org):
    """Der Support-Zugang gibt die Rechte einer Leitung, aber keine Zuordnung (VA-05, BER-03)."""
    client = client_for(org.max)
    assert client.post(f"{unit_address(org.walhall)}support-zugang/", {"anlass": "lead_request"}).status_code == 302

    assert NAV not in nav_labels(_tree(client.get("/")))
    assert_no_access(client.get(CREATE))
    assert_no_access(client.post(CREATE, {**PROBELAGER, "creation_key": "b" * 20}))
    assert not Event.objects.exists()


@pytest.mark.rechtematrix("VA-02", "VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/bearbeiten/")
def test_vv2_niemand_ausser_finn_sieht_oder_aendert_probelager_2027(org, probelager):
    for user in (org.wanda, org.fiete, org.vera, org.tom, org.max, org.otto):
        client = client_for(user)
        for address in ("/", "/profil/", "/organisation/", LIST):
            assert "Probelager" not in client.get(address).content.decode(), (user.username, address)
        assert_like_missing(user, event_address(probelager))
        assert_like_missing(user, edit_address(probelager))
        for address in (event_address(probelager), edit_address(probelager)):
            assert client.get(address, **SCRIPT).status_code == 404
            assert client.post(address, {"name": "Gekapert", "start": "2027-01-01", "end": "2027-01-02"},
                               **SCRIPT).status_code == 404

    probelager.refresh_from_db()
    assert (probelager.name, probelager.start, probelager.end) == ("Probelager 2027", date(2027, 5, 15),
                                                                    date(2027, 5, 17))


@pytest.mark.rechtematrix("VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/")
def test_vv2_auch_im_support_zugang_fuer_die_falken_sieht_max_sie_nicht(org, probelager):
    client = client_for(org.max)
    assert client.post(f"{unit_address(org.falken)}support-zugang/", {"anlass": "lead_request"}).status_code == 302

    assert client.get(event_address(probelager)).status_code == 404
    assert client.post(edit_address(probelager), {"name": "Gekapert", "start": "2027-01-01",
                                                   "end": "2027-01-02"}).status_code == 404
    assert_like_missing(org.max, event_address(probelager))
    probelager.refresh_from_db()
    assert probelager.name == "Probelager 2027"


@pytest.mark.rechtematrix("VA-03")
def test_vv2_gegenprobe_finn_sieht_und_bearbeitet_seine_veranstaltung(org, probelager):
    assert client_for(org.finn).get(event_address(probelager)).status_code == 200
    assert client_for(org.finn).get(event_address(probelager), **SCRIPT).status_code == 200
    assert save(org.finn, probelager, name="Probelager 2027 (neu)").status_code == 302


@pytest.mark.rechtematrix("VA-01")
def test_vv3_eine_andere_leitung_im_formular_aendert_nichts(org):
    client = client_for(org.fiete)
    _found, creation_key = open_create(org.fiete, client=client)
    smuggled = {"leads": org.finn.key, "lead": org.finn.key, "leitung": org.finn.key, "user": org.finn.pk,
                "leads_id": org.finn.pk}

    response = client.post(CREATE, {**PROBELAGER, **smuggled, "creation_key": creation_key})

    assert response.status_code == 302
    assert leads_of(Event.objects.get()) == {"fiete.falke"}
    assert listed(org.finn) == []


@pytest.mark.rechtematrix("VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/bearbeiten/")
def test_vv3_fiete_tauscht_die_kennung_gegen_finns_und_findet_nichts(org, probelager):
    own = event_of(org.fiete, "Sippenfahrt", date(2027, 8, 1), date(2027, 8, 5))
    client = client_for(org.fiete)
    open_edit(org.fiete, own, client=client)

    response = client.post(edit_address(probelager), {"name": "Gekapert", "start": "2027-01-01", "end": "2027-01-02"})

    assert response.status_code == 404
    assert_like_missing(org.fiete, edit_address(probelager))
    probelager.refresh_from_db()
    own.refresh_from_db()
    assert (probelager.name, own.name) == ("Probelager 2027", "Sippenfahrt")
    assert leads_of(probelager) == {"finn.falke"}


@pytest.mark.rechtematrix("VA-04")
def test_vv4_es_gibt_keinen_knopf_und_keine_anfrage_zum_loeschen(org, probelager):
    client = client_for(org.finn)
    for address in (event_address(probelager), edit_address(probelager)):
        page = _visible_text(_tree(client.get(address)))
        assert "öschen" not in page, address
    for address in (f"{event_address(probelager)}loeschen/", f"{event_address(probelager)}delete/"):
        assert client.get(address).status_code == 404
        assert client.post(address).status_code == 404
    for address in (event_address(probelager), edit_address(probelager)):
        assert client.delete(address).status_code == 404

    assert Event.objects.filter(pk=probelager.pk, name="Probelager 2027").exists()


@pytest.mark.rechtematrix("VA-04")
def test_vv4_gegenprobe_finn_sieht_seine_veranstaltung_danach_weiter(org, probelager):
    client_for(org.finn).delete(event_address(probelager))

    assert client_for(org.finn).get(event_address(probelager)).status_code == 200
    assert listed(org.finn) == [("Probelager 2027", "15.05.2027 bis 17.05.2027")]


# ---------- Grenzfälle ----------


def test_vg1_name_leer_oder_nur_leerzeichen(org):
    for empty in ("", "   ", "  "):
        response = create(org.finn, name=empty)
        assert response.status_code == 200
        root = _tree(response)
        assert field_errors(root) == {"name": "Bitte gib den Namen ein."}, repr(empty)
        # Die übrigen Eingaben bleiben stehen.
        assert field_values(dialog_of(root))["start"] == "2027-05-15"

    assert not Event.objects.exists()
    assert create(org.finn, name="  Probelager ").status_code == 302
    assert Event.objects.get().name == "Probelager"


def test_vg2_hundert_zeichen_gehen_bei_hunderteins_kommt_die_meldung(org):
    response = create(org.finn, name="x" * 101)

    assert response.status_code == 200
    root = _tree(response)
    assert field_errors(root) == {"name": "Der Name darf höchstens 100 Zeichen lang sein."}
    # Nichts wird abgeschnitten.
    assert field_values(dialog_of(root))["name"] == "x" * 101
    assert not Event.objects.exists()
    assert create(org.finn, name="x" * 100).status_code == 302
    assert Event.objects.get().name == "x" * 100


def test_vg3_fehlender_beginn_fehlendes_ende_und_unmoegliches_datum(org):
    cases = [
        ({"start": ""}, {"start": "Bitte gib den Beginn ein."}),
        ({"end": ""}, {"end": "Bitte gib das Ende ein."}),
        ({"start": "", "end": ""}, {"start": "Bitte gib den Beginn ein.", "end": "Bitte gib das Ende ein."}),
        ({"start": "2027-02-31"}, {"start": "Bitte gib ein gültiges Datum ein."}),
        ({"end": "2027-02-31"}, {"end": "Bitte gib ein gültiges Datum ein."}),
        ({"start": "31.02.2027"}, {"start": "Bitte gib ein gültiges Datum ein."}),
    ]
    for values, errors in cases:
        response = create(org.finn, **values)
        assert response.status_code == 200, values
        root = _tree(response)
        assert field_errors(root) == errors, values
        assert field_values(dialog_of(root))["name"] == "Probelager 2027", values

    assert not Event.objects.exists()


def test_vg4_ende_vor_beginn_geht_nicht_ende_gleich_beginn_geht(org):
    response = create(org.finn, start="2027-05-17", end="2027-05-15")

    assert response.status_code == 200
    root = _tree(response)
    assert field_errors(root) == {"end": "Das Ende liegt vor dem Beginn."}
    assert field_values(dialog_of(root)) == {"name": "Probelager 2027", "start": "2027-05-17", "end": "2027-05-15"}
    assert not Event.objects.exists()
    assert create(org.finn, start="2027-05-15", end="2027-05-15").status_code == 302
    assert Event.objects.get().end == date(2027, 5, 15)


def test_vg5_eine_veranstaltung_in_der_vergangenheit_geht(org):
    assert create(org.finn, name="Rückblick", start="2026-03-01", end="2026-03-02").status_code == 302

    assert listed(org.finn) == [("Rückblick", "01.03.2026 bis 02.03.2026")]


def test_vg6_beim_bearbeiten_gelten_dieselben_regeln(org, probelager):
    cases = [
        ({"name": " "}, {"name": "Bitte gib den Namen ein."}),
        ({"name": "x" * 101}, {"name": "Der Name darf höchstens 100 Zeichen lang sein."}),
        ({"start": ""}, {"start": "Bitte gib den Beginn ein."}),
        ({"end": ""}, {"end": "Bitte gib das Ende ein."}),
        ({"end": "2027-02-31"}, {"end": "Bitte gib ein gültiges Datum ein."}),
        ({"end": "2027-05-14"}, {"end": "Das Ende liegt vor dem Beginn."}),
    ]
    for values, errors in cases:
        response = save(org.finn, probelager, **{"name": "Probelager 2028", **values})
        assert response.status_code == 200, values
        root = _tree(response)
        assert field_errors(root) == errors, values
        shown = field_values(dialog_of(root))
        for name, value in {"name": "Probelager 2028", "start": "2027-05-15", "end": "2027-05-17", **values}.items():
            assert shown[name] == value, (values, name)

    probelager.refresh_from_db()
    assert (probelager.name, probelager.start, probelager.end) == ("Probelager 2027", date(2027, 5, 15),
                                                                    date(2027, 5, 17))
    assert save(org.finn, probelager, name=" Probelager 2028 ").status_code == 302
    probelager.refresh_from_db()
    assert probelager.name == "Probelager 2028"


def test_vg7_zwei_veranstaltungen_mit_gleichem_namen_sind_erlaubt(org):
    assert create(org.finn).status_code == 302
    assert create(org.finn).status_code == 302

    assert [name for name, _period in listed(org.finn)] == ["Probelager 2027", "Probelager 2027"]


def test_vg8_doppelklick_auf_anlegen_legt_sie_nur_einmal_an(org):
    client = client_for(org.finn)
    _found, creation_key = open_create(org.finn, client=client)
    form = {**PROBELAGER, "creation_key": creation_key}

    first = client.post(CREATE, form)
    second = client.post(CREATE, form)

    assert (first.status_code, second.status_code) == (302, 302)
    assert Event.objects.count() == 1
    assert second.url == event_address(Event.objects.get())
    assert short_notices(client.get(second.url)) == ["Probelager 2027 ist angelegt. Du leitest diese Veranstaltung."]


def test_vg8_eine_kennung_in_falscher_form_legt_nichts_an(org):
    for creation_key in ("", "kurz", "A" * 20, "1" * 20):
        response = client_for(org.finn).post(CREATE, {**PROBELAGER, "creation_key": creation_key})
        assert response.status_code == 404, creation_key

    assert not Event.objects.exists()


def test_vg8_die_kennung_einer_fremden_veranstaltung_legt_nichts_an_und_zeigt_sie_nicht(org, probelager):
    """Schickt Fiete die Kennung des Formulars, aus dem Finn angelegt hat, entsteht nichts, und er landet nicht bei Finn."""
    response = client_for(org.fiete).post(CREATE, {**PROBELAGER, "creation_key": probelager.creation_key})

    assert response.status_code == 404
    assert Event.objects.count() == 1
    assert leads_of(probelager) == {"finn.falke"}


def test_der_dialog_erstellen_kommt_nicht_aus_dem_zwischenspeicher(org):
    """Nach „Zurück“ im Browser kommt das Formular neu, mit neuer Kennung (wie MG7 aus #117)."""
    assert "no-store" in client_for(org.finn).get(CREATE)["Cache-Control"]


@pytest.mark.django_db(transaction=True)
def test_vg8_gleichzeitig_abgeschickt_entsteht_sie_nur_einmal():
    o = build_people()
    values = {"name": "Probelager 2027", "start": date(2027, 5, 15), "end": date(2027, 5, 17)}
    creation_key = "d" * 20

    _one_after_the_other(lambda: Rights(o.finn).create_event(values, creation_key),
                         lambda: Rights(o.finn).create_event(values, creation_key))

    assert Event.objects.count() == 1


@pytest.mark.rechtematrix("VA-05")
def test_vg9_finn_verliert_die_mitgliedschaft_bei_offenem_formular(org):
    client = client_for(org.finn)
    _found, creation_key = open_create(org.finn, client=client)

    remove(org.finn, R.MEMBER, org.falken)
    response = client.post(CREATE, {**PROBELAGER, "creation_key": creation_key})

    assert_no_access(response)
    assert not Event.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_vg9_die_zuordnung_endet_waehrend_des_anlegens():
    """Wird die Mitgliedschaft gleichzeitig beendet, wartet das Anlegen und prüft danach frisch."""
    o = build_people()
    values = {"name": "Probelager 2027", "start": date(2027, 5, 15), "end": date(2027, 5, 17)}
    results = []

    def end_membership():
        remove(o.finn, R.MEMBER, o.falken)

    def create_event():
        try:
            Rights(o.finn).create_event(values, "e" * 20)
        except PermissionDenied:
            results.append("verboten")

    _one_after_the_other(end_membership, create_event)

    assert results == ["verboten"]
    assert not Event.objects.exists()


# ---------- Datenmodell und Liste ----------


def test_die_datenbank_lehnt_leeren_namen_und_ende_vor_beginn_ab(org):
    from django.db import IntegrityError, transaction

    for values in ({"name": " Probelager"}, {"name": ""}, {"end": date(2027, 5, 14)}):
        with pytest.raises(IntegrityError), transaction.atomic():
            Event.objects.create(**{"name": "Probelager", "start": date(2027, 5, 15), "end": date(2027, 5, 17),
                                    **values})


def test_die_liste_waechst_nicht_mit_den_abfragen(org):
    client = client_for(org.finn)

    def create_entry(number: int) -> None:
        event_of(org.finn, f"Fahrt {number}", date(2027, 1, 1 + number), date(2027, 1, 2 + number))

    def load_list() -> None:
        assert client.get(LIST).status_code == 200

    assert_queries_do_not_grow(create_entry, load_list)
    assert len(listed(org.finn)) == 10


def test_der_punkt_ist_auf_den_seiten_der_veranstaltungen_hervorgehoben(org, probelager):
    for address in (LIST, CREATE, event_address(probelager), edit_address(probelager)):
        root = page_tree(org.finn, address)
        active = [_visible_text(link) for link in _all(root, lambda e: "a-navlink" in _classes(e))
                  if _attr(link, "aria-current") == "page"]
        # Die Navigation steht dreimal: Seitenleiste, Menü am Handy und Liste am Seitenende (#281).
        assert set(active) == {NAV}, address
