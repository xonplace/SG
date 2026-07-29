from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import SystemHelpContent, TrainingAssignment, TrainingAttempt, TrainingCompletion, TrainingQuestion
from .forms import SgcDocumentForm, TrainingEvaluationForm
from .models import DocumentEventType, DocumentType, IsoClause, PublicationStatus, SgcDocument, SgcDocumentEvent, SgcDocumentType


class DocumentVersionControlTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="document-admin",
            email="document-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)

    def document(self, *, version, status=PublicationStatus.PUBLISHED):
        return SgcDocument.objects.create(
            title="Procedimiento de prueba",
            code="SGC-PR-01",
            document_type="procedimiento",
            clause=IsoClause.CLAUSE_8,
            version=version,
            file=SimpleUploadedFile(f"procedimiento-{version}.pdf", b"pdf"),
            status=status,
            uploaded_by=self.user,
        )

    def test_regular_upload_rejects_duplicate_published_code(self):
        self.document(version="V1")
        form = SgcDocumentForm(
            data={
                "title": "Procedimiento actualizado",
                "code": "sgc-pr-01",
                "document_type": "procedimiento",
                "clause": IsoClause.CLAUSE_8,
                "version": "V2",
                "status": PublicationStatus.PUBLISHED,
            },
            files={"file": SimpleUploadedFile("procedimiento-v2.pdf", b"pdf")},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Nueva version", form.errors["file"][0])

    def test_new_version_obsoletes_all_published_documents_in_family(self):
        first = self.document(version="V1")
        duplicate = self.document(version="V0")

        response = self.client.post(
            reverse("sgc:document_new_version", args=[first.pk]),
            data={
                "title": first.title,
                "code": first.code,
                "document_type": first.document_type,
                "clause": first.clause,
                "version": "V2",
                "process": "",
                "summary": "",
                "status": PublicationStatus.PUBLISHED,
                "replace_previous": "on",
                "file": SimpleUploadedFile("procedimiento-v2.pdf", b"pdf"),
            },
        )

        self.assertEqual(response.status_code, 302)
        first.refresh_from_db()
        duplicate.refresh_from_db()
        replacement = SgcDocument.objects.get(code=first.code, version="V2")

        self.assertEqual(first.status, PublicationStatus.OBSOLETE)
        self.assertEqual(duplicate.status, PublicationStatus.OBSOLETE)
        self.assertEqual(first.replaced_by, replacement)
        self.assertEqual(duplicate.replaced_by, replacement)
        self.assertEqual(replacement.status, PublicationStatus.PUBLISHED)
        self.assertTrue(
            SgcDocumentEvent.objects.filter(
                document=replacement,
                event_type=DocumentEventType.PUBLISHED,
            ).exists()
        )
        self.assertEqual(
            SgcDocumentEvent.objects.filter(event_type=DocumentEventType.REPLACED).count(),
            2,
        )

    def test_new_version_must_change_version_identifier(self):
        previous = self.document(version="V1")
        form = SgcDocumentForm(
            data={
                "title": previous.title,
                "code": previous.code,
                "document_type": previous.document_type,
                "clause": previous.clause,
                "version": "v1",
                "status": PublicationStatus.PUBLISHED,
                "replace_previous": "on",
            },
            files={"file": SimpleUploadedFile("procedimiento-v1.pdf", b"pdf")},
            is_new_version=True,
            previous_document=previous,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("debe ser distinta", form.errors["version"][0])

    def test_obsolete_document_can_be_restored_without_published_version(self):
        document = self.document(version="V1", status=PublicationStatus.OBSOLETE)
        document.obsolete_reason = "Baja de prueba"
        document.replaced_by = None
        document.save()

        response = self.client.post(reverse("sgc:document_restore", args=[document.pk]))

        self.assertRedirects(
            response,
            reverse("sgc:documents"),
            fetch_redirect_response=False,
        )
        document.refresh_from_db()
        self.assertEqual(document.status, PublicationStatus.PUBLISHED)
        self.assertEqual(document.obsolete_reason, "")
        self.assertIsNone(document.obsolete_at)
        self.assertIsNone(document.obsolete_by)
        self.assertTrue(
            document.events.filter(event_type=DocumentEventType.RESTORED).exists()
        )

    def test_obsolete_document_cannot_be_restored_when_family_is_published(self):
        obsolete = self.document(version="V1", status=PublicationStatus.OBSOLETE)
        current = self.document(version="V2")

        response = self.client.post(reverse("sgc:document_restore", args=[obsolete.pk]))

        self.assertRedirects(
            response,
            reverse("sgc:obsolete_documents"),
            fetch_redirect_response=False,
        )
        obsolete.refresh_from_db()
        current.refresh_from_db()
        self.assertEqual(obsolete.status, PublicationStatus.OBSOLETE)
        self.assertEqual(current.status, PublicationStatus.PUBLISHED)

    def test_metadata_update_preserves_file_and_tracks_code_and_version_changes(self):
        document = self.document(version="V1")
        original_file = document.file.name

        response = self.client.post(
            reverse("sgc:document_edit_metadata", args=[document.pk]),
            data={
                "code": "SGC-PR-01-A",
                "version": "V1 corregida",
                "document_type": document.document_type,
                "clause": IsoClause.CLAUSE_7,
                "effective_date": "2026-07-08",
                "process": "",
                "summary": "Resumen documental actualizado.",
            },
        )

        self.assertRedirects(
            response,
            reverse("sgc:document_history", args=[document.pk]),
            fetch_redirect_response=False,
        )
        document.refresh_from_db()
        self.assertEqual(document.code, "SGC-PR-01-A")
        self.assertEqual(document.version, "V1 corregida")
        self.assertEqual(document.file.name, original_file)
        self.assertEqual(document.clause, IsoClause.CLAUSE_7)
        self.assertEqual(document.summary, "Resumen documental actualizado.")
        self.assertTrue(
            document.events.filter(event_type=DocumentEventType.UPDATED).exists()
        )

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    def test_control_dashboard_detects_incomplete_and_duplicate_documents(self):
        first = self.document(version="V1")
        self.document(version="V2")
        first.effective_date = None
        first.process = ""
        first.save(update_fields=["effective_date", "process"])

        response = self.client.get(reverse("sgc:document_control_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_published"], 2)
        self.assertEqual(response.context["incomplete_count"], 2)
        self.assertEqual(response.context["unclassified_count"], 0)
        self.assertEqual(response.context["duplicate_group_count"], 1)
        self.assertIn("missing_code_documents", response.context)
        self.assertIn("missing_version_documents", response.context)
        self.assertIn("missing_effective_date_documents", response.context)
        self.assertIn("unclassified_documents", response.context)
        self.assertNotIn("without_process_count", response.context)

    def test_control_dashboard_export_marks_document_observations(self):
        document = self.document(version="")
        document.effective_date = None
        document.save(update_fields=["effective_date", "updated_at"])

        response = self.client.get(reverse("sgc:document_control_export"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        content = response.content.decode("utf-8-sig")
        self.assertIn("control-documental-sgc.csv", response["Content-Disposition"])
        self.assertIn("Sin version", content)

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    def test_document_matrix_defaults_to_published_documents(self):
        published = self.document(version="V1")
        obsolete = self.document(version="V0", status=PublicationStatus.OBSOLETE)

        response = self.client.get(reverse("sgc:document_matrix"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_status"], PublicationStatus.PUBLISHED)
        self.assertIn(published, list(response.context["documents"]))
        self.assertNotIn(obsolete, list(response.context["documents"]))

    def test_document_matrix_export_respects_filters(self):
        wanted = self.document(version="V1")
        wanted.title = "Manual filtrado"
        wanted.document_type = DocumentType.MANUAL
        wanted.save(update_fields=["title", "document_type", "updated_at"])
        self.document(version="V2")

        response = self.client.get(
            reverse("sgc:document_matrix_export"),
            data={"type": DocumentType.MANUAL, "status": PublicationStatus.PUBLISHED},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("matriz-documental-sgc.csv", response["Content-Disposition"])
        content = response.content.decode("utf-8-sig")
        self.assertIn("Manual filtrado", content)
        self.assertNotIn("Procedimiento de prueba", content)

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    def test_document_history_shows_master_record_sections(self):
        document = self.document(version="V1")

        response = self.client.get(reverse("sgc:document_history", args=[document.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ficha maestra documental")
        self.assertContains(response, "Identificacion documental")
        self.assertContains(response, "Historial de versiones")
        self.assertContains(response, document.title)

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    def test_obsolete_documents_show_traceability_and_retirement_filter(self):
        replacement = self.document(version="V2")
        obsolete = self.document(version="V1", status=PublicationStatus.OBSOLETE)
        obsolete.obsolete_reason = "Reemplazado por version V2."
        obsolete.obsolete_by = self.user
        obsolete.replaced_by = replacement
        obsolete.save(update_fields=["obsolete_reason", "obsolete_by", "replaced_by", "updated_at"])
        manual = SgcDocument.objects.create(
            title="Documento de baja manual",
            code="SGC-DI-01",
            document_type="documento-interno",
            clause=IsoClause.CLAUSE_4,
            version="V1",
            file=SimpleUploadedFile("documento-baja-manual.pdf", b"pdf"),
            status=PublicationStatus.OBSOLETE,
            obsolete_reason="Baja manual de prueba.",
            obsolete_by=self.user,
        )

        response = self.client.get(reverse("sgc:obsolete_documents"), data={"retirement": "replaced"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Documentos obsoletos")
        self.assertContains(response, "Reemplazado por")
        self.assertIn(obsolete, list(response.context["documents"]))
        self.assertNotIn(manual, list(response.context["documents"]))

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    def test_certificates_are_not_flagged_for_missing_code_or_version(self):
        SgcDocumentType.objects.get_or_create(
            value=DocumentType.CERTIFICATE,
            defaults={"name": "Certificado", "order": 70, "is_active": True},
        )
        SgcDocument.objects.create(
            title="Certificado externo ISO",
            code="",
            document_type=DocumentType.CERTIFICATE,
            clause=IsoClause.CLAUSE_1,
            version="",
            effective_date="2026-07-01",
            file=SimpleUploadedFile("certificado-externo.pdf", b"pdf"),
            status=PublicationStatus.PUBLISHED,
            uploaded_by=self.user,
        )

        response = self.client.get(reverse("sgc:document_control_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["missing_code_documents"].count(), 0)
        self.assertEqual(response.context["missing_version_documents"].count(), 0)

    def test_metadata_edit_from_control_returns_to_control_dashboard(self):
        document = self.document(version="V1")

        response = self.client.post(
            f"{reverse('sgc:document_edit_metadata', args=[document.pk])}?next=control",
            data={
                "code": "SGC-PR-01",
                "version": "V1",
                "document_type": document.document_type,
                "clause": document.clause,
                "effective_date": "2026-07-08",
                "process": "",
                "summary": "Actualizado desde control.",
            },
        )

        self.assertRedirects(
            response,
            reverse("sgc:document_control_dashboard"),
            fetch_redirect_response=False,
        )

    def test_same_code_with_different_full_names_are_distinct_documents(self):
        profile_a_v1 = SgcDocument.objects.create(
            title="Perfil de Cargo Ejecutivo de Ventas",
            code="SGC-F7",
            document_type="formulario",
            clause=IsoClause.CLAUSE_7,
            version="V1",
            file=SimpleUploadedFile(
                "SGC-F7-PERFIL_V1 Perfil de Cargo Ejecutivo de Ventas.docx",
                b"docx",
            ),
            status=PublicationStatus.PUBLISHED,
        )
        profile_b = SgcDocument.objects.create(
            title="Perfil de Cargo Gerente Comercial",
            code="SGC-F7",
            document_type="formulario",
            clause=IsoClause.CLAUSE_7,
            version="V1",
            file=SimpleUploadedFile(
                "SGC-F7-PERFIL_V1 Perfil de Cargo Gerente Comercial.docx",
                b"docx",
            ),
            status=PublicationStatus.PUBLISHED,
        )
        profile_a_v2 = SgcDocument.objects.create(
            title="Perfil de Cargo Ejecutivo de Ventas",
            code="SGC-F7",
            document_type="formulario",
            clause=IsoClause.CLAUSE_7,
            version="V2",
            file=SimpleUploadedFile(
                "SGC-F7-PERFIL_V2 Perfil de Cargo Ejecutivo de Ventas.docx",
                b"docx",
            ),
            status=PublicationStatus.PUBLISHED,
        )

        self.assertEqual(profile_a_v1.identity_key, profile_a_v2.identity_key)
        self.assertNotEqual(profile_a_v1.identity_key, profile_b.identity_key)
        self.assertEqual(profile_a_v1.version_family_queryset().count(), 2)
        self.assertEqual(profile_b.version_family_queryset().count(), 1)

    def test_document_type_catalog_uses_formulario_instead_of_formato(self):
        choices = dict(SgcDocumentForm().fields["document_type"].choices)

        self.assertEqual(choices["formulario"], "Formulario")
        self.assertNotIn("formato", choices)
        self.assertTrue(
            SgcDocumentType.objects.filter(value="formulario", is_active=True).exists()
        )


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class TrainingModuleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="training-admin",
            email="training-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.content = SystemHelpContent.objects.create(
            section=SystemHelpContent.Section.TRAINING,
            title="Tratamiento de hallazgos",
            summary="Capacitacion base",
            content="Contenido de prueba",
            show_on_training=True,
            is_active=True,
            estimated_minutes=15,
        )

    def test_training_page_renders_academy_metrics(self):
        response = self.client.get(reverse("sgc:training"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Academia SGC")
        self.assertContains(response, "Tratamiento de hallazgos")
        self.assertContains(response, "Listado de cursos")

    def test_training_assignment_creates_user_assignment(self):
        response = self.client.post(
            reverse("sgc:training_assign", args=[self.content.pk]),
            data={
                "users": [self.user.pk],
                "due_date": "2026-07-31",
                "note": "Capacitacion obligatoria",
            },
        )

        self.assertRedirects(response, reverse("sgc:training"), fetch_redirect_response=False)
        assignment = TrainingAssignment.objects.get(content=self.content, user=self.user)
        self.assertEqual(str(assignment.due_date), "2026-07-31")
        self.assertEqual(assignment.note, "Capacitacion obligatoria")

    def test_my_training_lists_assigned_progress(self):
        TrainingAssignment.objects.create(content=self.content, user=self.user, due_date="2026-07-31", assigned_by=self.user)
        TrainingAttempt.objects.create(user=self.user, content=self.content, score=3, total_questions=5, passed=False)

        response = self.client.get(reverse("sgc:my_training"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mis capacitaciones")
        self.assertContains(response, "Tratamiento de hallazgos")
        self.assertContains(response, "60%")
        self.assertContains(response, "Certificado pendiente")

    def test_training_certificate_requires_completion(self):
        response = self.client.get(reverse("sgc:training_certificate", args=[self.content.pk]))

        self.assertRedirects(response, reverse("sgc:training_detail", args=[self.content.pk]), fetch_redirect_response=False)

    def test_training_certificate_downloads_pdf_when_completed(self):
        TrainingCompletion.objects.create(user=self.user, content=self.content)
        TrainingAttempt.objects.create(user=self.user, content=self.content, score=4, total_questions=5, passed=True)

        response = self.client.get(reverse("sgc:training_certificate", args=[self.content.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("certificado-tratamiento-de-hallazgos.pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-1.4"))

    def test_training_certificate_requires_passing_evaluation(self):
        TrainingAssignment.objects.create(content=self.content, user=self.user, assigned_by=self.user)
        TrainingQuestion.objects.create(
            content=self.content,
            question="Que permite el tratamiento de hallazgos?",
            option_a="Cerrar sin evidencia",
            option_b="Controlar y mejorar",
            correct_option=TrainingQuestion.CorrectOption.B,
        )
        TrainingCompletion.objects.create(user=self.user, content=self.content)
        TrainingAttempt.objects.create(user=self.user, content=self.content, score=1, total_questions=5, passed=False)

        response = self.client.get(reverse("sgc:training_certificate", args=[self.content.pk]))

        self.assertRedirects(response, reverse("sgc:training_detail", args=[self.content.pk]), fetch_redirect_response=False)

        my_training_response = self.client.get(reverse("sgc:my_training"))
        self.assertContains(my_training_response, "20%")
        self.assertContains(my_training_response, "Certificado pendiente")
        self.assertNotContains(my_training_response, 'sg-badge-success">Completada', html=False)

        report_response = self.client.get(reverse("sgc:training_report"))
        self.assertContains(report_response, "1/5 - 20%")
        self.assertContains(report_response, "Pendiente")
        self.assertContains(report_response, "Completadas</span><strong>0</strong>", html=False)

    def test_training_deactivate_hides_content_from_catalog(self):
        response = self.client.post(reverse("sgc:training_deactivate", args=[self.content.pk]))

        self.assertRedirects(response, reverse("sgc:training"), fetch_redirect_response=False)
        self.content.refresh_from_db()
        self.assertFalse(self.content.is_active)

    def test_unassigned_non_general_training_is_locked_for_standard_user(self):
        standard_user = get_user_model().objects.create_user(
            username="training-user",
            email="training-user@example.com",
            password="test-password",
        )
        self.content.training_category = SystemHelpContent.TrainingCategory.FINDINGS
        self.content.save(update_fields=["training_category"])
        self.client.force_login(standard_user)

        response = self.client.get(reverse("sgc:training"))

        self.assertContains(response, "sg-lms-course-locked")
        self.assertContains(response, "No inscrito")

        response = self.client.get(reverse("sgc:training_detail", args=[self.content.pk]))

        self.assertRedirects(response, reverse("sgc:training"), fetch_redirect_response=False)

    def test_general_training_can_be_opened_without_assignment(self):
        standard_user = get_user_model().objects.create_user(
            username="general-training-user",
            email="general-training-user@example.com",
            password="test-password",
        )
        self.content.training_category = SystemHelpContent.TrainingCategory.GENERAL
        self.content.save(update_fields=["training_category"])
        self.client.force_login(standard_user)

        response = self.client.get(reverse("sgc:training_detail", args=[self.content.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tratamiento de hallazgos")

    def test_training_detail_renders_uploaded_video_player(self):
        self.content.video_file = SimpleUploadedFile("curso.mp4", b"video", content_type="video/mp4")
        self.content.save(update_fields=["video_file"])

        response = self.client.get(reverse("sgc:training_detail", args=[self.content.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<video", html=False)
        self.assertContains(response, "empresa/capacitaciones/videos/")

    def test_training_detail_embeds_youtube_video_url(self):
        self.content.video_url = "https://www.youtube.com/watch?v=abc123"
        self.content.save(update_fields=["video_url"])

        response = self.client.get(reverse("sgc:training_detail", args=[self.content.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://www.youtube.com/embed/abc123")

    def test_training_evaluation_completes_when_passed(self):
        question = TrainingQuestion.objects.create(
            content=self.content,
            question="Que permite el tratamiento de hallazgos?",
            option_a="Cerrar sin evidencia",
            option_b="Controlar y mejorar",
            correct_option=TrainingQuestion.CorrectOption.B,
        )

        response = self.client.post(
            reverse("sgc:training_evaluation", args=[self.content.pk]),
            data={
                f"question_{question.pk}": "b",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("sgc:training_evaluation", args=[self.content.pk]), response["Location"])
        self.assertIn("resultado=", response["Location"])
        self.assertTrue(TrainingAttempt.objects.filter(user=self.user, content=self.content, passed=True).exists())
        self.assertTrue(TrainingCompletion.objects.filter(user=self.user, content=self.content).exists())

        result_response = self.client.get(response["Location"])
        self.assertContains(result_response, "Evaluacion aprobada")
        self.assertContains(result_response, "Aceptar")

    def test_training_evaluation_result_popup_when_failed(self):
        question = TrainingQuestion.objects.create(
            content=self.content,
            question="Que permite el tratamiento de hallazgos?",
            option_a="Cerrar sin evidencia",
            option_b="Controlar y mejorar",
            correct_option=TrainingQuestion.CorrectOption.B,
        )

        response = self.client.post(
            reverse("sgc:training_evaluation", args=[self.content.pk]),
            data={
                f"question_{question.pk}": "a",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("resultado=", response["Location"])
        result_response = self.client.get(response["Location"])
        self.assertContains(result_response, "Evaluacion no aprobada")
        self.assertContains(result_response, "Reintentar evaluacion")

    def test_training_evaluation_randomizes_choices_without_breaking_score(self):
        question = TrainingQuestion.objects.create(
            content=self.content,
            question="Que permite el tratamiento de hallazgos?",
            option_a="Cerrar sin evidencia",
            option_b="Controlar y mejorar",
            option_c="Eliminar trazabilidad",
            correct_option=TrainingQuestion.CorrectOption.B,
        )

        with patch("apps.sgc.forms.random.shuffle", side_effect=lambda choices: choices.reverse()):
            form = TrainingEvaluationForm(
                data={"question_%s" % question.pk: "b"},
                questions=[question],
            )

        self.assertEqual([value for value, _label in form.fields[f"question_{question.pk}"].choices], ["c", "b", "a"])
        self.assertTrue(form.is_valid())
        self.assertEqual(form.score(), 1)

    def test_training_report_export_returns_csv(self):
        TrainingAssignment.objects.create(content=self.content, user=self.user, due_date="2026-07-31", assigned_by=self.user)

        response = self.client.get(reverse("sgc:training_report_export"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("reporte-capacitaciones-sgc.csv", response["Content-Disposition"])
        self.assertIn("Tratamiento de hallazgos", response.content.decode("utf-8-sig"))

    def test_training_question_can_be_created_from_site(self):
        response = self.client.post(
            reverse("sgc:training_question_create", args=[self.content.pk]),
            data={
                "question": "Que se debe hacer ante un hallazgo?",
                "option_a": "Registrar evidencia",
                "option_b": "Ignorarlo",
                "option_c": "",
                "option_d": "",
                "correct_option": "a",
                "order": 1,
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("sgc:training_questions", args=[self.content.pk]), fetch_redirect_response=False)
        self.assertTrue(self.content.questions.filter(question__icontains="hallazgo", correct_option="a").exists())

    def test_training_question_can_be_toggled_and_deleted(self):
        question = TrainingQuestion.objects.create(
            content=self.content,
            question="Pregunta temporal",
            option_a="Si",
            option_b="No",
            correct_option=TrainingQuestion.CorrectOption.A,
        )

        response = self.client.post(reverse("sgc:training_question_toggle", args=[question.pk]))
        self.assertRedirects(response, reverse("sgc:training_questions", args=[self.content.pk]), fetch_redirect_response=False)
        question.refresh_from_db()
        self.assertFalse(question.is_active)

        response = self.client.post(reverse("sgc:training_question_delete", args=[question.pk]))
        self.assertRedirects(response, reverse("sgc:training_questions", args=[self.content.pk]), fetch_redirect_response=False)
        self.assertFalse(TrainingQuestion.objects.filter(pk=question.pk).exists())
