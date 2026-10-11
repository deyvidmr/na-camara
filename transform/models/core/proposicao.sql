-- Projetos (PL, PEC, MPV...). Projetos renumerados mantêm o id; o número exibido é o atual.
select distinct on (proposicao_id)
    proposicao_id,
    sigla_tipo || ' ' || numero || '/' || ano   as nome,
    sigla_tipo,
    numero,
    ano,
    descricao_tipo,
    ementa,
    apresentada_em,
    principal_id,
    situacao,
    situacao_em,
    url_inteiro_teor
from {{ ref('stg_camara__proposicoes') }}
order by proposicao_id, arquivo_ano desc
