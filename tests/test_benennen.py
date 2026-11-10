"""Tests für „Leitung benennen“ auf der Seite einer Organisation (#190, Teil 2 von #93).

Die Nummern B1 bis B15 und BV1 bis BV13 verweisen auf Sebastians Szenarien vom 27.10.2026
(https://github.com/sebivtt/dpv-participant-management/issues/190#issuecomment-6441094377), die
Wortlaute auf seine Entscheidungen bei der Umsetzung vom 28.10.2026
(https://github.com/sebivtt/dpv-participant-management/issues/190#issuecomment-6468685698). Personen und Einheiten wie in den Tests zu #189
(`tests/test_organisation.py`); Fahrtennamen und Mails sind erfunden. Geprüft wird, was beim
Browser ankommt, und was danach in der Datenbank steht.
"""

import threading
from datetime import timedelta

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.utils import timezone

from access.rights import Rights
from accounts.models import AccountSearch
from roles.models import Role, RoleChange
from tests import test_organisation
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, leads_notice, leads_on_page, lock, nav_labels, page_tree, unit_address
from tests.test_rechtepruefung import remove
from tests.test_rollen import build_org, give, person

R = Role.Kind
pytestmark = pytest.mark.django_db
User = get_user_model()

# Die Fixtures aus tests/test_organisation.py unter eigenem Namen.
base_org = test_organisation.base_org
org_189 = test_organisation.org


@pytest.fixture
def org(org_189):
    """Die Personen aus #189; Finn heißt „Flink“ wie im Beispiel, und jedes Konto war schon einmal angemeldet.

    Jede Mail steht, wie nach einem Login, als bestätigter Eintrag in der Mail-Liste (#251).
    """
    org = org_189
    org.falke.scout_name = "Flink"
    org.falke.save()
    User.objects.update(last_login=timezone.now())
    for user in User.objects.exclude(email=""):
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    for name in vars(org):
        value = getattr(org, name)
        if isinstance(value, User):
            value.refresh_from_db()
    return org


def appoint_address(unit) -> str:
    return f"{unit_address(unit)}benennen/"


def search_address(unit) -> str:
    return f"{appoint_address(unit)}suchen/"


def suggestions_address(unit) -> str:
    return f"{appoint_address(unit)}vorschlaege/"


def suggest(user, unit, text: str):
    """Die Vorschläge beim Tippen, wie das Skript des Dialogs sie abfragt."""
    response = client_for(user).post(suggestions_address(unit), {"suche": text})
    assert response.status_code == 200
    return _tree(response)


def search(user, unit, text: str, client=None):
    """„Suchen“ im Dialog; gibt den Dialog der Antwort zurück."""
    response = (client or client_for(user)).post(search_address(unit), {"suche": text})
    return dialog_of(_tree(response))


def appoint(user, where, target, client=None, **more):
    """„Benennen“ im Dialog für `target`, wie der Knopf neben einem Treffer es abschickt; `more` sind weitere Felder."""
    return (client or client_for(user)).post(appoint_address(where), {"person": target.key, **more})


def dialog_of(root):
    return _one(_by_tag(root, "dialog", aria_labelledby="h-dialog"))


def hits(root) -> dict[str, dict]:
    """Die Einträge der Trefferliste: sichtbarer Text, ob es den Knopf „Benennen“ gibt, und welche Kennung er schickt."""
    found = {}
    for entry in _all(root, lambda e: "a-treffer" in _classes(e) and e.name == "li"):
        name = _text(_one(_all(entry, lambda e: "a-leitung-name" in _classes(e))))
        fields = _by_tag(entry, "input", name="person")
        found[name] = {"text": _visible_text(entry), "button": bool(fields), "key": _attr(fields[0], "value") if fields else None}
    return found


def notices(root) -> list[str]:
    return [_visible_text(entry) for entry in _all(root, lambda e: "a-meldung" in _classes(e))]


def roles_of(user) -> set[tuple[str, str]]:
    return set(Role.objects.filter(user=user).values_list("kind", "unit__name"))


def short_notices(response) -> list[str]:
    """Die kurzen Meldungen auf der Seite nach der Weiterleitung."""
    root = _tree(response)
    return [_visible_text(entry) for entry in _all(root, lambda e: e.name == "div" and _attr(e, "data-kurz") is not None)]


def appoint_button(user, unit) -> str | None:
    """Die Beschriftung des Knopfs „… benennen“ auf der Seite der Organisation, oder None."""
    # Seit #285 hat auch der Abschnitt „Personen“ einen Knopf; gemeint ist der unter „Leitungen“.
    root = _one(_by_tag(page_tree(user, unit_address(unit)), "section", aria_labelledby="h-leitungen"))
    links = _all(root, lambda e: "a-flaeche-aktion" in _classes(e))
    if not links:
        return None
    assert _attr(_one(links), "href") == appoint_address(unit)
    return _visible_text(_one(links))


