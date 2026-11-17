"""Seite springt nicht, wenn ein Dialog aufgeht (#220): was der Server dazu beiträgt.

Mit Skript merkt sich die Seite selbst, wie weit sie gerollt war; das prüft der Rauchtest
(rauchtests/test_stelle_merken.py). Ohne Skript springen Öffnen, Schließen und Speichern zum
Abschnitt der Seite, in dem der Knopf steht, der den Dialog geöffnet hat; die Sprungmarke steht in der
Adresse. Der Rauchtest prüft das an „Entfernen“ (S12) und „Bearbeiten“ (S13). Hier steht dazu je Dialog
mit eigener Adresse, ob seine Adressen die richtige Sprungmarke tragen: Ein einziger vergessener
Dialog spränge sonst ohne Skript nach oben. Die Nummern verweisen auf die Szenarien vom 14.11.2026 in
#220. Alle Personen sind erfunden.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from access.rights import Rights
from persons.models import DisplayedLead, ManagedPerson
from roles.models import Role
from tests.test_benennen import dialog_of
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _tree, _visible_text
from tests.test_organisation import client_for, unit_address
from tests.test_rollen import give, person, unit
from tests.test_veranstaltungen import event_of
from units.models import Unit

R = Role.Kind
U = Unit.Kind


@pytest.fixture
def org(db) -> SimpleNamespace:
    """Walhall mit Wanda als Stammesleitung, Lea als zweiter, Mia als Mitglied und Paul ohne Konto; dazu der Verband."""
    o = SimpleNamespace()
    o.dpv = unit(U.FEDERATION, "DPV")
    o.boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", o.dpv)
    o.walhall = unit(U.TROOP, "Walhall", o.boreas)
    o.falken = unit(U.GROUP, "Sippe Falken", o.walhall)
    o.wanda = person("wanda.walhall", "Wanda", "Walhall")
    give(o.wanda, R.TROOP_LEAD, o.walhall)
    give(o.wanda, R.EVENT_TEAM, o.dpv)
    o.lea = person("lea.leitung", "Lea", "Leitung")
    o.lea_role = give(o.lea, R.TROOP_LEAD, o.walhall)
    o.mia = person("mia.mitglied", "Mia", "Mitglied")
    give(o.mia, R.MEMBER, o.walhall)
    o.paul = ManagedPerson.objects.create(first_name="Paul", last_name="Probe", birth_date=date(2012, 9, 3),
                                          unit=o.walhall)
    done, _text = Rights(o.wanda).appoint_displayed(o.walhall, o.paul.key)
    assert done
    o.vera = person("vera.verband", "Vera", "Verband")
    give(o.vera, R.FEDERATION_LEAD, o.dpv)
    o.viktor_role = give(person("viktor.verband", "Viktor", "Verband"), R.FEDERATION_LEAD, o.dpv)
    o.tom_role = give(person("tom.team", "Tom", "Team"), R.EVENT_TEAM, o.dpv)
    o.bruno_role = give(person("bruno.bund", "Bruno", "Bund"), R.ASSOCIATION_LEAD, o.boreas)
    o.admin = person("ada.admin", "Ada", "Admin")
    give(o.admin, R.ADMIN)
    o.event = event_of(o.wanda)
    return o


def _jump(section: str) -> str:
    return f"#abschnitt-{section}"


def _opener(user, page: str, dialog: str) -> list[str]:
    """Die Links auf der Seite `page`, die den Dialog mit der Adresse `dialog` öffnen, mit Sprungmarke."""
    root = _tree(client_for(user).get(page))
    return [_attr(link, "href") for link in _by_tag(root, "a") if (_attr(link, "href") or "").split("#")[0] == dialog]


def _dialog_addresses(user, dialog: str) -> dict:
    """Wohin × und „Abbrechen“ führen und wohin die Formulare im Dialog schicken."""
    response = client_for(user).get(dialog)
    assert response.status_code == 200
    box = dialog_of(_tree(response))
    close = _one(_all(box, lambda e: "a-schliessen" in _classes(e)))
    cancel = _one(_all(box, lambda e: e.name == "a" and _visible_text(e) in ("Abbrechen", "Nicht löschen", "Zurück")))
    # Auch „Suchen“ und die Knöpfe in der Trefferliste sind Formulare im Dialog.
    forms = [_attr(form, "action") for form in _by_tag(box, "form")]
    return {"close": _attr(close, "href"), "cancel": _attr(cancel, "href"), "forms": forms}


def _cases(o) -> list[tuple]:
    """Je Dialog: wer ihn öffnet, auf welcher Seite, seine Adresse, der Abschnitt und wohin × zurückführt.

    Ohne Abschnitt steht der Knopf ganz oben auf der Seite; dort ist keine Sprungmarke nötig.
    """
    walhall = unit_address(o.walhall)
    displayed = DisplayedLead.objects.get(person=o.paul)
    managed = f"{walhall}verwaltete-person/{o.paul.key}/"
    federation = "/organisation/"
    bund = f"bund-{o.boreas.key}"
    choice = f"{walhall}person-aufnehmen/"
    button = f"{walhall}#person-aufnehmen"
    return [
        (o.wanda, walhall, f"{walhall}benennen/", "leitungen", None),
        (o.wanda, walhall, f"{walhall}entfernen/{o.lea_role.key}/", "leitungen", None),
        (o.wanda, walhall, f"{walhall}entfernen-anzeige/{displayed.key}/", "leitungen", None),
        (o.wanda, walhall, f"{walhall}anlegen/", "darunter", None),
        # Seit #298 öffnet „Person aufnehmen“ die Wahl; × führt zum Knopf, die Flächen öffnen die beiden Wege,
        # und dort führt × ebenso zum Knopf, „Zurück“ zur Wahl.
        (o.wanda, walhall, choice, "personen", button),
        (o.wanda, choice, f"{walhall}aufnehmen/", "personen", button),
        (o.wanda, walhall, f"{walhall}austragen/{o.mia.key}/", "personen", None),
        (o.wanda, walhall, f"{walhall}verschieben/{o.mia.key}/", "personen", None),
        # Verwaltete Personen (#117): × führt wie bisher zum Knopf selbst (S13), seit #298 zu „Person aufnehmen“.
        (o.wanda, choice, f"{walhall}verwaltete-person/anlegen/", "personen", button),
        (o.wanda, walhall, f"{managed}bearbeiten/", "personen", f"{walhall}#bearbeiten-{o.paul.key}"),
        (o.wanda, walhall, f"{managed}verschieben/", "personen", None),
        (o.wanda, walhall, f"{managed}austragen/", "personen", None),
        (o.wanda, f"{managed}bearbeiten/", f"{managed}loeschen/", "personen", f"{walhall}#bearbeiten-{o.paul.key}"),
        (o.wanda, walhall, f"{walhall}bearbeiten/", None, None),
        (o.wanda, "/profil/", "/profil/team-abgeben/", "rollen", None),
        (o.wanda, "/profil/", "/profil/austreten/", "rollen", None),
        (o.vera, federation, f"/organisation/verband/{o.dpv.key}/verbandsleitung/benennen/", "verbandsleitung", None),
        (o.vera, federation, f"/organisation/verband/entfernen/{o.viktor_role.key}/", "verbandsleitung", None),
        (o.vera, federation, f"/organisation/verband/{o.dpv.key}/team/benennen/", "team", None),
        (o.vera, federation, f"/organisation/verband/entfernen/{o.tom_role.key}/", "team", None),
        (o.vera, federation, f"/organisation/verband/bund/{o.boreas.key}/benennen/", bund, None),
        (o.vera, federation, f"/organisation/verband/entfernen/{o.bruno_role.key}/", bund, None),
        # „Veranstaltung erstellen“ ist seit #380 kein Dialog mehr, sondern Schritt 1 eines Ablaufs mit eigener Seite.
        (o.wanda, f"/veranstaltungen/{o.event.key}/", f"/veranstaltungen/{o.event.key}/bearbeiten/", None, None),
        (o.admin, walhall, f"{walhall}support-zugang/", None, None),
    ]


# S12, S13 für jeden Dialog: Öffnen, Schließen und Speichern führen ohne Skript zum Abschnitt mit dem Knopf.
def test_ohne_skript_fuehrt_jeder_dialog_zum_abschnitt_seines_knopfs(org):
    for user, page, dialog, section, close in _cases(org):
        jump = _jump(section) if section else ""
        assert _opener(user, page, dialog) == [f"{dialog}{jump}"], dialog
        found = _dialog_addresses(user, dialog)
        back = page
        if dialog.endswith("/loeschen/") or page.endswith("/person-aufnehmen/"):
            # „Nicht löschen“ führt zurück in den Dialog „Bearbeiten“ (#118), „Zurück“ in die Wahl (#298),
            # dort an denselben Abschnitt.
            assert found["cancel"] == f"{page}{jump}", dialog
            back = unit_address(org.walhall)
        else:
            assert found["cancel"] == (close or f"{back}{jump}"), dialog
        assert found["close"] == (close or f"{back}{jump}"), dialog
        # Die Wahl (#298) schickt nichts ab; ihre Flächen sind Links.
        assert found["forms"] or dialog.endswith("/person-aufnehmen/"), dialog
        for action in found["forms"]:
            assert action.endswith(jump) if jump else "#" not in action, (dialog, action)
        if section is None:
            assert "#abschnitt-" not in str(found), dialog


def test_die_abschnitte_tragen_ihre_sprungmarke(org):
    """Die Sprungmarken gehören zu den Abschnitten mit dem Knopf, nicht zu einer Überschrift darin."""
    expected = {
        (org.wanda, unit_address(org.walhall)): ["leitungen", "darunter", "personen"],
        (org.wanda, "/profil/"): ["rollen"],
        (org.vera, "/organisation/"): ["verbandsleitung", "team", f"bund-{org.boreas.key}"],
    }
    for (user, page), sections in expected.items():
        root = _tree(client_for(user).get(page))
        for section in sections:
            found = _one(_all(root, lambda e, s=section: _attr(e, "id") == f"abschnitt-{s}"))
            assert found.name == "section", (page, section)


# S5: Im Dialog „Verbandsleitung benennen“ steht unter dem Titel „für den DPV“; die anderen bleiben.
def test_verbandsleitung_benennen_heisst_fuer_den_dpv(org):
    lines = {}
    for address in (f"/organisation/verband/{org.dpv.key}/verbandsleitung/benennen/",
                    f"/organisation/verband/{org.dpv.key}/team/benennen/"):
        box = dialog_of(_tree(client_for(org.vera).get(address)))
        lines[address.split("/")[-3]] = _visible_text(_one(_all(box, lambda e: "a-unterzeile" in _classes(e))))
    assert lines == {"verbandsleitung": "für den DPV", "team": "für das DPV-Veranstaltungsteam"}
