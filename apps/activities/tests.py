from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import NotificationSettings
from apps.findings.permissions import REPRESENTATIVE_GROUP

from .models import Activity


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class ActivityReviewRescheduleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.reviewer = User.objects.create_user(
            username="reviewer",
            email="reviewer@example.com",
            password="pass",
        )
        self.responsible = User.objects.create_user(
            username="responsible",
            email="responsible@example.com",
            password="pass",
        )
        self.representative = User.objects.create_user(
            username="representative",
            email="representative@example.com",
            password="pass",
        )
        representative_group = Group.objects.create(name=REPRESENTATIVE_GROUP)
        self.representative.groups.add(representative_group)
        self.original_due = timezone.now() - timedelta(hours=2)
        self.activity = Activity.objects.create(
            title="Actividad de prueba",
            description="Descripcion de prueba",
            origin=Activity.Origin.MANAGEMENT_REVIEW,
            status=Activity.Status.REVIEW_ASSIGNED,
            assigned_to=self.responsible,
            review_assigned_to=self.reviewer,
            review_due_at=self.original_due,
            review_alert_24h_sent=True,
            review_overdue_alert_sent=True,
        )

    def _reschedule(self, user):
        self.client.force_login(user)
        new_due = timezone.localtime(timezone.now() + timedelta(days=2))
        new_due_value = new_due.strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(
            reverse("activities:reschedule_deadline", args=[self.activity.pk]),
            data={
                "new_due_at": new_due_value,
                "reason": "Se requiere tiempo adicional para validar los antecedentes.",
            },
        )
        return response, new_due_value

    def test_review_responsible_can_reschedule_and_alerts_are_reset(self):
        response, new_due_value = self._reschedule(self.reviewer)

        self.assertRedirects(
            response,
            reverse("activities:detail", args=[self.activity.pk]),
            fetch_redirect_response=False,
        )
        self.activity.refresh_from_db()
        self.assertEqual(
            timezone.localtime(self.activity.review_due_at).strftime("%Y-%m-%dT%H:%M"),
            new_due_value,
        )
        self.assertFalse(self.activity.review_alert_24h_sent)
        self.assertFalse(self.activity.review_overdue_alert_sent)
        history = self.activity.history.first()
        self.assertEqual(history.action, "Revision reprogramada")
        self.assertIn("Fecha anterior:", history.comment)
        self.assertIn("Nueva fecha:", history.comment)
        self.assertIn("Motivo:", history.comment)

    def test_management_representative_can_reschedule(self):
        response, _new_due = self._reschedule(self.representative)

        self.assertRedirects(
            response,
            reverse("activities:detail", args=[self.activity.pk]),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.activity.history.count(), 1)

    def test_representative_can_record_no_progress_and_set_new_delivery_commitment(self):
        self.activity.status = Activity.Status.ASSIGNED
        self.activity.delivery_due_at = self.original_due
        self.activity.delivery_alert_24h_sent = True
        self.activity.delivery_overdue_alert_sent = True
        self.activity.save(update_fields=[
            "status",
            "delivery_due_at",
            "delivery_alert_24h_sent",
            "delivery_overdue_alert_sent",
            "updated_at",
        ])

        response, new_due_value = self._reschedule(self.representative)

        self.assertRedirects(
            response,
            reverse("activities:detail", args=[self.activity.pk]),
            fetch_redirect_response=False,
        )
        self.activity.refresh_from_db()
        self.assertEqual(
            timezone.localtime(self.activity.delivery_due_at).strftime("%Y-%m-%dT%H:%M"),
            new_due_value,
        )
        self.assertFalse(self.activity.delivery_alert_24h_sent)
        self.assertFalse(self.activity.delivery_overdue_alert_sent)
        self.assertEqual(self.activity.history.first().action, "Plazo de entrega reprogramado")
        self.assertIn("Motivo:", self.activity.history.first().comment)

    def test_activity_responsible_cannot_reschedule_review(self):
        response, _new_due = self._reschedule(self.responsible)

        self.assertRedirects(
            response,
            reverse("activities:detail", args=[self.activity.pk]),
            fetch_redirect_response=False,
        )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.review_due_at, self.original_due)
        self.assertEqual(self.activity.history.count(), 0)

    def test_past_review_date_is_rejected(self):
        self.client.force_login(self.reviewer)
        response = self.client.post(
            reverse("activities:reschedule_deadline", args=[self.activity.pk]),
            data={
                "new_due_at": (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "reason": "Fecha invalida.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La nueva fecha de compromiso debe ser futura.")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.review_due_at, self.original_due)


class ActivityReviewAlertTests(TestCase):
    def setUp(self):
        self.reviewer = get_user_model().objects.create_user(
            username="reviewer-alert",
            email="reviewer-alert@example.com",
            password="pass",
        )
        self.activity = Activity.objects.create(
            title="Revision proxima",
            description="Actividad que requiere revision.",
            origin=Activity.Origin.MONTHLY_COMMITTEE,
            status=Activity.Status.REVIEW_ASSIGNED,
            review_assigned_to=self.reviewer,
            review_due_at=timezone.now() + timedelta(hours=12),
        )
        settings = NotificationSettings.current()
        settings.email_alerts_enabled = True
        settings.notify_due_24h = True
        settings.notify_overdue = True
        settings.save()

    @patch("apps.findings.management.commands.send_due_alerts.send_notification_email")
    def test_due_command_emails_only_reviewer_and_does_not_repeat(self, send_email):
        call_command("send_due_alerts")

        self.activity.refresh_from_db()
        self.assertTrue(self.activity.review_alert_24h_sent)
        send_email.assert_called_once()
        self.assertEqual(send_email.call_args.kwargs["recipients"], [self.reviewer.email])
        self.assertIn(self.activity.code, send_email.call_args.kwargs["subject"])

        call_command("send_due_alerts")
        send_email.assert_called_once()

    @patch("apps.findings.management.commands.send_due_alerts.send_notification_email")
    def test_delivery_due_alert_is_sent_to_activity_responsible(self, send_email):
        responsible = get_user_model().objects.create_user(
            username="activity-responsible-alert",
            email="responsible-alert@example.com",
            password="pass",
        )
        self.activity.status = Activity.Status.ASSIGNED
        self.activity.assigned_to = responsible
        self.activity.review_assigned_to = None
        self.activity.review_due_at = None
        self.activity.delivery_due_at = timezone.now() + timedelta(hours=10)
        self.activity.save(update_fields=[
            "status",
            "assigned_to",
            "review_assigned_to",
            "review_due_at",
            "delivery_due_at",
            "updated_at",
        ])

        call_command("send_due_alerts")

        self.activity.refresh_from_db()
        self.assertTrue(self.activity.delivery_alert_24h_sent)
        send_email.assert_called_once()
        self.assertEqual(send_email.call_args.kwargs["recipients"], [responsible.email])
        self.assertEqual(send_email.call_args.kwargs["subject"], f"Actividad proxima a vencer: {self.activity.code}")

    @patch("apps.findings.management.commands.send_due_alerts.send_notification_email")
    def test_overdue_command_emails_reviewer_once(self, send_email):
        self.activity.review_due_at = timezone.now() - timedelta(hours=1)
        self.activity.save(update_fields=["review_due_at", "updated_at"])

        call_command("send_due_alerts")

        self.activity.refresh_from_db()
        self.assertTrue(self.activity.review_overdue_alert_sent)
        send_email.assert_called_once()
        self.assertEqual(send_email.call_args.kwargs["recipients"], [self.reviewer.email])
        self.assertEqual(send_email.call_args.kwargs["subject"], f"Revision vencida: {self.activity.code}")

        call_command("send_due_alerts")
        send_email.assert_called_once()