# ---------- Wer den Knopf hat ----------


@pytest.mark.rechtematrix("RO-10", "RO-11")
def test_den_knopf_hat_wer_dort_leitungen_benennen_darf(org):
    allowed = [
        (org.bundesleitung, org.boreas, "Bundesleitung benennen"),
        (org.bundesleitung, org.walhall, "Stammesleitung benennen"),
        (org.bundesleitung, org.adler, "Gruppenleitung benennen"),
        (org.kueste_leitung, org.kueste, "Ringleitung benennen"),
        (org.kueste_leitung, org.leuchtturm, "Stammesleitung benennen"),
        (org.kueste_leitung, org.moewen, "Gruppenleitung benennen"),
        (org.walhall_leitung, org.walhall, "Stammesleitung benennen"),
        (org.walhall_leitung, org.falken, "Gruppenleitung benennen"),
        (org.willi, org.woelfe, "Gruppenleitung benennen"),
        (org.falken_leitung, org.falken, "Gruppenleitung benennen"),
    ]
    for user, unit, label in allowed:
        assert appoint_button(user, unit) == label, (user.username, unit.name)


@pytest.mark.rechtematrix("RO-13")
def test_auf_der_leseseite_und_ausserhalb_gibt_es_keinen_knopf(org):
    """BV6 und Leseseite (EH-28): Fiete auf Walhall, Wanda auf Boreas, Kai auf Mosaik."""
    for user, unit in [(org.falken_leitung, org.walhall), (org.walhall_leitung, org.boreas), (org.kueste_leitung, org.mosaik)]:
        assert appoint_button(user, unit) is None, (user.username, unit.name)


def test_der_knopf_steht_auch_auf_der_uebersicht_bei_der_eigenen_organisation(org):
    # Seit #285 hat auch der Abschnitt „Personen“ einen Knopf; gemeint ist der unter „Leitungen“.
    root = _one(_by_tag(page_tree(org.walhall_leitung), "section", aria_labelledby="h-leitungen"))

    link = _one(_all(root, lambda e: "a-flaeche-aktion" in _classes(e)))
    assert _visible_text(link) == "Stammesleitung benennen"
    assert _attr(link, "href") == appoint_address(org.walhall)


def test_der_dialog_hat_feld_suchen_und_abbrechen(org):
    """Frage 10 und Zielbild: Feld „Name, Fahrtenname, Mail oder Benutzername“, Knopf „Suchen“, zurück zur Seite."""
    dialog = dialog_of(_tree(client_for(org.walhall_leitung).get(appoint_address(org.falken))))

    assert _text(_one(_by_tag(dialog, "h2"))) == "Gruppenleitung benennen"
    assert "für Sippe Falken" in _text(dialog)
    label = _one(_by_tag(dialog, "label"))
    assert _text(label) == "Name, Fahrtenname, Mail oder Benutzername"
    field = _one(_by_tag(dialog, "input", name="suche"))
    assert _attr(field, "id") == _attr(label, "for")
    form = _one(_by_tag(dialog, "form", method="post"))
    assert _attr(form, "action") == search_address(org.falken)
    assert _visible_text(_one(_by_tag(form, "button", type="submit"))) == "Suchen"
    back = [_attr(link, "href") for link in _by_tag(dialog, "a")]
    assert back == [unit_address(org.falken), unit_address(org.falken)]
    assert "Abbrechen" in _visible_text(dialog)


# ---------- B1, BV9: Vorschläge beim Tippen ----------


@pytest.mark.rechtematrix("PK-09", "PK-10")
def test_b1_wanda_bekommt_fiete_mit_fahrtenname_und_organisation_vorgeschlagen(org):
    found = hits(suggest(org.walhall_leitung, org.falken, "Fie"))

    assert list(found) == ["Funke"]
    assert found["Funke"]["text"].startswith("Funke (Fiete Falke) Sippe Falken")
    assert found["Funke"]["button"]
    assert found["Funke"]["key"] == org.falken_leitung.key


@pytest.mark.rechtematrix("PK-09")
def test_b1_vorschlaege_erst_ab_drei_zeichen(org):
    for text in ("", "F", "Fi", "  Fi  "):
        root = suggest(org.walhall_leitung, org.falken, text)
        assert hits(root) == {}
        assert _text(root) == ""


@pytest.mark.rechtematrix("PK-09")
def test_b1_vorschlaege_kommen_aus_walhall_und_seinen_gruppen(org):
    names = set()
    for text in ("wal", "fal", "wol"):
        names |= set(hits(suggest(org.walhall_leitung, org.falken, text)))

    # Wilma, Wim und Wiebke haben keinen Fahrtennamen; Wanda findet sich selbst auch (BV4).
    assert names == {"Wirbelwind", "Wiesel", "Wilma Walhall", "Funke", "Flink", "Wim Wolf", "Wiebke Wolf"}


