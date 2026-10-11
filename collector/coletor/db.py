import os
import re

import psycopg


def conectar() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def snake(nome: str) -> str:
    """votosSim -> votos_sim; deputado_siglaPartido -> deputado_sigla_partido."""
    nome = nome.strip().lstrip("﻿")
    nome = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", nome)
    return re.sub(r"[^a-z0-9_]", "_", nome.lower())
