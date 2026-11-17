"""Tests für die Probe „Anmeldungen nennen konkrete Personen“ (#101, ANM-01, ANM-02).

Die Kennungen A1 bis A7, S1 bis S4, AV1 bis AV8, AG1 bis AG4 und U1 bis U4 verweisen auf den Kommentar
„Szenarien (15.11.2026)“ in #101
(https://github.com/sebivtt/dpv-participant-management/issues/101#issuecomment-6901245455), alle von Sebastian
angenommen. AG3 und U4 (Testdaten-Befehl) prüft `tests/test_testdaten.py`, AG4 (Handy, nur Tastatur) der
Rauchtest `rauchtests/test_anmeldungen.py`. Anmeldungen entstehen in P2 nur im Datenmodell, über die zentrale
Rechteprüfung (`Rights.register()`); ein Formular gibt es nicht (AN-06).

Personen wie in den Szenarien: Bea (Bundesleitung Boreas, leitet „Probelager 2027“), Wanda (Stammesleitung
Walhall), Fiete (Gruppenleitung Sippe Falken), Finn (Mitglied der Falken), Wilma (Mitglied direkt im Stamm
Walhall), Zeno (Stammesleitung Zugvögel), Kai (Ringleitung Küste), Lars (Stammesleitung Leuchtturm unter
Küste), Vera (Verbandsleitung), Tom (DPV-Veranstaltungsteam), Otto (Konto ohne Zuordnung), Max (nur Admin).
Verwaltete Personen: Paul Probe (Walhall), Lena Probe „Kiwi“ (Falken), Jonas Muster (Falken), Theo Probe
(Meute Wölfe), Ole Probe (Sippe Adler, Zugvögel; in den Szenarien Sippe Kraniche) und Karl Muster (Meute
Möwen unter Leuchtturm). Die Organisationen kommen aus `build_org()`. Alle Namen sind erfunden.
"""

from datetime import date
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction

from access.rights import Rights
from events.models import Event, RegisteredPerson, Registration
from persons.models import ManagedPerson
from roles.models import Role
from tests.query_limit import assert_queries_do_not_grow
from tests.test_benennen import _one_after_the_other
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import NO_ACCESS_TEXT, assert_like_missing
from tests.test_organisation import client_for, nav_labels, page_tree, unit_address
from tests.test_rechtepruefung import remove
from tests.test_rollen import build_org, give, person

R = Role.Kind
pytestmark = pytest.mark.django_db

