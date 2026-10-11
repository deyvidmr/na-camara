-- Uma linha por votação, com o tipo do que estava sendo decidido.
-- O "Sim" de cada votação responde à pergunta daquela votação: num destaque, "Sim" pode
-- significar manter um trecho, não apoiar o projeto. Por isso o tipo importa.
with votos as (
    select
        votacao_id,
        count(*)                                    as participantes,
        count(*) filter (where voto_original is null) as votos_ocultos
    from {{ ref('stg_camara__votos') }}
    group by 1
)

select
    v.votacao_id,
    v.data,
    v.registrada_em,
    v.orgao_id,
    v.sigla_orgao,
    v.sigla_orgao = 'PLEN'                          as plenario,
    v.evento_id,
    v.aprovada,
    v.votos_sim,
    v.votos_nao,
    v.votos_outros,
    -- nominal: a Câmara registrou quem votou. Simbólica: só o resultado.
    vo.votacao_id is not null                       as nominal,
    -- secreta: registra quem participou, mas não o voto (ex.: indicação de autoridades)
    coalesce(vo.votos_ocultos = vo.participantes, false) as secreta,
    case
        when v.descricao ~* '^\s*(mantid|suprimid)[oa]s? o texto'
          or v.descricao ~* 'destaque'                         then 'destaque'
        when v.descricao ~* 'urg[êe]ncia'
         and v.descricao ~* 'requerimento'                     then 'urgencia'
        when v.descricao ~* 'reda[çc][ãa]o final'              then 'redacao_final'
        when v.descricao ~* 'requerimento'                     then 'requerimento'
        -- preferência, recursos, inclusão em pauta e admissibilidade de MP: decisões sobre o andamento
        when v.descricao ~* '^\s*(aprovad|rejeitad)[oa]s? (a prefer[êe]ncia|o recurso|a inclus[ãa]o)'
          or v.descricao ~* 'aprecia[çc][ãa]o preliminar'      then 'procedimento'
        when v.descricao ~* '^\s*(aprovad|rejeitad)[oa]s?,?( em (primeiro|segundo) turno,)? (o|a|os|as) (projeto|proposta|substitutivo|subemenda substitutiva|medida provis|emenda aglutinativa substitutiva|dispositivos do substitutivo)'
                                                               then 'texto_principal'
        when v.descricao ~* '^\s*(aprovad|rejeitad)[oa]s? (a|as) emenda'
                                                               then 'emenda'
        else 'outro'
    end                                             as tipo,
    v.descricao,
    v.arquivo_ano
from {{ ref('stg_camara__votacoes') }} v
left join votos vo using (votacao_id)
