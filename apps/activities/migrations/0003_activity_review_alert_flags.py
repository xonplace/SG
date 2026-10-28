from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0002_activity_responsible_users_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="review_alert_24h_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="activity",
            name="review_overdue_alert_sent",
            field=models.BooleanField(default=False),
        ),
    ]
