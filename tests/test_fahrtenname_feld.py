"""Tests für das Feld „Fahrtenname“ zum Antippen und die Kopfzeile wie im Zielbild (#180).

Die Nummern verweisen auf Sebastians Szenarien vom 26.10.2026 in #180 („Szenarien (26.10.2026)“).
Hier steht, was der Server ausliefert: Ruhezustand, Eingabe mit „Verwerfen“ und „Speichern“,
Kopfzeile und der Rückfall ohne Skript. Öffnen, Schließen, Tastatur und Handy kann nur ein
echter Browser zeigen; das prüft rauchtests/test_rauchtest.py. Speichern, Meldungen, Länge,
Leerzeichen und Rechte bleiben wie in #111 und stehen in tests/test_fahrtenname.py.
"""

import re

import pytest

from tests import test_fahrtenname
from tests.test_fahrtenname import (
    DELETED,
    NOT_GIVEN,
    PROFILE,
    SAVE,
    SAVED,
    TOO_LONG,
    client_for,
    field,
    foreign_fields,
    notices,
    profile,
    save,
    set_stored,
    stored,
)
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _tree, _visible_text
from tests.test_mein_profil import main, raw_text, symbols
from tests.test_mein_profil import display_name as shown_name

pytestmark = pytest.mark.django_db

PLACEHOLDER = "Fahrtennamen eingeben"


@pytest.fixture
def org():
    """Dieselben erfundenen Personen wie in tests/test_fahrtenname.py, mit Stammesleitung Wanda."""
    return test_fahrtenname.org.__wrapped__()


def box(root):
    """Das Feld „Fahrtenname“ zum Antippen mit Beschriftung, Eingabe und Knöpfen."""
    return _one(_all(main(root), lambda e: _attr(e, "data-antippfeld") is not None))


def rest(root):
    """Der Ruhezustand: ein Knopf, der aussieht wie die anderen Angaben und die Eingabe öffnet."""
    return _one(_all(box(root), lambda e: e.name == "button" and _attr(e, "data-oeffnen") is not None))


def clear_button(root):
    return _one(_all(box(root), lambda e: e.name == "button" and _attr(e, "data-leeren") is not None))


def button(root, text: str):
    return _one([b for b in _by_tag(box(root), "button") if _visible_text(b) == text])


def shown_value(root) -> str:
    return re.sub(r"\s+", " ", _visible_text(rest(root)))


# Szenario 1: Erika hat den Fahrtennamen „Falkenflug“


def test_in_ruhe_sieht_das_feld_aus_wie_die_anderen_angaben(org):
    set_stored(org.erika, "Falkenflug")
    root = profile(org.erika)

    label = _one(_by_tag(box(root), "label"))
    assert _visible_text(label) == "Fahrtenname"
    assert _attr(rest(root), "type") == "button"
    assert symbols(rest(root)) == ["person"]
    assert shown_value(root) == "Falkenflug"
    assert "a-leer" not in _classes(_one(_all(rest(root), lambda e: "a-antippfeld-wert" in _classes(e))))
    # Vorleseprogramme hören, was der Knopf tut, und den Wert dazu; den genauen Namen prüft der Rauchtest.
    hidden = _one(_all(rest(root), lambda e: "sr-nur" in _classes(e)))
    assert raw_text(hidden).strip() == "Fahrtenname bearbeiten:"
    assert raw_text(rest(root)).endswith("Falkenflug")


def test_rechts_ein_leeren_knopf_der_vorgelesen_wird(org):
    set_stored(org.erika, "Falkenflug")
    clear = clear_button(profile(org.erika))

    assert _attr(clear, "type") == "button"
    assert _attr(clear, "aria-label") == "Fahrtenname leeren"
    assert _attr(clear, "title") == "Inhalt löschen"
    assert symbols(clear) == ["schliessen"]
    assert _attr(clear, "disabled") is None


# Szenario 2: Max hat keinen Fahrtennamen


