from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("operacion", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Semilla",
            fields=[
                ("clave", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("aplicada_en", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "semilla",
                "verbose_name_plural": "semillas",
            },
        ),
    ]
