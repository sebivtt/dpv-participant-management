"""Tests für das Anlegen einer Veranstaltung in Schritten mit Zusammenfassung und „Entwurf löschen“ (#380, Teil B von #29).

Die Kennungen B1 bis B7, BV1 bis BV4 und BG1 bis BG5 verweisen auf die Szenarien vom 17.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/380#issuecomment-6944638412), die Wortlaute auf den
Text von #380. BG6 (Handy, nur Tastatur) und das Schließen des Dialogs mit Esc (B6) prüft der Rauchtest
`rauchtests/test_veranstaltung_anlegen.py`. „Heute“ ist in allen Szenarien der 05.01.2028; die Tests stellen den Tag
des Servers darauf. Personen wie in den Szenarien: Wanda (Stammesleitung Walhall), Fiete (Gruppenleitung Falken),
Finn (Mitglied Sippe Falken), Vera (Verbandsleitung), Max (nur Admin), Otto (Konto ohne Zuordnung). Alle Namen sind
erfunden; „Burg Ludwigstein“ ist als Bezeichnung eines Orts aus dem Zielbild übernommen (#356).

Die Felder und Prüfungen von Schritt 1 sind die aus #379 (`tests/test_grunddaten.py`); hier steht nur, was der
Ablauf dazu bringt. Seit #358 liegt zwischen Schritt 1 und der Zusammenfassung Schritt 2 „Einladungstext“
(`tests/test_einladungstext.py`): „Weiter“ in Schritt 1 führt dorthin, „Zurück“ in der Zusammenfassung ebenso, und
die Zusammenfassung ist Schritt 3. Nur diese Erwartungen sind hier nachgezogen.
"""

from datetime import date

import pytest
from django.utils import timezone

from access.rights import Rights
from events.models import Event
from roles.models import Role
from tests.test_benennen import _one_after_the_other, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_rechtepruefung import remove
from tests.test_veranstaltungen import (
    CREATE,
    LIST,
    SCRIPT,
    assert_no_access,
    build_people,
    create_button,
    event_address,
    field_errors,
    field_values,
    leads_of,
)

R = Role.Kind
pytestmark = pytest.mark.django_db

TODAY = date(2028, 1, 5)
PFINGSTLAGER = {"name": "Pfingstlager 2028", "start": "2028-06-02", "start_time": "18:00", "end": "2028-06-05",
                "end_time": "12:00", "location": "Burg Ludwigstein"}
SOMMERFAHRT = {**PFINGSTLAGER, "name": "Sommerfahrt 2028", "start": "2028-07-20", "end": "2028-07-30",
               "location": ""}
SAVED = "%s ist als Entwurf gespeichert. Nur die Leitung sieht die Veranstaltung."
DELETED = "Der Entwurf %s ist gelöscht."
QUESTION = "Anlegen abbrechen?"
QUESTION_TEXT = ("Sommerfahrt 2028 ist als Entwurf gespeichert. Du kannst ihn speichern und später auf der "
                 "Leitungsseite weitermachen oder ihn löschen.")
PAST = "Der Beginn liegt in der Vergangenheit."


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    """Der Tag des Servers ist der 05.01.2028, wie in den Szenarien."""
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: TODAY)


@pytest.fixture
def org():
    return build_people()


@pytest.fixture
def entwurf(org):
    """Wandas „Pfingstlager 2028“ nach „Weiter“ in Schritt 1: ein Entwurf, das Anlegen läuft noch."""
    response = weiter(org.wanda)
    assert response.status_code == 302, response.status_code
    return Event.objects.get(name="Pfingstlager 2028")


@pytest.fixture
def sommerfahrt(org):
    """Wandas „Sommerfahrt 2028“ nach „Weiter“ in Schritt 1 (B3, B4)."""
    response = weiter(org.wanda, **SOMMERFAHRT)
    assert response.status_code == 302, response.status_code
    return Event.objects.get(name="Sommerfahrt 2028")


# ---------- Adressen und Hilfen ----------


def basics_address(entry) -> str:
    """Schritt 1 „Grunddaten“ eines gespeicherten Entwurfs, Ziel von „Zurück“ und dem Stift."""
    return f"{event_address(entry)}anlegen/"


