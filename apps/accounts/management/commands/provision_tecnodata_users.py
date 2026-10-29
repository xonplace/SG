from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.findings.permissions import (
    CORRECTION_GROUP,
    CORRECTIVE_ACTION_GROUP,
    QUERY_GROUP,
    VERIFICATION_GROUP,
)


USERS = [
    ("Abigail", "Valdivia", "avaldivia@tecnodatasa.cl"),
    ("Yenifer", "Rivera", "yrivera@tecnodatasa.cl"),
    ("Veronica", "Carrasco", "vcarrasco@tecnodatasa.cl"),
    ("Katherine", "Gomez", "kgomez@tecnodatasa.cl"),
    ("Fabrizio", "Montagna", "fmontagna@tecnodatasa.cl"),
    ("Juan Pablo", "Canessa", "jcanessa@tecnodatasa.cl"),
    ("Marcelo", "Jaramillo", "mjaramillo@tecnodatasa.cl"),
    ("Julio", "Esquivel", "jesquivel@tecnodatasa.cl"),
    ("Rodrigo", "Jimenez", "rjimenez@tecnodatasa.cl"),
    ("Angelo", "Pacheco", "apacheco@tecnodatasa.cl"),
    ("Cristian", "Mendieta", "cmendieta@tecnodatasa.cl"),
    ("Henry", "Andrewartha", "handrew@tecnodatasa.cl"),
]

ROLE_NAMES = [CORRECTION_GROUP, CORRECTIVE_ACTION_GROUP, VERIFICATION_GROUP]


class Command(BaseCommand):
    help = "Precrea usuarios Tecnodata para acceso SSO y asignacion de actividades y hallazgos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra los cambios sin guardarlos en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        User = get_user_model()

        with transaction.atomic():
            roles = [Group.objects.get_or_create(name=name)[0] for name in ROLE_NAMES]
            created_count = 0
            updated_count = 0

            for first_name, last_name, email in USERS:
                email = email.lower()
                username = email.split("@", 1)[0]
                user = User.objects.filter(email__iexact=email).first()

                if user is None:
                    user = User.objects.filter(username__iexact=username).first()
                    if user and user.email and user.email.lower() != email:
                        raise CommandError(
                            f"Conflicto: el usuario {username} ya existe con el correo {user.email}."
                        )

                created = user is None
                if created:
                    user = User(username=username)

                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.is_active = True
                user.set_unusable_password()
                user.save()
                user.groups.add(*roles)
                user.groups.remove(*Group.objects.filter(name=QUERY_GROUP))

                if created:
                    created_count += 1
                    status = "CREAR"
                else:
                    updated_count += 1
                    status = "ACTUALIZAR"
                self.stdout.write(f"{status}: {user.get_full_name()} <{user.email}> ({user.username})")

            if dry_run:
                transaction.set_rollback(True)

        mode = "SIMULACION" if dry_run else "APLICADO"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: {created_count} usuarios nuevos, {updated_count} actualizados; "
                f"{len(USERS)} cuentas SSO sin contrasena local."
            )
        )
