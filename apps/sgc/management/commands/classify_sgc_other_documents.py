import re
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sgc.models import (
    DocumentEventType,
    DocumentType,
    PublicationStatus,
    SgcDocument,
    SgcDocumentEvent,
    SgcDocumentType,
)


DOCUMENT_TYPES = {
    DocumentType.CERTIFICATE: ("Certificado", 70),
    DocumentType.EXTERNAL_STANDARD: ("Normativa externa", 75),
    DocumentType.PROCEDURE: ("Procedimiento", 10),
    "documento-interno": ("Documento Interno", 25),
    DocumentType.RECORD: ("Registro", 40),
}

CLASSIFICATION_PATTERNS = (
    (
        DocumentType.CERTIFICATE,
        re.compile(r"certificado|certificacion|certificaci[oó]n|tuv|t[uü]v", re.IGNORECASE),
    ),
    (
        DocumentType.EXTERNAL_STANDARD,
        re.compile(
            r"^(apg|iaf|iso|ley|dfl|ds|dto)\b|codigo\s*trabajo|sernac|subcontratacion|teletrabajo|propiedad\s*intelectual|comite\s*paritario",
            re.IGNORECASE,
        ),
    ),
    (
        DocumentType.PROCEDURE,
        re.compile(r"(?:^|[^a-z0-9])sgc[\s_-]*pg(?:[^a-z0-9]|$)", re.IGNORECASE),
    ),
    (
        "documento-interno",
        re.compile(
            r"(?:^|[^a-z0-9])sgc[\s_-]*(mpt|mc|csp)(?:[^a-z0-9]|$)|organigrama|cumplimiento|informe|planilla|presentaci[oó]n|revision\s+de\s+procesos",
            re.IGNORECASE,
        ),
    ),
    (
        DocumentType.RECORD,
        re.compile(r"actividad|actividades|diagramas\s+de\s+flujos|revisar|\.msg$", re.IGNORECASE),
    ),
)


def document_source(document):
    filename = Path(document.file.name).name if document.file else ""
    return " ".join(part for part in (filename, document.code, document.title) if part)


def infer_document_type(document):
    source = document_source(document)
    for value, pattern in CLASSIFICATION_PATTERNS:
        if pattern.search(source):
            return value
    return ""


class Command(BaseCommand):
    help = "Clasifica documentos vigentes que quedaron como tipo Otro."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica los cambios. Sin esta opcion solo muestra una simulacion.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        documents = SgcDocument.objects.filter(
            status=PublicationStatus.PUBLISHED,
            document_type=DocumentType.OTHER,
        ).order_by("clause", "title")
        counters = Counter()
        unmatched = []

        if apply_changes:
            for value, (name, order) in DOCUMENT_TYPES.items():
                SgcDocumentType.objects.update_or_create(
                    value=value,
                    defaults={"name": name, "order": order, "is_active": True},
                )

        with transaction.atomic():
            for document in documents:
                inferred_type = infer_document_type(document)
                if not inferred_type:
                    counters["unmatched"] += 1
                    unmatched.append((document.pk, document.title, document.file_filename))
                    continue

                counters[f"type:{inferred_type}"] += 1
                counters["changed"] += 1
                if apply_changes:
                    before = document.document_type
                    document.document_type = inferred_type
                    document.save(update_fields=["document_type", "updated_at"])
                    SgcDocumentEvent.objects.create(
                        document=document,
                        family_key=document.document_key,
                        document_label=document.code or document.title,
                        version=document.version,
                        event_type=DocumentEventType.UPDATED,
                        detail=f"Clasificacion documental: tipo ({before} -> {inferred_type}).",
                    )

            if not apply_changes:
                transaction.set_rollback(True)

        mode = "APLICACION" if apply_changes else "SIMULACION"
        self.stdout.write(self.style.SUCCESS(f"{mode} - documentos tipo Otro revisados: {documents.count()}"))
        self.stdout.write(f"Documentos reclasificados: {counters['changed']}")
        for value, (name, _order) in DOCUMENT_TYPES.items():
            self.stdout.write(f"{name}: {counters[f'type:{value}']}")
        self.stdout.write(f"No clasificados: {counters['unmatched']}")

        if unmatched:
            self.stdout.write("\nDocumentos que requieren revision manual:")
            for pk, title, filename in unmatched:
                self.stdout.write(f"- ID {pk} | {title} | {filename}")
