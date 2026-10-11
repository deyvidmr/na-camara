"""Carga da camada raw: arquivos CSV da Câmara copiados como estão (tudo texto).

Para cada arquivo:
  1. HEAD: se o Last-Modified não mudou desde a última carga, pula.
  2. Baixa para o disco calculando o sha256; se o conteúdo é igual ao da última carga, pula.
  3. Numa transação: apaga as linhas daquele ano e insere o arquivo novo.
     Rodar duas vezes nunca duplica dados.
"""
import csv
import hashlib
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

from psycopg import sql

from .db import snake
from .fontes import BASE_API, CONJUNTOS, REFERENCIAS, Conjunto

log = logging.getLogger(__name__)

PASTA = Path("/data")
USER_AGENT = "projeto-civico-coletor/0.1"
csv.field_size_limit(10_000_000)


def _abrir(url: str, metodo: str = "GET"):
    req = urllib.request.Request(url, method=metodo, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=120)


def _ultima_carga(con, conjunto: str, ano: int | None):
    return con.execute(
        """select sha256, last_modified from raw.carga
           where conjunto = %s and ano is not distinct from %s and status = 'carregado'
           order by iniciado_em desc limit 1""",
        (conjunto, ano),
    ).fetchone()


def _registrar(con, conjunto, ano, url, status, **campos):
    return con.execute(
        """insert into raw.carga (conjunto, ano, url, status, sha256, last_modified, linhas, erro, concluido_em)
           values (%s, %s, %s, %s, %s, %s, %s, %s, now()) returning id""",
        (conjunto, ano, url, status, campos.get("sha256"), campos.get("last_modified"),
         campos.get("linhas"), campos.get("erro")),
    )


def _baixar(url: str, destino: Path) -> str:
    destino.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    tmp = destino.with_suffix(".tmp")
    with _abrir(url) as resp, open(tmp, "wb") as f:
        while bloco := resp.read(1 << 20):
            h.update(bloco)
            f.write(bloco)
    tmp.replace(destino)
    return h.hexdigest()


def _preparar_tabela(con, tabela: str, colunas: list[str]) -> None:
    """Cria a tabela raw se não existir e acrescenta colunas novas que a Câmara venha a publicar."""
    con.execute(sql.SQL("create table if not exists raw.{} (_ano int, _carga_id bigint)").format(
        sql.Identifier(tabela)))
    for c in colunas:
        con.execute(sql.SQL("alter table raw.{} add column if not exists {} text").format(
            sql.Identifier(tabela), sql.Identifier(c)))
    con.execute(sql.SQL("create index if not exists {} on raw.{} (_ano)").format(
        sql.Identifier(f"{tabela}__ano"), sql.Identifier(tabela)))


