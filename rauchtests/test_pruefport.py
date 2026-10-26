"""Der Rauchtest läuft auf seinem eigenen Port, nicht auf Port 8000 des eigenen Tools (#167)."""

from urllib.parse import urlparse

import pytest

from rauchtests.conftest import BASE
from tests.check_ports import SMOKE_TEST_PORT

pytestmark = pytest.mark.django_db(transaction=True)


def test_tool_laeuft_im_rauchtest_auf_dem_eigenen_pruefport(tool, live_server):
    assert urlparse(live_server.url).port == SMOKE_TEST_PORT
    assert tool == BASE == f"http://localhost:{SMOKE_TEST_PORT}"
