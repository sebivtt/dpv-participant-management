"""Vergleich des Leistungstests mit dem Ende der vorigen Phase (#145, NFA-05). Gerüst."""

LIMIT = 2.0
SLOWER = 0.25


def marker(phase: str) -> str:
    raise NotImplementedError


def check_inputs(phase: str, previous: str) -> None:
    raise NotImplementedError


def seconds(value: float) -> str:
    """Sekunden mit Komma und zwei Stellen, z. B. „0,61 s“."""
    return f"{value:.2f} s".replace(".", ",")


def load(paths: list[str]) -> tuple[dict[str, list[float]], list[str]]:
    raise NotImplementedError


def compare(new: dict[str, list[float]], old: dict[str, list[float]] | None) -> list[dict]:
    raise NotImplementedError


def section(rows: list[dict], *, phase: str, previous: str, commit: str, day: str, unmeasured: list[str],
            dropped: list[str]) -> str:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
