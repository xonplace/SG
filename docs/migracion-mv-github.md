# Migracion a MV mediante GitHub

Objetivo: publicar el Portal SGC en la maquina virtual `srv-docker09`, dejando inicialmente operativo el modulo de hallazgos y manteniendo el desarrollo controlado por GitHub.

## 1. Preparacion local

- No subir archivos sensibles ni datos locales:
  - `.env`
  - `.env.production`
  - `db.sqlite3`
  - `media/`
  - `staticfiles/`
  - `node_modules/`
  - `backups/`
- Subir al repositorio el codigo fuente, migraciones, plantillas, estaticos fuente, Dockerfile, docker compose y documentacion.
- Usar un repositorio privado.

## 2. Ramas recomendadas

- `main`: version productiva estable.
- `develop`: desarrollo y pruebas antes de pasar a produccion.

Flujo sugerido:

1. Trabajar cambios en `develop`.
2. Probar localmente con Docker.
3. Fusionar a `main` solo cuando este aprobado.
4. La MV productiva debe actualizarse desde `main`.

## 3. Preparacion de la MV

Servidor:

- Host: `srv-docker09`
- IP: `192.168.0.106`
- Sistema operativo: Ubuntu Server 26.04 LTS
- Docker y Docker Compose ya validados.

Carpeta sugerida:

```bash
sudo mkdir -p /opt/sgc
sudo chown -R administrador:administrador /opt/sgc
cd /opt/sgc
```

Clonar repositorio:

```bash
git clone URL_DEL_REPOSITORIO .
```

Crear archivo productivo:

```bash
cp .env.production.example .env.production
nano .env.production
```

Valores minimos a ajustar:

```env
DJANGO_SECRET_KEY=clave-segura-generada
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=192.168.0.106,sgc.tecnodata.local
DJANGO_CSRF_TRUSTED_ORIGINS=http://192.168.0.106,http://sgc.tecnodata.local
POSTGRES_PASSWORD=password-seguro
DATABASE_URL=postgres://sistema_gestion:password-seguro@db:5432/sistema_gestion
```

## 4. Levantar produccion

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py setup_roles
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

El contenedor `web` tambien ejecuta `migrate` y `collectstatic` al iniciar, pero estos comandos manuales ayudan a validar el despliegue.

## 5. Dejar solo Hallazgos activo

Cuando el sistema este levantado, configurar el perfil de empresa para ocultar los modulos no productivos:

- Ocultar Sistema de Gestion documental si no sera usado aun.
- Ocultar Procesos.
- Ocultar Formularios.
- Ocultar Capacitaciones.
- Mantener Hallazgos visible.

Tambien se puede ejecutar el comando preparado:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py configure_findings_only
```

## 6. Validaciones funcionales

Probar desde un equipo de la red:

- Abrir `http://192.168.0.106`.
- Iniciar sesion.
- Crear hallazgo.
- Validar hallazgo como Representante de la Gerencia.
- Asignar responsable de Correccion y Accion Correctiva.
- Registrar correccion.
- Registrar accion correctiva.
- Revisar tratamiento.
- Asignar seguimiento.
- Registrar seguimiento.
- Cerrar hallazgo.
- Descargar o visualizar evidencias.

## 7. Respaldos

Solicitar a TI respaldo de:

- Volumen PostgreSQL `postgres_data`.
- Volumen de archivos `mediafiles`.
- Opcionalmente snapshot completo de la MV.

Comando manual de respaldo de base:

```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U sistema_gestion sistema_gestion > backup_sgc.sql
```

## 8. Pendientes posteriores

- Configurar DNS interno.
- Configurar HTTPS.
- Activar SMTP/Office 365 para alertas reales.
- Evaluar SSO Microsoft Entra ID.
- Definir rutina formal de cambios con GitHub.
