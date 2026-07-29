import re
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.findings.models import MasterProcess
from apps.sgc.models import DocumentType, IsoClause, PublicationStatus, SgcDocument


ALLOWED_EXTENSIONS = {
    ".bpm",
    ".doc",
    ".docx",
    ".eml",
    ".jpeg",
    ".jpg",
    ".msg",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsm",
    ".xlsx",
}


class Command(BaseCommand):
    help = "Importa a la biblioteca documental SGC archivos ya copiados dentro de MEDIA_ROOT."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="sgc/importados/SGC 2015",
            help="Ruta relativa a MEDIA_ROOT o ruta absoluta dentro del proyecto.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra el resultado sin crear registros.",
        )

    def handle(self, *args, **options):
        source = self.resolve_source(options["source"])
        if not source.exists():
            raise CommandError(f"No existe la ruta de importacion: {source}")

        media_root = Path(settings.MEDIA_ROOT).resolve()
        processes = [process.name for process in MasterProcess.objects.filter(is_active=True)]
        created = 0
        updated = 0
        skipped = 0

        for file_path in sorted(source.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                skipped += 1
                continue

            relative_to_source = file_path.relative_to(source)
            clause = self.infer_clause(relative_to_source)
            if not clause:
                skipped += 1
                continue

            relative_to_media = file_path.resolve().relative_to(media_root)
            file_name = self.to_storage_name(relative_to_media)
            defaults = {
                "title": self.infer_title(file_path),
                "code": self.infer_code(file_path.name),
                "document_type": self.infer_document_type(file_path),
                "clause": clause,
                "version": self.infer_version(file_path.name),
                "process": self.infer_process(relative_to_source, processes),
                "summary": f"Importado desde carpeta documental: {relative_to_source}",
                "status": PublicationStatus.PUBLISHED,
            }

            if options["dry_run"]:
                self.stdout.write(f"DRY-RUN {file_name}")
                continue

            document, was_created = SgcDocument.objects.update_or_create(
                file=file_name,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Importacion terminada. Creados: {created}. Actualizados: {updated}. Omitidos: {skipped}."
            )
        )

    def resolve_source(self, raw_source):
        source = Path(raw_source)
        if not source.is_absolute():
            media_source = Path(settings.MEDIA_ROOT) / source
            project_source = Path(settings.BASE_DIR) / source
            source = media_source if media_source.exists() else project_source
        return source.resolve()

    def infer_clause(self, relative_path):
        first_folder = relative_path.parts[0] if relative_path.parts else ""
        match = re.match(r"^(10|[1-9])\s*-", first_folder)
        if not match:
            return ""
        value = match.group(1)
        return value if value in dict(IsoClause.choices) else ""

    def infer_title(self, file_path):
        title = file_path.stem.replace("_", " ").replace("-", " ")
        title = re.sub(r"\s+", " ", title).strip()
        return title[:220] or file_path.name[:220]

    def infer_code(self, name):
        match = re.search(r"\b(SGC[-_\s]?[A-Z]{1,4}[-_\s]?\d+[A-Z]?)\b", name, re.IGNORECASE)
        if not match:
            return ""
        return re.sub(r"\s+", "-", match.group(1).upper()).replace("_", "-")[:80]

    def infer_version(self, name):
        match = re.search(r"(?:^|[_\-\s])v(?:ersion)?\.?\s*(\d+)", name, re.IGNORECASE)
        return f"v{match.group(1)}" if match else ""

    def infer_document_type(self, file_path):
        text = " ".join(file_path.parts).lower()
        if "politica" in text or "politica" in self.normalize(text):
            return DocumentType.POLICY
        if "manual" in text:
            return DocumentType.MANUAL
        if "proced" in text:
            return DocumentType.PROCEDURE
        if "instruct" in text:
            return DocumentType.INSTRUCTION
        if "formato" in text or "formulario" in text or "sgc-f" in text:
            return DocumentType.FORM
        if "registro" in text:
            return DocumentType.RECORD
        return DocumentType.OTHER

    def infer_process(self, relative_path, processes):
        text = self.normalize(" ".join(relative_path.parts))
        for process in processes:
            if self.normalize(process) in text:
                return process
        return ""

    def normalize(self, value):
        replacements = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ñ": "n",
        }
        normalized = value.lower()
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        return normalized

    def to_storage_name(self, relative_path):
        return str(PurePosixPath(*relative_path.parts))