def test_ohne_fahrtennamen_noch_nicht_angegeben_und_leeren_ausgegraut(org):
    root = profile(org.max)

    assert shown_value(root) == NOT_GIVEN
    assert "a-leer" in _classes(_one(_all(rest(root), lambda e: "a-antippfeld-wert" in _classes(e))))
    assert _attr(clear_button(root), "disabled") == ""


# Szenario 3: Antippen öffnet die Eingabe mit „Verwerfen“ und „Speichern“


def test_die_eingabe_hat_den_fahrtennamen_und_den_platzhalter(org):
    set_stored(org.erika, "Falkenflug")

    input_ = field(profile(org.erika))

    assert _attr(input_, "value") == "Falkenflug"
    assert _attr(input_, "placeholder") == PLACEHOLDER
    assert symbols(_one(_all(box(profile(org.erika)), lambda e: "a-antippfeld-eingabe" in _classes(e)))) == ["person"]


def test_leer_zeigt_die_eingabe_den_platzhalter(org):
    input_ = field(profile(org.max))

    assert _attr(input_, "value") in (None, "")
    assert _attr(input_, "placeholder") == PLACEHOLDER


def test_unter_der_eingabe_verwerfen_und_speichern(org):
    root = profile(org.erika)

    discard = button(root, "Verwerfen")
    submit = button(root, "Speichern")
    assert _attr(discard, "type") == "button"
    assert _attr(discard, "data-verwerfen") is not None
    assert _attr(submit, "type") == "submit"
    knoepfe = _one(_all(box(root), lambda e: "a-antippfeld-knoepfe" in _classes(e)))
    assert [_visible_text(b) for b in _by_tag(knoepfe, "button")] == ["Verwerfen", "Speichern"]


def test_in_ruhe_ist_das_feld_beim_laden_zu(org):
    """Offen ist es erst nach dem Antippen; nur nach einem Fehler kommt es offen vom Server (Szenario 7)."""
    root = profile(org.erika)

    assert _attr(box(root), "data-offen") is None
    assert _attr(box(root), "data-fokus") is None


# Szenarien 4 bis 6: Ansagen für Vorleseprogramme nach Verwerfen und Leeren


def test_ansagen_fuer_verwerfen_und_leeren_sind_uebersetzbar_vorbereitet(org):
    """Das Skript liest die Texte aus der Seite, damit sie wie alle Texte übersetzbar sind (NFA-02)."""
    container = box(profile(org.erika))

    assert _attr(container, "data-ansage-verworfen") == "Änderungen verworfen."
    assert _attr(container, "data-ansage-geleert") == "Feld geleert. Mit Speichern übernehmen oder verwerfen."
    region = _one(_all(container, lambda e: _attr(e, "data-ansage") is not None))
    assert _attr(region, "role") == "status"
    assert raw_text(region) == ""


# Szenario 4: Speichern schließt das Feld und zeigt den neuen Namen


def test_nach_dem_speichern_zeigt_das_feld_den_neuen_namen_und_bekommt_den_fokus(org):
    set_stored(org.erika, "Falkenflug")
    client = client_for(org.erika)

    save(org.erika, "Kolibri", client=client)

    root = profile(org.erika, client=client)
    assert notices(root, "ist-erfolg") == [SAVED]
    assert shown_value(root) == "Kolibri"
    assert _attr(box(root), "data-offen") is None
    # Szenario 9: Der Fokus landet nach dem Speichern wieder auf dem Feld.
    assert _attr(box(root), "data-fokus") is not None
    # Nur einmal: Beim nächsten Aufruf steht weder Meldung noch Fokus da.
    again = profile(org.erika, client=client)
    assert notices(again, "ist-erfolg") == []
    assert _attr(box(again), "data-fokus") is None


# Szenario 6: × öffnet das Feld leer, erst „Speichern“ löscht


