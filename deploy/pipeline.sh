#!/usr/bin/env bash
# Sequência diária: coleta -> transformação -> projetos antigos citados -> transformação.
# A segunda passada do dbt incorpora os projetos antigos que a primeira descobriu que faltavam.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== $(date -Is) início"
docker compose run --rm coletor raw
docker compose run --rm dbt build
docker compose run --rm coletor raw proposicoes
docker compose run --rm dbt build
echo "== $(date -Is) fim"
