# Einladungstext einer Veranstaltung (#358, VER-05).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0006_veroeffentlicht'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='invitation_text',
            field=models.TextField(blank=True, default='', editable=False),
        ),
        migrations.AddField(
            model_name='event',
            name='invitation_version',
            field=models.PositiveIntegerField(default=1, editable=False),
        ),
    ]
