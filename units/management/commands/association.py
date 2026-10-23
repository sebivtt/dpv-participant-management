"""Gerüst."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Gerüst."""

    def add_arguments(self, parser):
        parser.add_argument("action")
        parser.add_argument("names", nargs="*")
        parser.add_argument("--rings", action="store_true")

    def handle(self, *args, **options):
        pass
