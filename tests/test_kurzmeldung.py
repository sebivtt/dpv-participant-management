"""Tests für kurze Meldungen und Fehlermeldungen an der Stelle der Handlung (#186, docs/gestaltung.md, NFA-03).

Die Nummern verweisen auf Sebastians „Szenarien (27.10.2026)“ in #186. Hier steht, was der
Server ausliefert: welche Meldung kurz wird, wo die Fehlermeldung steht, der Bereich für kurze
Meldungen und der Eintrag im Bausteinkatalog. Erscheinen, Verschwinden, Stapel, Lage, Maus,
Tastatur und „Bewegung reduzieren“ kann nur ein echter Browser zeigen; das prüft
rauchtests/test_kurzmeldung.py. Alle Namen sind erfunden.
"""

import hashlib
import re
from datetime import timedelta
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import DatabaseError
from django.template import Context, Template
from django.test.html import parse_html
from django.utils import timezone

from tests import test_fahrtenname
from tests.keycloak_fake import RETURN, keycloak_parameters, login, start_login
from tests.test_fahrtenname import DELETED, FAILED, SAVED, TOO_LONG, client_for, field, profile, save
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _tree, _visible_text
from tests.test_mein_profil import main, raw_text
from tests.test_meldungen import HINT_CANCELLED, HINT_EXPIRED, HINT_NAME, HINT_NO_ORG_BOLD, HINT_UNREACHABLE
from tests.test_rollen import build_org

pytestmark = pytest.mark.django_db

ROOT = Path(__file__).resolve().parent.parent
CLOSE = "Meldung schließen"


@pytest.fixture
def org():
    """Dieselben erfundenen Personen wie in tests/test_fahrtenname.py."""
    return test_fahrtenname.org.__wrapped__()


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def short_notices(root) -> list:
    """Meldungen, die das Skript als kurze Meldung unten einblendet."""
    return _all(root, lambda e: _attr(e, "data-kurz") is not None)


def region(root):
    """Der Bereich, in dem kurze Meldungen erscheinen und angesagt werden."""
    return _all(root, lambda e: _attr(e, "id") == "kurzmeldungen")


def close_button(notice):
    return _one(_all(notice, lambda e: e.name == "button" and "a-kurz-zu" in _classes(e)))


def render(source: str):
    """Rendert einen Baustein für sich, in einem Rahmen, damit die Suche ihn selbst mitzählt."""
    return parse_html("<div>" + Template("{% load layout %}" + source).render(Context()) + "</div>")


# ---------- Szenarien 1 bis 3: nach dem Speichern eine kurze Meldung ----------


@pytest.mark.parametrize("value, text", [("Kiwi", SAVED), ("", DELETED)])
def test_nach_dem_speichern_eine_kurze_erfolgsmeldung_mit_kreuz(org, value, text):
    client = client_for(org.erika)
    save(org.erika, "Falkenflug", client=client)
    client.get("/profil/")

    save(org.erika, value, client=client)
    root = profile(org.erika, client=client)

    notice = _one(short_notices(main(root)))
    assert {"a-meldung", "ist-erfolg"} <= set(_classes(notice))
    assert _clean(_visible_text(notice)) == text
    # Szenario 3: Vorleseprogramme hören „Erfolg:“ vorweg.
    assert _clean(raw_text(_one(_all(notice, lambda e: "sr-nur" in _classes(e) and e.name == "span")))) == "Erfolg:"
    # Das × zeigt erst das Skript; ohne Skript bleibt die Meldung fest oben ohne × (Szenario 17).
    close = close_button(notice)
    assert _attr(close, "type") == "button"
    assert _attr(close, "hidden") is not None
    assert _attr(close, "aria-label") == CLOSE
    # Es bleibt die einzige Meldung dieser Art auf der Seite.
    assert len(_all(main(root), lambda e: "ist-erfolg" in _classes(e))) == 1


def test_ohne_skript_steht_die_kurze_meldung_fest_oben_vor_den_angaben(org):
    """Szenario 17: ohne Skript wie bisher oben auf der Seite, angesagt wie nach einer Handlung."""
    client = client_for(org.erika)
    save(org.erika, "Kiwi", client=client)
    root = profile(org.erika, client=client)

    notice = _one(short_notices(main(root)))
    assert _attr(notice, "role") == "status"
    sections = _by_tag(main(root), "section")
    order = [e for e in _all(main(root), lambda e: e is notice or e is sections[0])]
    assert order == [notice, sections[0]]


