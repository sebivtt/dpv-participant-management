"""Tests für den Fahrtennamen (#111, PER-01; EP-01, EP-03, EP-04) und den gemeinsamen Baustein für Textfelder.

Die Nummern verweisen auf Sebastians Szenarien vom 26.10.2026 in #111 („Szenarien (26.10.2026)“).
Was nur ein echter Browser zeigen kann (Tippen wie am Handy mit Autokorrektur, Szenario 12),
prüft der Rauchtest in rauchtests/test_rauchtest.py. Alle Namen sind erfunden; die Einheiten
stammen aus `build_org()` in tests/test_rollen.py.
"""

import re

import pytest
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import Client

from accounts.models import display_name
from roles.models import Role
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _sidebar, _tree, _visible_text
from tests.test_mein_profil import display_name as shown_name
from tests.test_mein_profil import avatar, main, raw_text, text
from tests.test_rechte_ohne_seite import manipulated_form
from tests.test_rollen import build_org, give, person
from tests.test_rundumtest import ALL, _example_address

pytestmark = pytest.mark.django_db

R = Role.Kind
User = get_user_model()

PROFILE = "/profil/"
SAVE = "/profil/fahrtenname/"
SAVED = "Dein Fahrtenname ist gespeichert."
DELETED = "Dein Fahrtenname ist gelöscht."
TOO_LONG = "Dein Fahrtenname darf höchstens 30 Zeichen lang sein."
FAILED = "Dein Fahrtenname konnte nicht gespeichert werden. Versuche es noch einmal."
NOT_GIVEN = "Noch nicht angegeben"
HINT_NAME = "Ergänze deinen Namen in deinem DPV-Konto und melde dich danach neu an."


@pytest.fixture
def org():
    """Die Einheiten aus tests/test_rollen.py; Erika ist Mitglied der Sippe Falken in Walhall."""
    o = build_org()
    give(o.erika, R.MEMBER, o.falken)
    o.lead = person("wanda.walhall", "Wanda", "Walhall")
    give(o.lead, R.TROOP_LEAD, o.walhall)
    return o


