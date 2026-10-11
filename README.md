# Projeto cívico (nome provisório)

Ferramenta de consulta que conecta temas do dia a dia (custo de vida, saúde...) a projetos de lei e aos votos reais dos deputados.
Projeto de portfólio: Engenharia de Dados + IA Aplicada.

## Como rodar

```bash
cp .env.example .env            # e troque a senha; coloque sua ANTHROPIC_API_KEY
docker compose up -d db         # Postgres (só acessível de dentro do servidor)
./deploy/pipeline.sh            # coleta + transformação (dbt) + IA + testes
./deploy/criar_usuario_api.sh   # usuário só de leitura que a API usa
docker compose up -d api        # API em http://localhost:8000 (documentação em /docs)
```

O pipeline roda todo dia às 04:00 (Brasília) via cron (`deploy/cron-coletor`).

## Pipeline

1. **Coletor** (`collector/`): baixa os arquivos anuais da Câmara para `raw`. Pula o que não mudou.
2. **dbt** (`transform/`): `raw` → `staging` (limpeza) → `core` (regras do domínio), com testes.
3. Coletor de novo, só para os anos antigos de projetos citados em votações atuais.
4. **IA** (`ia/`): avalia, para cada projeto votado ainda não avaliado, a relevância (0 a 3) para
   cada tema do cidadão, com uma justificativa em linguagem simples. Resultado em `ia.relevancia_tema`,
   com modelo, versão do prompt e campo de revisão humana.
5. dbt de novo.

## API

FastAPI só de leitura (`api/`), conectada ao banco com um usuário que só tem permissão de `SELECT`.
A documentação interativa fica em `/docs`.

| Rota | O que devolve |
|---|---|
| `GET /temas` | Temas do dia a dia e quantos projetos votados cada um tem |
| `GET /temas/{tema}/projetos?ordem=relevancia\|recentes\|divididos` | Projetos do tema com placar e justificativa da IA |
| `GET /projetos/{id}` | Projeto: dados oficiais, autores, temas, votação principal e demais votações do texto |
| `GET /votacoes/{id}?incluir_votos=true` | Placar, orientação das lideranças, votos e orientação por partido, voto de cada deputado |

Testes de integração com fatos conferidos nas fontes oficiais: `docker compose run --rm api pytest -q`.

## IA aplicada: relevância por tema

A ligação entre temas do cidadão e temas oficiais da Câmara é ampla e erra nos dois sentidos:
traz projetos sem relação (regras para multinacionais em "Custo de vida") e perde projetos óbvios
(a Tarifa Social de Água está em "Previdência e Assistência Social" e não chegava a "Custo de vida").
Por isso a IA avalia cada projeto votado contra todos os temas, numa chamada só, a partir da ementa.

- Modelo: Claude Opus 5.5, esforço baixo, saída em JSON validado por esquema.
- `app.projetos_curados`: grau 2 ou 3, ou confirmado por revisão humana; rejeitados ficam de fora.
- Custo da primeira avaliação completa (167 projetos x 11 temas): cerca de US$ 3.

## Armadilhas dos dados tratadas na camada core

- O registro da Câmara liga a votação ao projeto mais antigo de um grupo de anexados (a Reforma
  Tributária, PEC 45/2019, aparece como PEC 293/2004). A descrição da votação tem prioridade.
- Projetos antigos são renumerados (PL 2148/2015 hoje aparece como PL 182/2024); o id não muda.
- PDL se chamava PDC antes de 2019.
- Votações secretas registram quem participou, mas não o voto.
- "Sim" responde à pergunta de cada votação: num destaque pode significar manter um trecho.
  Por isso cada votação tem um `tipo` (texto principal, destaque, urgência...).
- Projetos que voltam do Senado têm votações das mudanças do Senado (`texto_senado`), separadas
  do texto principal votado pela Câmara.
- Orientações vêm por bloco, com nomes cortados ("Bl UniPpFdrPsdbCid..."). A composição de cada bloco
  está em `editorial.bancada_partido`, com a origem de cada partido: nome do bloco, API ou inferido
  dos dados (partido que nunca orientou separado enquanto o bloco existiu).
- Teste: todo projeto votado no Plenário tem cadastro (nome, ementa). Ele pegou 30 votações cujos
  projetos (entre eles a Reforma Tributária, PEC 45/2019) estavam ligados por id mas sem os dados.
- Teste: o placar oficial bate com a soma dos votos individuais em todas as votações não secretas.

## Camadas do banco

| Schema | Conteúdo |
|---|---|
| `raw` | Arquivos da Câmara como vieram (tudo texto) + registro de cargas em `raw.carga` |
| `staging` | Limpeza e tipagem de cada arquivo (views do dbt) |
| `core` | Dados limpos e relacionados: `votacao`, `voto`, `votacao_proposicao`, `proposicao`, `proposicao_tema`, `proposicao_autor`, `deputado`, `orientacao`, `orientacao_partido` |
| `editorial` | Conteúdo nosso, versionado como seeds do dbt (`transform/seeds/`): temas do cidadão, ligação com os temas oficiais, composição dos blocos partidários. A importação nunca escreve aqui |
| `app` | Views para o site e a API: `projetos_votados`, `projetos_curados` (temas pela IA) e `projetos_por_tema` (temas pela ligação oficial, para comparação) |
| `ia` | Resultados da IA, com modelo, versão do prompt e revisão humana |

Fonte: [Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/).
