"""Der Rauchtest läuft auf seinem eigenen Port, nicht auf Port 8000 des eigenen Tools (#167)."""

import socket
from urllib.parse import urlparse

import pytest

from rauchtests.conftest import BASE
from tests.check_ports import SMOKE_TEST_LOCK_PORT, SMOKE_TEST_PORT

pytestmark = pytest.mark.django_db(transaction=True)


def test_tool_laeuft_im_rauchtest_auf_dem_eigenen_pruefport(tool, live_server):
    assert urlparse(live_server.url).port == SMOKE_TEST_PORT
    assert tool == BASE == f"http://localhost:{SMOKE_TEST_PORT}"


def test_rauchtest_haelt_die_wartesperre_solange_das_tool_laeuft(tool, live_server):
    # Ein Rauchtest aus einer anderen Arbeitskopie wartet so, bis dieser fertig ist (#184).
    with socket.socket() as other_run:
        with pytest.raises(OSError):
            other_run.bind(("127.0.0.1", SMOKE_TEST_LOCK_PORT))
