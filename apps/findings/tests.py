from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Correction, CorrectiveAction, EffectivenessVerification, Evidence, Finding
from .permissions import CORRECTION_GROUP, CORRECTIVE_ACTION_GROUP, QUERY_GROUP, REPRESENTATIVE_GROUP
from apps.core.models import NotificationSettings

from .services import notify_assignment, representative_emails
from .views import action_available, display_status_label


class FindingTreatmentReviewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass",
        )
        self.client.force_login(self.user)
        self.query_group = Group.objects.create(name=QUERY_GROUP)
        self.correction_group = Group.objects.create(name=CORRECTION_GROUP)
        self.corrective_action_group = Group.objects.create(name=CORRECTIVE_ACTION_GROUP)
        self.representative_group = Group.objects.create(name=REPRESENTATIVE_GROUP)

    def finding(self, *, status, classification=Finding.Classification.NO_CONFORMIDAD_MENOR):
        return Finding.objects.create(
            title="Hallazgo de prueba",
            description="Descripcion del hallazgo de prueba",
            detection_date=timezone.localdate(),
            reported_by_name="Usuario prueba",
            reported_by_email="usuario@example.com",
            source=Finding.Source.DETECCION_INTERNA,
            classification=classification,
            applies_treatment=True,
            status=status,
        )

    def test_rejected_correction_returns_to_responsible_with_observed_label_and_new_due_date(self):
        finding = self.finding(status=Finding.Status.CORRECCION_EN_REVISION)
        Correction.objects.create(
            finding=finding,
            assigned_to=self.user,
            assigned_at=timezone.now(),
            submitted_at=timezone.now(),
            result="Correccion realizada",
        )

        response = self.client.post(
            reverse("findings:review_correction", args=[finding.pk]),
            data={"is_conform": "False", "review_observations": "Falta evidencia suficiente."},
        )

        self.assertRedirects(response, reverse("findings:detail", args=[finding.pk]), fetch_redirect_response=False)
        finding.refresh_from_db()
        self.assertEqual(finding.status, Finding.Status.EN_CORRECCION)
        self.assertIsNotNone(finding.correction_due_at)
        self.assertIsNone(finding.correction_review_due_at)
        self.assertEqual(display_status_label(finding), "Correccion observada")
        self.assertEqual(finding.history.first().action, "Correccion observada y devuelta")

    def test_rejected_corrective_action_returns_to_responsible_with_observed_label(self):
        finding = self.finding(status=Finding.Status.ACCION_CORRECTIVA_EN_REVISION)
        CorrectiveAction.objects.create(
            finding=finding,
            assigned_to=self.user,
            assigned_at=timezone.now(),
            submitted_at=timezone.now(),
            action_description="Accion propuesta",
        )

        response = self.client.post(
            reverse("findings:review_corrective_action", args=[finding.pk]),
            data={"is_conform": "False", "review_observations": "Debe reforzar causa raiz."},
        )

        self.assertRedirects(response, reverse("findings:detail", args=[finding.pk]), fetch_redirect_response=False)
        finding.refresh_from_db()
        self.assertEqual(finding.status, Finding.Status.EN_ACCION_CORRECTIVA)
        self.assertIsNotNone(finding.corrective_action_due_at)
        self.assertIsNone(finding.corrective_action_review_due_at)
        self.assertEqual(display_status_label(finding), "Accion correctiva observada")
        self.assertEqual(finding.history.first().action, "Accion correctiva observada y devuelta")

    def test_not_effective_verification_returns_to_corrective_action(self):
        finding = self.finding(status=Finding.Status.SEGUIMIENTO_EN_REVISION)
        CorrectiveAction.objects.create(
            finding=finding,
            assigned_to=self.user,
            assigned_at=timezone.now(),
            is_conform=True,
        )
        EffectivenessVerification.objects.create(
            finding=finding,
            assigned_to=self.user,
            assigned_at=timezone.now(),
            submitted_at=timezone.now(),
            result="No se logro evitar recurrencia.",
        )

        response = self.client.post(
            reverse("findings:review_verification", args=[finding.pk]),
            data={"is_effective": "False", "observations": "La accion no fue eficaz."},
        )

        self.assertRedirects(response, reverse("findings:detail", args=[finding.pk]), fetch_redirect_response=False)
        finding.refresh_from_db()
        self.assertEqual(finding.status, Finding.Status.EN_ACCION_CORRECTIVA)
        self.assertIsNotNone(finding.corrective_action_due_at)
        self.assertIsNone(finding.verification_due_at)
        self.assertEqual(display_status_label(finding), "Seguimiento no eficaz - revisar accion correctiva")
        self.assertEqual(finding.history.first().action, "Seguimiento no eficaz, accion devuelta")

    def test_evidence_upload_is_not_available_for_user_who_only_can_view_findings(self):
        viewer = get_user_model().objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="pass",
        )
        viewer.groups.add(self.query_group)
        finding = self.finding(status=Finding.Status.CORRECCION_ASIGNADA)
        Correction.objects.create(
            finding=finding,
            assigned_to=self.user,
            assigned_at=timezone.now(),
        )

        self.assertFalse(action_available(finding, viewer, "upload_evidence"))
        self.client.force_login(viewer)
        response = self.client.get(reverse("findings:upload_evidence", args=[finding.pk]))

        self.assertRedirects(response, reverse("findings:detail", args=[finding.pk]), fetch_redirect_response=False)

    def test_assigned_correction_responsible_can_upload_evidence_for_own_stage(self):
        responsible = get_user_model().objects.create_user(
            username="responsible",
            email="responsible@example.com",
            password="pass",
        )
        responsible.groups.add(self.correction_group)
        finding = self.finding(status=Finding.Status.CORRECCION_ASIGNADA)
        correction = Correction.objects.create(
            finding=finding,
            assigned_to=responsible,
            assigned_at=timezone.now(),
        )

        self.assertTrue(action_available(finding, responsible, "upload_evidence"))
        self.client.force_login(responsible)
        response = self.client.post(
            reverse("findings:upload_evidence", args=[finding.pk]),
            data={
                "phase": "general",
                "description": "Evidencia de correccion",
                "file": SimpleUploadedFile("evidencia.txt", b"contenido", content_type="text/plain"),
            },
        )

        self.assertRedirects(response, reverse("findings:detail", args=[finding.pk]), fetch_redirect_response=False)
        evidence = Evidence.objects.get(finding=finding)
        self.assertEqual(evidence.correction, correction)
        self.assertIsNone(evidence.corrective_action)

    def test_improvement_opportunity_evidence_is_not_available_for_unassigned_user(self):
        viewer = get_user_model().objects.create_user(
            username="om-viewer",
            email="om-viewer@example.com",
            password="pass",
        )
        viewer.groups.add(self.query_group)
        responsible = get_user_model().objects.create_user(
            username="om-responsible",
            email="om-responsible@example.com",
            password="pass",
        )
        responsible.groups.add(self.corrective_action_group)
        finding = self.finding(
            status=Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
            classification=Finding.Classification.OPORTUNIDAD_MEJORA,
        )
        CorrectiveAction.objects.create(
            finding=finding,
            assigned_to=responsible,
            assigned_at=timezone.now(),
        )

        self.assertFalse(action_available(finding, viewer, "upload_evidence"))
        self.client.force_login(viewer)
        response = self.client.get(
            reverse("findings:upload_evidence", args=[finding.pk]),
            data={"phase": "corrective_action"},
        )

        self.assertRedirects(response, reverse("findings:detail", args=[finding.pk]), fetch_redirect_response=False)

    def test_improvement_opportunity_responsible_can_upload_plan_evidence(self):
        responsible = get_user_model().objects.create_user(
            username="plan-responsible",
            email="plan-responsible@example.com",
            password="pass",
        )
        responsible.groups.add(self.corrective_action_group)
        finding = self.finding(
            status=Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
            classification=Finding.Classification.OPORTUNIDAD_MEJORA,
        )
        plan = CorrectiveAction.objects.create(
            finding=finding,
            assigned_to=responsible,
            assigned_at=timezone.now(),
        )

        self.assertTrue(action_available(finding, responsible, "upload_evidence"))
        self.client.force_login(responsible)
        response = self.client.post(
            reverse("findings:upload_evidence", args=[finding.pk]),
            data={
                "phase": "general",
                "description": "Evidencia del plan de accion",
                "file": SimpleUploadedFile("plan.txt", b"contenido", content_type="text/plain"),
            },
        )

        self.assertRedirects(response, reverse("findings:detail", args=[finding.pk]), fetch_redirect_response=False)
        evidence = Evidence.objects.get(finding=finding)
        self.assertEqual(evidence.corrective_action, plan)
        self.assertIsNone(evidence.correction)

    def test_superuser_can_delete_finding_definitively(self):
        finding = self.finding(status=Finding.Status.INGRESADO)
        Evidence.objects.create(
            finding=finding,
            uploaded_by=self.user,
            description="Evidencia de prueba",
            file=SimpleUploadedFile("delete-me.txt", b"contenido", content_type="text/plain"),
        )

        response = self.client.post(reverse("findings:delete", args=[finding.pk]))

        self.assertRedirects(response, reverse("findings:list"), fetch_redirect_response=False)
        self.assertFalse(Finding.objects.filter(pk=finding.pk).exists())
        self.assertFalse(Evidence.objects.filter(finding_id=finding.pk).exists())

    def test_non_superuser_cannot_delete_finding(self):
        viewer = get_user_model().objects.create_user(
            username="delete-viewer",
            email="delete-viewer@example.com",
            password="pass",
        )
        viewer.groups.add(self.query_group)
        finding = self.finding(status=Finding.Status.INGRESADO)

        self.client.force_login(viewer)
        response = self.client.post(reverse("findings:delete", args=[finding.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Finding.objects.filter(pk=finding.pk).exists())

    def test_representative_group_users_are_notification_recipients(self):
        representative = get_user_model().objects.create_user(
            username="representative",
            email="representative@example.com",
            password="pass",
        )
        representative.groups.add(self.representative_group)

        self.assertIn("representative@example.com", representative_emails())

    def test_assignment_notification_goes_only_to_assigned_user(self):
        NotificationSettings.objects.update_or_create(pk=1, defaults={"email_alerts_enabled": True})
        responsible = get_user_model().objects.create_user(
            username="assigned-user",
            email="assigned@example.com",
            password="pass",
        )
        representative = get_user_model().objects.create_user(
            username="notify-representative",
            email="notify-representative@example.com",
            password="pass",
        )
        representative.groups.add(self.representative_group)
        finding = self.finding(status=Finding.Status.SEGUIMIENTO_ASIGNADO)

        with patch("apps.findings.services.send_notification_email") as send_mock:
            notify_assignment(finding, responsible, "seguimiento", due_at=timezone.now())

        recipients = send_mock.call_args.kwargs["recipients"]
        self.assertEqual(recipients, ["assigned@example.com"])
