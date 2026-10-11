{{ config(indexes=[{'columns': ['proposicao_id']}]) }}

select
    proposicao_id,
    deputado_id,
    nome_autor,
    tipo_autor,
    partido,
    uf,
    ordem_assinatura,
    proponente
from {{ ref('stg_camara__autores') }}
