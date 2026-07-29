# Control de cambios con GitHub

Este documento define el flujo recomendado para desarrollar, probar y publicar cambios del Portal SGC sin afectar produccion.

## Objetivo

Mantener una separacion clara entre:

- Desarrollo local.
- Version validada.
- Produccion.

## Ramas recomendadas

### `main`

Rama estable. Debe representar lo que esta publicado o listo para publicar en produccion.

Reglas:

- No desarrollar directamente sobre `main`.
- Solo fusionar cambios probados.
- Cada despliegue productivo debe salir desde esta rama.

### `develop`

Rama de trabajo diario.

Reglas:

- Nuevas funcionalidades se integran aqui.
- Se prueban localmente antes de pasar a `main`.
- Puede contener cambios aun no liberados.

### Ramas de funcionalidad

Formato sugerido:

```text
feature/nombre-corto
fix/nombre-corto
hotfix/nombre-corto
```

Ejemplos:

- `feature/smtp-alertas`
- `feature/sso-entra-id`
- `fix/plazo-correccion`
- `hotfix/error-login-produccion`

## Flujo normal

1. Crear rama desde `develop`.
2. Implementar cambios.
3. Probar localmente.
4. Registrar cambios en `CHANGELOG.md` si aplica.
5. Fusionar a `develop`.
6. Validar con usuario clave.
7. Fusionar a `main`.
8. Desplegar produccion desde `main`.
9. Crear tag de version si corresponde.

## Versionado sugerido

Usar formato:

```text
v1.0.0
v1.1.0
v1.1.1
```

Ejemplo:

- `v1.0.0`: primera salida productiva Hallazgos.
- `v1.1.0`: activacion SMTP.
- `v1.2.0`: SSO.
- `v2.0.0`: liberacion de modulos SGC adicionales.

## Archivos que no deben subirse

Nunca subir:

- `.env`
- `.env.production`
- Base de datos local.
- Carpeta `media/`.
- Carpeta `staticfiles/`.
- Respaldos productivos.
- Credenciales SMTP.
- Secret keys.

Ya se encuentran considerados en `.gitignore`, pero deben revisarse antes del primer commit.

## Comandos iniciales sugeridos

Cuando decidamos inicializar Git:

```bash
git init
git checkout -b develop
git add .
git commit -m "Version inicial Portal SGC"
git branch -M main
git checkout -b develop
```

Luego se conecta con GitHub segun la URL del repositorio:

```bash
git remote add origin URL_DEL_REPOSITORIO
git push -u origin main
git push -u origin develop
```

> Nota: estos comandos se ejecutaran cuando confirmemos el repositorio GitHub definitivo.
