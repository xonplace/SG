#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "" ]; then
  echo "Uso: scripts/restore_production.sh backups/production/YYYYMMDD-HHMMSS"
  exit 1
fi

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
SOURCE_DIR="$1"

if [ ! -f "${SOURCE_DIR}/database.sql" ]; then
  echo "No existe ${SOURCE_DIR}/database.sql"
  exit 1
fi

echo "Restaurando base de datos desde ${SOURCE_DIR}/database.sql..."
docker compose -f "${COMPOSE_FILE}" exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"' < "${SOURCE_DIR}/database.sql"

if [ -f "${SOURCE_DIR}/mediafiles.tar.gz" ]; then
  echo "Restaurando archivos cargados..."
  docker compose -f "${COMPOSE_FILE}" exec -T web sh -c "rm -rf /app/media/* && tar -xzf - -C /app/media" < "${SOURCE_DIR}/mediafiles.tar.gz"
fi

echo "Restauracion finalizada."
