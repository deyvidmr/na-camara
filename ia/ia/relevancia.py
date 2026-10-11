"""Relevância de cada projeto votado para cada tema do cidadão.

Uma chamada por projeto avalia todos os temas de uma vez. A versão anterior (relevancia-v1) só
avaliava os pares que a ligação por tema oficial da Câmara sugeria, e com isso perdia projetos:
a Tarifa Social de Água (PL 9543/2018) está classificada como "Previdência e Assistência Social"
e nunca chegava a ser avaliada para "Custo de vida".

O modelo dá um grau de 0 a 3 por tema, com uma justificativa em linguagem simples. Tudo fica em
ia.relevancia_tema com o modelo e a versão do prompt, para revisão humana.
"""
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import anthropic
import psycopg

log = logging.getLogger(__name__)

MODELO = "claude-opus-5-5"
PROMPT_VERSAO = "relevancia-v2"

SISTEMA = """Você ajuda um site de educação cívica, apartidário, a decidir quais projetos de lei mostrar \
para uma pessoa comum que escolheu um tema do dia a dia.

Para cada tema da lista, avalie se o projeto afeta esse tema de forma direta e reconhecível na vida \
de uma família comum.

Grau:
0 = não tem relação com o tema.
1 = relação indireta ou técnica, que uma pessoa leiga não reconheceria.
2 = relação clara com o tema.
3 = afeta diretamente o bolso, o acesso a serviços ou o dia a dia das pessoas nesse tema.

Justificativa: para grau 2 ou 3, uma ou duas frases em português simples dizendo o que o projeto \
muda e por que se relaciona com o tema. Para grau 0 ou 1, uma frase curta. Seja neutro: não diga se \
o projeto é bom ou ruim e não opine sobre partidos ou políticos. Use só a ementa; se ela não permitir \
avaliar, use grau 1 e diga isso. Avalie todos os temas da lista, cada um uma vez."""


def esquema(temas: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "avaliacoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tema_slug": {"type": "string", "enum": temas},
                        "grau": {"type": "integer", "enum": [0, 1, 2, 3]},
                        "justificativa": {"type": "string"},
                    },
                    "required": ["tema_slug", "grau", "justificativa"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["avaliacoes"],
        "additionalProperties": False,
    }


@dataclass
class Projeto:
    proposicao_id: int
    projeto: str
    ementa: str
    temas_oficiais: str | None


@dataclass
class Tema:
    slug: str
    nome: str
    descricao: str


def carregar_temas(con) -> list[Tema]:
    return [Tema(*l) for l in con.execute(
        "select tema_slug, nome, descricao from editorial.tema_cidadao order by ordem")]


def candidatos(con, refazer: bool, limite: int | None) -> list[Projeto]:
    sql = """
        select proposicao_id, projeto, ementa, temas_oficiais
        from app.projetos_votados p
        where ementa is not null
          and (%(refazer)s or not exists (
              select 1 from ia.relevancia_tema r
              where r.proposicao_id = p.proposicao_id
                and r.prompt_versao = %(versao)s and r.status = 'ok'))
        order by proposicao_id
    """
    if limite:
        sql += " limit %(limite)s"
    return [Projeto(*l) for l in con.execute(
        sql, {"refazer": refazer, "versao": PROMPT_VERSAO, "limite": limite})]


def mensagem(p: Projeto, temas: list[Tema]) -> str:
    lista = "\n".join(f"- {t.slug}: {t.nome} ({t.descricao})" for t in temas)
    return (
        f"Temas:\n{lista}\n\n"
        f"Projeto: {p.projeto}\n"
        f"Temas oficiais na Câmara: {p.temas_oficiais or 'não informados'}\n"
        f"Ementa: {p.ementa}"
    )


