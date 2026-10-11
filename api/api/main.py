"""API de leitura do projeto cívico: temas, projetos votados e votos."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from . import esquemas as e
from .db import consultar, consultar_um, pool


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    pool.open(wait=True)
    yield
    pool.close()


app = FastAPI(
    title="Projeto cívico",
    description=(
        "Projetos de lei votados na Câmara dos Deputados, organizados por temas do dia a dia, "
        "com os votos de cada deputado e a orientação de cada partido. "
        "Fonte: Dados Abertos da Câmara. A relevância por tema é avaliada por IA, com revisão humana."
    ),
    version="0.1.0",
    lifespan=ciclo_de_vida,
)


def _placar(linha: dict) -> e.Placar:
    return e.Placar(sim=linha["votos_sim"], nao=linha["votos_nao"],
                    outros=linha["votos_outros"], pct_sim=linha.get("pct_sim"))


def _pct(sim: int, nao: int) -> float | None:
    return round(100 * sim / (sim + nao), 1) if sim + nao else None


@app.get("/saude", tags=["infra"])
def saude():
    consultar("select 1")
    return {"status": "ok"}


@app.get("/temas", response_model=list[e.Tema], tags=["temas"])
def listar_temas():
    """Temas do dia a dia, com quantos projetos votados cada um tem."""
    return consultar("""
        select t.tema_slug, t.nome, t.descricao, count(c.proposicao_id)::int as projetos
        from editorial.tema_cidadao t
        left join app.projetos_curados c using (tema_slug)
        group by t.tema_slug, t.nome, t.descricao, t.ordem
        order by t.ordem
    """)


@app.get("/temas/{tema_slug}/projetos", response_model=list[e.ProjetoResumo], tags=["temas"])
def projetos_do_tema(
    tema_slug: str,
    ordem: str = Query("relevancia", pattern="^(relevancia|recentes|divididos)$",
                       description="relevancia: grau da IA; recentes: data da votação; "
                                   "divididos: placares mais apertados primeiro"),
):
    """Projetos votados relacionados ao tema, com o placar da votação principal."""
    if not consultar_um("select 1 from editorial.tema_cidadao where tema_slug = %(t)s", {"t": tema_slug}):
        raise HTTPException(404, f"tema '{tema_slug}' não existe")
    ordenacao = {
        "relevancia": "grau desc, data_votacao desc",
        "recentes": "data_votacao desc",
        "divididos": "abs(coalesce(pct_sim, 100) - 50), data_votacao desc",
    }[ordem]
    linhas = consultar(f"""
        select * from app.projetos_curados where tema_slug = %(t)s order by {ordenacao}
    """, {"t": tema_slug})
    return [e.ProjetoResumo(**l, placar=_placar(l)) for l in linhas]


@app.get("/projetos/{proposicao_id}", response_model=e.Projeto, tags=["projetos"])
def projeto(proposicao_id: int):
    """Um projeto: dados oficiais, autores, temas, votação principal e demais votações do texto."""
    p = consultar_um("""
        select proposicao_id, nome, ementa, situacao, apresentada_em, url_inteiro_teor
        from core.proposicao where proposicao_id = %(id)s
    """, {"id": proposicao_id})
    if not p:
        raise HTTPException(404, f"projeto {proposicao_id} não encontrado")

    autores = consultar("""
        select nome_autor as nome, tipo_autor as tipo, partido, uf
        from core.proposicao_autor where proposicao_id = %(id)s
        order by proponente desc, ordem_assinatura
    """, {"id": proposicao_id})
    temas = consultar("""
        select tema_slug, tema, grau, justificativa from app.projetos_curados
        where proposicao_id = %(id)s order by grau desc, tema
    """, {"id": proposicao_id})
    principal = consultar_um("select votacao_id from app.projetos_votados where proposicao_id = %(id)s",
                             {"id": proposicao_id})
    votacoes = consultar("""
        select v.votacao_id, v.data, v.tipo, v.descricao, v.aprovada, v.votos_sim, v.votos_nao, v.votos_outros
        from core.votacao v join core.votacao_proposicao vp using (votacao_id)
        where vp.proposicao_id = %(id)s and v.plenario and v.nominal
          and v.tipo in ('texto_principal', 'texto_senado')
        order by v.registrada_em
    """, {"id": proposicao_id})
    resumos = [e.VotacaoResumo(**v, placar=e.Placar(sim=v["votos_sim"], nao=v["votos_nao"],
               outros=v["votos_outros"], pct_sim=_pct(v["votos_sim"], v["votos_nao"])))
               for v in votacoes]
    id_principal = principal["votacao_id"] if principal else None
    return e.Projeto(
        **p,
        autores=autores,
        temas=temas,
        votacao_principal=next((v for v in resumos if v.votacao_id == id_principal), None),
        outras_votacoes=[v for v in resumos if v.votacao_id != id_principal],
    )


@app.get("/votacoes/{votacao_id}", response_model=e.Votacao, response_model_exclude_none=True,
         tags=["votações"])
def votacao(votacao_id: str, incluir_votos: bool = Query(False, description="lista o voto de cada deputado")):
    """Uma votação: placar, orientação das lideranças, votos e orientação por partido."""
    v = consultar_um("""
        select v.votacao_id, v.data, v.tipo, v.descricao, v.aprovada, v.secreta,
               v.votos_sim, v.votos_nao, v.votos_outros, vp.proposicao_id, p.nome as projeto
        from core.votacao v
        left join core.votacao_proposicao vp using (votacao_id)
        left join core.proposicao p using (proposicao_id)
        where v.votacao_id = %(id)s
    """, {"id": votacao_id})
    if not v:
        raise HTTPException(404, f"votação {votacao_id} não encontrada")

    liderancas = consultar("""
        select sigla_bancada as bancada, orientacao from core.orientacao
        where votacao_id = %(id)s and tipo_bancada = 'lideranca' order by sigla_bancada
    """, {"id": votacao_id})
    partidos = consultar("""
        select vo.partido,
               count(*) filter (where vo.voto = 'sim')::int as sim,
               count(*) filter (where vo.voto = 'nao')::int as nao,
               count(*) filter (where vo.voto not in ('sim', 'nao'))::int as outros,
               op.orientacao, op.fonte_bancada as orientacao_fonte, op.fonte_origem as orientacao_origem
        from core.voto vo
        left join core.orientacao_partido op on op.votacao_id = vo.votacao_id and op.partido = vo.partido
        where vo.votacao_id = %(id)s and vo.partido is not null
        group by vo.partido, op.orientacao, op.fonte_bancada, op.fonte_origem
        order by count(*) desc, vo.partido
    """, {"id": votacao_id})
    votos = None
    if incluir_votos:
        votos = consultar("""
            select deputado_id, deputado_nome as nome, partido, uf, voto from core.voto
            where votacao_id = %(id)s order by deputado_nome
        """, {"id": votacao_id})
    return e.Votacao(
        **v,
        placar=e.Placar(sim=v["votos_sim"], nao=v["votos_nao"], outros=v["votos_outros"],
                        pct_sim=_pct(v["votos_sim"], v["votos_nao"])),
        liderancas=liderancas,
        partidos=partidos,
        votos=votos,
    )
