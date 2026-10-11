# Projeto cívico (nome provisório)

Ferramenta de consulta que conecta temas do dia a dia (custo de vida, saúde...) a projetos de lei e aos votos reais dos deputados.
Projeto de portfólio: Engenharia de Dados + IA Aplicada.

## Como rodar

```bash
cp .env.example .env            # e troque a senha
docker compose up -d db         # Postgres (só acessível de dentro do servidor)
./deploy/pipeline.sh            # coleta + transformação (dbt) + testes
```

O pipeline roda todo dia às 04:00 (Brasília) via cron (`deploy/cron-coletor`).

## Pipeline

1. **Coletor** (`collector/`): baixa os arquivos anuais da Câmara para `raw`. Pula o que não mudou.
2. **dbt** (`transform/`): `raw` → `staging` (limpeza) → `core` (regras do domínio), com testes.
3. Coletor de novo, só para os anos antigos de projetos citados em votações atuais, e dbt de novo.

## Armadilhas dos dados tratadas na camada core

- O registro da Câmara liga a votação ao projeto mais antigo de um grupo de anexados (a Reforma
  Tributária, PEC 45/2019, aparece como PEC 293/2004). A descrição da votação tem prioridade.
- Projetos antigos são renumerados (PL 2148/2015 hoje aparece como PL 182/2024); o id não muda.
- PDL se chamava PDC antes de 2019.
- Votações secretas registram quem participou, mas não o voto.
- "Sim" responde à pergunta de cada votação: num destaque pode significar manter um trecho.
  Por isso cada votação tem um `tipo` (texto principal, destaque, urgência...).
- Teste: o placar oficial bate com a soma dos votos individuais em todas as votações não secretas.

## Camadas do banco

| Schema | Conteúdo |
|---|---|
| `raw` | Arquivos da Câmara como vieram (tudo texto) + registro de cargas em `raw.carga` |
| `staging` | Limpeza e tipagem de cada arquivo (views do dbt) |
| `core` | Dados limpos e relacionados: `votacao`, `voto`, `votacao_proposicao` |
| `editorial` | Conteúdo nosso: temas do cidadão, explicações, fontes. A importação nunca escreve aqui |
| `app` | Views para o site (a fazer) |

Fonte: [Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/).
