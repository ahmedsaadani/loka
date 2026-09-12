from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Extensions PostgreSQL : btree_gist pour la contrainte d'exclusion des réservations."""

    initial = True
    dependencies: list[tuple[str, str]] = []
    operations = [BtreeGistExtension()]
