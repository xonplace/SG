from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_notificationsettings_site_base_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="companyprofile",
            name="activities_label",
            field=models.CharField(default="Actividades SGC", max_length=80, verbose_name="menu actividades SGC"),
        ),
        migrations.AddField(
            model_name="companyprofile",
            name="show_activities_module",
            field=models.BooleanField(default=True, verbose_name="mostrar actividades SGC"),
        ),
    ]
