"""ABSICHTLICHE VERSTÖSSE für den Nachweis in #4. Wird im nächsten Commit wieder entfernt."""

import os  # F401: ungenutzter Import

PASSWORD = "geheim123"  # S105: Passwort im Code

unused = 1  # noqa
also_unused = 2  # noqa: E501


def show(value: int) -> None:
    """T20: print() im Anwendungscode."""
    print(value)


def too_complex(a: int) -> int:  # C901: Komplexität über 12
    """Zu viele Verzweigungen."""
    if a == 1:
        return 1
    if a == 2:
        return 2
    if a == 3:
        return 3
    if a == 4:
        return 4
    if a == 5:
        return 5
    if a == 6:
        return 6
    if a == 7:
        return 7
    if a == 8:
        return 8
    if a == 9:
        return 9
    if a == 10:
        return 10
    if a == 11:
        return 11
    if a == 12:
        return 12
    return 0
