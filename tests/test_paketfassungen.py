"""Feste Paketfassungen in `uv.lock`, die wegen einer bekannten Sicherheitslücke nicht unterschritten
werden dürfen (#274).

`pip-audit` meldet eine Lücke erst, wenn sie bekannt ist. Dieser Test hält fest, dass eine spätere
Änderung an `uv.lock` nicht still auf eine Fassung mit bekannter Lücke zurückfällt.
"""

import tomllib
from pathlib import Path

LOCKFILE = Path(__file__).resolve().parent.parent / "uv.lock"


def _fassung(paket: str) -> tuple[int, ...]:
    daten = tomllib.loads(LOCKFILE.read_text(encoding="utf-8"))
    fassungen = [p["version"] for p in daten["package"] if p["name"] == paket]
    assert len(fassungen) == 1, f"{paket} steht {len(fassungen)}-mal in uv.lock"
    return tuple(int(teil) for teil in fassungen[0].split("."))


def test_oauthlib_mindestens_in_fassung_ohne_bekannte_luecke():
    # CVE-2026-49272 betrifft oauthlib 4.0.0, behoben in 4.0.1 (#274).
    assert _fassung("oauthlib") >= (4, 0, 1)
