{{ config(indexes=[{'columns': ['votacao_id'], 'unique': True}]) }}

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
    -- A ordem importa: o texto principal costuma terminar com "ressalvados os destaques",
    -- então ele é reconhecido antes da regra genérica de destaque.
    case
        when v.descricao ~* '^\s*(mantid|suprimid)[oa]s? o texto'  then 'destaque'
        -- projeto que voltou do Senado: a Câmara decide sobre as mudanças feitas lá
        when v.descricao ~* '^\s*(aprovad|rejeitad)[oa]s?,?( em (primeiro|segundo) turno,)? (o|a|os|as) (substitutivo|emendas?|dispositivos do substitutivo) do senado'
                                                               then 'texto_senado'
        when v.descricao ~* '^\s*(aprovad|rejeitad)[oa]s?,?( em (primeiro|segundo) turno,)? (o|a|os|as) (projeto|proposta|substitutivo|subemenda substitutiva|medida provis|emenda aglutinativa substitutiva)'
                                                               then 'texto_principal'
        when v.descricao ~* 'destaque'                         then 'destaque'
        when v.descricao ~* 'urg[êe]ncia'
         and v.descricao ~* 'requerimento'                     then 'urgencia'
        when v.descricao ~* 'reda[çc][ãa]o final'              then 'redacao_final'
        when v.descricao ~* 'requerimento'                     then 'requerimento'
        -- preferência, recursos, inclusão em pauta e admissibilidade de MP: decisões sobre o andamento
        when v.descricao ~* '^\s*(aprovad|rejeitad)[oa]s? (a prefer[êe]ncia|o recurso|a inclus[ãa]o)'
          or v.descricao ~* 'aprecia[çc][ãa]o preliminar'      then 'procedimento'
        when v.descricao ~* '^\s*(aprovad|rejeitad)[oa]s? (a|as) emenda'
                                                               then 'emenda'
        else 'outro'
    end                                             as tipo,
    v.descricao,
    v.arquivo_ano
from {{ ref('stg_camara__votacoes') }} v
left join votos vo using (votacao_id)
