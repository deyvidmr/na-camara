"""O que coletar da Câmara dos Deputados e de onde."""
from dataclasses import dataclass
from datetime import date

BASE_ARQUIVOS = "https://dadosabertos.camara.leg.br/arquivos"
BASE_API = "https://dadosabertos.camara.leg.br/api/v2"

# Legislatura 57 (2023-2027). É o escopo inicial do projeto.
ANO_INICIAL = 2023

# Temas de projetos são pequenos e precisamos de todos os anos:
# votações atuais tratam de projetos antigos (ex.: PL 9543/2018, PEC 293/2004).
ANO_INICIAL_TEMAS = 1990


@dataclass(frozen=True)
class Conjunto:
    nome: str             # nome do arquivo na Câmara, ex.: votacoesVotos
    anual: bool = True    # um arquivo por ano?
    ano_inicial: int = ANO_INICIAL

    def url(self, ano: int | None) -> str:
        arquivo = f"{self.nome}-{ano}.csv" if self.anual else f"{self.nome}.csv"
        return f"{BASE_ARQUIVOS}/{self.nome}/csv/{arquivo}"

    def anos(self) -> list[int | None]:
        if not self.anual:
            return [None]
        return list(range(self.ano_inicial, date.today().year + 1))


CONJUNTOS = [
    Conjunto("votacoes"),
    Conjunto("votacoesVotos"),
    Conjunto("votacoesOrientacoes"),
    Conjunto("votacoesProposicoes"),
    Conjunto("votacoesObjetos"),
    Conjunto("proposicoes"),
    Conjunto("proposicoesAutores"),
    Conjunto("proposicoesTemas", ano_inicial=ANO_INICIAL_TEMAS),
    Conjunto("deputados", anual=False),
]

# Tabelas de referência que só existem na API (pequenas, recarregadas sempre).
REFERENCIAS = [
    "proposicoes/codTema",
    "proposicoes/siglaTipo",
    "proposicoes/codSituacao",
]