def classificar(cliente: anthropic.Anthropic, p: Projeto, temas: list[Tema]) -> dict:
    slugs = [t.slug for t in temas]
    resp = cliente.beta.messages.create(
        model=MODELO,
        max_tokens=4000,
        system=SISTEMA,
        messages=[{"role": "user", "content": mensagem(p, temas)}],
        # tarefa de classificação: esforço baixo
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": esquema(slugs)}},
        # se o modelo recusar, a API tenta o modelo recomendado para aquela categoria
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    base = {
        "modelo_resposta": resp.model,
        "tokens_entrada": resp.usage.input_tokens,
        "tokens_saida": resp.usage.output_tokens,
        "request_id": resp._request_id,
    }
    if resp.stop_reason == "refusal":
        categoria = resp.stop_details.category if resp.stop_details else None
        return base | {"status": "recusado", "avaliacoes": {},
                       "erro": f"recusado (categoria: {categoria})"}
    if resp.stop_reason == "max_tokens":
        raise ValueError("resposta cortada por max_tokens")

    texto = next(b.text for b in resp.content if b.type == "text")
    avaliacoes = {a["tema_slug"]: a for a in json.loads(texto)["avaliacoes"]}
    faltando = set(slugs) - set(avaliacoes)
    if faltando:
        raise ValueError(f"temas sem avaliação: {sorted(faltando)}")
    return base | {"status": "ok", "avaliacoes": avaliacoes}


def simular(p: Projeto, temas: list[Tema]) -> dict:
    """Resposta falsa para testar o fluxo sem chamar a API."""
    return {"status": "ok", "modelo_resposta": "simulacao",
            "avaliacoes": {t.slug: {"grau": 1, "justificativa": "[simulação]"} for t in temas}}


def salvar(con, p: Projeto, temas: list[Tema], r: dict, versao: str) -> None:
    # Os tokens e o request_id são da chamada inteira e se repetem em cada tema.
    # Para somar custo, conte cada request_id uma vez só.
    with con.transaction():
        for t in temas:
            a = r.get("avaliacoes", {}).get(t.slug, {})
            con.execute(
                """insert into ia.relevancia_tema
                     (proposicao_id, tema_slug, prompt_versao, grau, justificativa, status, modelo,
                      modelo_resposta, tokens_entrada, tokens_saida, request_id)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   on conflict (proposicao_id, tema_slug, prompt_versao) do update set
                     grau = excluded.grau, justificativa = excluded.justificativa,
                     status = excluded.status, modelo_resposta = excluded.modelo_resposta,
                     tokens_entrada = excluded.tokens_entrada, tokens_saida = excluded.tokens_saida,
                     request_id = excluded.request_id, classificado_em = now(),
                     revisao_humana = null, revisado_em = null""",
                (p.proposicao_id, t.slug, versao, a.get("grau"),
                 a.get("justificativa") or r.get("erro"), r["status"], MODELO,
                 r.get("modelo_resposta"), r.get("tokens_entrada"), r.get("tokens_saida"),
                 r.get("request_id")),
            )


def executar(refazer: bool = False, limite: int | None = None, modo_simulacao: bool = False,
             paralelo: int = 4) -> int:
    with psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        autocommit=True,
    ) as con:
        temas = carregar_temas(con)
        lista = candidatos(con, refazer, limite)
        log.info("%d projetos x %d temas para classificar (prompt %s)", len(lista), len(temas), PROMPT_VERSAO)
        if not lista:
            return 0

        # a simulação grava com outra versão de prompt para não se misturar aos resultados reais
        versao = PROMPT_VERSAO + ("-simulacao" if modo_simulacao else "")
        cliente = None if modo_simulacao else anthropic.Anthropic()
        tarefa = simular if modo_simulacao else (lambda p, t: classificar(cliente, p, t))

        falhas = 0
        tokens = [0, 0]
        with ThreadPoolExecutor(max_workers=paralelo) as pool:
            futuros = {pool.submit(tarefa, p, temas): p for p in lista}
            for n, f in enumerate(as_completed(futuros), start=1):
                p = futuros[f]
                try:
                    r = f.result()
                except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
                    raise  # chave inválida: não adianta continuar
                except anthropic.BadRequestError as e:
                    if "credit balance" in str(e.message):
                        raise  # sem créditos: não adianta continuar
                    falhas += 1
                    log.error("%s: %s", p.projeto, e.message)
                    r = {"status": "erro", "erro": str(e.message)[:500]}
                except (anthropic.APIStatusError, anthropic.APIConnectionError, ValueError, KeyError) as e:
                    falhas += 1
                    log.error("%s: %s", p.projeto, e)
                    r = {"status": "erro", "erro": str(e)[:500]}
                salvar(con, p, temas, r, versao)
                tokens[0] += r.get("tokens_entrada") or 0
                tokens[1] += r.get("tokens_saida") or 0
                if n % 20 == 0 or n == len(lista):
                    log.info("%d/%d projetos (tokens: %d entrada, %d saída)", n, len(lista), *tokens)
        return falhas