def invitation_step_address(entry) -> str:
    """Schritt 2 „Einladungstext“ (#358), wohin „Weiter“ in Schritt 1 führt."""
    return f"{event_address(entry)}anlegen/einladungstext/"


def summary_address(entry) -> str:
    return f"{event_address(entry)}anlegen/zusammenfassung/"


def cancel_address(entry) -> str:
    """Der Dialog „Anlegen abbrechen?“; ein Formular hierher ist „Entwurf speichern“."""
    return f"{event_address(entry)}anlegen/abbrechen/"


def delete_address(entry) -> str:
    return f"{event_address(entry)}anlegen/loeschen/"


def flow_addresses(entry) -> list[str]:
    return [basics_address(entry), invitation_step_address(entry), summary_address(entry), cancel_address(entry),
            delete_address(entry)]


def step_form(root):
    """Das Formular eines Schritts mit seinen Feldern und Knöpfen."""
    return _one(_by_tag(root, "form", id="f-schritt"))


def progress(root) -> list[tuple[str, bool]]:
    """Die Fortschrittsanzeige: je Schritt der sichtbare Text und ob er der aktuelle ist."""
    found = _one(_all(root, lambda e: e.name == "ol" and "a-schritte" in _classes(e)))
    return [(_visible_text(step), _attr(step, "aria-current") == "step") for step in _by_tag(found, "li")]


def buttons(root) -> dict[str, str]:
    """Die Knöpfe unter einem Schritt: Beschriftung und Ziel; ein Knopf, der das Formular abschickt, hat „senden“."""
    bar = _one(_all(root, lambda e: "a-schritt-knoepfe" in _classes(e)))
    found = {}
    for element in _all(bar, lambda e: e.name in ("a", "button")):
        found[_visible_text(element)] = _attr(element, "href") if element.name == "a" else "senden"
    return found


def head(root) -> tuple[str, str]:
    """Der Kopf der Seite: Überschrift und, falls da, die Zeile darunter."""
    found = _one(_all(root, lambda e: "a-kopf" in _classes(e)))
    lines = _by_tag(found, "p")
    return _text(_one(_by_tag(found, "h1"))), _visible_text(_one(lines)) if lines else ""


def basics_tile(root):
    """Der Abschnitt „Grunddaten“ der Zusammenfassung."""
    return _one(_by_tag(root, "section", aria_labelledby="h-grunddaten"))


def place(root) -> str | None:
    found = _all(basics_tile(root), lambda e: "a-kalender-ort" in _classes(e))
    return _visible_text(_one(found)) if found else None


def open_dialog(root):
    return _one(_by_tag(root, "dialog", aria_labelledby="h-dialog"))


def dialog_buttons(dialog) -> dict[str, tuple[str, str]]:
    """Die Knöpfe unten im Dialog: Beschriftung, Ziel (Formular oder Link) und Farbe (Klasse des Knopfs)."""
    footer = _one(_all(dialog, lambda e: "a-dialog-fuss" in _classes(e)))
    found = {}
    for form in _by_tag(footer, "form"):
        button = _one(_by_tag(form, "button"))
        colour = "rot" if "btn-gefahr" in _classes(button) else "blau" if "btn-primary" in _classes(button) else "?"
        found[_visible_text(button)] = (_attr(form, "action"), colour)
    for link in _by_tag(footer, "a"):
        found[_visible_text(link)] = (_attr(link, "href"), "Link")
    return found


def open_step_one(user, client=None):
    """Öffnet „Veranstaltung erstellen“ (Schritt 1); gibt die Seite und die Kennung des Formulars zurück."""
    response = (client or client_for(user)).get(CREATE)
    assert response.status_code == 200, response.status_code
    root = _tree(response)
    return root, _attr(_one(_by_tag(step_form(root), "input", name="creation_key")), "value")


def weiter(user, client=None, **values):
    """Füllt Schritt 1 aus wie in B1 und klickt auf „Weiter“."""
    client = client or client_for(user)
    _root, creation_key = open_step_one(user, client=client)
    return client.post(CREATE, {**PFINGSTLAGER, **values, "creation_key": creation_key})


