# Projeto cívico (nome provisório)

Ferramenta de consulta que conecta temas do dia a dia (custo de vida, saúde...) a projetos de lei e aos votos reais dos deputados.
Projeto de portfólio: Engenharia de Dados + IA Aplicada.

## Como rodar

```bash
cp .env.example .env            # e troque a senha
docker compose up -d db         # Postgres (só acessível de dentro do servidor)
docker compose run --rm coletor raw   # baixa os dados da Câmara para a camada raw
```

## Camadas do banco

| Schema | Conteúdo |
|---|---|
| `raw` | Arquivos da Câmara como vieram (tudo texto) + registro de cargas em `raw.carga` |
| `core` | Dados limpos e relacionados (a fazer) |
| `editorial` | Conteúdo nosso: temas do cidadão, explicações, fontes. A importação nunca escreve aqui |
| `app` | Views para o site (a fazer) |

Fonte: [Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/).
