from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_systemhelpcontent_passing_percentage"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemhelpcontent",
            name="video_file",
            field=models.FileField(blank=True, upload_to="empresa/capacitaciones/videos/", verbose_name="archivo de video"),
        ),
    ]
