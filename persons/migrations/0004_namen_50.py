"""Vor- und Nachname verwalteter Personen höchstens 50 statt 100 Zeichen, auch in der Datenbank (#330).

Was länger ist, wird vorher nach dem 50. Zeichen gekürzt, ohne Leerzeichen am Ende (Klärung zu #330,
Frage 2); kürzere Namen bleiben, wie sie sind. Bei der Umstellung gab es nur erfundene Testdaten.
Zurück auf 100 bleibt jeder Name, wie er ist; gekürzte werden nicht wieder länger.

Gekürzt wird wie `trimmed()` in `accounts/keycloak_abgleich.py` (#77), hier als eigene Kopie: Eine
Umstellung bleibt so, wie sie war, auch wenn sich der Code des Tools später ändert.
"""

import re

from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Length

LIMIT = 50
_EDGE_SPACES = re.compile(r"^[\s\u00ad\u180e\u200b-\u200d\u2060\ufeff]+|[\s\u00ad\u180e\u200b-\u200d\u2060\ufeff]+$")


def shortened(value: str) -> str:
    return _EDGE_SPACES.sub("", value[:LIMIT])


def shorten_too_long(apps, schema_editor):
    ManagedPerson = apps.get_model("persons", "ManagedPerson")
    too_long = ManagedPerson.objects.annotate(first=Length("first_name"), last=Length("last_name")).filter(
        Q(first__gt=LIMIT) | Q(last__gt=LIMIT)
    )
    for person in too_long:
        person.first_name = shortened(person.first_name)
        person.last_name = shortened(person.last_name)
        person.save(update_fields=["first_name", "last_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("persons", "0003_displayed_lead"),
    ]

    operations = [
        migrations.RunPython(shorten_too_long, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="managedperson",
            name="first_name",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="managedperson",
            name="last_name",
            field=models.CharField(max_length=50),
        ),
    ]
