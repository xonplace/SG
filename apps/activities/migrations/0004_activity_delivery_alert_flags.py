from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0003_activity_review_alert_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="delivery_alert_24h_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="activity",
            name="delivery_overdue_alert_sent",
            field=models.BooleanField(default=False),
        ),
    ]
