select
    id::bigint                              as proposicao_id,
    sigla_tipo,
    numero::int                             as numero,
    ano::int                                as ano,
    descricao_tipo,
    ementa,
    data_apresentacao::timestamp            as apresentada_em,
    regexp_substr(uri_prop_principal, '\d+$')::bigint as principal_id,
    url_inteiro_teor,
    ultimo_status_descricao_situacao        as situacao,
    ultimo_status_data_hora::timestamp      as situacao_em
from {{ source('camara', 'proposicoes') }}
