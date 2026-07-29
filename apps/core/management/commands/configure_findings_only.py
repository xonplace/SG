from django.core.management.base import BaseCommand

from apps.core.models import CompanyProfile


class Command(BaseCommand):
    help = "Configura el portal para la salida inicial a produccion solo con el modulo de hallazgos visible."

    def handle(self, *args, **options):
        profile = CompanyProfile.current()
        profile.show_findings_module = True
        profile.show_documents_module = False
        profile.show_certificate_module = False
        profile.show_updates_module = False
        profile.show_processes_module = False
        profile.show_training_module = False
        profile.save(
            update_fields=[
                "show_findings_module",
                "show_documents_module",
                "show_certificate_module",
                "show_updates_module",
                "show_processes_module",
                "show_training_module",
                "updated_at",
            ]
        )
        self.stdout.write(self.style.SUCCESS("Modo produccion inicial configurado: solo Hallazgos visible."))
