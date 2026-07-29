# Checklist produccion inicial - Modulo Hallazgos

## Antes de publicar

- [ ] MV creada por TI.
- [ ] Docker Engine instalado.
- [ ] Docker Compose disponible.
- [ ] DNS o IP interna definida.
- [ ] `.env.production` creado con claves reales.
- [ ] `DJANGO_DEBUG=False`.
- [ ] `DJANGO_ALLOWED_HOSTS` configurado.
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` configurado.
- [ ] PostgreSQL sin puerto publicado hacia usuarios.
- [ ] Volumen de base de datos persistente.
- [ ] Volumen de archivos `media` persistente.
- [ ] Politica de respaldo definida.

## Primera puesta en marcha

- [ ] Levantar contenedores con `docker-compose.prod.yml`.
- [ ] Ejecutar migraciones.
- [ ] Ejecutar `collectstatic`.
- [ ] Crear superusuario.
- [ ] Ejecutar `setup_roles`.
- [ ] Ejecutar `configure_findings_only`.
- [ ] Confirmar que al iniciar sesion carga la Bandeja de Hallazgos.
- [ ] Configurar usuarios y roles.
- [ ] Configurar plazos, areas, procesos y fuentes.
- [ ] Validar registro de hallazgo publico.
- [ ] Validar flujo del Representante de la Gerencia.
- [ ] Validar carga de evidencias.
- [ ] Validar bandeja, Mis tareas, Vencidos y Reportes.

## Pendiente posterior

- [ ] Activar SMTP productivo.
- [ ] Configurar alertas por correo.
- [ ] Evaluar SSO con Microsoft Entra ID.
- [ ] Implementar flujo GitHub con ramas `main` y `develop`.
- [ ] Crear procedimiento de despliegue controlado.