def carregar_arquivo(con, conj: Conjunto, ano: int | None, forcar: bool = False) -> str:
    url = conj.url(ano)
    rotulo = f"{conj.nome}{'-' + str(ano) if ano else ''}"
    anterior = _ultima_carga(con, conj.nome, ano)

    try:
        with _abrir(url, "HEAD") as resp:
            last_modified = resp.headers.get("Last-Modified")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            log.info("%s: não existe na Câmara (404), ignorado", rotulo)
            return "inexistente"
        raise

    if not forcar and anterior and last_modified and anterior[1] == last_modified:
        log.info("%s: sem mudança (Last-Modified)", rotulo)
        return "sem_mudanca"

    destino = PASTA / conj.nome / url.rsplit("/", 1)[1]
    sha = _baixar(url, destino)
    if not forcar and anterior and anterior[0] == sha:
        log.info("%s: sem mudança (sha256)", rotulo)
        with con.transaction():
            _registrar(con, conj.nome, ano, url, "sem_mudanca", sha256=sha, last_modified=last_modified)
        return "sem_mudanca"

    tabela = snake(conj.nome)
    with open(destino, encoding="utf-8-sig", newline="") as f:
        leitor = csv.reader(f, delimiter=";", quotechar='"')
        colunas = [snake(c) for c in next(leitor)]
        with con.transaction():
            cur = _registrar(con, conj.nome, ano, url, "carregando", sha256=sha, last_modified=last_modified)
            carga_id = cur.fetchone()[0]
            _preparar_tabela(con, tabela, colunas)
            if ano is None:
                con.execute(sql.SQL("delete from raw.{}").format(sql.Identifier(tabela)))
            else:
                con.execute(sql.SQL("delete from raw.{} where _ano = %s").format(sql.Identifier(tabela)), (ano,))

            alvo = sql.SQL(", ").join(map(sql.Identifier, ["_ano", "_carga_id", *colunas]))
            copy_sql = sql.SQL("copy raw.{} ({}) from stdin").format(sql.Identifier(tabela), alvo)
            linhas = 0
            with con.cursor().copy(copy_sql) as copy:
                for n, linha in enumerate(leitor, start=2):
                    if len(linha) != len(colunas):
                        raise ValueError(f"{rotulo} linha {n}: {len(linha)} campos, esperado {len(colunas)}")
                    copy.write_row([ano, carga_id, *(v if v != "" else None for v in linha)])
                    linhas += 1
            con.execute("update raw.carga set status = 'carregado', linhas = %s, concluido_em = now() where id = %s",
                        (linhas, carga_id))
    log.info("%s: %s linhas carregadas", rotulo, f"{linhas:,}".replace(",", "."))
    return "carregado"


def carregar_referencias(con) -> None:
    """Listas de referência da API (temas oficiais, tipos, situações). Pequenas: recarrega sempre."""
    for ref in REFERENCIAS:
        url = f"{BASE_API}/referencias/{ref}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            dados = json.load(resp)["dados"]
        tabela = "ref_" + snake(ref.replace("/", "_"))
        colunas = [snake(c) for c in dados[0]]
        with con.transaction():
            cur = _registrar(con, f"referencias/{ref}", None, url, "carregado", linhas=len(dados))
            carga_id = cur.fetchone()[0]
            _preparar_tabela(con, tabela, colunas)
            con.execute(sql.SQL("delete from raw.{}").format(sql.Identifier(tabela)))
            alvo = sql.SQL(", ").join(map(sql.Identifier, ["_ano", "_carga_id", *colunas]))
            with con.cursor().copy(sql.SQL("copy raw.{} ({}) from stdin").format(sql.Identifier(tabela), alvo)) as copy:
                for item in dados:
                    copy.write_row([None, carga_id, *(str(v) if v not in ("", None) else None for v in item.values())])
        log.info("referência %s: %d itens", ref, len(dados))


def _anos(con, conj: Conjunto) -> list[int | None]:
    anos = conj.anos()
    if conj.anos_extras_sql and con.execute("select to_regclass('core.votacao_proposicao')").fetchone()[0]:
        extras = [r[0] for r in con.execute(conj.anos_extras_sql, {"ano_inicial": conj.ano_inicial})]
        # anos já carregados antes continuam sendo atualizados
        extras += [r[0] for r in con.execute(
            "select distinct ano from raw.carga where conjunto = %s and ano < %s and status = 'carregado'",
            (conj.nome, conj.ano_inicial))]
        anos = sorted(set(extras)) + anos
    return anos


def executar(con, nomes: set[str] | None = None, forcar: bool = False) -> int:
    falhas = 0
    for conj in CONJUNTOS:
        if nomes and conj.nome not in nomes:
            continue
        for ano in _anos(con, conj):
            try:
                carregar_arquivo(con, conj, ano, forcar)
            except Exception as e:  # um arquivo com problema não impede os outros
                falhas += 1
                log.exception("%s %s: erro", conj.nome, ano)
                with con.transaction():
                    _registrar(con, conj.nome, ano, conj.url(ano), "erro", erro=str(e)[:2000])
    if not nomes or "referencias" in nomes:
        carregar_referencias(con)
    return falhas
