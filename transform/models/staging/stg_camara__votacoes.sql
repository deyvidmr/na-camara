select
    id                              as votacao_id,
    data::date                      as data,
    data_hora_registro::timestamp   as registrada_em,
    id_orgao::bigint                as orgao_id,
    sigla_orgao,
    nullif(id_evento, '0')::bigint  as evento_id,
    aprovacao::int = 1              as aprovada,
    votos_sim::int                  as votos_sim,
    votos_nao::int                  as votos_nao,
    votos_outros::int               as votos_outros,
    -- descrições vêm com \r\n e às vezes com espaço não separável (U+00A0) entre as palavras
    translate(replace(descricao, E'\r', ''), E' ', ' ') as descricao,
    _ano                            as arquivo_ano
from {{ source('camara', 'votacoes') }}
