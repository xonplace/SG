from django.db import migrations


def seed_document_types(apps, schema_editor):
    DocumentType = apps.get_model("sgc", "SgcDocumentType")
    types = [
        ("diagrama-flujo", "Diagrama de flujo", 15),
        ("documento-interno", "Documento Interno", 25),
    ]
    for value, name, order in types:
        DocumentType.objects.update_or_create(
            value=value,
            defaults={"name": name, "order": order, "is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("sgc", "0012_sgcdocumenttype_alter_sgcdocument_document_type"),
    ]

    operations = [
        migrations.RunPython(seed_document_types, migrations.RunPython.noop),
    ]