@pytest.mark.rechtematrix("PK-09")
def test_b1_vorschlaege_nach_vorname_nachname_und_fahrtenname(org):
    for text in ("Finn", "falke", "Flink", "Finn Fal"):
        assert "Flink" in hits(suggest(org.walhall_leitung, org.falken, text)), text


def test_vorschlaege_nur_als_formular_nie_mit_dem_namen_in_der_adresse(org):
    """Befund der unabhängigen Prüfung: Ein getippter Name stünde sonst im Protokoll eines Webservers."""
    response = client_for(org.walhall_leitung).get(suggestions_address(org.falken), {"suche": "Fie"})

    assert response.status_code == 404
    assert "Funke" not in response.content.decode()


def test_b1_hoechstens_zehn_vorschlaege(org):
    for number in range(12):
        give(person(f"walli.{number}", "Walli", f"Muster{number}"), R.MEMBER, org.walhall)

    assert len(hits(suggest(org.walhall_leitung, org.falken, "Walli"))) == 10


def test_b1_ohne_vorschlag_steht_der_hinweis_auf_suchen(org):
    root = suggest(org.walhall_leitung, org.falken, "Xaver")

    assert hits(root) == {}
    assert _text(root) == (
        "Keine Vorschläge aus deinem Bereich. Mit „Suchen“ findest du andere über die genaue Mail oder den Benutzernamen."
    )


def test_b12_vorschlaege_zaehlen_nicht_als_suche(org):
    for _ in range(25):
        suggest(org.walhall_leitung, org.falken, "Fie")

    assert not AccountSearch.objects.exists()


@pytest.mark.rechtematrix("PK-10", "PK-09")
def test_bv9_keine_vorschlaege_ausserhalb_des_bereichs(org):
    for user, unit, text in [
        (org.walhall_leitung, org.falken, "Zor"),
        (org.walhall_leitung, org.falken, "Ant"),
        (org.walhall_leitung, org.falken, "Bea"),
        (org.bundesleitung, org.walhall, "Mon"),
        (org.falken_leitung, org.falken, "Wim"),
    ]:
        assert hits(suggest(user, unit, text)) == {}, (user.username, text)


@pytest.mark.rechtematrix("PK-11", "PK-12")
def test_konten_ohne_zuordnung_erscheinen_nicht_in_den_vorschlaegen(org):
    """PK-11, PK-12: Otto findet niemand über seinen Namen, auch nicht die Bundesleitung."""
    for user, unit in [(org.bundesleitung, org.boreas), (org.walhall_leitung, org.walhall), (org.falken_leitung, org.falken)]:
        assert hits(suggest(user, unit, "Otto")) == {}
        assert hits(suggest(user, unit, "Ohne")) == {}


@pytest.mark.rechtematrix("PK-11", "PK-12")
def test_gegenprobe_otto_findet_man_ueber_die_genaue_mail(org):
    for user, unit in [(org.bundesleitung, org.boreas), (org.falken_leitung, org.falken)]:
        assert "Otto Ohne" in hits(search(user, unit, "otto.ohne@example.org"))


def test_bv11_gesperrtes_konto_erscheint_nicht_in_den_vorschlaegen(org):
    lock(org.falke)

    assert hits(suggest(org.walhall_leitung, org.falken, "Flink")) == {}
    assert notices(search(org.walhall_leitung, org.falken, "finn.falke@example.org")) == [
        "Kein Konto gefunden. Die Person muss sich zuerst einmal im Tool anmelden."
    ]


def test_platzhalter_in_vorschlaegen_finden_nichts(org):
    for text in ("%%%", "___", "***", "%a%"):
        assert hits(suggest(org.bundesleitung, org.boreas, text)) == {}, text


# ---------- „Suchen“: genaue Mail oder genauer Benutzername ----------


@pytest.mark.rechtematrix("PK-13", "PK-16")
def test_b7_bruno_findet_otto_ueber_die_genaue_mail(org):
    dialog = search(org.bundesleitung, org.walhall, "otto.ohne@example.org")

    found = hits(dialog)
    assert list(found) == ["Otto Ohne"]
    assert "noch nirgends Mitglied" in found["Otto Ohne"]["text"]
    assert "Mit dem Benennen wird die Person Mitglied von Walhall." in found["Otto Ohne"]["text"]
    assert found["Otto Ohne"]["button"]
    assert "Treffer" in _text(dialog)


@pytest.mark.rechtematrix("PK-13", "PK-15")
def test_b9_gross_und_kleinschreibung_ist_egal(org):
    for text in ("OTTO.OHNE@EXAMPLE.ORG", "Otto.Ohne", "  otto.ohne  ", "OTTO.ohne"):
        assert list(hits(search(org.bundesleitung, org.walhall, text))) == ["Otto Ohne"], text


