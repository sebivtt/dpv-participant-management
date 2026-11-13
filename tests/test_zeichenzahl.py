"""Tests für die mitlaufende Zahl der Zeichen unter Feldern mit fachlicher Grenze (#215).

Die Nummern verweisen auf Sebastians Szenarien vom 30.10.2026 in #215
(https://github.com/sebivtt/dpv-participant-management/issues/215#issuecomment-6524812974).
Hier steht, was der Server ausliefert: die leere, versteckte Stelle für die Zahl, ihre Verknüpfung
mit der Eingabe und die Grenze am Feld. Die Zahl selbst schreibt erst das Skript; Tippen, Einfügen,
Wortvorschläge, Farbe und Ansage prüft rauchtests/test_zeichenzahl.py. Alle Namen sind erfunden.
"""

import pytest
from django import forms
from django.template import Context, Template
from django.test.html import parse_html

from accounts.models import SCOUT_NAME_MAX_LENGTH
from core.forms import AccountSearchForm
from tests import test_fahrtenname
from tests.test_bausteinkatalog import ADDRESS as CATALOG
from tests.test_bausteinkatalog import _client_for, _section
from tests.test_fahrtenname import TOO_LONG, field, profile, save, stored
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree
from tests.test_mein_profil import main
from tests.test_rollen import build_org

pytestmark = pytest.mark.django_db

COUNTER_ID = "id_scout_name-zahl"
ERROR_ID = "id_scout_name-fehler"


@pytest.fixture
def org():
    """Dieselben erfundenen Personen wie in tests/test_fahrtenname.py."""
    return test_fahrtenname.org.__wrapped__()


def counter(root):
    return _one(_all(root, lambda e: "a-zeichenzahl" in _classes(e)))


def described_by(element) -> list[str]:
    return (_attr(element, "aria-describedby") or "").split()


# Szenarien 1 bis 5, 13 und 14: die Stelle für die Zahl, verknüpft mit der Eingabe


def test_das_feld_traegt_seine_grenze_und_die_meldung_fuer_das_skript(org):
    input_ = field(profile(org.erika))

    assert _attr(input_, "data-hoechstens") == str(SCOUT_NAME_MAX_LENGTH) == "30"
    assert _attr(input_, "data-zu-lang") == TOO_LONG
    # Keine harte Sperre: Der Browser schnitte beim Einfügen still ab (Entscheidung vom 26.10.2026 zu #111).
    assert _attr(input_, "maxlength") is None


def test_unter_der_eingabe_steht_die_leere_versteckte_stelle_fuer_die_zahl(org):
    """Ohne Skript keine Zahl (Szenario 14): Die Stelle ist versteckt und leer, bis das Skript sie füllt."""
    root = profile(org.erika)
    box = _one(_all(main(root), lambda e: _attr(e, "data-antippfeld") is not None))
    count = counter(box)

    assert _attr(count, "id") == COUNTER_ID
    assert _attr(count, "hidden") == ""
    assert _text(count) == ""
    # Nicht bei jedem Tastendruck ansagen (Szenario 13): keine Live-Region.
    assert _attr(count, "aria-live") is None
    assert _attr(count, "role") is None
    # Unter der Eingabe, vor den Knöpfen „Verwerfen“ und „Speichern“.
    children = [c for c in box.children if not isinstance(c, str)]
    names = ["gruppe" if "a-antippfeld-gruppe" in _classes(c) else "zahl" if c is count
             else "knoepfe" if "a-antippfeld-knoepfe" in _classes(c) else None for c in children]
    assert [n for n in names if n] == ["gruppe", "zahl", "knoepfe"]


def test_die_zahl_ist_mit_der_eingabe_verknuepft_und_wird_beim_betreten_vorgelesen(org):
    assert described_by(field(profile(org.erika))) == [COUNTER_ID]


# Szenario 8: zu lang gespeichert; das Feld kommt offen mit Text, Meldung und Zahl zurück


