"""Tests sprechen nur die Keycloak-Testumgebung auf dem eigenen Rechner an (#325, Szenario V11).

Keycloak-Tests und Rauchtests legen Konten an, löschen Realms und melden sich an. Zeigt die
Adresse des Realms woanders hin, etwa auf den Keycloak des DPV, bricht der Lauf ab, bevor ein
Test oder seine Vorbereitung beginnt: Eingebunden ist die Prüfung in tests/conftest.py und
rauchtests/conftest.py, nach dem Sammeln der Tests.
"""

from urllib.parse import urlparse

import pytest
from django.conf import settings

OWN_MACHINE = {"localhost", "127.0.0.1", "::1"}


def require_local_keycloak() -> None:
    """Bricht den ganzen Lauf ab, wenn das Tool oder ein Test Keycloak außerhalb des eigenen Rechners anspräche."""
    # Der Browser nutzt KEYCLOAK_REALM_URL, das Tool selbst KEYCLOAK_REALM_URL_INTERN (config/settings.py).
    for name in ("KEYCLOAK_REALM_URL", "KEYCLOAK_REALM_URL_INTERN"):
        if urlparse(getattr(settings, name)).hostname not in OWN_MACHINE:
            pytest.exit(
                f"Abgebrochen: Keycloak-Tests und Rauchtests laufen nur gegen die Keycloak-Testumgebung auf dem "
                f"eigenen Rechner (localhost), aber {name} zeigt woanders hin. Kein Test hat Keycloak angesprochen. "
                "Lokal die Werte aus .env.example nehmen (README.md).",
                returncode=1,
            )
