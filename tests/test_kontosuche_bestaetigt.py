"""Tests: Die Kontosuche findet nur über bestätigte Mails (#251, P-07a, PK-13).

Die Nummern E1 bis E5, V1 bis V5 und G1 bis G4 verweisen auf den Kommentar „Szenarien (04.11.2026)“
in #251. Erfundene Personen: Bruno ist Bundesleitung, Vera Verbandsleitung, Otto hat ein Konto ohne
Zuordnung, Ulli ist das fremde Konto, Anna ein weiteres. „Bestätigt“ heißt: Keycloak hat die Mail
beim letzten Login des Kontos als bestätigt gemeldet; das steht in der Mail-Liste von allauth
(`account_emailaddress`). Keycloak ist nachgestellt (tests/keycloak_fake.py); alle Daten sind erfunden.
"""

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from accounts.models import AccountSearch
from tests import test_benennen, test_organisation, test_verband
from tests.keycloak_fake import login
from tests.test_rollen import person

pytestmark = pytest.mark.django_db
User = get_user_model()

# Die Fixtures wie in tests/test_verband.py: Bruno und Co. aus den Tests zu #190, Vera und Viktor aus den Tests zu #94.
base_org = test_organisation.base_org
org_189 = test_organisation.org
org_190 = test_benennen.org
org = test_verband.org

NOT_FOUND = "Kein Konto gefunden. Die Person muss sich zuerst einmal im Tool anmelden."
OTTO = "otto.ohne@example.org"
# Die Person, die sich im Test bei Keycloak anmeldet; nicht Erika, die schon in den Personen der Fixture vorkommt.
PAULA = {
    "sub": "33333333-aaaa-4bbb-8ccc-000000000003",
    "preferred_username": "paula.pruefung",
    "email": "paula.pruefung@example.org",
    "email_verified": True,
    "given_name": "Paula",
    "family_name": "Pruefung",
}


def set_mail(user, mail: str, verified: bool) -> None:
    """Lässt die Mail-Liste des Kontos genau diese Mail enthalten, so wie ein Login sie hinterlässt."""
    User.objects.filter(pk=user.pk).update(email=mail)
    EmailAddress.objects.filter(user=user).delete()
    EmailAddress.objects.create(user=user, email=mail, verified=verified, primary=True)


def stranger(username: str, mail: str, verified: bool):
    """Ein angemeldetes Konto ohne Zuordnung mit dieser Mail."""
    user = person(username, username.split(".")[0].title(), "Fremd")
    User.objects.filter(pk=user.pk).update(last_login=User.objects.get(username="otto.ohne").last_login)
    set_mail(user, mail, verified)
    return user


@pytest.fixture
def paula(keycloak):
    """Der nachgestellte Keycloak meldet Paula an."""
    keycloak.person.clear()
    keycloak.person.update(PAULA)
    return keycloak


def found_by_bruno(org, text: str) -> list[str]:
    return list(test_benennen.hits(test_benennen.search(org.bundesleitung, org.walhall, text)))


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("PK-13")
def test_e1_bruno_findet_ottos_bestaetigte_mail_und_zeigt_sie_nicht(org):
    dialog = test_benennen.search(org.bundesleitung, org.walhall, OTTO)

    found = test_benennen.hits(dialog)
    assert list(found) == ["Otto Ohne"]
    assert "@" not in found["Otto Ohne"]["text"]  # der Treffer zeigt keine Mail


def test_e2_gross_und_kleinschreibung_ist_egal(org):
    assert found_by_bruno(org, "OTTO.Ohne@Example.ORG") == ["Otto Ohne"]


@pytest.mark.rechtematrix("PK-13")
def test_e3_vera_findet_ottos_bestaetigte_mail_im_dialog_verband(org):
    dialog = test_verband.search(org.verbandsleitung, test_verband.lead_address(org.boreas), OTTO)

    assert list(test_verband.hits(dialog)) == ["Otto Ohne"]


def test_e4_der_genaue_benutzername_findet_otto_auch_mit_unbestaetigter_mail(org):
    set_mail(org.ohne, OTTO, verified=False)

    assert found_by_bruno(org, "otto.ohne") == ["Otto Ohne"]


def test_e5_zwei_konten_mit_derselben_bestaetigten_mail_erscheinen_beide(org):
    stranger("zora.zweitkonto", OTTO, verified=True)

    assert sorted(found_by_bruno(org, OTTO)) == ["Otto Ohne", "Zora Fremd"]


# ---------- Verboten ----------


@pytest.mark.rechtematrix("PK-13")
def test_v1_bruno_findet_ullis_unbestaetigte_mail_nicht(org):
    stranger("ulli.unbestaetigt", "ulli@example.org", verified=False)

    dialog = test_benennen.search(org.bundesleitung, org.walhall, "ulli@example.org")

    assert test_benennen.hits(dialog) == {}
    assert test_benennen.notices(dialog) == [NOT_FOUND]


@pytest.mark.rechtematrix("PK-13")
def test_v2_vera_findet_ullis_unbestaetigte_mail_im_dialog_verband_nicht(org):
    stranger("ulli.unbestaetigt", "ulli@example.org", verified=False)

    dialog = test_verband.search(org.verbandsleitung, test_verband.lead_address(org.boreas), "ulli@example.org")

    assert test_verband.hits(dialog) == {}
    assert test_verband.notices(dialog) == [NOT_FOUND]


