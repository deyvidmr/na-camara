select
    regexp_substr(uri, '\d+$')::bigint  as deputado_id,
    nome,
    nome_civil,
    sigla_sexo                          as sexo,
    id_legislatura_inicial::int         as legislatura_inicial,
    id_legislatura_final::int           as legislatura_final,
    data_nascimento::date               as nascimento,
    uf_nascimento,
    municipio_nascimento
from {{ source('camara', 'deputados') }}