def shown(user, entry, client=None) -> dict[str, str]:
    """Die Angaben, wie Schritt 1 eines Entwurfs sie zeigt, mit allen Feldern, auch versteckten (Stand)."""
    root = _tree((client or client_for(user)).get(basics_address(entry)))
    return {_attr(field, "name"): _attr(field, "value") or "" for field in _by_tag(step_form(root), "input")
            if _attr(field, "name") != "csrfmiddlewaretoken"}


def rows(user) -> list[str]:
    """Die Namen unter „Von mir geleitet“."""
    section = _one(_by_tag(page_tree(user, LIST), "section", aria_labelledby="h-veranstaltungen"))
    return [_visible_text(_one(_by_tag(row, "a"))) for row in _all(section, lambda e: "a-va-zeile" in _classes(e))]


def second_lead(entry, user) -> None:
    """Eine Mitleitung, wie sie #357 bringt; bis dahin nur im Datenmodell."""
    entry.leads.add(user)


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VA-01")
def test_b1_wanda_legt_das_pfingstlager_in_schritten_an(org):
    client = client_for(org.wanda)
    assert create_button(org.wanda) == CREATE

    root, _key = open_step_one(org.wanda, client=client)
    assert head(root) == ("Veranstaltung erstellen", "")
    assert progress(root) == [("Schritt 1 Grunddaten", True), ("Schritt 2 Einladungstext", False),
                              ("Schritt 3 Zusammenfassung", False)]
    labels = [_visible_text(label) for label in _by_tag(step_form(root), "label") if "sr-nur" not in _classes(label)]
    # Seit #163 folgt unter dem Ort das Adressfeld (tests/test_adressfeld.py); seit der Vorschau dort heißt der Ort
    # „Bezeichnung“ und steht mit der Adresse in einer eigenen Fläche „Ort“.
    assert labels == ["Name (Pflicht)", "Beginn (Pflicht, Uhrzeit freiwillig)", "Ende (Pflicht, Uhrzeit freiwillig)",
                      "Bezeichnung", "Straße und Hausnummer", "PLZ", "Ort", "Bundesland", "Land"]
    # In Schritt 1 gibt es kein „Zurück“; „Abbrechen“ führt ohne Rückfrage zur Liste (B5).
    assert buttons(root) == {"Abbrechen": LIST, "Weiter": "senden"}
    assert not _by_tag(root, "dialog", aria_labelledby="h-dialog")

    response = weiter(org.wanda, client=client)

    created = Event.objects.get()
    assert (created.name, created.location) == ("Pfingstlager 2028", "Burg Ludwigstein")
    assert leads_of(created) == {"wanda.walhall"}
    assert response.status_code == 302
    assert response.url == invitation_step_address(created)
    assert rows(org.wanda) == ["Pfingstlager 2028"]

    page = client.get(summary_address(created))
    assert short_notices(page) == []
    root = _tree(page)
    assert head(root) == ("Pfingstlager 2028", "Entwurf · Veranstaltung erstellen")
    assert progress(root) == [("Schritt 1 Grunddaten", False), ("Schritt 2 Einladungstext", False),
                              ("Schritt 3 Zusammenfassung", True)]
    tile = basics_tile(root)
    assert _visible_text(_one(_by_tag(tile, "h2"))) == "Grunddaten"
    pencil = _one(_all(tile, lambda e: "a-stift" in _classes(e)))
    assert _attr(pencil, "href") == basics_address(created)
    # Vorleseprogramme hören „Grunddaten ändern“ statt des Symbols (Baustein „Bearbeiten-Symbol“, Zielbild 5).
    assert _text(_one(_all(pencil, lambda e: "sr-nur" in _classes(e)))) == "Grunddaten ändern"
    sheets = [_visible_text(sheet) for sheet in _all(tile, lambda e: "a-kalenderblatt" in _classes(e))]
    assert sheets == ["Fr 02 Jun 2028 18:00", "Mo 05 Jun 2028 12:00"]
    assert place(root) == "Burg Ludwigstein"
    assert buttons(root) == {"Abbrechen": cancel_address(created), "Zurück": invitation_step_address(created),
                             "Veranstaltung speichern": "senden"}

    response = client.post(summary_address(created))

    assert response.status_code == 302
    assert response.url == event_address(created)
    page = client.get(response.url)
    assert short_notices(page) == [SAVED % "Pfingstlager 2028"]
    assert _text(_one(_by_tag(_tree(page), "h1"))) == "Pfingstlager 2028"
    assert Event.objects.count() == 1


