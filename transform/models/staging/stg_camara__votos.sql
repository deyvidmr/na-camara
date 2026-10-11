select
    id_votacao                      as votacao_id,
    deputado_id::bigint             as deputado_id,
    data_hora_voto::timestamp       as votado_em,
    voto                            as voto_original,
    deputado_nome,
    -- partido e UF na data do voto (não o partido atual do deputado)
    deputado_sigla_partido          as partido,
    deputado_sigla_uf               as uf,
    deputado_id_legislatura::int    as legislatura,
    deputado_url_foto
from {{ source('camara', 'votacoes_votos') }}
