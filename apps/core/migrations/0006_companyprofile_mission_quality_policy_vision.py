from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_companyprofile_show_processes_module"),
    ]

    operations = [
        migrations.AddField(
            model_name="companyprofile",
            name="mission",
            field=models.TextField(blank=True, verbose_name="mision"),
        ),
        migrations.AddField(
            model_name="companyprofile",
            name="quality_policy",
            field=models.TextField(blank=True, verbose_name="politica de la calidad"),
        ),
        migrations.AddField(
            model_name="companyprofile",
            name="vision",
            field=models.TextField(blank=True, verbose_name="vision"),
        ),
    ]
