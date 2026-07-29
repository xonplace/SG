from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("findings", "0006_deadlinesetting_correction_review_days_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="finding",
            name="similar_previous_finding_record",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="related_similar_findings",
                to="findings.finding",
                verbose_name="hallazgo previo similar",
            ),
        ),
        migrations.AlterField(
            model_name="finding",
            name="classification",
            field=models.CharField(
                blank=True,
                choices=[
                    ("no_conformidad_mayor", "No Conformidad Mayor"),
                    ("no_conformidad_menor", "No Conformidad Menor"),
                    ("oportunidad_mejora", "Oportunidad de Mejora"),
                    ("oportunidad", "Oportunidad"),
                ],
                max_length=40,
                verbose_name="clasificacion",
            ),
        ),
    ]
