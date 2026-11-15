"""Tests für den Knopf „Person aufnehmen“ und die Wahl im Dialog (#298, PER-01, PER-02).

Die Kennungen PA1 bis PA9, PV1 bis PV3, PG1, PG2 und U1 bis U5 verweisen auf die Szenarien vom 14.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/298#issuecomment-6875044923), die Wortlaute
auf den Text von #298. Personen und Organisationen wie in den Tests zu #117 (`tests/test_verwaltete_personen.py`):
Wanda leitet Stamm Walhall, Fiete die Sippe Falken, Wim die Meute Wölfe, Zora die Zugvögel, Bruno den
Pfadfinderbund Boreas; Finn ist Mitglied der Falken, Otto hat ein Konto ohne Zuordnung, Vera ist Verbandsleitung,
Tom im DPV-Veranstaltungsteam, Max Admin. Alle Namen sind erfunden. Was nur ein Browser zeigt (Fokus, Handy, ohne
Skript, nur mit der Tastatur, PA9), prüft `rauchtests/test_person_aufnehmen.py`.
"""

import hashlib
import re
from pathlib import Path

import pytest

from core.sections import to_section
from persons.models import ManagedPerson
from roles.models import Role
from tests import test_verwaltete_personen
from tests.test_benennen import dialog_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_personen import admit, admit_address, find, membership_of, persons_section, search_address
from tests.test_rechtepruefung import remove
from tests.test_rollen import give, person, unit
from tests.test_verwaltete_personen import LENA, add, add_address, head_buttons, open_add
from units.models import Kind as U

R = Role.Kind
pytestmark = pytest.mark.django_db

# Die Fixtures aus tests/test_verwaltete_personen.py unter eigenem Namen, mit allem, worauf sie aufbauen.
base_org = test_verwaltete_personen.base_org
org_189 = test_verwaltete_personen.org_189
org_190 = test_verwaltete_personen.org_190
org_285 = test_verwaltete_personen.org_285
org = test_verwaltete_personen.org

ADMIT_TEXT = "Für Personen, die sich schon einmal mit ihrem DPV-Konto im Tool angemeldet haben."
ADD_TEXT = "Für Personen ohne eigenes Konto, meist Kinder und Jugendliche. Ihre Angaben pflegt die Leitung."
FIRST = "Dieser Organisation sind noch keine Personen zugeordnet."
SECOND = "Mit „Person aufnehmen“ oben kannst du eine Person mit Konto aufnehmen oder eine verwaltete Person anlegen."


def choice_address(where) -> str:
    """Die eigene Adresse des Dialogs „Person aufnehmen“ mit der Wahl (Technische Wahl im Protokoll der Klärung)."""
    return f"{unit_address(where)}person-aufnehmen/"


def back_to_button(where) -> str:
    """Wohin × und „Abbrechen“ führen: zur Seite, mit der Kennung des Knopfs „Person aufnehmen“ (PA7)."""
    return f"{unit_address(where)}#person-aufnehmen"


def tiles(dialog) -> list[dict]:
    """Die großen Flächen der Wahl in ihrer Reihenfolge: Titel, Satz, Adresse und ob sie den Fokus bekommt."""
    found = []
    for link in _all(dialog, lambda e: "a-wahlflaeche" in _classes(e) and e.name == "a"):
        found.append({
            "title": _visible_text(_one(_by_tag(link, "strong"))),
            "text": _visible_text(_one(_all(link, lambda e: "a-wahlflaeche-satz" in _classes(e)))),
            "href": _attr(link, "href"),
            "autofocus": _attr(link, "autofocus") is not None,
        })
    return found


def bottom_links(dialog) -> dict[str, str]:
    """Die Knöpfe unten im Dialog mit ihren Adressen, etwa „Zurück“ oder „Abbrechen“."""
    foot = _one(_all(dialog, lambda e: "a-dialog-fuss" in _classes(e)))
    return {_visible_text(link): _attr(link, "href") for link in _by_tag(foot, "a")}


def close_link(dialog) -> str:
    return _attr(_one(_all(dialog, lambda e: "a-schliessen" in _classes(e))), "href")


