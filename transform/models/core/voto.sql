{{ config(indexes=[{'columns': ['votacao_id']}, {'columns': ['deputado_id']}]) }}

-- Um voto de um deputado numa votação nominal.
select
    votacao_id || ':' || deputado_id                as voto_id,
    votacao_id,
    deputado_id,
    case
        when voto_original is null          then 'secreto'      -- votação secreta: só a presença é registrada
        when voto_original = 'Sim'          then 'sim'
        when voto_original = 'Não'          then 'nao'
        when voto_original = 'Abstenção'    then 'abstencao'
        when voto_original = 'Obstrução'    then 'obstrucao'
        when voto_original = 'Artigo 17'    then 'presidente'   -- quem preside a sessão não vota (art. 17 do Regimento)
    end                                             as voto,
    voto_original,
    votado_em,
    deputado_nome,
    partido,
    uf,
    legislatura
from {{ ref('stg_camara__votos') }}