@pytest.mark.rechtematrix("PK-13", "PK-15")
def test_bv10_teil_einer_mail_findet_nichts(org):
    for text in ("otto.ohne@example", "otto", "ohne@example.org", "otto.ohne@example.or", "@example.org", "otto%", "otto_ohne"):
        dialog = search(org.bundesleitung, org.walhall, text)
        assert hits(dialog) == {}, text
        assert notices(dialog) == ["Kein Konto gefunden. Die Person muss sich zuerst einmal im Tool anmelden."], text


@pytest.mark.rechtematrix("PK-15")
def test_bv10_leer_und_platzhalter_zeigen_nichts_und_zaehlen_nicht(org):
    for text in ("", "   ", "*", "%", "_", "**", "%_*"):
        dialog = search(org.bundesleitung, org.walhall, text)
        assert hits(dialog) == {}, text
        assert notices(dialog) == [], text

    assert not AccountSearch.objects.exists()


@pytest.mark.rechtematrix("PK-16")
def test_bv1_wanda_findet_anton_ohne_seine_organisation_und_ohne_knopf(org):
    dialog = search(org.walhall_leitung, org.falken, "anton.adler@example.org")

    found = hits(dialog)
    assert list(found) == ["Anton Adler"]
    assert "schon woanders Mitglied" in found["Anton Adler"]["text"]
    assert not found["Anton Adler"]["button"]
    assert notices(dialog) == [
        "Diese Person gehört schon zu einer anderen Organisation und kann hier keine Leitung werden. Sie kann bei "
        "ihrer bisherigen Leitung den Wechsel veranlassen."
    ]
    for secret in ("Adler", "Zugvögel"):
        assert secret not in _text(dialog).replace("Anton Adler", "").replace("anton.adler@example.org", ""), secret


@pytest.mark.rechtematrix("PK-16")
def test_im_eigenen_bereich_nennt_der_treffer_die_organisation(org):
    """Gegenprobe zu PK-16."""
    found = hits(search(org.walhall_leitung, org.falken, "finn.falke@example.org"))

    assert "Sippe Falken" in found["Flink"]["text"]


@pytest.mark.rechtematrix("RO-13")
def test_bv1_wanda_kann_anton_auch_mit_manipuliertem_formular_nicht_benennen(org):
    response = appoint(org.walhall_leitung, org.falken, org.adler_kind)

    assert response.status_code == 200
    assert notices(dialog_of(_tree(response))) == [
        "Diese Person gehört schon zu einer anderen Organisation und kann hier keine Leitung werden. Sie kann bei "
        "ihrer bisherigen Leitung den Wechsel veranlassen."
    ]
    assert roles_of(org.adler_kind) == {(R.MEMBER, "Sippe Adler")}


def test_b13_ohne_konto_und_nie_angemeldet_kein_konto_gefunden_und_es_zaehlt(org):
    never = person("nie.angemeldet", "Nie", "Angemeldet")
    never.email = "nie.angemeldet@example.org"
    never.save()

    for text in ("niemand@example.org", "nie.angemeldet@example.org", "nie.angemeldet"):
        dialog = search(org.walhall_leitung, org.falken, text)
        assert hits(dialog) == {}
        assert notices(dialog) == ["Kein Konto gefunden. Die Person muss sich zuerst einmal im Tool anmelden."]

    assert AccountSearch.objects.filter(user=org.walhall_leitung).count() == 3


def test_suche_speichert_nur_wer_und_wann_nicht_wonach(org):
    search(org.walhall_leitung, org.falken, "otto.ohne@example.org")

    assert [field.name for field in AccountSearch._meta.get_fields()] == ["id", "user", "searched_at"]
    assert AccountSearch.objects.get().user == org.walhall_leitung


def test_suchen_lesend_aufgerufen_fuehrt_zum_dialog(org):
    """Etwa nach einem Login mitten im Suchen; es zählt nichts."""
    response = client_for(org.walhall_leitung).get(search_address(org.falken))

    assert response.status_code == 302
    assert response["Location"] == appoint_address(org.falken)
    assert not AccountSearch.objects.exists()


# ---------- B12, BV13: Suchlimit ----------

LIMIT_TEXT = "Du hast in kurzer Zeit sehr oft gesucht. Bitte versuche es in {} noch einmal."


def searched(user, *minutes_ago: float) -> None:
    now = timezone.now()
    AccountSearch.objects.bulk_create(
        [AccountSearch(user=user, searched_at=now - timedelta(minutes=minutes)) for minutes in minutes_ago]
    )


