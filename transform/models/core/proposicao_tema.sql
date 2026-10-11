-- Temas oficiais de cada projeto (um projeto pode ter vários).
select
    pt.proposicao_id || ':' || pt.cod_tema   as proposicao_tema_id,
    pt.proposicao_id,
    pt.cod_tema,
    t.tema,
    pt.relevancia
from {{ ref('stg_camara__proposicoes_temas') }} pt
join {{ ref('tema') }} t using (cod_tema)
