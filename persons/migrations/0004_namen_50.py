"""Vor- und Nachname verwalteter Personen höchstens 50 statt 100 Zeichen, auch in der Datenbank (#330).

Was länger ist, wird vorher nach dem 50. Zeichen gekürzt, ohne Leerzeichen am Ende (Klärung zu #330,
Frage 2); kürzere Namen bleiben, wie sie sind. Bei der Umstellung gab es nur erfundene Testdaten.
Zurück auf 100 bleibt jeder Name, wie er ist; gekürzte werden nicht wieder länger.
"""

from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Length

from accounts.keycloak_abgleich import trimmed

LIMIT = 50


def shorten_too_long(apps, schema_editor):
    ManagedPerson = apps.get_model("persons", "ManagedPerson")
    too_long = ManagedPerson.objects.annotate(first=Length("first_name"), last=Length("last_name")).filter(
        Q(first__gt=LIMIT) | Q(last__gt=LIMIT)
    )
    for person in too_long:
        person.first_name = trimmed(person.first_name, LIMIT)
        person.last_name = trimmed(person.last_name, LIMIT)
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
