"""Fahrtenname höchstens 30 statt 50 Zeichen, auch in der Datenbank (#214).

Was länger ist, wird vorher geleert (Klärung zu #214, Frage 6b): Danach steht „Noch nicht
angegeben“, und die Person trägt ihn neu ein. Bei der Umstellung gab es solche Namen nur in
Testkonten. Zurück auf 50 bleibt jeder Name, wie er ist; geleerte kommen nicht wieder.
"""

from django.db import migrations, models
from django.db.models.functions import Length


def clear_too_long(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.annotate(length=Length("scout_name")).filter(length__gt=30).update(scout_name="")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_account_search"),
    ]

    operations = [
        migrations.RunPython(clear_too_long, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="scout_name",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
    ]