@pytest.mark.rechtematrix("VA-02")
def test_b2_zurueck_und_der_stift_fuehren_zu_schritt_1_mit_allen_eingaben(org, entwurf):
    client = client_for(org.wanda)
    root = _tree(client.get(summary_address(entwurf)))
    # Seit #358 führt „Zurück“ zu Schritt 2 „Einladungstext“ und von dort zu Schritt 1.
    assert buttons(root)["Zurück"] == invitation_step_address(entwurf)
    assert buttons(_tree(client.get(invitation_step_address(entwurf))))["Zurück"] == basics_address(entwurf)
    assert _attr(_one(_all(basics_tile(root), lambda e: "a-stift" in _classes(e))), "href") == basics_address(entwurf)

    root = _tree(client.get(basics_address(entwurf)))

    assert head(root) == ("Pfingstlager 2028", "Entwurf · Veranstaltung erstellen")
    assert progress(root) == [("Schritt 1 Grunddaten", True), ("Schritt 2 Einladungstext", False),
                              ("Schritt 3 Zusammenfassung", False)]
    assert field_values(step_form(root)) == {key: value for key, value in PFINGSTLAGER.items()}
    assert buttons(root) == {"Abbrechen": LIST, "Weiter": "senden"}

    response = client.post(basics_address(entwurf), {**shown(org.wanda, entwurf, client), "location": "Zeltplatz Moor"})

    assert response.status_code == 302
    assert response.url == invitation_step_address(entwurf)
    assert place(_tree(client.get(summary_address(entwurf)))) == "Zeltplatz Moor"
    assert Event.objects.count() == 1
    entwurf.refresh_from_db()
    assert entwurf.location == "Zeltplatz Moor"


@pytest.mark.rechtematrix("VA-06")
def test_b3_wanda_bricht_die_sommerfahrt_ab_und_loescht_den_entwurf(org, sommerfahrt):
    client = client_for(org.wanda)
    assert buttons(_tree(client.get(summary_address(sommerfahrt))))["Abbrechen"] == cancel_address(sommerfahrt)

    root = _tree(client.get(cancel_address(sommerfahrt)))

    dialog = open_dialog(root)
    assert _text(_one(_by_tag(dialog, "h2"))) == QUESTION
    assert QUESTION_TEXT in _visible_text(dialog)
    # Statt „Abbrechen“ die beiden Knöpfe: „Entwurf löschen“ rot, „Entwurf speichern“ dunkelblau (#380, Zielbild 5b).
    assert dialog_buttons(dialog) == {"Entwurf löschen": (delete_address(sommerfahrt), "rot"),
                                      "Entwurf speichern": (cancel_address(sommerfahrt), "blau")}

    response = client.post(delete_address(sommerfahrt))

    assert response.status_code == 302
    assert response.url == LIST
    page = client.get(response.url)
    assert short_notices(page) == [DELETED % "Sommerfahrt 2028"]
    assert not Event.objects.filter(name="Sommerfahrt 2028").exists()
    assert rows(org.wanda) == []


@pytest.mark.rechtematrix("VA-02")
def test_b4_wanda_bricht_ab_und_speichert_den_entwurf(org, sommerfahrt):
    client = client_for(org.wanda)

    response = client.post(cancel_address(sommerfahrt))

    assert response.status_code == 302
    assert response.url == LIST
    assert short_notices(client.get(response.url)) == [SAVED % "Sommerfahrt 2028"]
    assert rows(org.wanda) == ["Sommerfahrt 2028"]
    # Das Anlegen ist beendet: Der Ablauf führt zur Leitungsseite (BV2).
    assert client.get(summary_address(sommerfahrt)).url == event_address(sommerfahrt)


@pytest.mark.rechtematrix("VA-01")
def test_b5_abbrechen_in_schritt_1_fuehrt_ohne_rueckfrage_und_ohne_meldung_zur_liste(org):
    client = client_for(org.wanda)
    root, _key = open_step_one(org.wanda, client=client)

    assert buttons(root)["Abbrechen"] == LIST
    assert short_notices(client.get(LIST)) == []
    assert not Event.objects.exists()