def test_zu_lang_gespeichert_bleiben_fehler_und_zahl_mit_der_eingabe_verknuepft(org):
    client = test_fahrtenname.client_for(org.erika)
    response = client.post(test_fahrtenname.SAVE, {"scout_name": "K" * 31})
    root = _tree(response)
    input_ = field(root)

    assert stored(org.erika) == ""
    assert _attr(input_, "value") == "K" * 31
    assert _attr(input_, "aria-invalid") == "true"
    assert described_by(input_) == [ERROR_ID, COUNTER_ID]
    assert _text(_one(_all(main(root), lambda e: _attr(e, "id") == ERROR_ID))) == TOO_LONG
    # Die Zahl steht über der Meldung „zu lang“, wie beim Tippen.
    box = _one(_all(main(root), lambda e: _attr(e, "data-antippfeld") is not None))
    order = [_attr(c, "id") for c in box.children if not isinstance(c, str) and _attr(c, "id")]
    assert order.index(COUNTER_ID) < order.index(ERROR_ID)


# Szenarien 4, 9 und 10: gezählt wird wie auf dem Server; die Zahl im Browser zählt genauso (Rauchtest)


@pytest.mark.parametrize("value", ["K" * 30, "  " + "K" * 30 + " ", "K" * 29 + "🥝"])
def test_genau_dreissig_zeichen_werden_gespeichert(org, value):
    save(org.erika, value)

    assert stored(org.erika) == value.strip()


# Szenario 15: das Suchfeld beim Benennen hat keine Zahl


def _render(form, name: str, **options) -> str:
    tag = " ".join([f"form.{name}"] + [f"{key}={key}" for key in options])
    return Template("{% load layout %}{% textfeld " + tag + " %}").render(Context({"form": form, **options}))


def test_das_suchfeld_hat_keine_zahl():
    html = _render(AccountSearchForm(), "suche", button="Suchen", help_text="Ab drei Zeichen.")

    assert "a-zeichenzahl" not in html
    assert "data-hoechstens" not in html


# „Wo“ im Issue: auch der Baustein Textfeld zeigt die Zahl, wenn das Formular eine Grenze festlegt


class _LimitedForm(forms.Form):
    """Erfundenes Feld mit fachlicher Grenze, nur für diesen Test."""

    motto = forms.CharField(label="Motto", widget=forms.TextInput(attrs={"data-hoechstens": 12,
                                                                          "data-zu-lang": "Höchstens 12."}))


def test_das_textfeld_zeigt_die_zahl_wenn_das_feld_eine_grenze_hat():
    root = parse_html(_render(_LimitedForm(), "motto", help_text="Kurz und knapp."))
    input_ = _one(_by_tag(root, "input"))
    count = counter(root)

    assert _attr(count, "id") == "id_motto-zahl"
    assert _attr(count, "hidden") == ""
    assert described_by(input_) == ["id_motto-hilfe", "id_motto-zahl"]


def test_das_textfeld_mit_fehler_verknuepft_fehler_und_zahl():
    form = _LimitedForm(data={"motto": ""})
    form.is_valid()
    input_ = _one(_by_tag(parse_html(_render(form, "motto")), "input"))

    assert described_by(input_) == ["id_motto-fehler", "id_motto-zahl"]


def test_ein_textfeld_ohne_grenze_hat_keine_zahl():
    form = _LimitedForm()
    form.fields["motto"].widget.attrs = {}

    assert "a-zeichenzahl" not in _render(form, "motto")


# Szenario 16: der Bausteinkatalog


@pytest.mark.bausteinkatalog
def test_der_katalog_zeigt_das_feld_zum_antippen_mit_der_stelle_fuer_die_zahl(settings):
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = _tree(_client_for(build_org().erika).get(CATALOG))

    section = _section(root, "h-antippfeld")
    assert _attr(counter(section), "id") == "katalog_scout_name-zahl"


@pytest.mark.bausteinkatalog
def test_der_katalog_nennt_die_zahl_beim_textfeld(settings):
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = _tree(_client_for(build_org().erika).get(CATALOG))

    purpose = _text(_one(_all(_section(root, "h-textfeld"), lambda e: "a-baustein-zweck" in _classes(e))))
    assert "fachliche Grenze" in purpose
    assert "„12/30“" in purpose
