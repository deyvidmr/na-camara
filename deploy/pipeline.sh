#!/usr/bin/env bash
# Sequência diária: coleta -> transformação -> projetos antigos citados -> IA -> transformação.
# A segunda passada do dbt incorpora os projetos antigos que a primeira descobriu que faltavam
# e as avaliações novas da IA.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== $(date -Is) início"
docker compose run --rm coletor raw
docker compose run --rm dbt build
docker compose run --rm coletor raw proposicoes
# A IA só avalia projetos ainda não avaliados. Se ela falhar (sem crédito, API fora do ar),
# o resto do pipeline continua e os projetos ficam para o dia seguinte.
docker compose run --rm ia relevancia || echo "!! IA falhou; seguindo sem as avaliações novas"
docker compose run --rm dbt build
echo "== $(date -Is) fim"