def open_choice(user, where, client=None):
    """Öffnet den Dialog „Person aufnehmen“; gibt die ganze Seite zurück."""
    response = (client or client_for(user)).get(choice_address(where))
    assert response.status_code == 200
    return _tree(response)


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("PK-17", "VP-01")
def test_pa1_fiete_sieht_im_kopf_nur_den_knopf_person_aufnehmen(org):
    root = page_tree(org.falken_leitung, unit_address(org.falken))

    assert head_buttons(root) == {"Person aufnehmen": to_section(choice_address(org.falken), "personen")}
    button = _one(_all(persons_section(root), lambda e: "a-flaeche-aktion" in _classes(e)))
    # Im Aussehen des heutigen Hauptknopfs, mit der Kennung, zu der die Dialoge zurückführen (PA7).
    assert "btn-primary" in _classes(button)
    assert _attr(button, "id") == "person-aufnehmen"
    text = _visible_text(persons_section(root))
    assert "Verwaltete Person anlegen" not in text
    assert "Person mit Konto aufnehmen" not in text


def test_pa2_die_wahl_hat_zwei_grosse_flaechen_nichts_vorgewaehlt(org):
    root = open_choice(org.falken_leitung, org.falken)
    found = dialog_of(root)

    assert _text(_one(_by_tag(found, "h2"))) == "Person aufnehmen"
    assert "in Sippe Falken" in _visible_text(found)
    assert tiles(found) == [
        {"title": "Person mit Konto aufnehmen", "text": ADMIT_TEXT,
         "href": to_section(admit_address(org.falken), "personen"), "autofocus": True},
        {"title": "Verwaltete Person anlegen", "text": ADD_TEXT,
         "href": to_section(add_address(org.falken), "personen"), "autofocus": False},
    ]
    # Nichts ist vorgewählt: keine Optionsfelder, kein Formular, ein Tipp führt direkt zum Weg.
    assert _by_tag(found, "input") == []
    assert _by_tag(found, "form") == []
    # Unten „Abbrechen“ zur Seite wie in jedem Dialog (Nachklärung N4), × ebenso.
    assert bottom_links(found) == {"Abbrechen": back_to_button(org.falken)}
    assert close_link(found) == back_to_button(org.falken)
    # Die Seite unter dem Dialog ist die Seite der Falken.
    assert persons_section(root) is not None


@pytest.mark.rechtematrix("PK-17")
def test_pa3_obere_flaeche_fuehrt_zum_aufnehmen_wie_heute(org):
    client = client_for(org.falken_leitung)
    upper = tiles(dialog_of(open_choice(org.falken_leitung, org.falken, client=client)))[0]["href"]

    shown = dialog_of(_tree(client.get(upper.split("#")[0])))
    assert _text(_one(_by_tag(shown, "h2"))) == "Person mit Konto aufnehmen"
    assert "Otto Ohne" in _visible_text(find(org.falken_leitung, org.falken, "otto.ohne@example.org", client=client))
    response = admit(org.falken_leitung, org.falken, org.ohne, client=client)

    assert response.status_code == 302
    assert response.url == back_to_button(org.falken)
    assert membership_of(org.ohne) == "Sippe Falken"
    assert short_notices(client.get(response.url)) == ["Otto Ohne gehört jetzt zu Sippe Falken."]


@pytest.mark.rechtematrix("VP-01")
def test_pa4_untere_flaeche_fuehrt_zum_anlegen_wie_heute(org):
    client = client_for(org.falken_leitung)
    lower = tiles(dialog_of(open_choice(org.falken_leitung, org.falken, client=client)))[1]["href"]

    shown = dialog_of(_tree(client.get(lower.split("#")[0])))
    assert _text(_one(_by_tag(shown, "h2"))) == "Verwaltete Person anlegen"
    response = add(org.falken_leitung, org.falken, client=client)

    assert response.status_code == 302
    assert response.url == back_to_button(org.falken)
    assert ManagedPerson.objects.get(first_name="Lena").unit_id == org.falken.pk
    assert short_notices(client.get(response.url)) == ["Kiwi (Lena Probe) gehört jetzt zu Sippe Falken."]


