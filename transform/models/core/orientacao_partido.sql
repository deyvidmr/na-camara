-- Orientação que valeu para cada partido em cada votação nominal.
-- Prioridade: orientação do próprio partido > da federação > do bloco.
-- A composição dos blocos vem de editorial.bancada_partido (coluna origem: nome, api ou inferido).
with partidos as (
    select distinct votacao_id, partido from {{ ref('voto') }} where partido is not null
),

orientacoes as (
    select o.votacao_id, o.sigla_bancada, o.orientacao, b.tipo, b.partido, b.origem
    from {{ ref('stg_camara__orientacoes') }} o
    join {{ ref('bancada_partido') }} b using (sigla_bancada)
    where b.partido is not null
)

select distinct on (p.votacao_id, p.partido)
    p.votacao_id || ':' || p.partido    as orientacao_partido_id,
    p.votacao_id,
    p.partido,
    o.orientacao,
    o.sigla_bancada                     as fonte_bancada,
    o.tipo                              as fonte_tipo,
    o.origem                            as fonte_origem
from partidos p
left join orientacoes o on o.votacao_id = p.votacao_id and o.partido = p.partido
order by p.votacao_id, p.partido,
    case o.tipo when 'partido' then 1 when 'federacao' then 2 when 'bloco' then 3 else 4 end
