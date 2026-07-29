from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_systemhelpcontent_video_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemhelpcontent",
            name="evaluation_time_minutes",
            field=models.PositiveIntegerField(default=5, verbose_name="tiempo evaluacion min."),
        ),
    ]