@pytest.mark.rechtematrix("PK-24")
def test_b12_zwanzig_suchen_gehen_die_einundzwanzigste_nicht(org):
    client = client_for(org.walhall_leitung)
    for number in range(20):
        dialog = search(org.walhall_leitung, org.falken, f"niemand{number}@example.org", client=client)
        assert LIMIT_TEXT.format("60 Minuten") not in " ".join(notices(dialog)), number

    dialog = search(org.walhall_leitung, org.falken, "otto.ohne@example.org", client=client)

    assert notices(dialog) == [LIMIT_TEXT.format("60 Minuten")]
    assert hits(dialog) == {}
    assert AccountSearch.objects.filter(user=org.walhall_leitung).count() == 20


@pytest.mark.rechtematrix("PK-24")
def test_b12_die_minuten_reichen_bis_die_aelteste_suche_eine_stunde_alt_ist(org):
    searched(org.walhall_leitung, 37, *([5] * 19))

    dialog = search(org.walhall_leitung, org.falken, "otto.ohne@example.org")

    assert notices(dialog) == [LIMIT_TEXT.format("23 Minuten")]


@pytest.mark.rechtematrix("PK-24")
def test_b12_aufgerundet_und_mindestens_eine_minute(org):
    searched(org.walhall_leitung, 59.99, *([1] * 19))

    assert notices(search(org.walhall_leitung, org.falken, "otto.ohne@example.org")) == [LIMIT_TEXT.format("1 Minute")]


@pytest.mark.rechtematrix("PK-24")
def test_b12_danach_geht_genau_eine_suche_wieder(org):
    searched(org.walhall_leitung, 60.5, *([10] * 19))
    client = client_for(org.walhall_leitung)

    assert list(hits(search(org.walhall_leitung, org.falken, "otto.ohne@example.org", client=client))) == ["Otto Ohne"]
    assert notices(search(org.walhall_leitung, org.falken, "otto.ohne@example.org", client=client)) == [
        LIMIT_TEXT.format("50 Minuten")
    ]


@pytest.mark.rechtematrix("PK-24")
def test_b12_das_limit_gilt_je_person(org):
    searched(org.walhall_leitung, *([1] * 20))

    assert list(hits(search(org.willi, org.falken, "otto.ohne@example.org"))) == ["Otto Ohne"]
    assert hits(suggest(org.walhall_leitung, org.falken, "Fie"))


def test_b12_alte_suchen_werden_geloescht(org):
    searched(org.walhall_leitung, 61, 90, 5)

    search(org.walhall_leitung, org.falken, "otto.ohne@example.org")

    assert AccountSearch.objects.filter(user=org.walhall_leitung).count() == 2


def test_alte_suchen_anderer_personen_werden_auch_geloescht(org):
    """Befund der unabhängigen Prüfung: Von jemandem, der nie wieder sucht, bleibt nichts liegen."""
    searched(org.walhall_leitung, 90)
    searched(org.willi, 30)

    search(org.bundesleitung, org.walhall, "otto.ohne@example.org")

    assert not AccountSearch.objects.filter(user=org.walhall_leitung).exists()
    assert AccountSearch.objects.filter(user=org.willi).count() == 1


def _in_thread(work, results: list) -> threading.Thread:
    def run():
        try:
            results.append(work())
        finally:
            connection.close()

    thread = threading.Thread(target=run)
    thread.start()
    return thread


def _one_after_the_other(first_work, second_work) -> list:
    """Die erste Anfrage hält ihre Transaktion offen, während die zweite schon startet (wie in tests/test_rollen.py)."""
    first_done, release = threading.Event(), threading.Event()
    results: list = []

    def first():
        with transaction.atomic():
            result = first_work()
            first_done.set()
            release.wait(10)
        return result

    def second():
        first_done.wait(10)
        return second_work()

    one = _in_thread(first, results)
    two = _in_thread(second, results)
    two.join(1)
    release.set()
    one.join(10)
    two.join(10)
    return results


@pytest.mark.django_db(transaction=True)
def test_bv13_zwanzigste_und_einundzwanzigste_suche_gleichzeitig():
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    give(wanda, R.TROOP_LEAD, o.walhall)
    searched(wanda, *([5] * 19))

    results = _one_after_the_other(lambda: Rights(wanda).count_search(), lambda: Rights(wanda).count_search())

    assert sorted(results) == [0, 55]
    assert AccountSearch.objects.filter(user=wanda).count() == 20


# ---------- Benennen ----------


@pytest.mark.rechtematrix("RO-10", "RO-14", "RO-12", "RO-13")
def test_b2_wanda_benennt_finn_als_zweite_gruppenleitung_der_falken(org):
    before = RoleChange.objects.count()

    response = appoint(org.walhall_leitung, org.falken, org.falke)

    assert response.status_code == 302
    assert response["Location"] == unit_address(org.falken)
    assert roles_of(org.falke) == {(R.MEMBER, "Sippe Falken"), (R.GROUP_LEAD, "Sippe Falken")}
    change = RoleChange.objects.get(kind=R.GROUP_LEAD, person_id=org.falke.pk)
    assert (change.actor_id, change.unit_id, change.action) == (org.walhall_leitung.pk, org.falken.pk, "granted")
    assert RoleChange.objects.count() == before + 1