@pytest.mark.bausteinkatalog
@pytest.mark.parametrize("address", ["/", "/profil/", "/bausteine/"])
def test_jede_seite_mit_login_hat_den_bereich_fuer_kurze_meldungen(org, address, settings):
    """Szenario 3: Der Bereich ist leer da, damit Vorleseprogramme neue Meldungen darin ansagen."""
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = _tree(client_for(org.erika).get(address))

    area = _one(region(root))
    assert _attr(area, "role") == "status"
    assert _attr(area, "aria-live") == "polite"
    # Jede neue Meldung allein ansagen, nicht den ganzen Stapel noch einmal.
    assert _attr(area, "aria-atomic") == "false"
    assert "a-kurz-bereich" in _classes(area)
    assert _clean(_visible_text(area)) == ""


def test_erfolgsmeldung_erscheint_nur_einmal(org):
    """Szenario 7: nach dem Neuladen keine Meldung mehr."""
    client = client_for(org.erika)
    save(org.erika, "Kiwi", client=client)
    profile(org.erika, client=client)

    assert short_notices(main(profile(org.erika, client=client))) == []


# ---------- Szenarien 8 und 8a: Fehlermeldung direkt unter dem Feld ----------


def _failing_save(org, monkeypatch, value="Kiwi"):
    client = client_for(org.erika)  # Der Login speichert selbst; erst danach fällt die Datenbank aus.

    def fail(self, *args, **kwargs):
        raise DatabaseError("Datenbank weg")

    monkeypatch.setattr(get_user_model(), "save", fail)
    return client, _tree(save(org.erika, value, client=client))


def _box(root):
    return _one(_all(main(root), lambda e: _attr(e, "data-antippfeld") is not None))


def test_speichern_scheitert_fehlermeldung_direkt_unter_dem_feld(org, monkeypatch):
    _, root = _failing_save(org, monkeypatch)

    box = _box(root)
    errors = _all(main(root), lambda e: "ist-fehler" in _classes(e))
    notice = _one(errors)
    assert _clean(_visible_text(notice)) == FAILED
    # In der Kachel des Felds, direkt unter der Eingabe, nicht oben auf der Seite. Dazwischen steht nur die
    # Zahl der Zeichen, die zur Eingabe gehört (#215).
    children = [c for c in box.children if not isinstance(c, str) and "a-zeichenzahl" not in _classes(c)]
    group = next(i for i, c in enumerate(children) if "a-antippfeld-gruppe" in _classes(c))
    assert children[group + 1] is notice
    # Sofort angesagt, nie kurz; mit dem Feld verknüpft, damit es beim Fokus vorgelesen wird.
    assert _attr(notice, "role") == "alert"
    assert _attr(notice, "data-kurz") is None
    assert _attr(notice, "id") in (_attr(field(root), "aria-describedby") or "").split()
    # Das Feld bleibt offen mit der Eingabe.
    assert _attr(box, "data-offen") is not None
    assert _attr(field(root), "value") == "Kiwi"
    assert short_notices(main(root)) == []


def test_danach_klappt_das_speichern_fehlermeldung_weg_und_kurze_meldung(org, monkeypatch):
    client, _ = _failing_save(org, monkeypatch)
    monkeypatch.undo()

    save(org.erika, "Kiwi", client=client)
    root = profile(org.erika, client=client)

    assert _all(main(root), lambda e: "ist-fehler" in _classes(e)) == []
    assert _clean(_visible_text(_one(short_notices(main(root))))) == SAVED
    assert _attr(_box(root), "data-offen") is None


def test_gegenprobe_ohne_fehler_ist_das_feld_mit_keiner_meldung_verknuepft(org):
    root = profile(org.erika)

    # Verknüpft ist nur die Zahl der Zeichen (#215).
    assert _attr(field(root), "aria-describedby") == "id_scout_name-zahl"
    assert _all(_box(root), lambda e: "a-meldung" in _classes(e)) == []


# ---------- Szenarien 9 bis 11: feste Meldungen bleiben fest ----------


