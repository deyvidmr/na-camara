"""Formato das respostas da API (também gera a documentação em /docs)."""
from datetime import date, datetime

from pydantic import BaseModel


class Tema(BaseModel):
    tema_slug: str
    nome: str
    descricao: str
    projetos: int


class Placar(BaseModel):
    sim: int
    nao: int
    outros: int
    pct_sim: float | None


class ProjetoResumo(BaseModel):
    proposicao_id: int
    projeto: str
    ementa: str
    grau: int
    justificativa: str
    revisao_humana: str | None
    votacao_id: str
    data_votacao: date
    aprovada: bool | None
    placar: Placar


class Autor(BaseModel):
    nome: str
    tipo: str | None
    partido: str | None
    uf: str | None


class TemaDoProjeto(BaseModel):
    tema_slug: str
    tema: str
    grau: int
    justificativa: str


class VotacaoResumo(BaseModel):
    votacao_id: str
    data: date
    tipo: str
    descricao: str
    aprovada: bool | None
    placar: Placar


class Projeto(BaseModel):
    proposicao_id: int
    nome: str
    ementa: str
    situacao: str | None
    apresentada_em: datetime | None
    url_inteiro_teor: str | None
    autores: list[Autor]
    temas: list[TemaDoProjeto]
    votacao_principal: VotacaoResumo | None
    outras_votacoes: list[VotacaoResumo]


class Lideranca(BaseModel):
    bancada: str
    orientacao: str | None


class Partido(BaseModel):
    partido: str
    sim: int
    nao: int
    outros: int
    orientacao: str | None
    orientacao_fonte: str | None
    orientacao_origem: str | None


class Voto(BaseModel):
    deputado_id: int
    nome: str
    partido: str | None
    uf: str | None
    voto: str


class Votacao(VotacaoResumo):
    proposicao_id: int | None
    projeto: str | None
    secreta: bool
    liderancas: list[Lideranca]
    partidos: list[Partido]
    votos: list[Voto] | None = None