@pytest.mark.rechtematrix("EH-18", "PK-17", "VP-01")
def test_pa5_ohne_gruppenleitung_springt_wanda_in_den_woelfen_ein(org):
    remove(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)
    client = client_for(org.walhall_leitung)

    root = page_tree(org.walhall_leitung, unit_address(org.woelfe))
    assert head_buttons(root) == {"Person aufnehmen": to_section(choice_address(org.woelfe), "personen")}
    found = tiles(dialog_of(open_choice(org.walhall_leitung, org.woelfe, client=client)))
    for tile in found:
        assert client.get(tile["href"].split("#")[0]).status_code == 200, tile["title"]

    assert admit(org.walhall_leitung, org.woelfe, org.ohne, client=client).status_code == 302
    assert add(org.walhall_leitung, org.woelfe, client=client).status_code == 302
    assert membership_of(org.ohne) == "Meute Wölfe"
    assert ManagedPerson.objects.get(first_name="Lena").unit_id == org.woelfe.pk


def test_pa7_in_beiden_wegen_fuehrt_zurueck_zur_wahl_und_schliessen_zum_knopf(org):
    client = client_for(org.falken_leitung)
    choice = to_section(choice_address(org.falken), "personen")
    shown = {
        "aufnehmen": dialog_of(_tree(client.get(admit_address(org.falken)))),
        "nach der Suche": find(org.falken_leitung, org.falken, "otto.ohne@example.org", client=client),
        "anlegen": open_add(org.falken_leitung, org.falken, client=client)[0],
    }
    for way, found in shown.items():
        assert bottom_links(found) == {"Zurück": choice}, way
        assert close_link(found) == back_to_button(org.falken), way
        # × und Escape führen über die Adresse des Dialogs zur Seite, mit der Kennung des Knopfs.
        assert _attr(found, "data-schliessen") == back_to_button(org.falken), way


def test_pa7_auch_ein_abgelehntes_anlegen_behaelt_zurueck(org):
    client = client_for(org.falken_leitung)
    _found, creation_key = open_add(org.falken_leitung, org.falken, client=client)

    response = client.post(add_address(org.falken), {**LENA, "first_name": "", "creation_key": creation_key})

    found = dialog_of(_tree(response))
    assert "Bitte gib den Vornamen ein." in _visible_text(found)
    assert bottom_links(found)["Zurück"] == to_section(choice_address(org.falken), "personen")


def test_u5_der_dialog_benennen_behaelt_abbrechen(org):
    found = dialog_of(_tree(client_for(org.falken_leitung).get(f"{unit_address(org.falken)}benennen/")))

    assert list(bottom_links(found)) == ["Abbrechen"]


def test_pa8_leere_liste_nennt_person_aufnehmen_nur_fuer_wer_dort_aufnehmen_darf(org):
    eulen = unit(U.GROUP, "Sippe Eulen", org.walhall)
    kraniche = unit(U.GROUP, "Sippe Kraniche", org.walhall)
    kira = person("kira.kranich", "Kira", "Kranich")
    give(kira, R.MEMBER, org.walhall)
    give(kira, R.GROUP_LEAD, kraniche)

    for user, where in [(org.walhall_leitung, eulen), (kira, kraniche)]:
        text = _visible_text(persons_section(page_tree(user, unit_address(where))))
        assert f"{FIRST} {SECOND}" in text, (user.username, where.name)
    for user, where in [(org.walhall_leitung, kraniche), (org.bundesleitung, eulen)]:
        text = _visible_text(persons_section(page_tree(user, unit_address(where))))
        assert FIRST in text and SECOND not in text, (user.username, where.name)
        assert "Du kannst oben" not in text


# ---------- Verboten ----------


@pytest.mark.rechtematrix("PK-26", "VP-17")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/person-aufnehmen/")
def test_pv1_wanda_auf_den_falken_und_bruno_auf_walhall_bekommen_nicht_gefunden(org):
    for user, where in [(org.walhall_leitung, org.falken), (org.bundesleitung, org.walhall)]:
        assert head_buttons(page_tree(user, unit_address(where))) == {}, user.username
        assert_like_missing(user, choice_address(where))
        # Auch eine Anfrage aus dem Skript oder ein Formular kommt nicht weiter.
        assert client_for(user).post(choice_address(where), {}).status_code == 404


