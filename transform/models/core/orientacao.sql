-- Orientação de cada bancada (partido, federação, bloco ou liderança) em cada votação.
select
    o.votacao_id || ':' || o.sigla_bancada  as orientacao_id,
    o.votacao_id,
    o.sigla_bancada,
    b.tipo                                  as tipo_bancada,
    o.orientacao,
    o.orientacao_original
from {{ ref('stg_camara__orientacoes') }} o
left join (select distinct sigla_bancada, tipo from {{ ref('bancada_partido') }}) b using (sigla_bancada)
