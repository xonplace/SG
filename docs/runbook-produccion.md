# Runbook produccion - Portal SGC

Guia operativa para actualizar o administrar el Portal SGC en la MV productiva.

## Entrar a la MV

```bash
ssh usuario@IP_O_DNS_SERVIDOR
cd /ruta/proyecto/ISO
```

## Ver estado

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 web
docker compose -f docker-compose.prod.yml logs --tail=100 nginx
docker compose -f docker-compose.prod.yml logs --tail=100 db
```

## Actualizacion productiva

Antes de actualizar:

```bash
scripts/backup_production.sh
```

Actualizar codigo desde GitHub:

```bash
git checkout main
git pull origin main
```

Reconstruir y levantar:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Validar configuracion:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py check
docker compose -f docker-compose.prod.yml exec web python manage.py check_production_config
```

## Primer despliegue

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
docker compose -f docker-compose.prod.yml exec web python manage.py setup_roles
docker compose -f docker-compose.prod.yml exec web python manage.py configure_findings_only
```

## Rollback simple

Si la actualizacion falla y existe version anterior en Git:

```bash
git checkout TAG_O_COMMIT_ANTERIOR
docker compose -f docker-compose.prod.yml up -d --build
```

Si ademas se requiere restaurar datos:

```bash
scripts/restore_production.sh backups/production/YYYYMMDD-HHMMSS
```

## Respaldo manual

```bash
scripts/backup_production.sh
```

El respaldo queda en:

```text
backups/production/YYYYMMDD-HHMMSS/
```

Incluye:

- `database.sql`
- `mediafiles.tar.gz`

## Tareas frecuentes

Crear superusuario adicional:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Ejecutar alertas de vencimiento manualmente:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py send_due_alerts
```

Validar servicio automatico de alertas:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps alerts
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=80 alerts
```

El servicio `alerts` revisa plazos cada 60 minutos. No envia correos si el mantenedor de notificaciones tiene las alertas desactivadas.

Ocultar modulos no liberados:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py configure_findings_only
```

## Validacion posterior a despliegue

- [ ] Abre la portada.
- [ ] Inicia sesion.
- [ ] Registra hallazgo de prueba.
- [ ] Valida hallazgo como Representante de la Gerencia.
- [ ] Revisa bandeja y Mis tareas.
- [ ] Carga evidencia.
- [ ] Revisa que los modulos no liberados esten ocultos.
- [ ] Revisa logs sin errores relevantes.
