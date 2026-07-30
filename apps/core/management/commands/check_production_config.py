from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.models import AuthenticationSettings, NotificationSettings


class Command(BaseCommand):
    help = "Revisa configuraciones criticas antes de publicar el Portal SGC en produccion."

    def handle(self, *args, **options):
        checks = [
            (not settings.DEBUG, "DJANGO_DEBUG debe estar en False."),
            (settings.SECRET_KEY != "dev-only-secret-key", "DJANGO_SECRET_KEY debe ser una clave real de produccion."),
            (bool(settings.ALLOWED_HOSTS), "DJANGO_ALLOWED_HOSTS debe incluir DNS o IP productiva."),
            (
                "localhost" not in settings.ALLOWED_HOSTS or len(settings.ALLOWED_HOSTS) > 1,
                "DJANGO_ALLOWED_HOSTS no deberia depender solo de localhost.",
            ),
            (settings.ADMIN_URL != "admin/", "DJANGO_ADMIN_URL deberia cambiar la ruta por defecto /admin/."),
            (bool(settings.DATABASES["default"].get("HOST")), "DATABASE_URL debe apuntar a PostgreSQL."),
            (bool(settings.FIELD_ENCRYPTION_KEY), "FIELD_ENCRYPTION_KEY debe estar configurada para cifrar secretos."),
        ]

        failed = False
        for passed, message in checks:
            if passed:
                self.stdout.write(self.style.SUCCESS(f"OK - {message}"))
            else:
                failed = True
                self.stdout.write(self.style.ERROR(f"REVISAR - {message}"))

        if settings.SECURE_SSL_REDIRECT:
            self.stdout.write(self.style.SUCCESS("OK - Redireccion HTTPS activa."))
        else:
            self.stdout.write(self.style.WARNING("AVISO - Redireccion HTTPS desactivada. Correcto solo si TI publica por HTTP interno o proxy aun no HTTPS."))

        notification_settings = NotificationSettings.current()
        if notification_settings.email_alerts_enabled:
            smtp_ready = notification_settings.is_smtp_configured
            if smtp_ready:
                self.stdout.write(self.style.SUCCESS("OK - Alertas por correo activas y SMTP configurado en mantenedor."))
            else:
                self.stdout.write(self.style.WARNING("AVISO - Alertas por correo activas, pero faltan datos SMTP en mantenedor."))

        authentication_settings = AuthenticationSettings.current()
        if authentication_settings.sso_enabled:
            sso_ready = authentication_settings.is_sso_configured
            if sso_ready:
                self.stdout.write(self.style.SUCCESS("OK - SSO activado y parametros configurados en mantenedor."))
            else:
                self.stdout.write(self.style.WARNING("AVISO - SSO activo, pero faltan parametros en mantenedor."))

        if failed:
            self.stdout.write(self.style.ERROR("Configuracion productiva incompleta. Revisar puntos marcados."))
        else:
            self.stdout.write(self.style.SUCCESS("Configuracion productiva basica validada."))