@pytest.mark.rechtematrix("VA-06")
def test_b6_kreuz_schliesst_den_dialog_ohne_aenderung(org, sommerfahrt):
    client = client_for(org.wanda)
    dialog = open_dialog(_tree(client.get(cancel_address(sommerfahrt))))
    close = _one(_all(dialog, lambda e: "a-schliessen" in _classes(e)))

    assert _attr(close, "href") == summary_address(sommerfahrt)
    assert _attr(dialog, "data-schliessen") == summary_address(sommerfahrt)
    root = _tree(client.get(summary_address(sommerfahrt)))
    assert not _by_tag(root, "dialog", aria_labelledby="h-dialog")
    assert progress(root)[2] == ("Schritt 3 Zusammenfassung", True)
    # Nichts hat sich geändert: Das Anlegen läuft, und „Entwurf löschen“ geht weiter.
    assert "Entwurf löschen" in dialog_buttons(open_dialog(_tree(client.get(cancel_address(sommerfahrt)))))


@pytest.mark.rechtematrix("VA-06")
def test_b7_nach_dem_schliessen_des_browsers_weiter_ueber_liste_oder_verlauf(org, entwurf):
    client = client_for(org.wanda)
    section = _one(_by_tag(page_tree(org.wanda, LIST), "section", aria_labelledby="h-veranstaltungen"))
    link = _one([a for a in _by_tag(section, "a") if _visible_text(a) == "Pfingstlager 2028"])
    assert _attr(link, "href") == event_address(entwurf)

    # Über die Liste zur Leitungsseite, dort mit dem Stift weiter, ohne Löschen.
    page = client.get(event_address(entwurf))
    assert page.status_code == 200
    assert "öschen" not in _visible_text(_tree(page))
    assert client.get(f"{event_address(entwurf)}bearbeiten/").status_code == 200

    # Über den Verlauf des Browsers zur Zusammenfassung: Speichern und „Entwurf löschen“ gehen noch.
    root = _tree(client.get(summary_address(entwurf)))
    assert "Veranstaltung speichern" in buttons(root)
    assert "Entwurf löschen" in dialog_buttons(open_dialog(_tree(client.get(cancel_address(entwurf)))))
    assert client.post(delete_address(entwurf)).url == LIST
    assert not Event.objects.exists()


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VA-06")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anlegen/")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anlegen/zusammenfassung/")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anlegen/abbrechen/")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anlegen/loeschen/")
def test_bv1_niemand_ausser_wanda_oeffnet_den_ablauf_oder_loescht_den_entwurf(org, entwurf):
    smuggled = {**PFINGSTLAGER, "name": "Gekapert", "version": "1"}
    for user in (org.fiete, org.finn, org.vera, org.max, org.otto):
        client = client_for(user)
        for address in flow_addresses(entwurf):
            assert_like_missing(user, address)
            assert client.get(address, **SCRIPT).status_code == 404, (user.username, address)
            assert client.post(address, smuggled).status_code == 404, (user.username, address)

    entwurf.refresh_from_db()
    assert entwurf.name == "Pfingstlager 2028"
    # Das Anlegen läuft weiter: Wanda kann es noch beenden und löschen.
    assert "Entwurf löschen" in dialog_buttons(open_dialog(page_tree(org.wanda, cancel_address(entwurf))))


@pytest.mark.rechtematrix("VA-06")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anlegen/loeschen/")
def test_bv1_auch_mitleitungen_und_admins_im_support_zugang_nicht(org, entwurf):
    second_lead(entwurf, org.fiete)
    for address in flow_addresses(entwurf):
        assert_like_missing(org.fiete, address)
    assert client_for(org.fiete).post(delete_address(entwurf)).status_code == 404

    client = client_for(org.max)
    assert client.post(f"{unit_address(org.walhall)}support-zugang/", {"anlass": "lead_request"}).status_code == 302
    for address in flow_addresses(entwurf):
        assert client.get(address).status_code == 404, address
        assert client.post(address).status_code == 404, address
    assert_like_missing(org.max, delete_address(entwurf))

    assert Event.objects.filter(pk=entwurf.pk).exists()