def test_zu_lang_fehler_am_feld_wie_bisher_und_keine_kurze_meldung(org):
    """Szenario 9."""
    root = _tree(save(org.erika, "K" * 51))

    assert short_notices(main(root)) == []
    assert _clean(_visible_text(_one(_all(_box(root), lambda e: "invalid-feedback" in _classes(e))))) == TOO_LONG
    assert _all(main(root), lambda e: "a-meldung" in _classes(e) and "ist-fehler" in _classes(e)) == []


def test_hinweise_zu_einem_zustand_bleiben_fest(settings):
    """Szenario 10: Max ohne Namen und ohne Organisation."""
    people = build_org()
    people.max.first_name = ""
    people.max.save()
    for address in ("/", "/profil/"):
        root = _tree(client_for(people.max).get(address))
        texts = [_clean(_visible_text(n)) for n in _all(main(root), lambda e: "a-meldung" in _classes(e))]
        assert any(HINT_NAME in t for t in texts), address
        assert any(HINT_NO_ORG_BOLD in t for t in texts), address
        assert short_notices(main(root)) == []


def _login_page_with(client, case, keycloak):
    """Die Login-Seite mit einer ihrer drei Meldungen nach einer Handlung."""
    if case == "abgebrochen":
        state = keycloak_parameters(start_login(client))["state"]
        client.get(RETURN, {"state": state, "error": "access_denied"})
        expected = HINT_CANCELLED
    elif case == "nicht erreichbar":
        keycloak.unreachable = True
        start_login(client)
        expected = HINT_UNREACHABLE
    else:
        login(client)
        Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))
        return _tree(client.get("/", follow=True)), HINT_EXPIRED
    return _tree(client.get("/anmelden/")), expected


@pytest.mark.parametrize("case", ["abgebrochen", "nicht erreichbar", "abgelaufen"])
def test_login_seite_meldungen_bleiben_fest_ueber_dem_knopf(client, keycloak, case):
    """Szenario 11: keine kurzen Meldungen und kein Bereich dafür auf der Login-Seite."""
    root, expected = _login_page_with(client, case, keycloak)

    notice = _one([n for n in _all(root, lambda e: "a-meldung" in _classes(e)) if expected in _clean(_visible_text(n))])
    assert _attr(notice, "data-kurz") is None
    assert _all(notice, lambda e: e.name == "button") == []
    assert region(root) == []
    assert short_notices(root) == []


# ---------- Regel: Fehler und Warnungen werden nie kurz ----------


@pytest.mark.parametrize("kind, role", [("warning", "alert"), ("error", "alert")])
def test_fehler_und_warnungen_werden_nie_kurz(kind, role):
    root = render(f'{{% kurzmeldung "{kind}" text="Etwas ist los." %}}')

    notice = _one(_all(root, lambda e: "a-meldung" in _classes(e)))
    assert _attr(notice, "data-kurz") is None
    assert _attr(notice, "role") == role
    assert _all(notice, lambda e: e.name == "button") == []


@pytest.mark.parametrize("kind, prefix", [("success", "Erfolg:"), ("info", "Information:")])
def test_erfolg_und_information_werden_kurz(kind, prefix):
    root = render(f'{{% kurzmeldung "{kind}" text="Etwas hat geklappt." %}}')

    notice = _one(_all(root, lambda e: "a-meldung" in _classes(e)))
    assert _attr(notice, "data-kurz") is not None
    assert _attr(notice, "role") == "status"
    assert prefix in raw_text(notice)
    assert _attr(close_button(notice), "aria-label") == CLOSE


def test_text_der_kurzen_meldung_erscheint_als_gewoehnlicher_text():
    html = Template("{% load layout %}{% kurzmeldung 'success' text=text %}").render(Context({"text": "<b>Kiwi</b>"}))

    assert "<b>Kiwi</b>" not in html
    assert "&lt;b&gt;Kiwi&lt;/b&gt;" in html


# ---------- Szenario 18: Bausteinkatalog und Doku ----------