SECTION = "h-anmeldungen"
NONE_YET = "Zu dieser Veranstaltung gibt es noch keine Anmeldungen."
SCRIPT = {"HTTP_HX_REQUEST": "true", "HTTP_SEC_FETCH_DEST": "empty", "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


# ---------- Personen und Hilfen ----------


def managed(unit, first_name: str, last_name: str, born: str, scout_name: str = "") -> ManagedPerson:
    """Eine verwaltete Person, wie sie nach dem Anlegen im Tool gespeichert ist."""
    entry = ManagedPerson(unit=unit, first_name=first_name, last_name=last_name, birth_date=date.fromisoformat(born),
                          scout_name=scout_name)
    entry.save()
    return entry


def lead(username: str, first_name: str, last_name: str, kind: str, unit):
    """Eine Leitung mit Konto; wer Leitung wird, ist dort zugleich Mitglied (#89)."""
    user = person(username, first_name, last_name)
    give(user, R.MEMBER, unit)
    give(user, kind, unit)
    return user


def build_people() -> SimpleNamespace:
    """Die Organisationen aus `build_org()` und die Personen der Szenarien."""
    o = build_org()
    o.bea = lead("bea.boreas", "Bea", "Boreas", R.ASSOCIATION_LEAD, o.boreas)
    o.wanda = lead("wanda.walhall", "Wanda", "Walhall", R.TROOP_LEAD, o.walhall)
    o.fiete = lead("fiete.falke", "Fiete", "Falke", R.GROUP_LEAD, o.falken)
    o.zeno = lead("zeno.zugvogel", "Zeno", "Zugvogel", R.TROOP_LEAD, o.zugvoegel)
    o.kai = lead("kai.kueste", "Kai", "Küste", R.RING_LEAD, o.kueste)
    o.lars = lead("lars.leuchtturm", "Lars", "Leuchtturm", R.TROOP_LEAD, o.leuchtturm)
    o.finn = person("finn.falke", "Finn", "Falke")
    give(o.finn, R.MEMBER, o.falken)
    o.wilma = person("wilma.walhall", "Wilma", "Walhall")
    give(o.wilma, R.MEMBER, o.walhall)
    o.vera = person("vera.verband", "Vera", "Verband")
    give(o.vera, R.FEDERATION_LEAD, o.dpv)
    o.tom = person("tom.team", "Tom", "Team")
    give(o.tom, R.EVENT_TEAM, o.dpv)
    o.otto = person("otto.ohne", "Otto", "Ohne")
    o.max = person("max.admin", "Max", "Admin")
    give(o.max, R.ADMIN)
    o.paul = managed(o.walhall, "Paul", "Probe", "2012-09-03")
    o.lena = managed(o.falken, "Lena", "Probe", "2015-05-14", "Kiwi")
    o.jonas = managed(o.falken, "Jonas", "Muster", "2014-02-11")
    o.theo = managed(o.woelfe, "Theo", "Probe", "2017-01-19")
    o.ole = managed(o.adler, "Ole", "Probe", "2014-07-15", "Luchs")
    o.karl = managed(o.moewen, "Karl", "Muster", "2014-01-16", "Fuchs")
    o.probelager = event_of(o.bea)
    return o


@pytest.fixture
def org():
    return build_people()


def event_of(lead_user, name: str = "Probelager 2027", start: date = date(2027, 5, 15),
             end: date = date(2027, 5, 17)) -> Event:
    """Eine Veranstaltung, wie das Tool sie nach dem Anlegen durch `lead_user` speichert (#100)."""
    found = Event.objects.create(name=name, start=start, end=end)
    found.leads.add(lead_user)
    return found


@pytest.fixture
def sammelanmeldung(org) -> Registration:
    """Wandas Sammelanmeldung zum Probelager, wie nach A1."""
    return Rights(org.wanda).register(org.probelager, [org.wanda, org.paul, org.lena, org.theo])


def event_address(entry: Event) -> str:
    return f"/veranstaltungen/{entry.key}/"


def registration_address(entry: Registration) -> str:
    return f"/anmeldungen/{entry.key}/"


def copies(entry: Registration) -> list[tuple]:
    """Was die Anmeldung je Person gespeichert hat, in der Reihenfolge des Anmeldens."""
    return [(p.first_name, p.last_name, p.birth_date, p.scout_name, p.account_id, p.managed_id)
            for p in RegisteredPerson.objects.filter(registration=entry).order_by("pk")]


def refused(action) -> ValidationError:
    """Führt eine Anmeldung aus, die das Datenmodell ablehnen muss, und gibt die Ablehnung zurück."""
    with pytest.raises(ValidationError) as error, transaction.atomic():
        action()
    return error.value


def section_of(user, entry: Event):
    """Der Abschnitt „Anmeldungen“ auf der Seite der Veranstaltung."""
    return _one(_by_tag(page_tree(user, event_address(entry)), "section", aria_labelledby=SECTION))


def listed(user, entry: Event) -> list[tuple[str, str, str]]:
    """Die Anmeldungen im Abschnitt: Ansprechperson (Text des Links), Adresse des Links und die Namen."""
    found = []
    for item in _by_tag(section_of(user, entry), "li"):
        link = _one(_by_tag(item, "a"))
        found.append((_visible_text(link), _attr(link, "href"), _visible_text(_one(_by_tag(item, "span")))))
    return found


def registration_page(user, entry: Registration) -> dict:
    """Was die Seite einer Anmeldung zeigt: Veranstaltung, Zeitraum, Link, Ansprechperson und Personen."""
    response = client_for(user).get(registration_address(entry))
    assert response.status_code == 200, response.status_code
    root = _tree(response)
    event_section = _one(_by_tag(root, "section", aria_labelledby="h-anmeldung-veranstaltung"))
    persons_section = _one(_by_tag(root, "section", aria_labelledby="h-anmeldung-personen"))
    heading = _one(_by_tag(event_section, "h2"))
    links = _by_tag(heading, "a")
    rows = []
    for item in _by_tag(persons_section, "li"):
        parts = [_visible_text(part) for part in _by_tag(item, "span")]
        rows.append((parts[0], parts[1] if len(parts) > 1 else ""))
    return {
        "title": _text(_one(_by_tag(root, "h1"))),
        "event": _visible_text(heading),
        "event_href": _attr(_one(links), "href") if links else None,
        "text": _visible_text(event_section),
        "persons": rows,
    }


def assert_no_access(response) -> None:
    """„Dafür fehlt dir die Berechtigung.“ (403, Entscheidung zu #64)."""
    assert response.status_code == 403, response.status_code
    assert NO_ACCESS_TEXT in response.content.decode()


def start_support(user, unit) -> None:
    """Max startet einen Support-Zugang für `unit`, wie über den Knopf an der Seite der Organisation (#92)."""
    response = client_for(user).post(f"{unit_address(unit)}support-zugang/", {"anlass": "lead_request"})
    assert response.status_code == 302


# ---------- Anmelden im Datenmodell, erlaubt ----------


@pytest.mark.rechtematrix("AN-04")
def test_a1_wanda_meldet_sich_paul_lena_und_theo_an(org):
    created = Rights(org.wanda).register(org.probelager, [org.wanda, org.paul, org.lena, org.theo])

    assert Registration.objects.get() == created
    assert (created.event, created.contact) == (org.probelager, org.wanda)
    assert copies(created) == [
        ("Wanda", "Walhall", None, "", org.wanda.pk, None),
        ("Paul", "Probe", date(2012, 9, 3), "", None, org.paul.pk),
        ("Lena", "Probe", date(2015, 5, 14), "Kiwi", None, org.lena.pk),
        ("Theo", "Probe", date(2017, 1, 19), "", None, org.theo.pk),
    ]


@pytest.mark.rechtematrix("AN-04")
def test_a2_fiete_meldet_lena_und_jonas_an_ohne_sich_selbst(org):
    created = Rights(org.fiete).register(org.probelager, [org.lena, org.jonas])

    assert created.contact == org.fiete
    assert [row[:2] for row in copies(created)] == [("Lena", "Probe"), ("Jonas", "Muster")]


@pytest.mark.rechtematrix("AN-04")
def test_a3_kai_meldet_karl_und_lars_an(org):
    created = Rights(org.kai).register(org.probelager, [org.karl, org.lars])

    assert created.contact == org.kai
    assert copies(created) == [("Karl", "Muster", date(2014, 1, 16), "Fuchs", None, org.karl.pk),
                               ("Lars", "Leuchtturm", None, "", org.lars.pk, None)]


@pytest.mark.rechtematrix("AN-04", "AN-05")
def test_a4_finn_vera_tom_otto_und_max_melden_sich_selbst_an(org):
    for user in (org.finn, org.vera, org.tom, org.otto, org.max):
        created = Rights(user).register(org.probelager, [user])

        assert created.contact == user, user.username
        assert copies(created) == [(user.first_name, user.last_name, None, "", user.pk, None)], user.username
    assert Registration.objects.count() == 5


def test_a5_die_anmeldung_behaelt_die_angaben_vom_anmelden(org):
    org.finn.set_scout_name("Falke")
    created = Rights(org.fiete).register(org.probelager, [org.lena])
    own = Rights(org.finn).register(org.probelager, [org.finn])

    values = {"first_name": "Lena", "last_name": "Probe", "birth_date": date(2015, 5, 14), "scout_name": "Spatz"}
    done, _entry, _text = Rights(org.fiete).edit_managed(org.falken, org.lena.key, values, 1)
    assert done
    org.finn.set_scout_name("Habicht")

    assert copies(created) == [("Lena", "Probe", date(2015, 5, 14), "Kiwi", None, org.lena.pk)]
    assert copies(own) == [("Finn", "Falke", None, "Falke", org.finn.pk, None)]


def test_a6_lena_wird_geloescht_und_bleibt_in_der_anmeldung(org, sammelanmeldung):
    text = Rights(org.fiete).delete_managed(org.falken, org.lena.key)

    # Kein Hinweis beim Löschen (U2): dieselbe kurze Meldung wie ohne Anmeldung.
    assert text == "Kiwi (Lena Probe) wurde gelöscht."
    assert not ManagedPerson.objects.filter(pk=org.lena.pk).exists()
    assert copies(sammelanmeldung)[2] == ("Lena", "Probe", date(2015, 5, 14), "Kiwi", None, None)
    assert listed(org.bea, org.probelager)[0][2] == "Wanda Walhall, Paul Probe, Kiwi (Lena Probe), Theo Probe"


def test_a7_wanda_meldet_lena_ein_zweites_mal_an(org, sammelanmeldung):
    second = Rights(org.wanda).register(org.probelager, [org.lena])

    assert second != sammelanmeldung
    assert Registration.objects.count() == 2
    assert [row[5] for row in copies(second)] == [org.lena.pk]


# ---------- Ansehen, erlaubt ----------


@pytest.mark.rechtematrix("AN-01")
def test_s1_bea_sieht_die_anmeldungen_mit_ansprechperson_und_namen_die_aelteste_zuerst(org, sammelanmeldung):
    later = Rights(org.fiete).register(org.probelager, [org.lena, org.jonas])
    root = page_tree(org.bea, event_address(org.probelager))
    section = section_of(org.bea, org.probelager)

    assert _text(_one(_by_tag(section, "h2"))) == "Anmeldungen"
    assert listed(org.bea, org.probelager) == [
        ("Wanda Walhall", registration_address(sammelanmeldung),
         "Wanda Walhall, Paul Probe, Kiwi (Lena Probe), Theo Probe"),
        ("Fiete Falke", registration_address(later), "Kiwi (Lena Probe), Jonas Muster"),
    ]
    assert _text(_one(_by_tag(root, "h1"))) == "Probelager 2027"


@pytest.mark.rechtematrix("AN-01")
def test_s2_ohne_anmeldungen_steht_der_satz(org):
    section = section_of(org.bea, org.probelager)

    assert NONE_YET in _visible_text(section)
    assert _by_tag(section, "li") == []


@pytest.mark.rechtematrix("AN-01", "AN-02")
def test_s3_bea_und_wanda_sehen_dieselbe_seite_der_anmeldung(org, sammelanmeldung):
    shown_to_bea = registration_page(org.bea, sammelanmeldung)
    shown_to_wanda = registration_page(org.wanda, sammelanmeldung)

    assert shown_to_bea["title"] == "Anmeldung"
    assert shown_to_bea["event"] == "Probelager 2027"
    assert "15.05.2027 bis 17.05.2027" in shown_to_bea["text"]
    assert "Ansprechperson: Wanda Walhall" in shown_to_bea["text"]
    assert shown_to_bea["persons"] == [
        ("Wanda Walhall", ""),
        ("Paul Probe", "03.09.2012"),
        ("Kiwi (Lena Probe)", "14.05.2015"),
        ("Theo Probe", "19.01.2017"),
    ]
    # Nur die Veranstaltungsleitung kommt über den Namen zur Seite der Veranstaltung (VA-03).
    assert shown_to_bea["event_href"] == event_address(org.probelager)
    assert shown_to_wanda["event_href"] is None
    assert {**shown_to_wanda, "event_href": None} == {**shown_to_bea, "event_href": None}


@pytest.mark.rechtematrix("AN-02")
def test_s3_auch_aus_dem_skript_sieht_wanda_ihre_anmeldung(org, sammelanmeldung):
    response = client_for(org.wanda).get(registration_address(sammelanmeldung), **SCRIPT)

    assert response.status_code == 200
    assert "Kiwi (Lena Probe)" in response.content.decode()


@pytest.mark.rechtematrix("AN-02", "EP-06")
def test_s4_wanda_verliert_leitung_und_zuordnung_und_sieht_ihre_anmeldung_weiter(org, sammelanmeldung):
    remove(org.wanda, R.TROOP_LEAD, org.walhall)
    remove(org.wanda, R.MEMBER, org.walhall)
    assert not Role.objects.filter(user=org.wanda).exists()

    shown = registration_page(org.wanda, sammelanmeldung)

    assert [name for name, _born in shown["persons"]] == ["Wanda Walhall", "Paul Probe", "Kiwi (Lena Probe)",
                                                          "Theo Probe"]


# ---------- Verboten ----------


@pytest.mark.rechtematrix("AN-04", "AN-05")
def test_av1_fiete_und_wanda_melden_niemanden_ausserhalb_ihres_bereichs_an(org):
    cases = (
        (org.fiete, [org.wilma]),
        (org.fiete, [org.ole]),
        (org.fiete, [org.lena, org.ole]),
        (org.fiete, [org.paul]),
        (org.wanda, [org.ole]),
        (org.wanda, [org.wanda, org.paul, org.ole]),
        (org.wanda, [org.zeno]),
    )
    for user, people in cases:
        refused(lambda user=user, people=people: Rights(user).register(org.probelager, people))

    assert not Registration.objects.exists()
    assert not RegisteredPerson.objects.exists()


@pytest.mark.rechtematrix("AN-04", "AN-05")
def test_av1_auch_am_datenmodell_vorbei_entsteht_nichts(org, sammelanmeldung):
    """Das Datenmodell prüft selbst, nicht nur die Rechteprüfung davor (ANM-01, damit P4 nicht daran vorbeikommt)."""
    refused(lambda: Registration.create(org.probelager, org.fiete, [org.ole]))
    refused(lambda: Registration.create(org.probelager, org.fiete, [org.lena, org.wilma]))
    refused(lambda: RegisteredPerson(registration=sammelanmeldung, first_name="Ole", last_name="Probe",
                                     birth_date=date(2014, 7, 15), managed=org.ole).save())

    assert Registration.objects.count() == 1
    assert len(copies(sammelanmeldung)) == 4


@pytest.mark.rechtematrix("AN-04")
def test_av1_gegenprobe_wanda_meldet_lena_aus_einer_gruppe_ihres_stammes_an(org):
    created = Rights(org.wanda).register(org.probelager, [org.lena, org.wilma])

    assert [row[:2] for row in copies(created)] == [("Lena", "Probe"), ("Wilma", "Walhall")]


@pytest.mark.rechtematrix("AN-05")
def test_av2_finn_vera_tom_und_otto_melden_niemand_anderen_an(org):
    for user in (org.finn, org.vera, org.tom, org.otto, org.max):
        for other in (org.lena, org.wanda, org.finn if user != org.finn else org.wilma):
            refused(lambda user=user, other=other: Rights(user).register(org.probelager, [other]))
        refused(lambda user=user: Rights(user).register(org.probelager, [user, org.lena]))

    assert not Registration.objects.exists()


@pytest.mark.rechtematrix("AN-05", "SZ-03")
def test_av3_max_im_support_zugang_meldet_nur_sich_selbst_an(org):
    start_support(org.max, org.walhall)
    rights = Rights(org.max)
    assert rights.support is not None
    # Gegenprobe: Im Zugang sieht Max Lena wie die Stammesleitung (SZ-03).
    assert org.lena in rights.managed_in(org.falken)

    refused(lambda: Rights(org.max).register(org.probelager, [org.lena]))
    refused(lambda: Rights(org.max).register(org.probelager, [org.wilma]))
    assert not Registration.objects.exists()

    created = Rights(org.max).register(org.probelager, [org.max])
    assert [row[4] for row in copies(created)] == [org.max.pk]


@pytest.mark.rechtematrix("AN-03", "SZ-06")
@pytest.mark.wie_nicht_vorhanden("anmeldungen/<key:registration>/")
def test_av4_niemand_ausser_bea_und_wanda_sieht_wandas_anmeldung(org, sammelanmeldung):
    address = registration_address(sammelanmeldung)
    for user in (org.fiete, org.zeno, org.vera, org.tom, org.otto, org.finn, org.max, org.kai, org.wilma):
        client = client_for(user)
        assert client.get(address).status_code == 404, user.username
        assert client.get(address, **SCRIPT).status_code == 404, user.username
        assert_like_missing(user, address)


@pytest.mark.rechtematrix("AN-03")
@pytest.mark.wie_nicht_vorhanden("anmeldungen/<key:registration>/")
def test_av4_auch_im_support_zugang_fuer_walhall_sieht_max_sie_nicht(org, sammelanmeldung):
    start_support(org.max, org.walhall)

    assert client_for(org.max).get(registration_address(sammelanmeldung)).status_code == 404
    assert client_for(org.max).get(registration_address(sammelanmeldung), **SCRIPT).status_code == 404
    assert_like_missing(org.max, registration_address(sammelanmeldung))


@pytest.mark.rechtematrix("AN-03")
def test_av4_gegenprobe_bea_und_wanda_sehen_sie(org, sammelanmeldung):
    for user in (org.bea, org.wanda):
        assert client_for(user).get(registration_address(sammelanmeldung)).status_code == 200, user.username


@pytest.mark.rechtematrix("AN-02", "AN-03")
@pytest.mark.wie_nicht_vorhanden("anmeldungen/<key:registration>/")
def test_av5_fiete_sieht_seine_anmeldung_aber_nicht_wandas(org, sammelanmeldung):
    own = Rights(org.fiete).register(org.probelager, [org.lena, org.jonas])
    client = client_for(org.fiete)

    assert client.get(registration_address(own)).status_code == 200
    assert client.get(registration_address(sammelanmeldung)).status_code == 404
    assert_like_missing(org.fiete, registration_address(sammelanmeldung))
    # Die Seite des Probelagers bleibt für ihn „nicht gefunden“ (VA-03).
    assert client.get(event_address(org.probelager)).status_code == 404


@pytest.mark.rechtematrix("AN-01")
@pytest.mark.wie_nicht_vorhanden("anmeldungen/<key:registration>/")
def test_av6_bea_sieht_die_anmeldungen_zu_fietes_hajk_nicht(org, sammelanmeldung):
    hajk = event_of(org.fiete, "Hajk Falken", date(2027, 7, 1), date(2027, 7, 3))
    other = Rights(org.wanda).register(hajk, [org.lena])

    assert [row[0] for row in listed(org.bea, org.probelager)] == ["Wanda Walhall"]
    assert client_for(org.bea).get(registration_address(other)).status_code == 404
    assert_like_missing(org.bea, registration_address(other))
    assert listed(org.fiete, hajk) == [("Wanda Walhall", registration_address(other), "Kiwi (Lena Probe)")]


@pytest.mark.rechtematrix("AN-06")
def test_av7_es_gibt_keinen_knopf_und_keine_adresse_zum_anlegen_aendern_oder_loeschen(org, sammelanmeldung):
    client = client_for(org.bea)
    for address in (event_address(org.probelager), registration_address(sammelanmeldung)):
        main = _one(_by_tag(_tree(client.get(address)), "main"))
        # Ohne das Formular „Abmelden“ der Navigation am Seitenende (#281); die gehört nicht zur Seite.
        forms = [form for form in _by_tag(main, "form") if _attr(form, "action") != "/abmelden/"]
        assert forms == [], address
        text = " ".join(_visible_text(part) for part in _by_tag(main, "section") if "a-flaeche" in _classes(part))
        for word in ("öschen", "bmelden", "hinzufügen", "ändern", "Anmeldung erstellen"):
            assert word not in text, (address, word)
    attempts = (
        "/anmeldungen/", "/anmeldungen/erstellen/", f"{event_address(org.probelager)}anmelden/",
        f"{event_address(org.probelager)}anmeldungen/", f"{registration_address(sammelanmeldung)}bearbeiten/",
        f"{registration_address(sammelanmeldung)}loeschen/",
    )
    for user in (org.bea, org.wanda, org.fiete):
        for address in attempts:
            assert client_for(user).get(address).status_code == 404, (user.username, address)
            assert client_for(user).post(address, {"person": org.lena.key}).status_code == 404, (user.username, address)
        for method in ("post", "put", "patch", "delete"):
            response = getattr(client_for(user), method)(registration_address(sammelanmeldung))
            assert response.status_code == 404, (user.username, method)

    assert Registration.objects.count() == 1
    assert len(copies(sammelanmeldung)) == 4


@pytest.mark.rechtematrix("AN-06")
def test_av7_gegenprobe_bea_sieht_die_anmeldung_danach_unveraendert(org, sammelanmeldung):
    client_for(org.bea).post(registration_address(sammelanmeldung), {"contact": org.fiete.key})

    assert registration_page(org.bea, sammelanmeldung)["persons"][0] == ("Wanda Walhall", "")


@pytest.mark.rechtematrix("VA-05")
def test_av8_otto_ist_ansprechperson_und_legt_trotzdem_keine_veranstaltung_an(org):
    Rights(org.otto).register(org.probelager, [org.otto])
    client = client_for(org.otto)

    assert_no_access(client.get("/veranstaltungen/erstellen/"))
    assert_no_access(client.post("/veranstaltungen/erstellen/", {"name": "Ottos Lager", "start": "2027-05-15",
                                                                 "end": "2027-05-17", "creation_key": "e" * 20}))
    assert Event.objects.count() == 1
    assert not Rights(org.otto).may_create_event()


# ---------- Grenzfälle ----------


def test_ag1_ohne_person_oder_ohne_veranstaltung_entsteht_keine_anmeldung(org):
    refused(lambda: Rights(org.wanda).register(org.probelager, []))
    refused(lambda: Rights(org.wanda).register(None, [org.wanda]))
    refused(lambda: Registration.create(org.probelager, org.wanda, []))
    refused(lambda: Registration(event=org.probelager, contact=org.wanda).save())

    assert not Registration.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_ag1_die_leitung_endet_waehrend_des_anmeldens():
    """Wird Fietes Gruppenleitung gleichzeitig beendet, wartet das Anmelden und prüft danach frisch (wie VG9 aus #100)."""
    o = build_people()
    results = []

    def end_lead():
        remove(o.fiete, R.GROUP_LEAD, o.falken)

    def register():
        try:
            Rights(o.fiete).register(o.probelager, [o.lena])
        except ValidationError:
            results.append("abgelehnt")

    _one_after_the_other(end_lead, register)

    assert results == ["abgelehnt"]
    assert not Registration.objects.exists()


def test_ag2_der_abschnitt_waechst_nicht_mit_den_abfragen(org):
    client = client_for(org.bea)

    def create_entry(number: int) -> None:
        Rights(org.wanda).register(org.probelager, [org.wanda, org.paul, org.lena])

    def load_page() -> None:
        assert client.get(event_address(org.probelager)).status_code == 200

    assert_queries_do_not_grow(create_entry, load_page)
    assert len(listed(org.bea, org.probelager)) == 10


# ---------- Was bleibt unverändert? ----------


def test_u1_die_seite_der_veranstaltung_bleibt_und_bekommt_nur_den_abschnitt(org, sammelanmeldung):
    root = page_tree(org.bea, event_address(org.probelager))
    main = _one(_by_tag(root, "main"))

    assert _text(_one(_by_tag(main, "h1"))) == "Probelager 2027"
    assert "15.05.2027 bis 17.05.2027" in _visible_text(main)
    # Seit #379 ist die Seite die Leitungsseite: statt des Knopfs „Bearbeiten“ der Stift der Kachel „Grunddaten“,
    # und vor dem Abschnitt „Anmeldungen“ steht diese Kachel.
    edit = _all(main, lambda e: "a-stift" in _classes(e))
    assert [_attr(link, "href") for link in edit] == [f"{event_address(org.probelager)}bearbeiten/"]
    surfaces = [section for section in _by_tag(main, "section") if "a-flaeche" in _classes(section)]
    assert [_attr(section, "aria-labelledby") for section in surfaces] == ["h-grunddaten", SECTION]
    for user in (org.wanda, org.fiete, org.vera, org.max):
        assert client_for(user).get(event_address(org.probelager)).status_code == 404, user.username


def test_u3_meine_anmeldungen_gibt_es_nicht(org, sammelanmeldung):
    for user in (org.wanda, org.otto, org.bea):
        labels = nav_labels(page_tree(user, "/"))
        assert not [label for label in labels if "nmeldung" in label], (user.username, labels)
    assert client_for(org.wanda).get("/meine-anmeldungen/").status_code == 404
    profile = _visible_text(page_tree(org.wanda, "/profil/"))
    assert "Probelager" not in profile


# ---------- Befunde der unabhängigen Prüfung (PR #367) ----------


@pytest.mark.django_db(transaction=True)
def test_b1_wechselt_der_stamm_gleichzeitig_den_ring_meldet_kai_karl_nicht_an():
    """Befund B1: Wechselt Leuchtturm gleichzeitig von Küste nach Nord, wartet das Anmelden und prüft danach frisch."""
    o = build_people()
    mona = lead("mona.mosaik", "Mona", "Mosaik", R.ASSOCIATION_LEAD, o.mosaik)
    results = []

    def change_ring():
        done, _text = Rights(mona).change_ring(o.leuchtturm, o.nord.key)
        assert done

    def register():
        try:
            Rights(o.kai).register(o.probelager, [o.karl])
        except ValidationError:
            results.append("abgelehnt")

    _one_after_the_other(change_ring, register)

    assert results == ["abgelehnt"]
    assert not Registration.objects.exists()


def test_b2_die_kopie_kommt_aus_der_datenbank_nicht_aus_dem_objekt_im_speicher(org):
    """Befund B2: Ein ungespeichert verändertes Objekt ändert die Kopie nicht."""
    org.lena.first_name = "Gekapert"
    org.wanda.scout_name = "Gekapert"

    created = Rights(org.wanda).register(org.probelager, [org.wanda, org.lena])

    assert [row[:4] for row in copies(created)] == [("Wanda", "Walhall", None, ""),
                                                    ("Lena", "Probe", date(2015, 5, 14), "Kiwi")]


def test_b5_ein_gesperrtes_konto_meldet_niemanden_an_auch_sich_selbst_nicht(org):
    org.wanda.is_active = False
    org.wanda.save()

    refused(lambda: Registration.create(org.probelager, org.wanda, [org.wanda]))
    refused(lambda: Registration.create(org.probelager, org.wanda, [org.paul]))

    assert not Registration.objects.exists()