@pytest.mark.rechtematrix("PK-23", "VP-06")
def test_pv2_ohne_leitungsrolle_kein_knopf_und_keine_wahl(org):
    for user in (org.falke, org.ohne, org.verbandsleitung, org.team, org.max):
        for where in (org.walhall, org.falken, org.boreas):
            assert_like_missing(user, choice_address(where))
            assert client_for(user).post(choice_address(where), {}).status_code == 404
    # Finn sieht die Seite der Falken nur zum Lesen, ohne Abschnitt „Personen“ und ohne Knopf.
    assert "person-aufnehmen" not in client_for(org.falke).get(unit_address(org.falken)).content.decode()


def test_pv3_zora_erfaehrt_nicht_ob_es_die_falken_gibt(org):
    assert_like_missing(org.zugvoegel_leitung, choice_address(org.falken))


# ---------- Grenzfälle ----------


@pytest.mark.rechtematrix("VP-17", "PK-26")
def test_pg1_mit_neuer_gruppenleitung_fuehrt_die_offene_wahl_ins_leere(org):
    remove(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)
    client = client_for(org.walhall_leitung)
    found = tiles(dialog_of(open_choice(org.walhall_leitung, org.woelfe, client=client)))

    give(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)

    for tile in found:
        assert client.get(tile["href"].split("#")[0]).status_code == 404, tile["title"]
    assert admit(org.walhall_leitung, org.woelfe, org.ohne, client=client).status_code == 404
    response = client.post(add_address(org.woelfe), {**LENA, "consent": "an", "creation_key": "c" * 20})
    assert response.status_code == 404
    assert membership_of(org.ohne) is None
    assert not ManagedPerson.objects.filter(first_name="Lena").exists()


def test_pg2_die_bisherigen_adressen_gehen_weiter_und_zurueck_fuehrt_zur_wahl(org):
    client = client_for(org.falken_leitung)
    choice = to_section(choice_address(org.falken), "personen")

    for address, title in ((admit_address(org.falken), "Person mit Konto aufnehmen"),
                           (add_address(org.falken), "Verwaltete Person anlegen")):
        response = client.get(address)
        assert response.status_code == 200, address
        found = dialog_of(_tree(response))
        assert _text(_one(_by_tag(found, "h2"))) == title
        assert bottom_links(found) == {"Zurück": choice}
    # Lesend führt die Adresse der Suche wie bisher zum leeren Dialog.
    assert client.get(search_address(org.falken)).url == admit_address(org.falken)


def test_die_wahl_steht_nur_auf_der_seite_der_eigenen_organisation_und_die_organisation_kommt_aus_der_adresse(org):
    """Die Flächen führen in die Organisation der Adresse; die Wahl nimmt keine Organisation aus einem Parameter."""
    found = tiles(dialog_of(_tree(client_for(org.walhall_leitung).get(
        f"{choice_address(org.walhall)}?unit={org.falken.key}"))))

    assert [tile["href"].split("#")[0] for tile in found] == [admit_address(org.walhall), add_address(org.walhall)]



# ---------- Zielbild ----------

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "docs" / "zielbilder" / "person-aufnehmen.html"
CHECKSUM = "1a9d7d68b79aa79ce5234d341a5c5509a5a139235439b7c39957f923111be547"


def test_zielbild_liegt_unveraendert_mit_eintrag_im_repo():
    readme = (ROOT / "docs" / "zielbilder" / "README.md").read_text()

    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == CHECKSUM
    section = readme.split("## Person aufnehmen", 1)
    assert len(section) == 2
    for must in (CHECKSUM, "14.11.2026", "Orientierung, keine Anforderung", "Abweichungen", "#298"):
        assert must in section[1].split("\n## ", 1)[0], must


def test_zielbild_laedt_nichts_von_fremden_servern():
    content = TARGET.read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert all(mail.endswith("@example.org") for mail in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", content))