def test_b15_danach_steht_die_kurze_meldung(org):
    client = client_for(org.walhall_leitung)

    response = appoint(org.walhall_leitung, org.falken, org.falke, client=client)

    page = client.get(response["Location"])
    assert short_notices(page) == ["Flink (Finn Falke) ist jetzt Gruppenleitung von Sippe Falken."]
    assert "Flink" in [lead["name"] for lead in leads_on_page(_tree(page))]
    assert short_notices(client.get(response["Location"])) == []


def test_b2_finn_sieht_die_rolle_und_ab_dem_naechsten_klick_den_menuepunkt(org):
    finn = client_for(org.falke)
    assert "Organisation" not in nav_labels(_tree(finn.get("/profil/")))

    appoint(org.walhall_leitung, org.falken, org.falke)

    profile = _tree(finn.get("/profil/"))
    assert "Organisation" in nav_labels(profile)
    assert "Gruppenleitung" in _text(profile)
    assert finn.get("/organisation/").status_code == 200


@pytest.mark.rechtematrix("RO-11")
def test_b3_fiete_benennt_finn_als_zweite_gruppenleitung(org):
    response = appoint(org.falken_leitung, org.falken, org.falke)

    assert response.status_code == 302
    assert (R.GROUP_LEAD, "Sippe Falken") in roles_of(org.falke)


@pytest.mark.rechtematrix("RO-10")
def test_b4_bruno_benennt_wilma_als_gruppenleitung_der_woelfe(org):
    appoint(org.bundesleitung, org.woelfe, org.walhall_mitglied)

    assert roles_of(org.walhall_mitglied) == {(R.MEMBER, "Walhall"), (R.GROUP_LEAD, "Meute Wölfe")}


@pytest.mark.rechtematrix("RO-10")
def test_b5_wanda_benennt_finn_als_gruppenleitung_der_woelfe_er_bleibt_bei_den_falken(org):
    appoint(org.walhall_leitung, org.woelfe, org.falke)

    assert roles_of(org.falke) == {(R.MEMBER, "Sippe Falken"), (R.GROUP_LEAD, "Meute Wölfe")}


