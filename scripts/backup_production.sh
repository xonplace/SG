#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-backups/production}"
STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET_DIR="${BACKUP_DIR}/${STAMP}"

mkdir -p "${TARGET_DIR}"

echo "Creando respaldo de base de datos..."
docker compose -f "${COMPOSE_FILE}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > "${TARGET_DIR}/database.sql"

echo "Creando respaldo de archivos cargados..."
docker compose -f "${COMPOSE_FILE}" exec -T web tar -czf - -C /app/media . > "${TARGET_DIR}/mediafiles.tar.gz"

echo "Respaldo creado en ${TARGET_DIR}"
