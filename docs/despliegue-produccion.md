# Despliegue productivo - Portal SGC

Esta guia resume la configuracion sugerida para publicar el Portal SGC en una MV productiva usando Docker Compose.

## Servicios productivos

- `web`: aplicacion Django ejecutada con Gunicorn.
- `nginx`: proxy HTTP, publica `/static/` y `/media/`.
- `db`: PostgreSQL 16 con volumen persistente.

El archivo productivo es:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## Archivos requeridos

En la MV deben existir:

- `docker-compose.prod.yml`
- `Dockerfile`
- `deploy/nginx/default.conf`
- `.env.production`
- codigo fuente del proyecto

El archivo `.env.production` debe crearse desde `.env.production.example` y no debe subirse a GitHub.

## Variables criticas

- `DJANGO_SECRET_KEY`: clave segura y exclusiva de produccion.
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS`: DNS o IP real del servidor.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: origen HTTP/HTTPS permitido.
- `POSTGRES_PASSWORD`: clave robusta de base de datos.
- `DATABASE_URL`: debe coincidir con la clave de PostgreSQL.

## Comandos iniciales

Levantar ambiente:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Crear usuario administrador inicial:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Configurar roles base:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py setup_roles
```

Dejar visible solo el modulo de hallazgos:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py configure_findings_only
```

Con esta configuracion, los usuarios autenticados entran directamente a la Bandeja de Hallazgos. Si mas adelante se activan otros modulos del SGC, el acceso vuelve a dirigir al Inicio SGC.

Revisar configuracion productiva:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py check_production_config
```

## Respaldos minimos

Respaldar diariamente:

- Volumen `postgres_data`.
- Volumen `mediafiles`.

Ejemplo respaldo base de datos:

```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U sistema_gestion sistema_gestion > backup_sgc.sql
```

Scripts de apoyo:

```bash
chmod +x scripts/backup_production.sh scripts/restore_production.sh
scripts/backup_production.sh
scripts/restore_production.sh backups/production/YYYYMMDD-HHMMSS
```

Tambien se puede respaldar la MV completa segun politica de TI.

Ver detalle en `docs/seguridad-produccion.md`.

## Consideraciones de red

- Publicar solo `nginx` por puerto 80 o por proxy corporativo.
- No exponer PostgreSQL hacia la red.
- Si se usa HTTPS en un proxy externo, mantener `X-Forwarded-Proto`.
- Si Nginx interno termina HTTPS en el futuro, ajustar `DJANGO_CSRF_TRUSTED_ORIGINS` a `https://...`.

## Modulos visibles en salida inicial

Para la primera salida productiva se habilita:

- Hallazgos

Se ocultan:

- Biblioteca documental
- Certificado ISO
- Procesos
- Comunicados
- Capacitaciones

Los mantenedores siguen dependiendo de permisos por rol.
