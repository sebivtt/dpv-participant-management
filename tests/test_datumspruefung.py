"""Tests für die Datumsprüfungen schon beim Verlassen des Felds (#411, Teil C von #398): was die Seite dafür mitbringt.

Die Kennungen CA1 bis CA9 und CG1 bis CG4 verweisen auf die Szenarien vom 24.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/411#issuecomment-7124250592). Geprüft wird hier, was
der Server dem Skript mitgibt: den heutigen Tag des Servers (CG3), die Wortlaute der Meldungen (CA1 bis CA4), beim
Bearbeiten die gespeicherten Angaben (CA6), die Vorlage für den Schalter „Ja, die Dauer stimmt“ (CA4) und dass der
Server beim Speichern weiter selbst prüft (CA7). Wie sich die Meldungen im Browser zeigen, prüft
`rauchtests/test_datumspruefung.py`. „Heute“ ist wie in den Szenarien der 05.01.2028. Wanda (Stammesleitung Walhall)
ist erfunden, wie in #163.
"""

from datetime import date, time

import pytest
from django.utils import timezone

from events.models import Event
from tests.test_benennen import dialog_of
from tests.test_gestaltung import _all, _attr, _by_tag, _one, _tree
from tests.test_grunddaten import create, save, shown, switch_of
from tests.test_organisation import client_for
from tests.test_veranstaltung_anlegen import basics_address
from tests.test_veranstaltungen import CREATE, build_people, edit_address, event_of, field_errors, step_form

pytestmark = pytest.mark.django_db

TODAY = date(2028, 1, 5)
END_BEFORE_START = "Das Ende liegt vor dem Beginn."
PAST = "Der Beginn liegt in der Vergangenheit."
# Die Zahl der Tage setzt das Skript für „{anzahl}“ ein, wie bei der Zahl der Zeichen (#215).
DURATION = "Die Veranstaltung dauert {anzahl} Tage. Stimmt das?"
DATE_FIELDS = ("start", "start_time", "end", "end_time")


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    """Der Tag des Servers ist der 05.01.2028, wie in den Szenarien."""
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: TODAY)


@pytest.fixture
def org():
    return build_people()


@pytest.fixture
def pfingstlager(org):
    """Wandas Pfingstlager, das schon läuft (CA6): Beginn 02.01.2028, 18:00, Ende 05.06.2028 ohne Uhrzeit."""
    found = event_of(org.wanda, "Pfingstlager 2028", date(2028, 1, 2), date(2028, 6, 5))
    found.start_time = time(18, 0)
    found.save()
    return found


def inputs(root) -> dict:
    """Die Felder für Beginn, Ende und ihre Uhrzeiten, je Name."""
    return {name: _one(_by_tag(root, "input", name=name)) for name in DATE_FIELDS}


def templates(root) -> list:
    return _all(root, lambda e: e.name == "template" and _attr(e, "data-dauerfrage") is not None)


def stored(root) -> dict:
    """Die gespeicherten Angaben, die die Seite dem Skript mitgibt, je Feld (None: keine)."""
    return {name: _attr(field, "data-gespeichert") for name, field in inputs(root).items()}


# ---------- Was das Skript mitbekommt ----------


def test_cg3_die_seite_bringt_den_heutigen_tag_des_servers_mit(org):
    """CG3: „Heute“ ist der Tag des Servers, nicht die Uhr des Rechners."""
    root = step_form(_tree(client_for(org.wanda).get(CREATE)))

    assert _attr(inputs(root)["start"], "data-heute") == "2028-01-05"


def test_ca1_bis_ca4_die_meldungen_kommen_im_bekannten_wortlaut_mit(org):
    """CA1 bis CA4: dieselben Wortlaute wie vom Server, an den Feldern, an denen sie stehen; die Grenze 29 Tage."""
    fields = inputs(step_form(_tree(client_for(org.wanda).get(CREATE))))

    assert _attr(fields["start"], "data-vergangen") == PAST
    assert _attr(fields["end"], "data-vor-beginn") == END_BEFORE_START
    assert _attr(fields["end"], "data-dauer-frage") == DURATION
    assert _attr(fields["end"], "data-dauer-ab") == "29"
    # Das Ende kennt seinen Beginn, beide ihre Uhrzeit.
    assert _attr(fields["end"], "data-beginn") == _attr(fields["start"], "id")
    assert _attr(fields["start"], "data-uhrzeit") == _attr(fields["start_time"], "id")
    assert _attr(fields["end"], "data-uhrzeit") == _attr(fields["end_time"], "id")