@pytest.mark.rechtematrix("RO-11")
def test_b6_bruno_benennt_bea_als_zweite_bundesleitung(org):
    appoint(org.bundesleitung, org.boreas, org.boreas_mitglied)

    assert (R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas") in roles_of(org.boreas_mitglied)


@pytest.mark.rechtematrix("EP-08")
def test_b7_otto_wird_stammesleitung_und_dadurch_mitglied_von_walhall(org):
    before = RoleChange.objects.count()

    appoint(org.bundesleitung, org.walhall, org.ohne)

    assert roles_of(org.ohne) == {(R.TROOP_LEAD, "Walhall"), (R.MEMBER, "Walhall")}
    new = RoleChange.objects.filter(person_id=org.ohne.pk).order_by("id").values_list("kind", "unit_id", "actor_id")
    assert list(new) == [(R.TROOP_LEAD, org.walhall.pk, org.bundesleitung.pk), (R.MEMBER, org.walhall.pk, org.bundesleitung.pk)]
    assert RoleChange.objects.count() == before + 2


@pytest.mark.rechtematrix("EP-08")
def test_otto_kann_sich_nicht_selbst_einer_organisation_zuordnen(org):
    """Gegenprobe zu EP-08: Ohne Rolle erreicht Otto keine der Adressen."""
    assert_like_missing(org.ohne, appoint_address(org.walhall))

    assert roles_of(org.ohne) == set()


def test_b8_wanda_benennt_otto_als_gruppenleitung_der_falken(org):
    assert "Otto Ohne" in hits(search(org.walhall_leitung, org.falken, "otto.ohne@example.org"))

    appoint(org.walhall_leitung, org.falken, org.ohne)

    assert roles_of(org.ohne) == {(R.GROUP_LEAD, "Sippe Falken"), (R.MEMBER, "Sippe Falken")}


def test_b10_mit_neuer_leitung_springt_niemand_mehr_ein(org):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    before = page_tree(org.walhall_leitung, unit_address(org.falken))
    assert leads_notice(before).startswith("Die Gruppe Sippe Falken hat keine Gruppenleitung.")

    appoint(org.walhall_leitung, org.falken, org.falke)

    after = page_tree(org.walhall_leitung, unit_address(org.falken))
    assert leads_notice(after) == ""
    assert "Du springst ein" not in _text(after)
    assert not Rights(org.walhall_leitung).covers(org.falken)


@pytest.mark.rechtematrix("RO-10")
def test_b11_mona_benennt_svea_als_ringleitung_von_nord(org):
    appoint(org.mosaik_leitung, org.nord, org.sturmvogel_mitglied)

    assert (R.RING_LEAD, "Nord") in roles_of(org.sturmvogel_mitglied)


def test_b14_bruno_benennt_wanda_solange_fiete_gesperrt_ist(org):
    lock(org.falken_leitung)
    assert Rights(org.walhall_leitung).covers(org.falken)

    appoint(org.bundesleitung, org.falken, org.walhall_leitung)

    assert (R.GROUP_LEAD, "Sippe Falken") in roles_of(org.walhall_leitung)
    assert not Rights(org.willi).covers(org.falken)


# ---------- Abgelehnt ----------


@pytest.mark.rechtematrix("RO-13")
def test_bv2_finn_kann_keine_leitung_der_zugvoegel_werden(org):
    response = appoint(org.bundesleitung, org.zugvoegel, org.falke)

    assert response.status_code == 200
    assert notices(dialog_of(_tree(response))) == [
        "Flink (Finn Falke) ist Mitglied in Sippe Falken und kann deshalb keine Leitung bei Stamm Zugvögel sein."
    ]
    assert roles_of(org.falke) == {(R.MEMBER, "Sippe Falken")}


def test_bv2_mit_einer_gruppe_als_ziel_steht_die_art_davor(org):
    """Befund der unabhängigen Prüfung: Wortlaut, wenn das Ziel eine Gruppe ist."""
    response = appoint(org.bundesleitung, org.woelfe, org.adler_kind)

    assert notices(dialog_of(_tree(response))) == [
        "Anton Adler ist Mitglied in Sippe Adler und kann deshalb keine Leitung bei Gruppe Meute Wölfe sein."
    ]
    assert roles_of(org.adler_kind) == {(R.MEMBER, "Sippe Adler")}


def test_bv3_fiete_ist_schon_gruppenleitung(org):
    before = RoleChange.objects.count()

    response = appoint(org.walhall_leitung, org.falken, org.falken_leitung)

    assert notices(dialog_of(_tree(response))) == ["Funke (Fiete Falke) ist schon Gruppenleitung von Sippe Falken."]
    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("RO-12")
def test_bv4_bei_sich_selbst_gibt_es_keinen_knopf(org):
    for root in (suggest(org.walhall_leitung, org.falken, "Wirbel"),
                 search(org.walhall_leitung, org.falken, "wanda.walhall@example.org")):
        found = hits(root)["Wirbelwind"]
        assert not found["button"]
        assert "Dir selbst kannst du keine Rolle geben. Das kann eine andere Leitung von Walhall oder darüber." in found["text"]


@pytest.mark.rechtematrix("RO-12", "RO-11")
def test_bv4_auch_ein_manipuliertes_formular_gibt_wanda_keine_rolle(org):
    response = appoint(org.walhall_leitung, org.falken, org.walhall_leitung)

    assert notices(dialog_of(_tree(response))) == [
        "Dir selbst kannst du keine Rolle geben. Das kann eine andere Leitung von Walhall oder darüber."
    ]
    assert roles_of(org.walhall_leitung) == {(R.MEMBER, "Walhall"), (R.TROOP_LEAD, "Walhall")}


@pytest.mark.rechtematrix("RO-12")
def test_bv4_fiete_hoert_seine_eigene_organisation(org):
    found = hits(suggest(org.falken_leitung, org.falken, "Funke"))["Funke"]

    assert "Das kann eine andere Leitung von Sippe Falken oder darüber." in found["text"]


@pytest.mark.rechtematrix("RO-13")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/benennen/")
def test_bv5_zora_benennt_keine_leitung_in_walhall(org):
    for unit in (org.walhall, org.falken):
        assert_like_missing(org.zugvoegel_leitung, appoint_address(unit))

    assert roles_of(org.walhall_mitglied) == {(R.MEMBER, "Walhall")}


@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/benennen/suchen/")
def test_bv5_zora_sucht_nicht_ueber_walhall(org):
    for unit in (org.walhall, org.falken):
        assert_like_missing(org.zugvoegel_leitung, search_address(unit))

    assert not AccountSearch.objects.exists()


@pytest.mark.rechtematrix("PK-10")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/benennen/vorschlaege/")
def test_bv9_vorschlaege_an_die_adresse_der_adler_sind_nicht_gefunden(org):
    assert_like_missing(org.walhall_leitung, suggestions_address(org.adler))
    assert_like_missing(org.zugvoegel_leitung, suggestions_address(org.walhall))


@pytest.mark.rechtematrix("RO-13")
def test_bv5_manipuliertes_formular_an_walhall_aendert_nichts(org):
    response = appoint(org.zugvoegel_leitung, org.walhall, org.walhall_mitglied)

    assert response.status_code == 404
    assert roles_of(org.walhall_mitglied) == {(R.MEMBER, "Walhall")}


@pytest.mark.rechtematrix("RO-13", "RO-10")
def test_bv6_fiete_benennt_keine_stammesleitung_von_walhall_und_keine_gruppenleitung_der_woelfe(org):
    for unit in (org.walhall, org.woelfe, org.boreas):
        assert_like_missing(org.falken_leitung, appoint_address(unit))
        assert_like_missing(org.falken_leitung, search_address(unit))
        assert_like_missing(org.falken_leitung, suggestions_address(unit))

    assert roles_of(org.falke) == {(R.MEMBER, "Sippe Falken")}


def test_bv7_die_organisation_kommt_aus_der_adresse_nicht_aus_dem_formular(org):
    appoint(org.walhall_leitung, org.falken, org.falke, unit=org.adler.key, unit_key=org.adler.key, organisation=org.adler.key)

    assert roles_of(org.falke) == {(R.MEMBER, "Sippe Falken"), (R.GROUP_LEAD, "Sippe Falken")}
    assert not Role.objects.filter(unit=org.adler, user=org.falke).exists()


@pytest.mark.rechtematrix("PK-14", "RO-14", "RO-17")
def test_bv8_ohne_leitungsrolle_weder_suche_noch_vorschlaege_noch_benennen(org):
    for user in (org.falke, org.ohne, org.team, org.verbandsleitung, org.max):
        for address in (appoint_address(org.falken), search_address(org.falken), suggestions_address(org.falken)):
            assert_like_missing(user, address)

    assert roles_of(org.wolf) == {(R.MEMBER, "Meute Wölfe")}
    assert not AccountSearch.objects.exists()


@pytest.mark.rechtematrix("PK-14")
def test_gegenprobe_leitungen_suchen_weiter(org):
    assert list(hits(search(org.falken_leitung, org.falken, "otto.ohne@example.org"))) == ["Otto Ohne"]


@pytest.mark.rechtematrix("RO-17")
def test_verbandsleitung_mit_gruppenleitung_benennt_in_ihrer_gruppe(org):
    """Gegenprobe zu RO-17: Vera hat dort die Rechte der Gruppenleitung, nicht als Verbandsleitung."""
    give(org.verbandsleitung, R.GROUP_LEAD, org.adler)

    appoint(org.verbandsleitung, org.adler, org.adler_kind)

    assert (R.GROUP_LEAD, "Sippe Adler") in roles_of(org.adler_kind)
    assert_like_missing(org.verbandsleitung, appoint_address(org.zugvoegel))


def test_bv11_gesperrtes_konto_laesst_sich_nicht_benennen(org):
    lock(org.falke)

    response = appoint(org.walhall_leitung, org.falken, org.falke)

    assert response.status_code == 404
    assert roles_of(org.falke) == {(R.MEMBER, "Sippe Falken")}


def test_falsche_oder_fehlende_kennung_einer_person_ist_nicht_gefunden(org):
    client = client_for(org.walhall_leitung)
    for data in ({}, {"person": ""}, {"person": "a" * 20}, {"person": str(org.falke.pk)}, {"person": org.falken.key}):
        assert client.post(appoint_address(org.falken), data).status_code == 404, data

    assert roles_of(org.falke) == {(R.MEMBER, "Sippe Falken")}


def test_ausserhalb_des_bereichs_ohne_anmeldung_gefundene_person_nur_ueber_die_genaue_suche(org):
    """Wer nie angemeldet war und außerhalb des Bereichs liegt, ist auch per manipuliertem Formular nicht erreichbar."""
    never = person("nie.angemeldet", "Nie", "Angemeldet")

    assert appoint(org.walhall_leitung, org.falken, never).status_code == 404
    assert roles_of(never) == set()


@pytest.mark.django_db(transaction=True)
def test_bv12_wanda_und_willi_benennen_finn_gleichzeitig():
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    willi = person("willi.walhall", "Willi", "Walhall")
    finn = person("finn.falke", "Finn", "Falke")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(willi, R.TROOP_LEAD, o.walhall)
    give(finn, R.MEMBER, o.falken)
    before = RoleChange.objects.count()

    results = _one_after_the_other(lambda: Rights(wanda).appoint(o.falken, finn.key),
                                   lambda: Rights(willi).appoint(o.falken, finn.key))

    assert sorted(results) == [(False, "Finn Falke ist schon Gruppenleitung von Sippe Falken."),
                               (True, "Finn Falke ist jetzt Gruppenleitung von Sippe Falken.")]
    assert Role.objects.filter(user=finn, kind=R.GROUP_LEAD).count() == 1
    assert RoleChange.objects.count() == before + 1