def test_v3_anna_bestaetigt_ulli_unbestaetigt_nur_anna_erscheint(org):
    stranger("anna.bestaetigt", "gemeinsam@example.org", verified=True)
    stranger("ulli.unbestaetigt", "gemeinsam@example.org", verified=False)

    assert found_by_bruno(org, "gemeinsam@example.org") == ["Anna Fremd"]


@pytest.mark.rechtematrix("PK-13")
def test_v4_ein_benutzername_wie_eine_mail_findet_ulli_nicht(org):
    ulli = stranger("ulli.unbestaetigt", "ulli@example.org", verified=False)
    User.objects.filter(pk=ulli.pk).update(username="anna@example.org")

    assert found_by_bruno(org, "anna@example.org") == []
    stranger("anna.bestaetigt", "anna@example.org", verified=True)
    assert found_by_bruno(org, "anna@example.org") == ["Anna Fremd"]


@pytest.mark.parametrize("claim", ["false", None])
def test_v5_mail_bestaetigt_als_text_false_oder_gar_nicht_gilt_als_unbestaetigt(client, paula, org, claim):
    login(client)
    assert found_by_bruno(org, PAULA["email"]) == ["Paula Pruefung"]

    if claim is None:
        del paula.person["email_verified"]
    else:
        paula.person["email_verified"] = claim
    client.post("/abmelden/")
    login(client)

    assert list(EmailAddress.objects.filter(user__username=PAULA["preferred_username"]).values_list("verified", flat=True)) == [False]
    assert found_by_bruno(org, PAULA["email"]) == []
    assert found_by_bruno(org, PAULA["preferred_username"]) == ["Paula Pruefung"]


@pytest.mark.parametrize("claim", ["false", "true", None])
def test_v5_auch_beim_ersten_login_gilt_alles_ausser_einem_echten_ja_als_unbestaetigt(client, paula, org, claim):
    if claim is None:
        del paula.person["email_verified"]
    else:
        paula.person["email_verified"] = claim

    login(client)

    assert list(EmailAddress.objects.filter(user__username=PAULA["preferred_username"]).values_list("verified", flat=True)) == [False]
    assert found_by_bruno(org, PAULA["email"]) == []
    assert found_by_bruno(org, PAULA["preferred_username"]) == ["Paula Pruefung"]


# ---------- Grenzfälle ----------


def test_g1_ein_konto_mit_der_mail_als_benutzernamen_wird_ueber_die_bestaetigte_mail_gefunden(org):
    User.objects.filter(pk=org.ohne.pk).update(username=OTTO)

    assert found_by_bruno(org, OTTO) == ["Otto Ohne"]


def test_g2_nach_der_bestaetigung_gilt_die_mail_ab_dem_naechsten_login(client, paula, org):
    paula.person["email_verified"] = False
    login(client)
    assert found_by_bruno(org, PAULA["email"]) == []

    paula.person["email_verified"] = True
    client.post("/abmelden/")
    login(client)

    assert found_by_bruno(org, PAULA["email"]) == ["Paula Pruefung"]


def test_g3_nach_dem_mailwechsel_finden_alte_und_neue_unbestaetigte_mail_nichts_der_benutzername_schon(client, paula, org):
    login(client)
    assert found_by_bruno(org, PAULA["email"]) == ["Paula Pruefung"]

    paula.person["email"] = "paula.neu@example.org"
    paula.person["email_verified"] = False
    client.post("/abmelden/")
    login(client)

    assert found_by_bruno(org, PAULA["email"]) == []
    assert found_by_bruno(org, "paula.neu@example.org") == []
    assert found_by_bruno(org, PAULA["preferred_username"]) == ["Paula Pruefung"]


def test_g4_eine_suche_nach_einer_unbestaetigten_mail_zaehlt_furs_suchlimit(org):
    stranger("ulli.unbestaetigt", "ulli@example.org", verified=False)

    test_benennen.search(org.bundesleitung, org.walhall, "ulli@example.org")

    assert AccountSearch.objects.filter(user=org.bundesleitung).count() == 1


# ---------- Was unverändert bleibt ----------


def test_die_vorschlaege_beim_tippen_finden_personen_im_eigenen_bereich_auch_mit_unbestaetigter_mail(org):
    set_mail(org.falke, org.falke.email, verified=False)

    assert "Flink" in test_benennen.hits(test_benennen.suggest(org.walhall_leitung, org.falken, "Flink"))


def test_gesperrte_und_nie_angemeldete_konten_erscheinen_mit_bestaetigter_mail_weiter_nicht(org):
    blocked = stranger("gesa.gesperrt", "gesa@example.org", verified=True)
    User.objects.filter(pk=blocked.pk).update(is_active=False)
    never = stranger("nie.angemeldet", "nie@example.org", verified=True)
    User.objects.filter(pk=never.pk).update(last_login=None)

    assert found_by_bruno(org, "gesa@example.org") == []
    assert found_by_bruno(org, "nie@example.org") == []
