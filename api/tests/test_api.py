"""Testes de integração: rodam contra o banco real, com fatos conferidos à mão nas fontes oficiais.

Rodar: docker compose run --rm api pytest -q
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app

TARIFA_SOCIAL = 2167882          # PL 9543/2018, virou a Lei 14.898/2024
TARIFA_SOCIAL_VOTACAO = "2167882-83"


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}


def test_temas_tem_projetos(cliente):
    temas = {t["tema_slug"]: t for t in cliente.get("/temas").json()}
    assert "custo_de_vida" in temas
    assert temas["custo_de_vida"]["projetos"] > 0


def test_tema_inexistente(cliente):
    assert cliente.get("/temas/nao-existe/projetos").status_code == 404


def test_tarifa_social_em_custo_de_vida(cliente):
    # a ligação por tema oficial perdia este projeto; a avaliação da IA o recupera
    projetos = cliente.get("/temas/custo_de_vida/projetos").json()
    assert TARIFA_SOCIAL in [p["proposicao_id"] for p in projetos]


def test_ordem_divididos(cliente):
    projetos = cliente.get("/temas/custo_de_vida/projetos", params={"ordem": "divididos"}).json()
    distancias = [abs((p["placar"]["pct_sim"] or 100) - 50) for p in projetos]
    assert distancias == sorted(distancias)


def test_projeto_tarifa_social(cliente):
    p = cliente.get(f"/projetos/{TARIFA_SOCIAL}").json()
    assert p["nome"] == "PL 9543/2018"
    assert p["votacao_principal"]["votacao_id"] == TARIFA_SOCIAL_VOTACAO
    assert p["votacao_principal"]["placar"]["sim"] == 325
    assert p["votacao_principal"]["placar"]["nao"] == 97


def test_votacao_por_partido(cliente):
    v = cliente.get(f"/votacoes/{TARIFA_SOCIAL_VOTACAO}").json()
    partidos = {p["partido"]: p for p in v["partidos"]}
    assert partidos["PL"]["sim"] == 13 and partidos["PL"]["nao"] == 70
    assert partidos["PL"]["orientacao"] == "nao"
    assert sum(p["sim"] for p in v["partidos"]) == v["placar"]["sim"]
    assert {"bancada": "Governo", "orientacao": "sim"} in v["liderancas"]
    assert "votos" not in v


def test_votacao_com_votos(cliente):
    v = cliente.get(f"/votacoes/{TARIFA_SOCIAL_VOTACAO}", params={"incluir_votos": True}).json()
    assert len([x for x in v["votos"] if x["voto"] == "sim"]) == 325


def test_reforma_tributaria_ligada_a_pec_certa(cliente):
    # o registro da Câmara aponta para a PEC 293/2004; a votação foi da PEC 45/2019
    v = cliente.get("/votacoes/259094-136").json()
    assert v["projeto"] == "PEC 45/2019"


def test_projeto_inexistente(cliente):
    assert cliente.get("/projetos/1").status_code == 404
