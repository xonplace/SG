# Sistema de gestion

Proyecto para administrar hallazgos del Sistema de Gestion de Calidad.

El objetivo inicial es permitir que cualquier colaborador registre un hallazgo y que el area de Calidad pueda validarlo, clasificarlo, asignarlo, hacer seguimiento y cerrarlo con trazabilidad.

## Documentacion inicial

- [Arquitectura inicial](docs/arquitectura-inicial.md)
- [Levantamiento desde documentos actuales](docs/levantamiento-documentos-actuales.md)

## Stack sugerido

- Python
- Django
- PostgreSQL
- Tailwind CSS
- Docker Compose

## Stack definido

- Python 3.12
- Django 5
- PostgreSQL 16
- Tailwind CSS
- Variables de entorno con `.env`
- Docker preparado desde el inicio
- SMTP/Microsoft 365 para notificaciones

## Instalacion local

1. Copiar variables de entorno:

```powershell
Copy-Item .env.example .env
```

Para ejecutar localmente sin Docker, ajustar en `.env`:

```env
DATABASE_URL=sqlite:///db.sqlite3
```

2. Crear entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instalar dependencias Python:

```powershell
pip install -r requirements.txt
```

4. Instalar dependencias frontend:

```powershell
npm install
npm run build:css
```

5. Crear base de datos local inicial y ejecutar servidor:

```powershell
python manage.py migrate
python manage.py runserver
```

## Ejecucion con Docker

Para usar PostgreSQL con Docker, el archivo `.env` debe mantener:

```env
DATABASE_URL=postgres://sistema_gestion:sistema_gestion@db:5432/sistema_gestion
```

```powershell
Copy-Item .env.example .env
docker compose up --build
```

El sitio quedara disponible en `http://localhost:8000`.

Rutas principales:

- `http://localhost:8000`: inicio.
- `http://localhost:8000/hallazgos/`: bandeja de hallazgos.
- `http://localhost:8000/hallazgos/nuevo/`: registro de hallazgo.
- `http://localhost:8000/admin/`: administracion Django.

Rutas de flujo por hallazgo:

- `/hallazgos/<id>/validar/`
- `/hallazgos/<id>/asignar-correccion/`
- `/hallazgos/<id>/registrar-correccion/`
- `/hallazgos/<id>/revisar-correccion/`
- `/hallazgos/<id>/asignar-accion-correctiva/`
- `/hallazgos/<id>/registrar-accion-correctiva/`
- `/hallazgos/<id>/revisar-accion-correctiva/`
- `/hallazgos/<id>/asignar-seguimiento/`
- `/hallazgos/<id>/registrar-seguimiento/`
- `/hallazgos/<id>/revisar-seguimiento/`

Comandos utiles:

```powershell
docker compose exec web python manage.py migrate
docker compose exec web python manage.py setup_roles
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py send_due_alerts
```

## Usuarios y roles

El formulario publico de registro de hallazgos queda disponible en `/hallazgos/nuevo/`.

La bandeja, detalle y acciones del flujo requieren inicio de sesion. Los grupos iniciales se crean con:

```powershell
docker compose exec web python manage.py setup_roles
```

Grupos funcionales:

- Representante de la Gerencia.
- Responsable de Correccion.
- Responsable de Accion Correctiva.
- Responsable de Seguimiento.
- Consulta/Auditor.

Para crear el primer administrador:

```powershell
docker compose exec web python manage.py createsuperuser
```

### Nota para Windows

Docker Desktop requiere virtualizacion y WSL 2. Si Docker muestra el mensaje `Virtualization support not detected`, verificar que WSL este instalado y reiniciar Windows despues de habilitarlo.

Comandos utiles:

```powershell
wsl --status
docker version
```

Si Docker aun no inicia despues del reinicio, revisar en BIOS/UEFI que la virtualizacion del procesador este habilitada.

## Estilo visual

Interfaz minimalista, sobria y limpia, tomando como referencia general el sitio de H&M Chile: fondo blanco, tipografia simple, grillas ordenadas, navegacion clara y bajo uso de elementos decorativos.

## Alcance inicial

- Registro de hallazgos.
- Validacion por Representante de la Gerencia.
- Clasificacion como No Conformidad u Oportunidad de Mejora.
- Asignacion de responsable.
- Tratamiento.
- Seguimiento/verificacion.
- Cierre.
- Consultas y reportes basicos.
