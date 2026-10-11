#!/usr/bin/env bash
# Cria (ou atualiza) o usuário só de leitura da API com a senha do .env.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q -v ON_ERROR_STOP=1 -f - < db/init/003_api.sql
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q -v ON_ERROR_STOP=1 \
  -c "alter role api_leitura password '${API_DB_PASSWORD}'"
echo "usuário api_leitura pronto"