@pytest.mark.bausteinkatalog
def test_katalog_zeigt_die_kurze_meldung_mit_erfolg_information_und_stapel(org, settings):
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = _tree(client_for(org.erika).get("/bausteine/"))

    section = _one(_by_tag(root, "section", aria_labelledby="h-kurzmeldung"))
    assert _clean(_visible_text(_one(_by_tag(section, "h2")))) == "Kurze Meldung"
    # Die Beispiele stehen als Vorlagen bereit; das Skript blendet sie mit den Knöpfen unten ein.
    templates = _by_tag(section, "template")
    kinds = []
    for template in templates:
        for notice in _all(template, lambda e: "a-meldung" in _classes(e)):
            assert _attr(notice, "data-kurz") is not None
            kinds.append(next(c for c in _classes(notice) if c.startswith("ist-")))
    assert {"ist-erfolg", "ist-info"} == set(kinds)
    demo = _all(section, lambda e: _attr(e, "data-kurz-zeigen") is not None)
    assert [_clean(_visible_text(b)) for b in demo] == ["Erfolg zeigen", "Information zeigen", "Vier nacheinander zeigen"]
    for button in demo:
        assert button.name == "button" and _attr(button, "type") == "button"
        targets = _attr(button, "data-kurz-zeigen").split()
        assert targets and all(any(_attr(t, "id") == target for t in templates) for target in targets)
    stack = _attr(demo[2], "data-kurz-zeigen").split()
    assert len(stack) == 4


def test_katalog_nennt_mein_profil_als_seite_der_kurzen_meldung():
    from core.views import BUILDING_BLOCKS

    block = BUILDING_BLOCKS["kurzmeldung"]
    assert block["template"] == "core/_kurzmeldung.html"
    assert block["issues"] == [186]
    assert [str(p) for p in block["pages"]] == ["Mein Profil"]


def test_kurze_meldung_hat_einen_deutlichen_schatten_und_keinen_zeitbalken():
    """Lage, Schatten und × machen die kurze Form ohne Farbe erkennbar; keine Zeitleiste (#186, Frage 5)."""
    css = (ROOT / "core" / "static" / "core" / "app.css").read_text()

    rule = re.search(r"\.a-kurz \{([^}]*)\}", css)
    assert rule and "box-shadow" in rule.group(1)
    assert "a-kurz-zeit" not in css and "progress" not in css
    # Der Bereich bleibt für Vorleseprogramme da, auch leer; sonst sagen sie die erste Meldung oft nicht an.
    assert not re.search(r"\.a-kurz-bereich:empty", css)
    # Ein- und Ausblenden nur, wenn im Gerät „Bewegung reduzieren“ aus ist.
    motion = css.split("@media (prefers-reduced-motion: no-preference)")
    assert any("a-kurz" in part.split("\n}\n", 1)[0] for part in motion[1:])


def test_regel_steht_in_der_gestaltung_und_in_den_entscheidungen():
    design = (ROOT / "docs" / "gestaltung.md").read_text()
    decisions = (ROOT / "docs" / "entscheidungen.md").read_text()

    section = design.split("### Kurze Meldungen", 1)
    assert len(section) == 2, "Abschnitt „Kurze Meldungen“ fehlt in docs/gestaltung.md"
    text = section[1].split("\n### ", 1)[0]
    for must in ("#186", "eigene Handlung", "6 Sekunden", "an der Stelle", "Schatten", "Login-Seite"):
        assert must in text, must
    assert "kaum Schatten" in design and "#186" in design.split("kaum Schatten", 1)[1].split("\n", 1)[0]
    entry = decisions.split("(#186)", 1)
    assert len(entry) == 2, "Eintrag zu #186 fehlt in docs/entscheidungen.md"


# ---------- Zielbild ----------

TARGET = ROOT / "docs" / "zielbilder" / "kurze-meldungen.html"
CHECKSUM = "4b0ae4ad11e369f4043011234afe30f6fed0dfd9323b8c9cb14aa0429629e7e1"


def test_zielbild_liegt_unveraendert_mit_eintrag_im_repo():
    readme = (ROOT / "docs" / "zielbilder" / "README.md").read_text()

    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == CHECKSUM
    section = readme.split("## Kurze Meldungen", 1)
    assert len(section) == 2
    for must in (CHECKSUM, "27.10.2026", "Orientierung, keine Anforderung", "Abweichungen", "#186"):
        assert must in section[1], must


def test_zielbild_laedt_nichts_von_fremden_servern():
    content = TARGET.read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", content)) == {"erika@beispiel.invalid"}
