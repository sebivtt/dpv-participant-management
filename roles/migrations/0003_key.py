import access.keys
from django.db import migrations, models


def give_keys(apps, schema_editor):
    """Jede vorhandene Rolle bekommt eine eigene zufällige Kennung (#191, wie bei den Einheiten in #64).

    Direkt über `update()`, nicht über `save()`: Die Kennung ist keine Änderung, die ins
    Protokoll gehört, und die Regeln beim Speichern betreffen sie nicht.
    """
    model = apps.get_model("roles", "Role")
    for pk in model.objects.values_list("pk", flat=True):
        # Eine doppelte Kennung (bei 100 Bit Zufall praktisch ausgeschlossen) lehnt der
        # nächste Schritt ab, und die ganze Migration wird zurückgenommen.
        model.objects.filter(pk=pk).update(key=access.keys.new_key())


class Migration(migrations.Migration):
    """Zufällige Kennung für Adressen, in drei Schritten wie units/migrations/0003_key.py: Feld ohne Pflicht, füllen, eindeutig."""

    dependencies = [
        ("roles", "0002_role_change"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="key",
            field=models.CharField(max_length=20, null=True, editable=False),
        ),
        migrations.RunPython(give_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="role",
            name="key",
            field=models.CharField(default=access.keys.new_key, editable=False, max_length=20, unique=True),
        ),
    ]
