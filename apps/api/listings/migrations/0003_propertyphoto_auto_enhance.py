from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0002_property_published_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="propertyphoto",
            name="auto_enhance",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Retouche automatique des variantes publiques (niveaux, contraste, "
                    "balance des blancs). L'original privé n'est jamais modifié."
                ),
                verbose_name="retouche automatique",
            ),
        ),
    ]
