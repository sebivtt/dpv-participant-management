"""Der Rauchtest läuft auf seinem eigenen Port, auch wenn das eigene Tool läuft (#167).

Port 8000 ist im ganzen Rauchtest belegt, wie vom eigenen Tool aus README Schritt 9
(conftest.py, `_port_8000_wie_das_eigene_tool`).
"""

from urllib.parse import urlparse

import pytest

from rauchtests.conftest import BASE, login
from tests.check_ports import SMOKE_TEST_PORT, is_busy

pytestmark = pytest.mark.django_db(transaction=True)


def test_tool_laeuft_im_rauchtest_auf_dem_eigenen_pruefport(tool, live_server):
    assert urlparse(live_server.url).port == SMOKE_TEST_PORT
    assert tool == BASE == f"http://localhost:{SMOKE_TEST_PORT}"


def test_login_klappt_waehrend_port_8000_belegt_ist(pc):
    assert is_busy(8000)

    login(pc)

    assert pc.url == f"{BASE}/"