@pytest.mark.rechtematrix("VA-06")
def test_bv2_nach_veranstaltung_speichern_ist_das_anlegen_beendet(org, entwurf):
    client = client_for(org.wanda)
    assert client.post(summary_address(entwurf)).url == event_address(entwurf)

    for address in flow_addresses(entwurf)[:3]:
        response = client.get(address)
        assert (response.status_code, response.url) == (302, event_address(entwurf)), address
    response = client.post(delete_address(entwurf))

    assert (response.status_code, response.url) == (302, event_address(entwurf))
    assert Event.objects.filter(pk=entwurf.pk).exists()
    # Auch ein zweites „Veranstaltung speichern“ oder „Entwurf speichern“ ändert nichts mehr.
    assert client.post(summary_address(entwurf)).url == event_address(entwurf)
    assert client.post(cancel_address(entwurf)).url == event_address(entwurf)
    assert Event.objects.filter(pk=entwurf.pk).exists()


@pytest.mark.rechtematrix("VA-06")
def test_bv2_nach_entwurf_speichern_loescht_auch_wanda_nichts(org, sommerfahrt):
    client = client_for(org.wanda)
    assert client.post(cancel_address(sommerfahrt)).url == LIST

    response = client.post(delete_address(sommerfahrt))

    assert (response.status_code, response.url) == (302, event_address(sommerfahrt))
    assert Event.objects.filter(pk=sommerfahrt.pk).exists()
    assert "öschen" not in _visible_text(page_tree(org.wanda, event_address(sommerfahrt)))


@pytest.mark.rechtematrix("VA-06")
def test_bv3_mit_mitleitung_bietet_der_dialog_nur_entwurf_speichern(org, sommerfahrt):
    second_lead(sommerfahrt, org.fiete)
    client = client_for(org.wanda)

    dialog = open_dialog(_tree(client.get(cancel_address(sommerfahrt))))

    assert dialog_buttons(dialog) == {"Entwurf speichern": (cancel_address(sommerfahrt), "blau")}
    assert "löschen" not in _visible_text(dialog)
    response = client.post(delete_address(sommerfahrt))
    assert response.status_code == 302
    assert response.url == cancel_address(sommerfahrt)
    assert Event.objects.filter(pk=sommerfahrt.pk).exists()
    # Gegenprobe: „Entwurf speichern“ geht weiter.
    assert client.post(cancel_address(sommerfahrt)).url == LIST


@pytest.mark.rechtematrix("VA-06")
def test_bv3_mit_einer_anmeldung_bietet_der_dialog_nur_entwurf_speichern(org, sommerfahrt):
    Rights(org.wanda).register(sommerfahrt, [org.wanda])
    client = client_for(org.wanda)

    dialog = open_dialog(_tree(client.get(cancel_address(sommerfahrt))))

    assert dialog_buttons(dialog) == {"Entwurf speichern": (cancel_address(sommerfahrt), "blau")}
    client.post(delete_address(sommerfahrt))
    assert Event.objects.filter(pk=sommerfahrt.pk).exists()


@pytest.mark.rechtematrix("VA-05")
def test_bv4_otto_oeffnet_den_ablauf_nicht(org):
    client = client_for(org.otto)

    assert_no_access(client.get(CREATE))
    assert_no_access(client.post(CREATE, {**PFINGSTLAGER, "creation_key": "b" * 20}))
    assert not Event.objects.exists()


# ---------- Grenzfälle ----------


def test_bg1_doppelklick_auf_weiter_ergibt_nur_einen_entwurf(org):
    client = client_for(org.wanda)
    _root, creation_key = open_step_one(org.wanda, client=client)
    form = {**PFINGSTLAGER, "creation_key": creation_key}

    first = client.post(CREATE, form)
    second = client.post(CREATE, form)

    assert Event.objects.count() == 1
    assert first.url == second.url == invitation_step_address(Event.objects.get())


