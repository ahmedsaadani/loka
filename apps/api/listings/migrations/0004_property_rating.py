from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0003_propertyphoto_auto_enhance"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="rating",
            field=models.DecimalField(
                blank=True, decimal_places=1, help_text="Note moyenne /5", max_digits=2, null=True
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="review_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
