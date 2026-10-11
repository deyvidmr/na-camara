-- Há casos do mesmo projeto e tema repetidos com relevâncias diferentes; fica a maior.
select
    regexp_substr(uri_proposicao, '\d+$')::bigint as proposicao_id,
    cod_tema::int                                  as cod_tema,
    max(relevancia::int)                           as relevancia
from {{ source('camara', 'proposicoes_temas') }}
group by 1, 2
