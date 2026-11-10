"""Tests für „Austragen“ auf der Seite einer Organisation und „Austreten“ auf „Mein Profil“ (#286, Teil 2 von #65).

Die Kennungen P5 bis P12, PV3, PV6, PV8, PG2, PG3, PG6 und U1 bis U3 verweisen auf die Szenarien vom
10.11.2026 (https://github.com/sebivtt/dpv-participant-management/issues/286#issuecomment-6766976020),
die Wortlaute auf den Text von #286. Dazu kommen Sebastians
Antworten bei der Umsetzung vom 10.11.2026: „Austragen“ steht auch beim eigenen Eintrag, und die Wahl
ist der Baustein „Auswahl im Dialog“
(https://github.com/sebivtt/dpv-participant-management/issues/286#issuecomment-6770423268).
Personen und Einheiten wie in den Tests zu #285 (`tests/test_personen.py`): Fiete heißt „Funke“, Finn
„Flink“, Wanda „Wirbelwind“, Willi „Wiesel“; Wim ist direkt Mitglied von Walhall. Fahrtennamen und
Mails sind erfunden. Geprüft wird, was beim Browser ankommt, und was danach in der Datenbank steht.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from access.rights import Rights
from roles.models import Role, RoleChange
from tests import test_personen
from tests.test_benennen import _one_after_the_other, dialog_of, roles_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, lock, page_tree, unit_address
from tests.test_personen import admit, membership_of, persons_on_page
from tests.test_rechtepruefung import remove as remove_by_command
from tests.test_rollen import build_org, give, person

R = Role.Kind
pytestmark = pytest.mark.django_db
User = get_user_model()

# Die Fixtures aus tests/test_personen.py unter eigenem Namen; „org“ ist die Fixture zu #285.
base_org = test_personen.base_org
org_189 = test_personen.org_189
org_190 = test_personen.org_190
org = test_personen.org

PROFILE = "/profil/"
EXIT = "/profil/austreten/"
STAYS = "Bestehende Anmeldungen bleiben."
YOURS_STAY = "Deine Anmeldungen bleiben bestehen."
FALKEN_WITHOUT_LEAD = (
    "Danach hat Sippe Falken keine Gruppenleitung mehr. Bis eine neue benannt ist, springt die Leitung von "
    "Stamm Walhall ein."
)


def expel_address(where, target) -> str:
    return f"{unit_address(where)}austragen/{target.key}/"


def expel(user, where, target, choice: str, client=None, **more):
    """„Austragen“ im Dialog bestätigen, wie der rote Knopf es mit der gewählten Möglichkeit abschickt."""
    return (client or client_for(user)).post(expel_address(where, target), {"wahl": choice, **more})


def leave(user, level, client=None, **more):
    """„Austreten“ auf „Mein Profil“ bestätigen; `level` ist die gewählte Organisation der eigenen Kette."""
    fields = {"ebene": level.key}
    membership = Role.objects.filter(user=user, kind=R.MEMBER).select_related("unit").first()
    if membership is not None:
        fields["von"] = membership.unit.key
    fields.update(more)
    return (client or client_for(user)).post(EXIT, fields)


def choice_dialog(response) -> dict:
    """Der Dialog mit Auswahl: Titel, Möglichkeiten, Vorschau je Möglichkeit und der rote Knopf.

    Die Optionsfelder gehören über ihr Attribut `form` zum Formular des roten Knopfs, damit die
    Wahl mitgeht, auch ohne Skript.
    """
    assert response.status_code == 200
    dialog = dialog_of(_tree(response))
    form = _one(_by_tag(dialog, "form", method="post"))
    choice = _one(_all(dialog, lambda e: "a-auswahl" in _classes(e)))
    options = []
    for entry in _by_tag(choice, "input", type="radio"):
        assert _attr(entry, "form") == _attr(form, "id")
        label = _one(_by_tag(choice, "label", **{"for": _attr(entry, "id")}))
        preview = _one(_by_tag(dialog, "div", id=_attr(entry, "aria-describedby")))
        options.append({
            "value": _attr(entry, "value"),
            "name": _attr(entry, "name"),
            "label": _visible_text(label),
            "checked": _attr(entry, "checked") is not None,
            "preview": [_visible_text(line) for line in _by_tag(preview, "p")],
        })
    return {
        "title": _visible_text(_one(_by_tag(dialog, "h2"))),
        "options": options,
        "button": _visible_text(_one(_all(dialog, lambda e: "btn-gefahr" in _classes(e)))),
        "action": _attr(form, "action"),
        "hidden": {_attr(entry, "name"): _attr(entry, "value") for entry in _by_tag(form, "input", type="hidden")
                   if _attr(entry, "name") != "csrfmiddlewaretoken"},
    }


def expel_dialog(user, where, target) -> dict:
    return choice_dialog(client_for(user).get(expel_address(where, target)))


def exit_dialog(user) -> dict:
    return choice_dialog(client_for(user).get(EXIT))


def expel_buttons(user, where) -> dict[str, str]:
    """Je Person im Abschnitt „Personen“ die Adresse ihres Knopfs „Austragen“; ohne Knopf fehlt sie."""
    root = page_tree(user, unit_address(where))
    section = _one(_by_tag(root, "section", aria_labelledby="h-personen"))
    found = {}
    for entry in _all(section, lambda e: "a-leitung" in _classes(e) and e.name == "li"):
        name = _text(_one(_all(entry, lambda e: "a-leitung-name" in _classes(e))))
        links = [link for link in _all(entry, lambda e: "btn-entfernen" in _classes(e))
                 if _visible_text(link).startswith("Austragen")]
        if links:
            found[name] = _attr(_one(links), "href")
    return found


def exit_button(user) -> str | None:
    """Die Adresse des Knopfs „Austreten“ in der Fläche der Mitgliedschaft auf „Mein Profil“, oder None."""
    root = page_tree(user, PROFILE)
    places = _all(root, lambda e: "a-mitgliedschaft" in _classes(e))
    if not places:
        return None
    links = [link for link in _all(_one(places), lambda e: e.name == "a") if _visible_text(link) == "Austreten"]
    return _attr(_one(links), "href") if links else None


def log_since(before: int) -> list[tuple]:
    entries = RoleChange.objects.order_by("id")[before:]
    return [(entry.actor_name, entry.person_name, entry.kind, entry.unit_name, entry.action) for entry in entries]


# ---------- Wer den Knopf „Austragen“ hat ----------


@pytest.mark.rechtematrix("PK-21")
def test_die_leitung_der_eigenen_organisation_hat_austragen_bei_jeder_person(org):
    assert expel_buttons(org.falken_leitung, org.falken) == {
        "Funke": expel_address(org.falken, org.falken_leitung),
        "Flink": expel_address(org.falken, org.falke),
    }
    assert set(expel_buttons(org.walhall_leitung, org.walhall)) == {"Wirbelwind", "Wiesel", "Wilma Walhall", "Wim Wolf"}
    assert expel_buttons(org.bundesleitung, org.boreas) == {
        "Bea Boreas": expel_address(org.boreas, org.boreas_mitglied),
        "Brummbär": expel_address(org.boreas, org.bundesleitung),
    }


@pytest.mark.rechtematrix("PK-22", "EH-19")
def test_pv3_in_organisationen_darunter_mit_eigener_leitung_gibt_es_keinen_knopf(org):
    assert expel_buttons(org.walhall_leitung, org.falken) == {}
    assert expel_buttons(org.bundesleitung, org.walhall) == {}
    assert expel_buttons(org.kueste_leitung, org.leuchtturm) == {}


# ---------- Dialog „Austragen“ ----------


@pytest.mark.rechtematrix("PK-21")
def test_p5_der_dialog_zeigt_zwei_moeglichkeiten_und_die_vorschau_je_wahl(org):
    shown = expel_dialog(org.falken_leitung, org.falken, org.falke)

    assert shown["title"] == "Flink (Finn Falke) aus Sippe Falken austragen?"
    assert [(o["value"], o["label"], o["checked"]) for o in shown["options"]] == [
        ("hoch", "Flink (Finn Falke) gehört danach direkt zu Stamm Walhall", True),
        ("ganz", "Flink (Finn Falke) gehört danach keiner Organisation mehr an", False),
    ]
    assert shown["options"][0]["preview"] == [
        "Flink (Finn Falke) aus Sippe Falken austragen? Danach gehört Flink (Finn Falke) direkt zu Stamm Walhall.",
        STAYS,
    ]
    assert shown["options"][1]["preview"] == [
        "Flink (Finn Falke) aus Sippe Falken austragen? Danach gehört Flink (Finn Falke) keiner Organisation mehr an.",
        STAYS,
    ]
    assert shown["button"] == "Austragen"
    assert shown["action"] == expel_address(org.falken, org.falke)
    # Der Dialog allein ändert nichts.
    assert membership_of(org.falke) == "Sippe Falken"


@pytest.mark.rechtematrix("PK-21")
def test_p5_fiete_traegt_finn_eine_ebene_nach_oben_aus(org):
    before = RoleChange.objects.count()
    client = client_for(org.falken_leitung)

    response = expel(org.falken_leitung, org.falken, org.falke, "hoch", client=client)

    assert response.status_code == 302
    assert response["Location"] == unit_address(org.falken)
    assert short_notices(client.get(response["Location"])) == [
        "Flink (Finn Falke) ist aus Sippe Falken ausgetragen."]
    assert membership_of(org.falke) == "Walhall"
    assert log_since(before) == [
        ("Fiete Falke", "Finn Falke", R.MEMBER, "Sippe Falken (Walhall)", "removed"),
        ("Fiete Falke", "Finn Falke", R.MEMBER, "Walhall", "granted"),
    ]
    assert "Flink" not in persons_on_page(page_tree(org.falken_leitung, unit_address(org.falken)))
    assert len(mail.outbox) == 0


@pytest.mark.rechtematrix("PK-21")
def test_p6_fiete_traegt_finn_ganz_aus_und_finn_sieht_den_hinweis(org):
    before = RoleChange.objects.count()

    expel(org.falken_leitung, org.falken, org.falke, "ganz")

    assert membership_of(org.falke) is None
    assert log_since(before) == [("Fiete Falke", "Finn Falke", R.MEMBER, "Sippe Falken (Walhall)", "removed")]
    start = _visible_text(page_tree(org.falke, "/"))
    assert "Du bist noch keiner Organisation zugeordnet." in start


@pytest.mark.rechtematrix("PK-21")
def test_p7_beim_bund_gibt_es_nur_ganz_austragen(org):
    shown = expel_dialog(org.bundesleitung, org.boreas, org.boreas_mitglied)

    assert shown["title"] == "Bea Boreas aus Pfadfinderbund Boreas austragen?"
    assert [(o["value"], o["label"], o["checked"]) for o in shown["options"]] == [
        ("ganz", "Bea Boreas gehört danach keiner Organisation mehr an", True)]
    assert shown["options"][0]["preview"] == [
        "Bea Boreas aus Pfadfinderbund Boreas austragen? Danach gehört Bea Boreas keiner Organisation mehr an.", STAYS]

    expel(org.bundesleitung, org.boreas, org.boreas_mitglied, "ganz")

    assert roles_of(org.boreas_mitglied) == set()


@pytest.mark.rechtematrix("PK-21")
def test_beim_bund_lehnt_das_tool_eine_ebene_nach_oben_ab(org):
    """Ein manipuliertes Formular: Über dem Bund gibt es keine Organisation, in der Bea danach wäre."""
    assert expel(org.bundesleitung, org.boreas, org.boreas_mitglied, "hoch").status_code == 404
    assert expel(org.falken_leitung, org.falken, org.falke, "irgendwas").status_code == 404
    assert expel(org.falken_leitung, org.falken, org.falke, "").status_code == 404

    assert membership_of(org.boreas_mitglied) == "Pfadfinderbund Boreas"
    assert membership_of(org.falke) == "Sippe Falken"


@pytest.mark.rechtematrix("PK-21")
def test_pg2_wanda_traegt_willi_aus_und_die_vorschau_nennt_seine_rolle(org):
    shown = expel_dialog(org.walhall_leitung, org.walhall, org.willi)

    assert shown["options"][0]["label"] == "Wiesel (Willi Walhall) gehört danach direkt zu Pfadfinderbund Boreas"
    assert shown["options"][0]["preview"] == [
        "Wiesel (Willi Walhall) aus Stamm Walhall austragen? Danach gehört Wiesel (Willi Walhall) direkt zu "
        "Pfadfinderbund Boreas.",
        "Damit enden diese Rollen: Stammesleitung von Stamm Walhall.",
        STAYS,
    ]
    before = RoleChange.objects.count()

    expel(org.walhall_leitung, org.walhall, org.willi, "hoch")

    assert roles_of(org.willi) == {(R.MEMBER, "Pfadfinderbund Boreas")}
    assert log_since(before) == [
        ("Wanda Walhall", "Willi Walhall", R.TROOP_LEAD, "Walhall", "removed"),
        ("Wanda Walhall", "Willi Walhall", R.MEMBER, "Walhall", "removed"),
        ("Wanda Walhall", "Willi Walhall", R.MEMBER, "Pfadfinderbund Boreas", "granted"),
    ]


@pytest.mark.rechtematrix("PK-21")
def test_die_vorschau_nennt_die_letzte_leitung_und_wer_einspringt(org):
    """Wim leitet die Wölfe allein und ist direkt Mitglied von Walhall; ganz ausgetragen endet die Leitung."""
    shown = expel_dialog(org.walhall_leitung, org.walhall, org.woelfe_leitung)

    assert shown["options"][1]["preview"] == [
        "Wim Wolf aus Stamm Walhall austragen? Danach gehört Wim Wolf keiner Organisation mehr an.",
        "Damit enden diese Rollen: Gruppenleitung von Meute Wölfe.",
        "Danach hat Meute Wölfe keine Gruppenleitung mehr. Bis eine neue benannt ist, springt die Leitung von "
        "Stamm Walhall ein.",
        STAYS,
    ]
    # Auch eine Ebene nach oben endet sie: Die Wölfe liegen unter der verlassenen Organisation (ROL-01).
    assert shown["options"][0]["preview"][1:3] == shown["options"][1]["preview"][1:3]


@pytest.mark.rechtematrix("PK-21")
def test_fiete_traegt_sich_selbst_aus_und_landet_auf_mein_profil(org):
    """Antwort von Sebastian bei der Umsetzung: „Austragen“ auch beim eigenen Eintrag, mit derselben Vorschau."""
    shown = expel_dialog(org.falken_leitung, org.falken, org.falken_leitung)
    assert shown["title"] == "Funke (Fiete Falke) aus Sippe Falken austragen?"
    assert shown["options"][0]["preview"] == [
        "Funke (Fiete Falke) aus Sippe Falken austragen? Danach gehört Funke (Fiete Falke) direkt zu Stamm Walhall.",
        "Damit enden diese Rollen: Gruppenleitung von Sippe Falken.",
        FALKEN_WITHOUT_LEAD,
        STAYS,
    ]
    before = RoleChange.objects.count()
    client = client_for(org.falken_leitung)

    response = expel(org.falken_leitung, org.falken, org.falken_leitung, "hoch", client=client)

    assert response["Location"] == PROFILE
    assert short_notices(client.get(PROFILE)) == [
        "Funke (Fiete Falke) ist aus Sippe Falken ausgetragen."]
    assert roles_of(org.falken_leitung) == {(R.MEMBER, "Walhall")}
    assert {entry[0] for entry in log_since(before)} == {"Fiete Falke"}


@pytest.mark.rechtematrix("EH-18", "PK-21")
def test_p12_ohne_gruppenleitung_traegt_wanda_finn_aus(org):
    remove_by_command(org.falken_leitung, R.GROUP_LEAD, org.falken)

    assert set(expel_buttons(org.walhall_leitung, org.falken)) == {"Funke", "Flink"}
    expel(org.walhall_leitung, org.falken, org.falke, "hoch")

    assert membership_of(org.falke) == "Walhall"


@pytest.mark.rechtematrix("EH-18", "PK-21")
def test_auch_bei_gesperrter_gruppenleitung_springt_wanda_ein(org):
    lock(org.falken_leitung)

    expel(org.walhall_leitung, org.falken, org.falke, "ganz")

    assert membership_of(org.falke) is None


# ---------- Wer nicht austragen darf ----------


@pytest.mark.rechtematrix("PK-22", "EH-19")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/austragen/<key:person>/")
def test_pv3_wanda_traegt_finn_nicht_aus_auch_nicht_ueber_die_adresse(org):
    assert_like_missing(org.walhall_leitung, expel_address(org.falken, org.falke))
    assert expel(org.walhall_leitung, org.falken, org.falke, "ganz").status_code == 404
    # Auch nicht über die eigene Organisation: Finn ist kein direktes Mitglied von Walhall.
    assert expel(org.walhall_leitung, org.walhall, org.falke, "ganz").status_code == 404
    assert expel(org.bundesleitung, org.boreas, org.walhall_mitglied, "ganz").status_code == 404

    assert membership_of(org.falke) == "Sippe Falken"
    assert membership_of(org.walhall_mitglied) == "Walhall"


@pytest.mark.rechtematrix("PK-23")
def test_pv6_ohne_leitungsrolle_traegt_niemand_jemanden_aus(org):
    org.max.refresh_from_db()
    for user in (org.verbandsleitung, org.team, org.max, org.walhall_mitglied, org.ohne):
        for where, target in ((org.falken, org.falke), (org.walhall, org.willi), (org.boreas, org.boreas_mitglied)):
            assert_like_missing(user, expel_address(where, target))
            assert expel(user, where, target, "ganz").status_code == 404

    assert membership_of(org.falke) == "Sippe Falken"
    assert membership_of(org.willi) == "Walhall"
    assert membership_of(org.boreas_mitglied) == "Pfadfinderbund Boreas"


@pytest.mark.rechtematrix("PK-21", "PK-22")
def test_leitungen_ausserhalb_tragen_niemanden_aus(org):
    for user, where, target in (
        (org.zugvoegel_leitung, org.walhall, org.walhall_mitglied),
        (org.adler_leitung, org.falken, org.falke),
        (org.mosaik_leitung, org.boreas, org.boreas_mitglied),
        (org.falken_leitung, org.walhall, org.walhall_mitglied),
    ):
        assert expel(user, where, target, "ganz").status_code == 404

    assert membership_of(org.walhall_mitglied) == "Walhall"
    assert membership_of(org.falke) == "Sippe Falken"
    assert membership_of(org.boreas_mitglied) == "Pfadfinderbund Boreas"


def test_die_organisation_kommt_aus_der_adresse_nicht_aus_dem_formular(org):
    expel(org.falken_leitung, org.falken, org.falke, "hoch", unit=org.zugvoegel.key, ziel=org.adler.key)

    assert membership_of(org.falke) == "Walhall"


def test_falsche_oder_fehlende_kennung_einer_person_ist_nicht_gefunden(org):
    client = client_for(org.falken_leitung)
    for address in (f"{unit_address(org.falken)}austragen/{org.falken.key}/",
                    f"{unit_address(org.falken)}austragen/{org.falke.pk}/"):
        assert client.get(address).status_code == 404
        assert client.post(address, {"wahl": "ganz"}).status_code == 404
    assert membership_of(org.falke) == "Sippe Falken"


def test_nur_lesen_und_abschicken_andere_anfragen_sind_nicht_gefunden(org):
    response = client_for(org.falken_leitung).put(expel_address(org.falken, org.falke))

    assert response.status_code == 404
    assert membership_of(org.falke) == "Sippe Falken"


# ---------- Austreten auf „Mein Profil“ ----------


@pytest.mark.rechtematrix("EP-06")
def test_den_knopf_austreten_hat_jede_person_mit_mitgliedschaft(org):
    for user in (org.falke, org.falken_leitung, org.walhall_leitung, org.boreas_mitglied):
        assert exit_button(user) == EXIT, user.username
    for user in (org.ohne, org.verbandsleitung, org.team):
        assert exit_button(user) is None, user.username
        assert client_for(user).get(EXIT).status_code == 404


@pytest.mark.rechtematrix("EP-06")
def test_der_dialog_bietet_die_ebenen_der_eigenen_kette(org):
    shown = exit_dialog(org.falke)

    assert shown["title"] == "Austreten"
    assert [(o["value"], o["label"], o["checked"]) for o in shown["options"]] == [
        (org.falken.key, "aus Sippe Falken (danach gehörst du direkt zu Stamm Walhall)", True),
        (org.walhall.key, "aus Stamm Walhall (danach gehörst du direkt zu Pfadfinderbund Boreas)", False),
        (org.boreas.key, "aus Pfadfinderbund Boreas (danach gehörst du keiner Organisation mehr an, bis dich eine "
                         "Leitung wieder aufnimmt)", False),
    ]
    assert [o["preview"] for o in shown["options"]] == [
        ["Du trittst aus Sippe Falken aus und gehörst danach direkt zu Stamm Walhall.", YOURS_STAY],
        ["Du trittst aus Stamm Walhall aus und gehörst danach direkt zu Pfadfinderbund Boreas.", YOURS_STAY],
        ["Du trittst aus Pfadfinderbund Boreas aus und gehörst danach keiner Organisation mehr an.", YOURS_STAY],
    ]
    assert shown["button"] == "Austreten"
    assert shown["action"] == EXIT
    assert shown["hidden"] == {"von": org.falken.key}
    assert membership_of(org.falke) == "Sippe Falken"


@pytest.mark.rechtematrix("EP-06")
def test_p8_finn_tritt_aus_den_falken_aus(org):
    before = RoleChange.objects.count()
    client = client_for(org.falke)

    response = leave(org.falke, org.falken, client=client)

    assert response.status_code == 302
    assert response["Location"] == PROFILE
    assert short_notices(client.get(PROFILE)) == ["Du bist aus Sippe Falken ausgetreten."]
    assert membership_of(org.falke) == "Walhall"
    assert log_since(before) == [
        ("Finn Falke", "Finn Falke", R.MEMBER, "Sippe Falken (Walhall)", "removed"),
        ("Finn Falke", "Finn Falke", R.MEMBER, "Walhall", "granted"),
    ]
    assert len(mail.outbox) == 0


@pytest.mark.rechtematrix("EP-06")
def test_p9_fiete_tritt_aus_und_verliert_den_zugriff(org):
    shown = exit_dialog(org.falken_leitung)
    assert shown["options"][0]["preview"] == [
        "Du trittst aus Sippe Falken aus und gehörst danach direkt zu Stamm Walhall.",
        "Damit enden deine Rollen: Gruppenleitung von Sippe Falken.",
        FALKEN_WITHOUT_LEAD,
        YOURS_STAY,
    ]
    client = client_for(org.falken_leitung)
    assert client.get("/organisation/").status_code == 200

    leave(org.falken_leitung, org.falken, client=client)

    assert roles_of(org.falken_leitung) == {(R.MEMBER, "Walhall")}
    assert client.get("/organisation/").status_code == 403


@pytest.mark.rechtematrix("EP-06")
def test_p10_wanda_tritt_aus_boreas_aus_ohne_satz_zur_letzten_leitung(org):
    shown = exit_dialog(org.walhall_leitung)
    assert [o["label"] for o in shown["options"]] == [
        "aus Stamm Walhall (danach gehörst du direkt zu Pfadfinderbund Boreas)",
        "aus Pfadfinderbund Boreas (danach gehörst du keiner Organisation mehr an, bis dich eine Leitung wieder "
        "aufnimmt)",
    ]
    assert shown["options"][1]["preview"] == [
        "Du trittst aus Pfadfinderbund Boreas aus und gehörst danach keiner Organisation mehr an.",
        "Damit enden deine Rollen: Stammesleitung von Stamm Walhall.",
        YOURS_STAY,
    ]

    client = client_for(org.walhall_leitung)
    leave(org.walhall_leitung, org.boreas, client=client)

    assert roles_of(org.walhall_leitung) == set()
    assert short_notices(client.get(PROFILE)) == [
        "Du bist aus Pfadfinderbund Boreas ausgetreten."]


@pytest.mark.rechtematrix("EP-06", "PK-17")
def test_p11_anton_tritt_aus_boreas_aus_und_wanda_nimmt_ihn_auf(org):
    leave(org.adler_kind, org.boreas)
    assert membership_of(org.adler_kind) is None

    response = admit(org.walhall_leitung, org.walhall, org.adler_kind)

    assert response.status_code == 302
    assert membership_of(org.adler_kind) == "Walhall"


@pytest.mark.rechtematrix("EP-07")
def test_pv8_finn_schickt_wiebkes_kennung_mit_und_tritt_nur_selbst_aus(org):
    leave(org.falke, org.falken, person=org.wolf.key, konto=org.wolf.key, key=org.wolf.key)

    assert membership_of(org.falke) == "Walhall"
    assert membership_of(org.wolf) == "Meute Wölfe"


@pytest.mark.rechtematrix("EP-07")
def test_pg6_eine_manipulierte_fremde_ebene_wird_abgelehnt(org):
    for level in (org.woelfe, org.zugvoegel, org.adler, org.mosaik, org.dpv):
        assert leave(org.falke, level).status_code == 404, level.name
    assert leave(org.falke, org.falken, ebene="kaputt").status_code == 404
    assert client_for(org.falke).post(EXIT, {"von": org.falken.key}).status_code == 404

    assert membership_of(org.falke) == "Sippe Falken"


@pytest.mark.rechtematrix("EP-06")
def test_ohne_mitgliedschaft_gibt_es_kein_austreten(org):
    assert leave(org.ohne, org.boreas).status_code == 404
    assert client_for(org.team).post(EXIT, {"ebene": org.dpv.key}).status_code == 404

    assert roles_of(org.team) == {(R.EVENT_TEAM, "DPV")}


def test_austreten_nimmt_nur_lesen_und_abschicken_an(org):
    assert client_for(org.falke).put(EXIT).status_code == 404
    assert membership_of(org.falke) == "Sippe Falken"


# ---------- Gleichzeitige Änderungen (PG3) ----------


@pytest.mark.django_db(transaction=True)
def test_pg3_zwei_leitungen_tragen_dieselbe_person_gleichzeitig_aus():
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    willi = person("willi.walhall", "Willi", "Walhall")
    wilma = person("wilma.walhall", "Wilma", "Walhall")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(willi, R.TROOP_LEAD, o.walhall)
    give(wilma, R.MEMBER, o.walhall)
    before = RoleChange.objects.count()

    results = _one_after_the_other(lambda: _outcome(lambda: Rights(wanda).expel(o.walhall, wilma.key, "ganz")),
                                   lambda: _outcome(lambda: Rights(willi).expel(o.walhall, wilma.key, "hoch")))

    assert sorted(results) == ["gelungen", "nicht gefunden"]
    assert roles_of(wilma) == set()
    assert RoleChange.objects.count() == before + 1


@pytest.mark.django_db(transaction=True)
def test_pg3_finn_tritt_aus_waehrend_fiete_ihn_austraegt():
    o = build_org()
    fiete = person("fiete.falke", "Fiete", "Falke")
    finn = person("finn.falke", "Finn", "Falke")
    give(fiete, R.GROUP_LEAD, o.falken)
    give(finn, R.MEMBER, o.falken)
    before = RoleChange.objects.count()

    results = _one_after_the_other(
        lambda: _outcome(lambda: Rights(fiete).expel(o.falken, finn.key, "ganz")),
        lambda: _outcome(lambda: Rights(finn).leave_own(o.falken.key, o.falken.key)))

    assert sorted(results) == ["gelungen", "nicht gefunden"]
    assert roles_of(finn) == set()
    assert RoleChange.objects.count() == before + 1


def _outcome(work) -> str:
    from django.http import Http404

    try:
        work()
    except Http404:
        return "nicht gefunden"
    return "gelungen"


# ---------- Was unverändert bleibt ----------


@pytest.mark.rechtematrix("RO-10", "RO-20")
def test_u1_leitung_entfernen_laesst_die_mitgliedschaft_stehen(org):
    """U1: „Entfernen“ (#191) bleibt gleich; die Mitgliedschaft endet nur über Austragen oder Austreten."""
    fiete = Role.objects.get(user=org.falken_leitung, kind=R.GROUP_LEAD, unit=org.falken)

    client_for(org.walhall_leitung).post(f"{unit_address(org.falken)}entfernen/{fiete.key}/")

    assert roles_of(org.falken_leitung) == {(R.MEMBER, "Sippe Falken")}


def test_u2_mein_profil_behaelt_fahrtenname_und_rolle_abgeben(org):
    root = page_tree(org.team, PROFILE)

    assert _by_tag(root, "form", action="/profil/fahrtenname/")
    assert [_attr(link, "href") for link in _all(root, lambda e: "a-kachel-knopf" in _classes(e))] == [
        "/profil/team-abgeben/"]


def test_u3_der_wechsel_der_mitgliedschaft_lehnt_mit_leitungsrolle_weiter_ab(org):
    """U3: Die Meldung aus #89 bleibt beim Wechsel der Organisation einer Mitgliedschaft."""
    from django.core.exceptions import ValidationError

    membership = Role.objects.get(user=org.falken_leitung, kind=R.MEMBER)
    membership.unit = org.adler
    with pytest.raises(ValidationError) as error:
        membership.save(by=org.walhall_leitung)

    assert "Diese Rolle muss zuerst entfernt werden." in str(error.value)
    assert membership_of(org.falken_leitung) == "Sippe Falken"


# ---------- Baustein „Auswahl im Dialog“ ----------


def test_der_bausteinkatalog_zeigt_die_auswahl_im_dialog(settings, org):
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = page_tree(org.falke, "/bausteine/")
    names = [_text(_one(_by_tag(entry, "h2")))
             for entry in _all(root, lambda e: e.name == "section" and "a-baustein" in _classes(e))]

    assert "Auswahl im Dialog" in names