def test_leeres_feld_speichern_loescht_den_fahrtennamen(org):
    set_stored(org.erika, "Falkenflug")
    client = client_for(org.erika)

    save(org.erika, "", client=client)

    root = profile(org.erika, client=client)
    assert stored(org.erika) == ""
    assert notices(root, "ist-erfolg") == [DELETED]
    assert shown_value(root) == NOT_GIVEN
    assert _attr(clear_button(root), "disabled") == ""


def test_leeren_knopf_loescht_nichts_selbst(org):
    """Der Knopf ist kein Formularknopf und schickt nichts ab; er hat keine Adresse und keinen Wert."""
    set_stored(org.erika, "Falkenflug")
    clear = clear_button(profile(org.erika))

    assert _attr(clear, "type") == "button"
    assert _attr(clear, "name") is None
    assert _attr(clear, "formaction") is None
    assert stored(org.erika) == "Falkenflug"


# Szenario 7: 51 Zeichen und „Speichern“


def test_zu_lang_das_feld_bleibt_offen_mit_fehler_und_eingabe(org):
    set_stored(org.erika, "Falkenflug")

    response = save(org.erika, "K" * 51)

    root = _tree(response)
    assert _attr(box(root), "data-offen") is not None
    input_ = field(root)
    assert _attr(input_, "value") == "K" * 51
    assert _attr(input_, "aria-invalid") == "true"
    error = _one(_by_tag(box(root), "div", id=_attr(input_, "aria-describedby")))
    assert _visible_text(error) == TOO_LONG
    # In Ruhe stünde weiter der gespeicherte Name, nicht die zu lange Eingabe.
    assert shown_value(root) == "Falkenflug"
    assert stored(org.erika) == "Falkenflug"
    assert _attr(box(root), "data-fokus") is None


def test_speichern_scheitert_das_feld_bleibt_offen_mit_der_eingabe(org, monkeypatch):
    """Unabhängige Prüfung: Auch nach einem technischen Fehler kommt das Feld offen, in Ruhe stünde der alte Wert."""
    from django.contrib.auth import get_user_model
    from django.db import DatabaseError

    set_stored(org.erika, "Falkenflug")
    client = client_for(org.erika)

    def fail(self, *args, **kwargs):
        raise DatabaseError("Datenbank weg")

    monkeypatch.setattr(get_user_model(), "save", fail)

    root = _tree(save(org.erika, "Kolibri", client=client))

    assert _attr(box(root), "data-offen") is not None
    assert _attr(field(root), "value") == "Kolibri"
    assert _attr(box(root), "data-gespeichert") == "Falkenflug"
    assert shown_value(root) == "Falkenflug"


# Szenario 8: Kopfzeile wie im Zielbild


def head(root):
    return _one(_all(main(root), lambda e: "a-anzeigename" in _classes(e)))


def test_kopfzeile_fahrtenname_gross_und_der_name_kleiner_dahinter(org):
    set_stored(org.erika, "Falkenflug")
    root = profile(org.erika)

    addition = _one(_all(head(root), lambda e: "a-anzeigename-zusatz" in _classes(e)))
    assert _visible_text(addition) == "(Erika Testfrau)"
    assert shown_name(root) == "Falkenflug (Erika Testfrau)"


def test_kopfzeile_ohne_fahrtennamen_nur_der_name(org):
    root = profile(org.erika)

    assert shown_name(root) == "Erika Testfrau"
    assert not _all(head(root), lambda e: "a-anzeigename-zusatz" in _classes(e))


@pytest.mark.parametrize(("first", "last", "expected"), [("Erika", "", "(Erika)"), ("", "", None)])
def test_kopfzeile_mit_teil_des_namens_oder_ganz_ohne_namen(org, first, last, expected):
    """Wie in #111: ohne Vor- und Nachname nur „Kiwi“, ohne leere Klammern."""
    org.erika.first_name, org.erika.last_name = first, last
    org.erika.save(update_fields=["first_name", "last_name"])
    set_stored(org.erika, "Kiwi")

    additions = _all(head(profile(org.erika)), lambda e: "a-anzeigename-zusatz" in _classes(e))

    assert [_visible_text(a) for a in additions] == ([expected] if expected else [])
    assert shown_name(profile(org.erika)) == ("Kiwi " + expected if expected else "Kiwi")


