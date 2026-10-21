#!/usr/bin/env python
"""Verwaltungsbefehle von Django, z. B. python manage.py migrate."""

import os
import sys


def main() -> None:
    """Führt den angegebenen Verwaltungsbefehl aus."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