def test_ca4_ohne_nachfrage_liegt_der_schalter_als_vorlage_bereit(org):
    """CA4: Den Schalter „Ja, die Dauer stimmt“ holt das Skript aus einer Vorlage, die ohne Skript nichts zeigt."""
    root = step_form(_tree(client_for(org.wanda).get(CREATE)))

    found = _one(templates(root))
    assert _by_tag(found, "input", name="duration_ok")
    assert _attr(_one(_by_tag(found, "input", name="duration_ok")), "checked") is None


def test_ca4_mit_nachfrage_vom_server_genau_ein_schalter_und_keine_vorlage(org):
    """CA4: Fragt schon der Server nach der Dauer, steht der Schalter da, und es gibt keinen zweiten als Vorlage."""
    response = create(org.wanda, start="2028-06-02", end="2028-06-30")

    root = step_form(_tree(response))
    assert field_errors(root)["end"] == "Die Veranstaltung dauert 29 Tage. Stimmt das?"
    assert switch_of(root) is not None
    assert templates(root) == []


def test_ca6_beim_anlegen_gilt_alles_als_eingegeben(org):
    """CA6, Gegenprobe: Beim Anlegen gibt es nichts Gespeichertes, verglichen wird nicht."""
    root = step_form(_tree(client_for(org.wanda).get(CREATE)))

    assert stored(root) == dict.fromkeys(DATE_FIELDS)


def test_ca6_im_dialog_des_stifts_kennt_das_skript_die_gespeicherten_angaben(org, pfingstlager):
    """CA6: Beim Bearbeiten prüft das Skript wie der Server nur Geändertes; dafür bringt die Seite das Gespeicherte mit."""
    root = dialog_of(_tree(client_for(org.wanda).get(edit_address(pfingstlager))))

    assert stored(root) == {"start": "2028-01-02", "start_time": "18:00", "end": "2028-06-05", "end_time": ""}


def test_ca6_auch_nach_adresse_leeren_im_dialog_des_stifts(org, pfingstlager):
    """CA6: Auch nachdem die Seite vom Adressfeld neu kommt, vergleicht das Skript mit dem Gespeicherten, nicht mit
    den Eingaben; sonst meldete es beim laufenden Pfingstlager „Der Beginn liegt in der Vergangenheit.“"""
    client = client_for(org.wanda)
    response = client.post(f"{edit_address(pfingstlager)}adresse-suchen/",
                           {**shown(pfingstlager), "end": "2028-06-07", "leeren": ""})

    root = dialog_of(_tree(response))
    assert stored(root) == {"start": "2028-01-02", "start_time": "18:00", "end": "2028-06-05", "end_time": ""}


def test_ca6_in_schritt_1_eines_entwurfs_ebenso(org):
    """CA6: Schritt 1 eines gespeicherten Entwurfs speichert wie der Stift; das Skript vergleicht ebenso."""
    create(org.wanda, name="Pfingstlager 2028", start="2028-06-02", end="2028-06-05")
    entwurf = Event.objects.get(name="Pfingstlager 2028")

    root = step_form(_tree(client_for(org.wanda).get(basics_address(entwurf))))

    assert stored(root) == {"start": "2028-06-02", "start_time": "18:00", "end": "2028-06-05", "end_time": "12:00"}


# ---------- Der Server prüft weiter ----------


def test_ca7_wer_die_meldung_uebergeht_bekommt_sie_vom_server_und_nichts_ist_gespeichert(org, pfingstlager):
    """CA7: Die Prüfung im Browser ersetzt nichts; „Speichern“ mit Ende vor Beginn speichert nicht."""
    response = save(org.wanda, pfingstlager, end="2027-12-31")

    assert response.status_code == 200
    assert field_errors(dialog_of(_tree(response)))["end"] == END_BEFORE_START
    pfingstlager.refresh_from_db()
    assert pfingstlager.end == date(2028, 6, 5)
