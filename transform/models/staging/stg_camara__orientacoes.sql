select distinct
    id_votacao      as votacao_id,
    sigla_bancada,
    case orientacao
        when 'Sim'        then 'sim'
        when 'Não'        then 'nao'
        when 'Obstrução'  then 'obstrucao'
        when 'Liberado'   then 'liberado'   -- a bancada liberou cada deputado para votar como quisesse
    end             as orientacao,
    orientacao      as orientacao_original
from {{ source('camara', 'votacoes_orientacoes') }}
