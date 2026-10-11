select
    id_proposicao::bigint                           as proposicao_id,
    nullif(id_deputado_autor, '')::bigint           as deputado_id,
    nome_autor,
    tipo_autor,
    sigla_partido_autor                             as partido,
    sigla_ufautor                                   as uf,
    ordem_assinatura::int                           as ordem_assinatura,
    proponente = '1'                                as proponente
from {{ source('camara', 'proposicoes_autores') }}
