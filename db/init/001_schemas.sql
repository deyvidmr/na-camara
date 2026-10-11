-- Camadas do banco.
-- raw:       cópia fiel dos arquivos da Câmara (tudo texto) + metadados de carga.
-- core:      dados limpos, tipados e relacionados.
-- editorial: conteúdo nosso (temas do cidadão, explicações, fontes). A importação nunca escreve aqui.
-- app:       views prontas para o site.
create schema if not exists raw;
create schema if not exists core;
create schema if not exists editorial;
create schema if not exists app;

-- Registro de cada arquivo carregado na camada raw.
-- O sha256 permite pular arquivos que não mudaram desde a última carga.
create table if not exists raw.carga (
    id            bigserial primary key,
    conjunto      text        not null,          -- ex.: votacoesVotos
    ano           int,                           -- null para arquivos sem ano (ex.: deputados)
    url           text        not null,
    sha256        text,
    last_modified text,                          -- cabeçalho HTTP da Câmara, evita baixar o que não mudou
    linhas        bigint,
    status        text        not null,          -- carregando | carregado | sem_mudanca | erro
    erro          text,
    iniciado_em   timestamptz not null default now(),
    concluido_em  timestamptz
);
create index if not exists carga_conjunto_ano on raw.carga (conjunto, ano, iniciado_em desc);
