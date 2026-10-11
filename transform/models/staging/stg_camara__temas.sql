-- Temas oficiais da Câmara (referência da API).
select
    cod::int    as cod_tema,
    nome        as tema
from {{ source('camara', 'ref_proposicoes_cod_tema') }}
