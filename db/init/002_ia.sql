-- Resultados de IA. Ficam separados de raw (dados da Câmara) e de editorial (conteúdo humano).
-- Cada linha guarda modelo, versão do prompt e a revisão humana, para auditar o que a IA decidiu.
create schema if not exists ia;

create table if not exists ia.relevancia_tema (
    proposicao_id    bigint      not null,
    tema_slug        text        not null,
    prompt_versao    text        not null,
    grau             int         check (grau between 0 and 3),
    justificativa    text,
    status           text        not null,      -- ok | recusado | erro
    modelo           text        not null,      -- modelo pedido
    modelo_resposta  text,                      -- modelo que respondeu (pode diferir com fallback)
    tokens_entrada   int,
    tokens_saida     int,
    request_id       text,
    classificado_em  timestamptz not null default now(),
    revisao_humana   text        check (revisao_humana in ('confirmado', 'rejeitado')),
    revisado_em      timestamptz,
    primary key (proposicao_id, tema_slug, prompt_versao)
);
