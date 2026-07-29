from django.db import migrations


def seed_certificate_document_type(apps, schema_editor):
    DocumentType = apps.get_model("sgc", "SgcDocumentType")
    DocumentType.objects.update_or_create(
        value="certificado",
        defaults={"name": "Certificado", "order": 70, "is_active": True},
    )


def remove_certificate_document_type(apps, schema_editor):
    DocumentType = apps.get_model("sgc", "SgcDocumentType")
    DocumentType.objects.filter(value="certificado").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sgc", "0013_seed_flow_and_internal_document_types"),
    ]

    operations = [
        migrations.RunPython(seed_certificate_document_type, remove_certificate_document_type),
    ]
