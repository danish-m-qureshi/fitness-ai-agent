#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
BACKUP_FILE="${BACKUP_DIR}/fitness_ai_agent_${TIMESTAMP}.sql"

mkdir -p "${BACKUP_DIR}"

cd "${PROJECT_ROOT}"

docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > "${BACKUP_FILE}"

echo "PostgreSQL backup written to ${BACKUP_FILE}"
