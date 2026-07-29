# Changelog

Todas las versiones relevantes del Portal SGC se documentaran en este archivo.

El formato sugerido sigue una estructura simple basada en versiones semanticas:

- `MAJOR`: cambios incompatibles o reestructuraciones grandes.
- `MINOR`: nuevos modulos o funcionalidades compatibles.
- `PATCH`: correcciones menores, ajustes visuales o mejoras internas.

## [1.0.0] - Pendiente liberacion

### Objetivo

Primera version productiva enfocada en el modulo de hallazgos del Sistema de Gestion de Calidad.

### Incluye

- Registro publico de hallazgos.
- Validacion por Representante de la Gerencia.
- Clasificacion como No Conformidad u Oportunidad de Mejora.
- Nomenclatura automatica `H`, `NC` y `OM`.
- Asignacion de responsables por etapa.
- Tratamiento de correccion para No Conformidades.
- Plan de accion para Oportunidades de Mejora.
- Accion correctiva con analisis de causa raiz.
- Seguimiento y verificacion de eficacia.
- Cierre del hallazgo.
- Evidencias por etapa.
- Bandeja de hallazgos con filtros, estados y plazos.
- Mis tareas unificado con pendientes del Representante de la Gerencia.
- Reporte de hallazgos.
- Mantenedores de usuarios, roles, plazos, areas, procesos y fuentes.
- Matriz de permisos por rol.
- Modo productivo inicial solo Hallazgos.
- Docker Compose productivo con Django, PostgreSQL y Nginx.
- Guia de despliegue, seguridad y respaldos.

### Pendiente posterior

- Activacion SMTP productiva.
- SSO con Microsoft Entra ID.
- Flujo GitHub formal con ramas `main` y `develop`.
- Liberacion progresiva de modulos SGC adicionales.
