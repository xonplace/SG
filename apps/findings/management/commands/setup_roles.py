from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.findings.permissions import (
    ADMINISTRATOR_GROUP,
    CORRECTION_GROUP,
    CORRECTIVE_ACTION_GROUP,
    QUERY_GROUP,
    REPRESENTATIVE_GROUP,
    VERIFICATION_GROUP,
)


ROLE_PERMISSIONS = {
    ADMINISTRATOR_GROUP: "__all__",
    REPRESENTATIVE_GROUP: [
        "view_finding",
        "add_finding",
        "change_finding",
        "view_correction",
        "add_correction",
        "change_correction",
        "view_correctiveaction",
        "add_correctiveaction",
        "change_correctiveaction",
        "view_effectivenessverification",
        "add_effectivenessverification",
        "change_effectivenessverification",
        "view_evidence",
        "add_evidence",
        "change_evidence",
        "view_findinghistory",
        "view_holiday",
        "add_holiday",
        "change_holiday",
        "view_sgcdocument",
        "add_sgcdocument",
        "change_sgcdocument",
        "delete_sgcdocument",
        "view_sgcofficialform",
        "add_sgcofficialform",
        "change_sgcofficialform",
        "delete_sgcofficialform",
        "view_sgcprocess",
        "add_sgcprocess",
        "change_sgcprocess",
        "delete_sgcprocess",
        "view_sgcprocessversion",
        "add_sgcprocessversion",
        "change_sgcprocessversion",
        "delete_sgcprocessversion",
        "view_isocertificate",
        "add_isocertificate",
        "change_isocertificate",
        "delete_isocertificate",
        "view_sgcupdate",
        "add_sgcupdate",
        "change_sgcupdate",
        "delete_sgcupdate",
        "view_sgcimportantdates",
        "add_sgcimportantdates",
        "change_sgcimportantdates",
        "delete_sgcimportantdates",
    ],
    CORRECTION_GROUP: ["view_finding", "view_correction", "change_correction", "add_evidence", "view_evidence"],
    CORRECTIVE_ACTION_GROUP: [
        "view_finding",
        "view_correctiveaction",
        "change_correctiveaction",
        "add_evidence",
        "view_evidence",
    ],
    VERIFICATION_GROUP: [
        "view_finding",
        "view_effectivenessverification",
        "change_effectivenessverification",
        "add_evidence",
        "view_evidence",
    ],
    QUERY_GROUP: [
        "view_finding",
        "view_correction",
        "view_correctiveaction",
        "view_effectivenessverification",
        "view_evidence",
        "view_findinghistory",
    ],
}


class Command(BaseCommand):
    help = "Crea grupos funcionales iniciales para Sistema de gestion."

    def handle(self, *args, **options):
        for group_name, permission_codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            if permission_codenames == "__all__":
                permissions = Permission.objects.all()
            else:
                permissions = Permission.objects.filter(codename__in=permission_codenames)
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f"Grupo configurado: {group_name}"))
