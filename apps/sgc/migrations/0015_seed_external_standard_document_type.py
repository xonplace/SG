from django.db import migrations


def seed_external_standard_document_type(apps, schema_editor):
    DocumentType = apps.get_model("sgc", "SgcDocumentType")
    DocumentType.objects.update_or_create(
        value="normativa-externa",
        defaults={"name": "Normativa externa", "order": 75, "is_active": True},
    )


def remove_external_standard_document_type(apps, schema_editor):
    DocumentType = apps.get_model("sgc", "SgcDocumentType")
    DocumentType.objects.filter(value="normativa-externa").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("sgc", "0014_seed_certificate_document_type"),
    ]

    operations = [
        migrations.RunPython(seed_external_standard_document_type, remove_external_standard_document_type),
    ]