def test_doppelklick_auf_weiter_nach_zurueck_fuehrt_zur_zusammenfassung(org, entwurf):
    """Risikovariante zu #391: Schritt 1 eines Entwurfs speichert über dieselbe Funktion wie der Stift.

    Grundlage ist der Eintrag zu #380 in `docs/entscheidungen.md`, „Technische Wahl“, Nr. 4.

    Die Regel „gleiche Angaben bei älterem Stand gelten als gespeichert“ (#391, DK2) gilt darum auch hier: Der
    zweite Klick auf „Weiter“ führt zur Zusammenfassung statt zu „… wurde inzwischen geändert“. Seit #358 ist der
    nächste Schritt nach Schritt 1 „Einladungstext“; die Regel ist dieselbe.
    """
    client = client_for(org.wanda)
    form = {**shown(org.wanda, entwurf, client), "location": "Zeltplatz Moor"}

    first = client.post(basics_address(entwurf), form)
    second = client.post(basics_address(entwurf), form)

    assert (first.status_code, second.status_code) == (302, 302)
    assert first.url == second.url == invitation_step_address(entwurf)
    entwurf.refresh_from_db()
    assert (entwurf.location, entwurf.version) == ("Zeltplatz Moor", 2)


@pytest.mark.rechtematrix("VA-06")
def test_bg2_doppelklick_auf_entwurf_loeschen_fuehrt_ohne_fehler_zur_liste(org, sommerfahrt):
    client = client_for(org.wanda)

    first = client.post(delete_address(sommerfahrt))
    second = client.post(delete_address(sommerfahrt))

    assert (first.status_code, first.url) == (302, LIST)
    assert (second.status_code, second.url) == (302, LIST)
    assert short_notices(client.get(LIST)) == [DELETED % "Sommerfahrt 2028"]
    assert not Event.objects.exists()


def test_bg2_gegenprobe_eine_andere_person_bekommt_nach_dem_loeschen_nicht_gefunden(org, sommerfahrt):
    """Die Weiterleitung nach dem zweiten Klick gibt es nur für die Person, die gelöscht hat."""
    address = delete_address(sommerfahrt)
    assert client_for(org.wanda).post(address).url == LIST

    assert client_for(org.fiete).post(address).status_code == 404
    # Auch in einem neuen Fenster ohne die Sitzung des Löschens ist es „nicht gefunden“.
    assert client_for(org.wanda).post(address).status_code == 404


@pytest.mark.parametrize("values, errors", [
    ({"name": "  "}, {"name": "Bitte gib den Namen ein."}),
    ({"start": "2028-01-04"}, {"start": PAST}),
    ({"start": "2028-07-20", "end": "2028-08-29"}, {"end": "Die Veranstaltung dauert 41 Tage. Stimmt das?"}),
])
def test_bg3_ein_fehler_in_schritt_1_speichert_nichts(org, values, errors):
    response = weiter(org.wanda, **values)

    assert response.status_code == 200
    root = _tree(response)
    assert field_errors(root) == errors
    assert field_values(step_form(root))["location"] == "Burg Ludwigstein"
    assert progress(root)[0] == ("Schritt 1 Grunddaten", True)
    assert not Event.objects.exists()


def test_bg4_leerer_name_nach_zurueck_der_entwurf_behaelt_den_alten(org, entwurf):
    client = client_for(org.wanda)

    response = client.post(basics_address(entwurf), {**shown(org.wanda, entwurf, client), "name": ""})

    assert response.status_code == 200
    root = _tree(response)
    assert field_errors(root) == {"name": "Bitte gib den Namen ein."}
    assert field_values(step_form(root))["name"] == ""
    entwurf.refresh_from_db()
    assert entwurf.name == "Pfingstlager 2028"


def test_bg5_endet_die_zuordnung_bei_offenem_schritt_1_entsteht_nichts(org):
    client = client_for(org.wanda)
    _root, creation_key = open_step_one(org.wanda, client=client)
    remove(org.wanda, R.TROOP_LEAD, org.walhall)
    remove(org.wanda, R.MEMBER, org.walhall)

    assert_no_access(client.post(CREATE, {**PFINGSTLAGER, "creation_key": creation_key}))
    assert not Event.objects.exists()


