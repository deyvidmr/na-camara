select distinct
    id_votacao                      as votacao_id,
    proposicao_id::bigint           as proposicao_id,
    proposicao_sigla_tipo           as sigla_tipo,
    proposicao_numero::int          as numero,
    proposicao_ano::int             as ano,
    proposicao_ementa               as ementa
from {{ source('camara', 'votacoes_proposicoes') }}
where proposicao_id is not null
