from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from apps.findings.permissions import CORRECTION_GROUP, CORRECTIVE_ACTION_GROUP, QUERY_GROUP, VERIFICATION_GROUP

from .management.commands.provision_tecnodata_users import ROLE_NAMES, USERS


class ProvisionTecnodataUsersTests(TestCase):
    def test_command_creates_sso_only_users_with_requested_roles(self):
        call_command("provision_tecnodata_users", stdout=StringIO())

        User = get_user_model()
        self.assertEqual(User.objects.filter(email__endswith="@tecnodatasa.cl").count(), len(USERS))
        for first_name, last_name, email in USERS:
            user = User.objects.get(email=email)
            self.assertEqual(user.first_name, first_name)
            self.assertEqual(user.last_name, last_name)
            self.assertTrue(user.is_active)
            self.assertFalse(user.has_usable_password())
            self.assertEqual(
                set(user.groups.values_list("name", flat=True)),
                {CORRECTION_GROUP, CORRECTIVE_ACTION_GROUP, VERIFICATION_GROUP},
            )

    def test_command_is_idempotent_and_preserves_additional_roles(self):
        User = get_user_model()
        existing = User.objects.create_user(
            username="fmontagna",
            email="fmontagna@tecnodatasa.cl",
            password="temporary-password",
        )
        additional_role = Group.objects.create(name="Rol adicional")
        query_role = Group.objects.create(name=QUERY_GROUP)
        existing.groups.add(additional_role, query_role)

        call_command("provision_tecnodata_users", stdout=StringIO())
        call_command("provision_tecnodata_users", stdout=StringIO())

        self.assertEqual(User.objects.filter(email="fmontagna@tecnodatasa.cl").count(), 1)
        existing.refresh_from_db()
        self.assertFalse(existing.has_usable_password())
        self.assertTrue(existing.groups.filter(name=additional_role.name).exists())
        self.assertFalse(existing.groups.filter(name=QUERY_GROUP).exists())
        self.assertTrue(set(ROLE_NAMES).issubset(set(existing.groups.values_list("name", flat=True))))

    def test_dry_run_does_not_persist_users_or_groups(self):
        call_command("provision_tecnodata_users", dry_run=True, stdout=StringIO())

        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertFalse(Group.objects.filter(name__in=ROLE_NAMES).exists())
