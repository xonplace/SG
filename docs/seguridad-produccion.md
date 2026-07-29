# Seguridad produccion - Portal SGC

## Variables obligatorias

En produccion el archivo `.env.production` debe contener:

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=clave-larga-unica-y-secreta
DJANGO_ALLOWED_HOSTS=sgc.tecnodata.local,IP_DEL_SERVIDOR
DJANGO_CSRF_TRUSTED_ORIGINS=http://sgc.tecnodata.local,http://IP_DEL_SERVIDOR
```

Si TI publica el sitio por HTTPS, ajustar:

```env
DJANGO_CSRF_TRUSTED_ORIGINS=https://sgc.tecnodata.local
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=False
```

> Activar HSTS solo cuando HTTPS este confirmado y estable.

## Ruta de administracion Django

La ruta del admin puede cambiarse con:

```env
DJANGO_ADMIN_URL=admin-sgc-interno/
```

Recomendacion:

- No publicar `/admin/` con el nombre por defecto en produccion.
- Usar contrasenas robustas.
- Mantener pocos superusuarios.
- Revisar periodicamente usuarios activos.

## Base de datos

- PostgreSQL no debe exponerse hacia la red de usuarios.
- Solo los contenedores internos deben acceder a `db:5432`.
- La clave `POSTGRES_PASSWORD` debe ser distinta a desarrollo.
- `DATABASE_URL` debe usar la misma clave definida para PostgreSQL.

## Archivos cargados

El volumen `mediafiles` contiene evidencias y archivos subidos por usuarios.

Debe respaldarse junto con la base de datos, porque ambos forman la trazabilidad del sistema.

## Respaldos

Scripts disponibles:

```bash
scripts/backup_production.sh
scripts/restore_production.sh backups/production/YYYYMMDD-HHMMSS
```

Frecuencia sugerida:

- Diario: base de datos + media.
- Semanal: respaldo completo de la MV o snapshot.
- Antes de cada actualizacion: respaldo manual.

## Acceso recomendado

- Acceso interno por red corporativa o VPN.
- HTTPS si se publica fuera del segmento local.
- SSH solo para administradores tecnicos.
- No almacenar `.env.production` en GitHub.