# Szenario 11: ohne Skript das einfache Formular


def test_ohne_skript_bleibt_das_einfache_formular(org):
    """Was nur mit Skript geht, ist versteckt, bis das Skript es zeigt; Eingabe und „Speichern“ sind gleich da."""
    set_stored(org.erika, "Falkenflug")
    root = profile(org.erika)

    form = _one(_by_tag(main(root), "form"))
    assert (_attr(form, "method"), _attr(form, "action")) == ("post", SAVE)
    assert _attr(rest(root), "hidden") == ""
    assert _attr(clear_button(root), "hidden") == ""
    assert _attr(button(root, "Verwerfen"), "hidden") == ""
    assert _attr(field(root), "hidden") is None
    assert _attr(button(root, "Speichern"), "hidden") is None
    hidden_parents = _all(box(root), lambda e: _attr(e, "hidden") is not None and field(root) in _all(e, lambda x: True))
    assert hidden_parents == []


def test_ohne_skript_speichert_das_formular_wie_bisher(org):
    client = client_for(org.erika)

    response = client.post(SAVE, {"scout_name": "Kolibri"})

    assert response.status_code == 302
    assert response["Location"] == PROFILE
    assert stored(org.erika) == "Kolibri"


def test_das_skript_kommt_vom_eigenen_server(org):
    scripts = [_attr(s, "src") for s in _by_tag(profile(org.erika), "script")]

    assert scripts == ["/static/core/app.js"]


# Szenario 12: Rechte wie in #111


def test_im_feld_steht_keine_kennung_einer_person(org):
    """Wessen Konto sich ändert, bestimmt allein die Anmeldung (EP-04); die Seite liefert keine Kennung mit."""
    set_stored(org.erika, "Falkenflug")
    container = box(profile(org.erika))

    values = [value or "" for element in _all(container, lambda e: True) for _name, value in element.attributes]
    for identifier in (str(org.erika.pk), str(org.erika.key), org.erika.username):
        assert not any(identifier == value or f"/{identifier}/" in value for value in values), identifier
    names = {_attr(e, "name") for e in _all(container, lambda e: e.name in ("input", "button")) if _attr(e, "name")}
    assert names == {"scout_name"}


@pytest.mark.rechtematrix("EP-04")
def test_stammesleitung_aendert_erikas_fahrtennamen_auch_ueber_das_neue_feld_nicht(org):
    set_stored(org.erika, "Falkenflug")

    for htmx in (False, True):
        save(org.lead, "Gekapert", htmx=htmx, **foreign_fields(org.erika))

    assert stored(org.erika) == "Falkenflug"
    assert shown_value(profile(org.erika)) == "Falkenflug"
    assert shown_value(profile(org.lead)) == "Gekapert"


# Neuer Baustein zuerst auf der Musterseite (docs/gestaltung.md)


def test_musterseite_zeigt_das_feld_zum_antippen(org):
    """Mit erfundenem Fahrtennamen; das Formular dort schickt nichts ab."""
    section = _one(_by_tag(_tree(client_for(org.erika).get("/muster/")), "section", aria_labelledby="h-profil"))

    form = _one(_by_tag(section, "form"))
    assert _attr(form, "data-nur-ansicht") is not None
    container = _one(_all(form, lambda e: _attr(e, "data-antippfeld") is not None))
    assert _visible_text(_one(_by_tag(container, "label"))) == "Fahrtenname"
    assert [_visible_text(b) for b in _by_tag(container, "button") if _attr(b, "data-oeffnen") is None] == [
        "", "Verwerfen", "Speichern",
    ]
    head_ = _one(_all(section, lambda e: "a-anzeigename" in _classes(e)))
    assert _all(head_, lambda e: "a-anzeigename-zusatz" in _classes(e))