def test_bg5_besteht_der_entwurf_schon_beendet_wanda_das_anlegen(org, entwurf):
    remove(org.wanda, R.TROOP_LEAD, org.walhall)
    remove(org.wanda, R.MEMBER, org.walhall)
    client = client_for(org.wanda)

    assert client.get(summary_address(entwurf)).status_code == 200
    assert client.post(summary_address(entwurf)).url == event_address(entwurf)
    assert short_notices(client.get(event_address(entwurf))) == [SAVED % "Pfingstlager 2028"]


@pytest.mark.django_db(transaction=True)
def test_entwurf_speichern_und_loeschen_gleichzeitig_der_entwurf_bleibt():
    """Klickt Wanda in zwei Fenstern zugleich „Entwurf speichern“ und „Entwurf löschen“, gewinnt das erste.

    Hier ist „Entwurf speichern“ zuerst; danach ist das Anlegen beendet, und das Löschen wartet und löscht nichts.
    """
    o = build_people()
    entry = Rights(o.wanda).create_event(
        {"name": "Sommerfahrt 2028", "start": date(2028, 7, 20), "end": date(2028, 7, 30)}, "f" * 20)

    results = _one_after_the_other(lambda: Rights(o.wanda).finish_creating(entry.key),
                                   lambda: Rights(o.wanda).delete_draft(entry.key))

    assert Event.objects.filter(pk=entry.pk).exists()
    assert results[-1] is None


# ---------- Bausteinkatalog ----------


@pytest.mark.bausteinkatalog
def test_der_katalog_zeigt_die_fortschrittsanzeige_und_den_dialog_mit_zwei_knoepfen(settings, org):
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = page_tree(org.wanda, "/bausteine/")

    entry = _one(_by_tag(root, "section", aria_labelledby="h-fortschritt"))
    assert _text(_one(_by_tag(entry, "h2"))) == "Fortschrittsanzeige"
    assert "#380" in _visible_text(entry)
    assert _visible_text(_one(_all(entry, lambda e: "a-baustein-seiten" in _classes(e)))) == (
        "Genutzt auf: Veranstaltungen")
    steps = _one(_all(entry, lambda e: e.name == "ol" and "a-schritte" in _classes(e)))
    assert [_attr(step, "aria-current") for step in _by_tag(steps, "li")] == [None, "step"]

    dialog = _one(_by_tag(root, "section", aria_labelledby="h-dialog"))
    assert "#380" in _visible_text(_one(_all(dialog, lambda e: "a-baustein-herkunft" in _classes(e))))
    preview = _one(_by_tag(dialog, "dialog", aria_labelledby="h-dialog-abbrechen"))
    assert set(dialog_buttons(preview)) == {"Entwurf löschen", "Entwurf speichern"}


# ---------- Befunde der unabhängigen Prüfung ----------


@pytest.mark.django_db(transaction=True)
def test_bg2_echter_doppelklick_auf_entwurf_loeschen_beide_klicks_fuehren_zur_liste():
    """Befund B1: Beide Anfragen kommen, bevor die erste fertig ist; die zweite wartet und darf nicht „nicht gefunden“ zeigen."""
    o = build_people()
    entry = Rights(o.wanda).create_event(
        {"name": "Sommerfahrt 2028", "start": date(2028, 7, 20), "end": date(2028, 7, 30)}, "g" * 20)
    client = client_for(o.wanda)

    results = _one_after_the_other(lambda: client.post(delete_address(entry)),
                                   lambda: client.post(delete_address(entry)))

    assert [(response.status_code, response.url) for response in results] == [(302, LIST), (302, LIST)]
    assert not Event.objects.exists()


def test_bg5_ohne_zuordnung_fuehrt_entwurf_loeschen_zur_startseite_mit_der_meldung(org, entwurf):
    """Befund B2: Ohne Zuordnung und ohne geleitete Veranstaltung gibt es die Liste nicht; „kein Zugriff“ darf nicht kommen."""
    remove(org.wanda, R.TROOP_LEAD, org.walhall)
    remove(org.wanda, R.MEMBER, org.walhall)
    client = client_for(org.wanda)

    response = client.post(delete_address(entwurf))

    assert response.status_code == 302
    page = client.get(response.url)
    assert page.status_code == 200
    assert short_notices(page) == [DELETED % "Pfingstlager 2028"]
    assert not Event.objects.exists()
