import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# Usuário só de leitura (api_leitura): a API não consegue alterar nada no banco.
pool = ConnectionPool(
    conninfo=(
        f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
        f"dbname={os.environ['POSTGRES_DB']} "
        f"user={os.environ['API_DB_USER']} "
        f"password={os.environ['API_DB_PASSWORD']}"
    ),
    min_size=1,
    max_size=4,
    kwargs={"row_factory": dict_row},
    open=False,
)


def consultar(sql: str, params: dict | None = None) -> list[dict]:
    with pool.connection() as con:
        return con.execute(sql, params or {}).fetchall()


def consultar_um(sql: str, params: dict | None = None) -> dict | None:
    linhas = consultar(sql, params)
    return linhas[0] if linhas else None
