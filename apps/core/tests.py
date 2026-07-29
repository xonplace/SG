from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.core.models import SystemHelpContent, TrainingAssignment, TrainingAttempt, TrainingQuestion
from apps.core.context_processors import _topbar_notifications
from apps.findings.permissions import REPRESENTATIVE_GROUP
from apps.sgc.models import IsoClause, PublicationStatus, SgcDocument


class TopbarDocumentNotificationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="standard",
            email="standard@example.com",
            password="test-password",
        )
        self.representative = get_user_model().objects.create_user(
            username="representative",
            email="representative@example.com",
            password="test-password",
        )
        group, _created = Group.objects.get_or_create(name=REPRESENTATIVE_GROUP)
        self.representative.groups.add(group)

    def create_incomplete_document(self):
        return SgcDocument.objects.create(
            title="Procedimiento sin version",
            code="SGC-PR-01",
            document_type="procedimiento",
            clause=IsoClause.CLAUSE_8,
            version="",
            file=SimpleUploadedFile("procedimiento-sin-version.pdf", b"pdf"),
            status=PublicationStatus.PUBLISHED,
        )

    def test_standard_user_does_not_receive_document_control_alerts(self):
        self.create_incomplete_document()

        notifications = _topbar_notifications(self.user)

        self.assertEqual(notifications["count"], 0)
        self.assertEqual(notifications["items"], [])

    def test_representative_receives_document_control_alerts(self):
        self.create_incomplete_document()

        notifications = _topbar_notifications(self.representative)

        self.assertGreaterEqual(notifications["count"], 1)
        self.assertTrue(
            any(item["action"] == "Completar versiones" for item in notifications["items"])
        )

    def test_user_receives_pending_training_assignment_notification(self):
        content = SystemHelpContent.objects.create(
            section=SystemHelpContent.Section.TRAINING,
            title="Tratamiento de hallazgos",
            content="Contenido",
            show_on_training=True,
            is_active=True,
            training_category=SystemHelpContent.TrainingCategory.FINDINGS,
        )
        TrainingAssignment.objects.create(content=content, user=self.user, assigned_by=self.representative)

        notifications = _topbar_notifications(self.user)

        self.assertEqual(notifications["count"], 1)
        self.assertTrue(
            any(item["action"] == "Capacitacion asignada" and item["description"] == content.title for item in notifications["items"])
        )

    def test_approved_training_assignment_notification_disappears(self):
        content = SystemHelpContent.objects.create(
            section=SystemHelpContent.Section.TRAINING,
            title="Tratamiento de hallazgos",
            content="Contenido",
            show_on_training=True,
            is_active=True,
            training_category=SystemHelpContent.TrainingCategory.FINDINGS,
        )
        TrainingAssignment.objects.create(content=content, user=self.user, assigned_by=self.representative)
        TrainingQuestion.objects.create(
            content=content,
            question="Pregunta",
            option_a="Incorrecta",
            option_b="Correcta",
            correct_option=TrainingQuestion.CorrectOption.B,
        )
        TrainingAttempt.objects.create(user=self.user, content=content, score=3, total_questions=3, passed=True)

        notifications = _topbar_notifications(self.user)

        self.assertEqual(notifications["count"], 0)