def client_for(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def save(who, value, client=None, htmx=False, **extra):
    """Schickt als `who` das Formular „Fahrtenname“ ab, wie es der Knopf „Speichern“ tut."""
    headers = {"HX-Request": "true"} if htmx else {}
    return (client or client_for(who)).post(SAVE, {"scout_name": value, **extra}, headers=headers)


def stored(user) -> str:
    return User.objects.get(pk=user.pk).scout_name


def set_stored(user, value: str) -> None:
    user.scout_name = value
    user.save(update_fields=["scout_name"])


def profile(user, client=None):
    response = (client or client_for(user)).get(PROFILE)
    assert response.status_code == 200, response.status_code
    return _tree(response)


def field(root):
    """Das Eingabefeld „Fahrtenname“ auf „Mein Profil“."""
    return _one(_all(main(root), lambda e: e.name == "input" and _attr(e, "name") == "scout_name"))


def label_of(root, element) -> str:
    return _visible_text(_one(_all(root, lambda e: e.name == "label" and _attr(e, "for") == _attr(element, "id"))))


def greeting(user) -> str:
    return _visible_text(_one(_by_tag(_tree(client_for(user).get("/")), "h1")))


def circles(root) -> list[tuple[str, str]]:
    """Profilkreise in Seitenleiste, Handy-Leiste und Handy-Menü als (Buchstabe, Name daneben)."""
    found = []
    for circle in _all(root, lambda e: e.name == "a" and "a-profil" in _classes(e)):
        letter = _one(_all(circle, lambda e: "a-avatar" in _classes(e)))
        found.append((raw_text(letter), re.sub(r"^Mein Profil: ", "", _visible_text(circle)).strip()))
    return found


def notices(root, kind: str) -> list[str]:
    return [re.sub(r"\s+", " ", _visible_text(n)) for n in _all(main(root), lambda e: kind in _classes(e))]


# Szenario 1: Erika trägt „Kiwi“ ein


@pytest.mark.rechtematrix("EP-03", "EP-01")
def test_erika_traegt_kiwi_ein_und_wird_ueberall_so_genannt(org):
    client = client_for(org.erika)

    response = save(org.erika, "Kiwi", client=client)

    assert response.status_code == 302
    assert response["Location"] == PROFILE
    assert stored(org.erika) == "Kiwi"
    root = profile(org.erika, client=client)
    assert notices(root, "ist-erfolg") == [SAVED]
    assert shown_name(root) == "Kiwi (Erika Testfrau)"
    assert raw_text(avatar(root)) == "K"
    assert _attr(field(root), "value") == "Kiwi"
    assert set(circles(root)) == {("K", "Kiwi"), ("K", "")}
    assert greeting(org.erika) == "Hallo Kiwi!"


def test_erfolgsmeldung_erscheint_nur_einmal(org):
    client = client_for(org.erika)
    save(org.erika, "Kiwi", client=client)
    profile(org.erika, client=client)

    assert notices(profile(org.erika, client=client), "ist-erfolg") == []


def test_erfolgsmeldung_wird_vorgelesen_sobald_das_vorleseprogramm_frei_ist(org):
    """Meldung nach einer Handlung (#165): Erfolg als role="status"."""
    client = client_for(org.erika)
    save(org.erika, "Kiwi", client=client)

    notice = _one(_all(main(profile(org.erika, client=client)), lambda e: "ist-erfolg" in _classes(e)))

    assert _attr(notice, "role") == "status"


# Szenario 2: Erika ändert „Kiwi“ in „Kolibri“


def test_erika_aendert_kiwi_in_kolibri(org):
    set_stored(org.erika, "Kiwi")
    client = client_for(org.erika)

    save(org.erika, "Kolibri", client=client)

    root = profile(org.erika, client=client)
    assert stored(org.erika) == "Kolibri"
    assert notices(root, "ist-erfolg") == [SAVED]
    assert shown_name(root) == "Kolibri (Erika Testfrau)"
    assert set(circles(root)) == {("K", "Kolibri"), ("K", "")}
    assert greeting(org.erika) == "Hallo Kolibri!"
    assert "Kiwi" not in client.get(PROFILE).content.decode()


# Szenario 3: Erika löscht ihren Fahrtennamen


@pytest.mark.rechtematrix("EP-03")
def test_erika_leert_das_feld_und_der_fahrtenname_ist_geloescht(org):
    set_stored(org.erika, "Kiwi")
    client = client_for(org.erika)

    save(org.erika, "", client=client)

    root = profile(org.erika, client=client)
    assert stored(org.erika) == ""
    assert notices(root, "ist-erfolg") == [DELETED]
    assert shown_name(root) == "Erika Testfrau"
    assert set(circles(root)) == {("E", "Erika"), ("E", "")}
    assert greeting(org.erika) == "Hallo Erika!"


# Szenario 4: Max hat keinen Fahrtennamen


def test_ohne_fahrtennamen_steht_noch_nicht_angegeben(org):
    """Seit #180 steht „Noch nicht angegeben“ im Feld in Ruhe; die leere Eingabe zeigt „Fahrtennamen eingeben“."""
    root = profile(org.max)

    assert _attr(field(root), "value") in (None, "")
    assert _attr(field(root), "placeholder") == "Fahrtennamen eingeben"
    rest = _one(_all(main(root), lambda e: _attr(e, "data-oeffnen") is not None))
    assert _visible_text(rest) == NOT_GIVEN
    assert label_of(root, field(root)) == "Fahrtenname"
    assert shown_name(root) == "Max Testmann"
    assert greeting(org.max) == "Hallo Max!"


# Szenarien 5 und 6: Niemand sonst ändert Erikas Fahrtennamen (EP-04)


def foreign_fields(target) -> dict:
    """Alles, womit ein manipuliertes Formular auf ein fremdes Konto zeigen könnte."""
    return {
        "user": target.pk, "user_id": target.pk, "person": target.pk, "id": target.pk, "pk": target.pk,
        "key": target.key, "person_key": target.key, "username": target.username, "email": target.email,
    }


@pytest.mark.rechtematrix("EP-04", "EP-03")
@pytest.mark.parametrize("htmx", [False, True])
def test_stammesleitung_aendert_mit_erikas_kennung_nur_den_eigenen_fahrtennamen(org, htmx):
    set_stored(org.erika, "Kiwi")

    save(org.lead, "Gekapert", htmx=htmx, **foreign_fields(org.erika))

    assert stored(org.erika) == "Kiwi"
    assert stored(org.lead) == "Gekapert"


@pytest.mark.rechtematrix("EP-04")
def test_direkte_adresse_mit_erikas_kennung_gibt_es_nicht(org):
    set_stored(org.erika, "Kiwi")
    client = client_for(org.lead)

    for address in (f"{SAVE}{org.erika.key}/", f"{SAVE}{org.erika.pk}/", f"/profil/{org.erika.key}/fahrtenname/"):
        for htmx in (False, True):
            headers = {"HX-Request": "true"} if htmx else {}
            response = client.post(address, {"scout_name": "Gekapert"}, headers=headers)
            assert response.status_code == 404, address
        response = client.post(f"{SAVE}?person={org.erika.key}&user={org.erika.pk}", {"scout_name": "Gekapert"})
        assert response.status_code == 302

    assert stored(org.erika) == "Kiwi"


@pytest.mark.rechtematrix("EP-04")
def test_admin_aendert_erikas_fahrtennamen_nicht(org):
    """Szenario 6: Den Support-Zugang gibt es noch nicht (#92); auch als Admin ändert sich nur das eigene Konto."""
    admin = person("ada.admin", "Ada", "Admin")
    give(admin, R.ADMIN)
    set_stored(org.erika, "Kiwi")

    for htmx in (False, True):
        save(admin, "Gekapert", htmx=htmx, **foreign_fields(org.erika))

    assert stored(org.erika) == "Kiwi"
    assert stored(admin) == "Gekapert"


@pytest.mark.rechtematrix("EP-04")
def test_keine_adresse_aendert_den_fahrtennamen_einer_anderen_person(org):
    """Jede Adresse, als Mitglied, Leitung, Verbandsleitung, Admin, ohne Zuordnung und mit vielen Rollen."""
    give(org.max, R.ASSOCIATION_LEAD, org.boreas)
    give(org.max, R.FEDERATION_LEAD, org.dpv)
    give(org.max, R.ADMIN)
    federation_lead = person("vera.verband", "Vera", "Verband")
    give(federation_lead, R.FEDERATION_LEAD, org.dpv)
    admin = person("ada.admin", "Ada", "Admin")
    give(admin, R.ADMIN)
    without = person("otto.ohne", "Otto", "Ohne")
    set_stored(org.erika, "Kiwi")
    form = {**manipulated_form(org), **foreign_fields(org.erika), "scout_name": "Gekapert"}

    for pattern, _entry in ALL:
        address = _example_address(pattern)
        for user in (org.max, org.lead, federation_lead, admin, without):
            for method, htmx in (("get", False), ("post", False), ("post", True)):
                headers = {"HX-Request": "true"} if htmx else {}
                getattr(client_for(user), method)(address, form, headers=headers)

    assert stored(org.erika) == "Kiwi"


@pytest.mark.rechtematrix("EP-03", "EP-04")
def test_gegenprobe_die_stammesleitung_aendert_ihren_eigenen_fahrtennamen(org):
    client = client_for(org.lead)

    save(org.lead, "Wiesel", client=client)

    assert stored(org.lead) == "Wiesel"
    assert shown_name(profile(org.lead, client=client)) == "Wiesel (Wanda Walhall)"


# Szenario 7: ohne Login


def test_ohne_login_geht_es_zur_anmeldung_und_nichts_wird_gespeichert(org):
    for htmx in (False, True):
        headers = {"HX-Request": "true"} if htmx else {}
        response = Client().post(SAVE, {"scout_name": "Kiwi", **foreign_fields(org.erika)}, headers=headers)
        assert response.status_code == 302
        assert response["Location"].startswith("/anmelden/")

    assert User.objects.exclude(scout_name="").count() == 0


def test_aufruf_ohne_formular_fuehrt_zu_mein_profil_und_aendert_nichts(org):
    """Unabhängige Prüfung: Wer beim Speichern abgemeldet war, kommt nach dem Login hierher, nicht auf eine leere Seite."""
    set_stored(org.erika, "Kiwi")

    response = client_for(org.erika).get(SAVE, {"scout_name": "Kolibri"})

    assert response.status_code == 302
    assert response["Location"] == PROFILE
    assert stored(org.erika) == "Kiwi"


def test_formular_ohne_das_feld_loescht_nichts(org):
    """Unabhängige Prüfung: Ein Formular ohne das Feld ist kein leeres Feld."""
    set_stored(org.erika, "Kiwi")
    client = client_for(org.erika)

    response = client.post(SAVE, {"first_name": "Gekapert"})

    assert response.status_code == 302
    assert response["Location"] == PROFILE
    assert stored(org.erika) == "Kiwi"
    assert notices(profile(org.erika, client=client), "ist-erfolg") == []


# Szenarien 8 und 9: Leerzeichen


@pytest.mark.parametrize("value", ["  Kiwi ", " Kiwi​", "\tKiwi\n"])
def test_leerzeichen_am_rand_werden_entfernt(org, value):
    save(org.erika, value)

    assert stored(org.erika) == "Kiwi"


def test_leerzeichen_innen_bleiben(org):
    save(org.erika, " Kleiner  Bär ")

    assert stored(org.erika) == "Kleiner  Bär"


@pytest.mark.parametrize("value", ["   ", " ​ "])
def test_nur_leerzeichen_gilt_als_kein_fahrtenname(org, value):
    set_stored(org.erika, "Kiwi")
    client = client_for(org.erika)

    save(org.erika, value, client=client)

    root = profile(org.erika, client=client)
    assert stored(org.erika) == ""
    assert notices(root, "ist-erfolg") == [DELETED]
    assert greeting(org.erika) == "Hallo Erika!"


# Szenario 10: höchstens 30 Zeichen (bis #214: 50; die Szenarien dazu in tests/test_fahrtenname_grenze.py)


def test_dreissig_zeichen_werden_gespeichert(org):
    value = "K" * 30

    save(org.erika, f" {value} ")

    assert stored(org.erika) == value


@pytest.mark.parametrize("value", ["K" * 31, "Ä" * 31])
def test_einunddreissig_zeichen_fehler_am_feld_und_die_eingabe_bleibt(org, value):
    set_stored(org.erika, "Kiwi")

    response = save(org.erika, value)

    assert response.status_code == 200
    root = _tree(response)
    assert stored(org.erika) == "Kiwi"
    input_ = field(root)
    assert _attr(input_, "value") == value
    assert _attr(input_, "aria-invalid") == "true"
    error = _one(_by_tag(root, "div", id=_attr(input_, "aria-describedby").split()[0]))
    assert _visible_text(error) == TOO_LONG
    assert "invalid-feedback" in _classes(error)
    # Der Fehler steht am Feld, nicht als Meldung oben auf der Seite.
    assert notices(root, "a-meldung") == notices(profile(org.erika), "a-meldung")
    assert shown_name(root) == "Kiwi (Erika Testfrau)"
    # Auch unter der Adresse zum Speichern ist der Profilkreis als aktuelle Seite gekennzeichnet (#13).
    marked = _all(root, lambda e: e.name == "a" and "a-profil" in _classes(e))
    assert marked and all(_attr(circle, "aria-current") == "page" for circle in marked)


def test_das_feld_begrenzt_die_eingabe_nicht_selbst(org):
    """Sonst schnitte der Browser beim Einfügen still ab, statt den Fehler am Feld zu zeigen (Szenario 10)."""
    assert _attr(field(profile(org.erika)), "maxlength") is None


# Szenario 11: Sonderzeichen und HTML


@pytest.mark.parametrize("value", ["Bär", "Fuchs-Ölmühle", "Ich & du", "O'Neill"])
def test_umlaute_und_zeichen_werden_gespeichert_wie_sie_sind(org, value):
    save(org.erika, value)

    assert stored(org.erika) == value
    assert shown_name(profile(org.erika)) == f"{value} (Erika Testfrau)"


def test_html_im_fahrtennamen_erscheint_als_gewoehnlicher_text(org):
    client = client_for(org.erika)
    save(org.erika, "<b>Kiwi</b>", client=client)

    for address in ("/", PROFILE, "/bausteine/"):
        content = client.get(address).content.decode()
        assert "<b>Kiwi</b>" not in content, address
        root = _tree(client.get(address))
        assert not _by_tag(main(root), "b") and not _by_tag(_sidebar(root), "b"), address
    assert stored(org.erika) == "<b>Kiwi</b>"
    assert greeting(org.erika) == "Hallo <b>Kiwi</b>!"


# Szenario 13: zwei Tabs nacheinander


def test_zwei_tabs_es_gilt_der_zuletzt_gespeicherte(org):
    first, second = client_for(org.erika), client_for(org.erika)
    first.get(PROFILE)
    second.get(PROFILE)

    save(org.erika, "Kiwi", client=first)
    save(org.erika, "Kolibri", client=second)

    assert stored(org.erika) == "Kolibri"
    assert shown_name(profile(org.erika, client=first)) == "Kolibri (Erika Testfrau)"


def test_speichern_aendert_nur_den_fahrtennamen(org):
    """Ein Tab mit altem Stand überschreibt nicht, was seit dem Öffnen beim Login neu kam (Szenario 13)."""
    client = client_for(org.erika)
    User.objects.filter(pk=org.erika.pk).update(last_name="Neuname", email="erika.neu@example.org")

    save(org.erika, "Kiwi", client=client, first_name="Gekapert", last_name="Gekapert", email="g@example.org")

    erika = User.objects.get(pk=org.erika.pk)
    assert (erika.scout_name, erika.first_name, erika.last_name, erika.email) == (
        "Kiwi", "Erika", "Neuname", "erika.neu@example.org"
    )


# Szenario 14: Speichern scheitert technisch


def test_speichern_scheitert_fehlermeldung_und_zeile_im_log_ohne_fahrtennamen(org, monkeypatch, log_output):
    client = client_for(org.erika)  # Der Login speichert selbst; erst danach fällt die Datenbank aus.

    def fail(self, *args, **kwargs):
        raise DatabaseError("Datenbank weg, Wert: Geheimkiwi")

    monkeypatch.setattr(User, "save", fail)

    response = save(org.erika, "Geheimkiwi", client=client)

    root = _tree(response)
    assert notices(root, "ist-fehler") == [FAILED]
    assert _attr(_one(_all(main(root), lambda e: "ist-fehler" in _classes(e))), "role") == "alert"
    assert _attr(field(root), "value") == "Geheimkiwi"
    assert shown_name(root) == "Erika Testfrau"
    assert stored(org.erika) == ""
    log = log_output()
    assert "Fahrtenname" in log
    assert "Geheimkiwi" not in log


def test_beim_normalen_speichern_steht_der_fahrtenname_nicht_im_log(org, log_output):
    save(org.erika, "Geheimkiwi")
    save(org.erika, "G" * 51 + "Geheimkiwi")
    profile(org.erika)

    assert "Geheimkiwi" not in log_output()


# Szenario 15: Konto ohne Vor- und Nachname


def test_konto_ohne_namen_mit_fahrtennamen(org):
    nameless = person("ohne.name", "", "")
    client = client_for(nameless)

    save(nameless, "Kiwi", client=client)

    root = profile(nameless, client=client)
    assert greeting(nameless) == "Hallo Kiwi!"
    assert circles(root)[0] == ("K", "Kiwi")
    assert HINT_NAME in text(root)
    assert HINT_NAME in re.sub(r"\s+", " ", _visible_text(_tree(client.get("/"))))
    assert shown_name(root) == "Kiwi"


# Die gemeinsame Stelle für „Kiwi (Erika Testfrau)“ (Nachklärung vom 26.10.2026)


@pytest.mark.parametrize(
    ("first", "last", "scout", "expected"),
    [
        ("Erika", "Testfrau", "Kiwi", "Kiwi (Erika Testfrau)"),
        ("Erika", "Testfrau", "", "Erika Testfrau"),
        ("Erika", "", "Kiwi", "Kiwi (Erika)"),
        ("", "Testfrau", "Kiwi", "Kiwi (Testfrau)"),
        ("", "", "Kiwi", "Kiwi"),
        ("", "", "", ""),
    ],
)
def test_gemeinsame_stelle_fuer_den_vollen_namen(first, last, scout, expected):
    assert display_name(first, last, scout) == expected


def test_leitungen_liefern_den_fahrtennamen_mit(org):
    """BER-01, Grund 3: Wer eine Leitung sieht, sieht Name, Fahrtenname und Rolle (RO-01 bis RO-03)."""
    from access.rights import Rights

    set_stored(org.lead, "Wiesel")

    entries = list(Rights(org.erika).leads())

    assert [(e["first_name"], e["last_name"], e["scout_name"]) for e in entries] == [("Wanda", "Walhall", "Wiesel")]
    assert "email" not in entries[0]


# Der gemeinsame Baustein für Textfelder (technischer Hinweis vom 25.10.2026) und Szenario 16


def test_fahrtenname_ist_das_einzige_feld_zum_bearbeiten(org):
    """W1 mit der Ergänzung zu #111: genau ein Feld, nichts für Name und Mail.

    Seit #180 gehören zum Feld der Knopf zum Öffnen, der Knopf zum Leeren und „Verwerfen“;
    abgeschickt wird weiter nur mit „Speichern“.
    """
    content = main(profile(org.erika))

    form = _one(_by_tag(content, "form"))
    assert _attr(form, "method") == "post"
    assert _attr(form, "action") == SAVE
    inputs = [e for e in _all(content, lambda e: e.name in ("input", "textarea", "select"))]
    assert [(_attr(e, "name"), _attr(e, "type")) for e in inputs] == [
        ("csrfmiddlewaretoken", "hidden"), ("scout_name", "text"),
    ]
    buttons = _by_tag(content, "button")
    assert [(_visible_text(b), _attr(b, "type")) for b in buttons] == [
        (NOT_GIVEN, "button"), ("", "button"), ("Verwerfen", "button"), ("Speichern", "submit"),
    ]


def test_feld_mit_beschriftung_ohne_pflicht_und_passender_tastatur(org):
    root = profile(org.erika)
    input_ = field(root)

    assert label_of(root, input_) == "Fahrtenname"
    assert "(Pflicht)" not in label_of(root, input_)
    assert _attr(input_, "required") is None
    assert "form-control" in _classes(input_)
    # Ein Name: Großbuchstabe am Wortanfang, keine Korrektur, die ihn in ein Wort verwandelt.
    assert _attr(input_, "autocapitalize") == "words"
    assert _attr(input_, "autocorrect") == "off"
    assert _attr(input_, "spellcheck") == "false"
    assert _attr(input_, "autocomplete") == "nickname"
    assert _attr(input_, "aria-invalid") is None
    # Verknüpft ist nur die Zahl der Zeichen (#215), kein Fehler.
    assert _attr(input_, "aria-describedby") == "id_scout_name-zahl"


def test_katalog_zeigt_den_baustein_textfeld(org):
    """Szenario 16: Beschriftung, Pflicht-Hinweis und Fehler am Feld, gebaut mit demselben Baustein (seit #176 im Katalog)."""
    root = _tree(client_for(org.erika).get("/bausteine/"))
    section = _one(_by_tag(root, "section", aria_labelledby="h-textfeld"))

    fields = _all(section, lambda e: "a-textfeld" in _classes(e))
    assert len(fields) >= 2
    required = _one(_all(section, lambda e: e.name == "input" and _attr(e, "required") is not None))
    assert label_of(section, required) == "Name der Veranstaltung (Pflicht)"
    error = _one(_by_tag(section, "div", id=_attr(required, "aria-describedby")))
    assert _visible_text(error) == "Gib einen Namen für die Veranstaltung ein."
    assert _attr(required, "aria-invalid") == "true"
    optional = [e for box in fields for e in _by_tag(box, "input") if _attr(e, "required") is None]
    assert optional, "Beispiel ohne Pflicht fehlt"
