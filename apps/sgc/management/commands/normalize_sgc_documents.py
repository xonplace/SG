import re
from collections import Counter
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sgc.models import (
    DocumentEventType,
    PublicationStatus,
    SgcDocument,
    SgcDocumentEvent,
    SgcDocumentType,
)


EFFECTIVE_DATE = date(2024, 7, 1)
DOCUMENT_TYPES = {
    "diagrama-flujo": ("Diagrama de flujo", 15),
    "documento-interno": ("Documento Interno", 25),
    "formulario": ("Formulario", 20),
    "procedimiento": ("Procedimiento", 10),
    "instructivo": ("Instructivo", 30),
}

TYPE_PATTERNS = (
    ("diagrama-flujo", re.compile(r"(?:^|[^A-Z0-9])DF(?:[^A-Z0-9]|$)", re.IGNORECASE)),
    ("documento-interno", re.compile(r"(?:^|[^A-Z0-9])DI(?:[^A-Z0-9]|$)", re.IGNORECASE)),
    ("procedimiento", re.compile(r"(?:^|[^A-Z0-9])PR(?:[^A-Z0-9]|$)", re.IGNORECASE)),
    ("instructivo", re.compile(r"(?:^|[^A-Z0-9])IT(?:[^A-Z0-9]|$)", re.IGNORECASE)),
    ("formulario", re.compile(r"(?:^|[^A-Z0-9])F[\s_-]*\d+", re.IGNORECASE)),
)

VERSION_PATTERN = re.compile(
    r"(?:^|[^A-Z0-9])V(?:ERSION)?[\s._-]*(\d+(?:[._-]\d+)*)",
    re.IGNORECASE,
)


def document_source(document):
    filename = Path(document.file.name).stem if document.file else ""
    return " ".join(part for part in (filename, document.code, document.title) if part)


def infer_document_type(document):
    source = document_source(document)
    for value, pattern in TYPE_PATTERNS:
        if pattern.search(source):
            return value
    return ""


def infer_version(document):
    source = document_source(document)
    match = VERSION_PATTERN.search(source)
    if not match:
        return ""
    number = match.group(1).replace("_", ".")
    return f"V{number}"


class Command(BaseCommand):
    help = "Normaliza vigencia, tipo y version de los documentos SGC no obsoletos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica los cambios. Sin esta opcion solo muestra una simulacion.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        documents = SgcDocument.objects.exclude(status=PublicationStatus.OBSOLETE).order_by("pk")
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
                changes = []
                inferred_type = infer_document_type(document)
                inferred_version = infer_version(document)

                if document.status != PublicationStatus.PUBLISHED:
                    changes.append(("estado", document.get_status_display(), "Publicado"))
                    document.status = PublicationStatus.PUBLISHED

                if document.effective_date != EFFECTIVE_DATE:
                    changes.append(
                        (
                            "vigencia",
                            document.effective_date.isoformat() if document.effective_date else "-",
                            EFFECTIVE_DATE.isoformat(),
                        )
                    )
                    document.effective_date = EFFECTIVE_DATE

                if inferred_type:
                    counters[f"type:{inferred_type}"] += 1
                    if document.document_type != inferred_type:
                        changes.append(("tipo", document.document_type or "-", inferred_type))
                        document.document_type = inferred_type
                else:
                    counters["type:unmatched"] += 1
                    unmatched.append((document.pk, document.file_filename, document.code))

                if inferred_version:
                    counters["version:detected"] += 1
                    if document.version != inferred_version:
                        changes.append(("version", document.version or "-", inferred_version))
                        document.version = inferred_version
                else:
                    counters["version:not_detected"] += 1

                if not changes:
                    counters["unchanged"] += 1
                    continue

                counters["changed"] += 1
                if apply_changes:
                    document.save(
                        update_fields=[
                            "status",
                            "effective_date",
                            "document_type",
                            "version",
                            "updated_at",
                        ]
                    )
                    detail = "Normalizacion masiva: " + "; ".join(
                        f"{field} ({before} -> {after})"
                        for field, before, after in changes
                    )
                    SgcDocumentEvent.objects.create(
                        document=document,
                        family_key=document.document_key,
                        document_label=document.code or document.title,
                        version=document.version,
                        event_type=DocumentEventType.UPDATED,
                        detail=detail,
                    )

            if not apply_changes:
                transaction.set_rollback(True)

        mode = "APLICACION" if apply_changes else "SIMULACION"
        self.stdout.write(self.style.SUCCESS(f"{mode} - documentos revisados: {documents.count()}"))
        self.stdout.write(f"Documentos con cambios: {counters['changed']}")
        self.stdout.write(f"Sin cambios: {counters['unchanged']}")
        for value, (name, _order) in DOCUMENT_TYPES.items():
            self.stdout.write(f"{name}: {counters[f'type:{value}']}")
        self.stdout.write(f"Tipo no reconocido: {counters['type:unmatched']}")
        self.stdout.write(f"Version detectada: {counters['version:detected']}")
        self.stdout.write(f"Version no detectada: {counters['version:not_detected']}")

        if unmatched:
            self.stdout.write("\nDocumentos sin clasificacion automatica:")
            for pk, filename, code in unmatched:
                self.stdout.write(f"- ID {pk} | {code or '-'} | {filename}")
