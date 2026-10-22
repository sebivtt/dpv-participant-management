"""Inhalt der Importdatei für den Test-Realm im Keycloak des DPV (#62).

Der Admin des DPV importiert die Datei; danach setzt Sebastian die Passwörter selbst
(Protokoll in #38). Diese Tests lesen nur die Datei und brauchen keinen Keycloak. Dass
Keycloak die Datei wirklich so versteht, prüft tests/test_testrealm_echt.py.
"""

import json
from pathlib import Path

TEST_REALM_FILE = Path(__file__).resolve().parent.parent / "testumgebung" / "keycloak" / "dpv-test-realm.json"

# Erkennbarer Platzhalter für die Testdomain, bis der Admin sie angelegt hat (#59). Die Endung
# .invalid gibt es im Internet nicht; ein vergessener Platzhalter führt also nirgendwohin.
PLACEHOLDER = "https://testdomain-eintragen.invalid"

USERS = {
    "erika.testfrau": ("Erika", "Testfrau"),
    "max.testmann": ("Max", "Testmann"),
    "ohne.name": (None, None),
    "ohne.nachname": ("Erika", None),
}

# Schlüssel, unter denen Keycloak Passwörter und Geheimnisse in einer Importdatei liest.
SECRET_KEYS = {"credentials", "secret", "password", "hashedPassword", "secretData", "credentialData"}


def load_realm() -> dict:
    """Liest die Importdatei des Test-Realms."""
    return json.loads(TEST_REALM_FILE.read_text(encoding="utf-8"))


def secret_keys_in(value, path: str = "") -> list[str]:
    """Nennt jede Stelle, an der ein Passwort oder Geheimnis stehen könnte, egal wie tief."""
    found = []
    if isinstance(value, dict):
        for key, inner in value.items():
            if key in SECRET_KEYS:
                found.append(f"{path}/{key}")
            found += secret_keys_in(inner, f"{path}/{key}")
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            found += secret_keys_in(inner, f"{path}/{index}")
    return found


def _client(realm: dict) -> dict:
    clients = [client for client in realm.get("clients", []) if client["clientId"] == "dpv-anmeldetool"]
    assert len(clients) == 1, "Der Login-Client dpv-anmeldetool fehlt oder steht doppelt in der Datei"
    return clients[0]


def test_importdatei_enthaelt_kein_passwort_und_kein_client_secret():
    assert secret_keys_in(load_realm()) == []


def test_pruefung_auf_passwoerter_findet_ein_eingeschleustes_passwort():
    # Gegenprobe: Die Prüfung oben schlägt wirklich fehl, sobald ein Passwort oder Secret hineinkommt.
    realm = load_realm()
    realm["users"][0]["credentials"] = [{"type": "password", "value": "geheim"}]
    _client(realm)["secret"] = "geheim"

    assert set(secret_keys_in(realm)) == {"/clients/0/secret", "/users/0/credentials"}


def test_realm_heisst_dpv_test_ohne_anzeigenamen():
    realm = load_realm()

    assert realm["realm"] == "dpv-test"
    assert realm["enabled"] is True
    # Keine Kennzeichnung (Entscheidung in #38); ohne Anzeigenamen zeigt Keycloak „dpv-test“.
    assert "displayName" not in realm
    assert "displayNameHtml" not in realm
    # HTTPS ist Pflicht, außer bei Aufrufen vom eigenen Rechner.
    assert realm["sslRequired"] == "external"


def test_genau_vier_erfundene_konten_mit_bestaetigter_mail():
    users = load_realm()["users"]

    assert {user["username"]: (user.get("firstName"), user.get("lastName")) for user in users} == USERS
    for user in users:
        assert user["email"] == f"{user['username']}@example.org"
        assert user["emailVerified"] is True
        assert user["enabled"] is True


def test_konten_haben_keine_rollen_und_keine_pflichtschritte():
    for user in load_realm()["users"]:
        assert not user.get("realmRoles"), user["username"]
        assert not user.get("clientRoles"), user["username"]
        assert not user.get("groups"), user["username"]
        assert not user.get("requiredActions"), user["username"]


def test_selbstregistrierung_passwort_vergessen_und_mailversand_aus():
    realm = load_realm()

    assert realm["registrationAllowed"] is False
    assert realm["resetPasswordAllowed"] is False
    assert realm["verifyEmail"] is False
    assert realm["rememberMe"] is False
    # Ohne Mailserver kann Keycloak aus dem Test-Realm keine Mail verschicken.
    assert not realm.get("smtpServer")


def test_schutz_gegen_passwortraten_ist_an():
    realm = load_realm()

    assert realm["bruteForceProtected"] is True
    assert realm["permanentLockout"] is False
    assert realm["failureFactor"] == 10


def test_login_client_ist_ein_normaler_vertraulicher_client_ohne_admin_rechte():
    realm = load_realm()
    client = _client(realm)

    assert client["publicClient"] is False
    assert client["clientAuthenticatorType"] == "client-secret"
    assert client["standardFlowEnabled"] is True
    assert client["implicitFlowEnabled"] is False
    assert client["directAccessGrantsEnabled"] is False
    assert client["serviceAccountsEnabled"] is False
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"
    # Keine eigenen Rollen und keine Zuordnungen, über die der Client Rechte bekäme.
    for key in ("roles", "scopeMappings", "clientScopeMappings", "groups"):
        assert not realm.get(key), key


def test_ruecksprung_und_abmelden_nur_zur_testdomain():
    client = _client(load_realm())

    assert client["redirectUris"] == [f"{PLACEHOLDER}/anmelden/keycloak/zurueck/"]
    assert client["attributes"]["post.logout.redirect.uris"] == f"{PLACEHOLDER}/anmelden/"
    assert client["webOrigins"] == ["+"]
    assert client.get("rootUrl", "") == ""
    assert client.get("baseUrl", "") == ""
