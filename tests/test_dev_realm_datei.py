"""Feste Kennungen der erfundenen Konten in dev/keycloak/dpv-realm.json (#199).

Keycloak liest die Datei bei jedem Start neu ein; Entwicklung und lokale Testumgebung im
Container teilen sie. Ohne feste Kennung (`id`, im Login `sub`) vergibt Keycloak bei jedem
Start eine neue, und das Tool legt beim nächsten Login ein neues Konto an
(docs/entscheidungen.md, 21.10.2026, Punkt 4). Die Nummern verweisen auf die Szenarien in #199.
Diese Tests lesen nur die Datei; dass der Login wirklich mit der Kennung verknüpft, prüft
tests/test_keycloak_echt.py.
"""

import json
from pathlib import Path

DEV_REALM_FILE = Path(__file__).resolve().parent.parent / "dev" / "keycloak" / "dpv-realm.json"

# Erkennbar erfunden: lauter Nullen, nur die letzte Stelle zählt hoch. Die Form ist die übliche
# einer zufälligen Kennung (Fassung 4), damit Keycloak sie wie jede andere behandelt.
ACCOUNT_IDS = {
    "erika.testfrau": "00000000-0000-4000-8000-000000000001",
    "max.testmann": "00000000-0000-4000-8000-000000000002",
    "ohne.name": "00000000-0000-4000-8000-000000000003",
    "ohne.nachname": "00000000-0000-4000-8000-000000000004",
    "ohne.mail": "00000000-0000-4000-8000-000000000005",
}


def load_users() -> list[dict]:
    return json.loads(DEV_REALM_FILE.read_text(encoding="utf-8"))["users"]


# Szenario S3
def test_jedes_erfundene_konto_hat_seine_feste_kennung():
    assert {user["username"]: user.get("id") for user in load_users()} == ACCOUNT_IDS


# Szenario S3
def test_keine_kennung_kommt_doppelt_vor():
    ids = [user.get("id") for user in load_users()]

    assert len(ids) == len(set(ids))
