{{ config(indexes=[{'columns': ['votacao_id'], 'unique': True}, {'columns': ['proposicao_id']}]) }}

-- Qual projeto foi realmente votado em cada votação.
--
-- O registro da Câmara (votacoesProposicoes) às vezes aponta para o projeto mais antigo de um
-- grupo de projetos anexados: os votos da Reforma Tributária (PEC 45/2019) aparecem na PEC 293/2004.
-- A descrição da votação cita o projeto votado, então ela tem prioridade.
--
-- Outra armadilha: a Câmara renumera projetos antigos. O PL 2148/2015 (id 1548579) aparece hoje como
-- PL 182/2024, mas a descrição da votação usa o número antigo. O id e a data de apresentação não mudam.
--
-- metodo:
--   descricao             projeto citado na descrição e encontrado nos dados
--   descricao_renumerado  citado com número antigo; é o projeto do registro da Câmara (mesmo tipo,
--                         apresentado no ano citado)
--   descricao_sem_id      projeto citado na descrição, mas ainda não temos o id
--   registro_camara       descrição não cita projeto; usa o registro da Câmara
with conhecidas as (
    select distinct on (sigla_tipo, numero, ano) proposicao_id, sigla_tipo, numero, ano
    from (
        select proposicao_id, sigla_tipo, numero, ano from {{ ref('stg_camara__proposicoes') }}
        union all
        select proposicao_id, sigla_tipo, numero, ano from {{ ref('stg_camara__votacoes_proposicoes') }}
    ) u
    order by sigla_tipo, numero, ano, proposicao_id
),

citada as (
    select
        votacao_id,
        coalesce(extenso, abreviado) as m
    from (
        select
            votacao_id,
            regexp_match(descricao,
                '(projeto de lei complementar|projeto de lei de convers[ãa]o|projeto de lei|proposta de emenda [àa] constitui[çc][ãa]o|medida provis[óo]ria|projeto de decreto legislativo|projeto de resolu[çc][ãa]o)\s*(?:n[º°o]?\.?\s*)?([0-9.]+)\s*,?\s*de\s*([0-9]{4})',
                'i') as extenso,
            regexp_match(descricao, '\m(PLP|PEC|MPV|PDL|PLV|PRC|PL)\s*(?:n[º°]?\s*)?([0-9.]+)/([0-9]{4})') as abreviado
        from {{ ref('votacao') }}
    ) x
    where coalesce(extenso, abreviado) is not null
),

citada_norm as (
    select
        votacao_id,
        case
            when lower(m[1]) like 'projeto de lei complementar%' then 'PLP'
            when lower(m[1]) like 'projeto de lei de convers%'   then 'PLV'
            when lower(m[1]) like 'projeto de lei%'              then 'PL'
            when lower(m[1]) like 'proposta de emenda%'          then 'PEC'
            when lower(m[1]) like 'medida provis%'               then 'MPV'
            when lower(m[1]) like 'projeto de decreto%'          then 'PDL'
            when lower(m[1]) like 'projeto de resolu%'           then 'PRC'
            else upper(m[1])
        end                                   as sigla_tipo,
        replace(m[2], '.', '')::int           as numero,
        m[3]::int                             as ano
    from citada
),

registrada as (
    -- quando há mais de um registro, prefere projetos de mérito a requerimentos
    select distinct on (vp.votacao_id)
        vp.votacao_id, vp.proposicao_id, vp.sigla_tipo, vp.numero, vp.ano,
        extract(year from p.apresentada_em)::int as ano_apresentacao
    from {{ ref('stg_camara__votacoes_proposicoes') }} vp
    left join {{ ref('stg_camara__proposicoes') }} p using (proposicao_id)
    order by vp.votacao_id, (vp.sigla_tipo in ('PEC', 'PLP', 'PL', 'MPV', 'PDL', 'PRC')) desc, vp.proposicao_id
),

resolvida as (
    select
        v.votacao_id,
        c.votacao_id is not null                    as citou,
        c.sigla_tipo, c.numero, c.ano,
        k.proposicao_id                             as citada_id,
        -- citado com número antigo: registro da Câmara do mesmo tipo, apresentado no ano citado
        case when k.proposicao_id is null
              and r.sigla_tipo = c.sigla_tipo
              and r.ano_apresentacao = c.ano
             then r.proposicao_id end              as renumerada_id,
        r.proposicao_id as r_id, r.sigla_tipo as r_sigla, r.numero as r_numero, r.ano as r_ano
    from {{ ref('votacao') }} v
    left join citada_norm c on c.votacao_id = v.votacao_id
    -- PDL se chamava PDC antes de 2019
    left join conhecidas k
           on (k.numero, k.ano) = (c.numero, c.ano)
          and (k.sigla_tipo = c.sigla_tipo or (c.sigla_tipo = 'PDL' and k.sigla_tipo = 'PDC'))
    left join registrada r on r.votacao_id = v.votacao_id
    where c.votacao_id is not null or r.votacao_id is not null
)

select
    votacao_id,
    case when citou then coalesce(citada_id, renumerada_id) else r_id end as proposicao_id,
    case when citou then sigla_tipo else r_sigla end  as sigla_tipo,
    case when citou then numero else r_numero end     as numero,
    case when citou then ano else r_ano end           as ano,
    case
        when citou and citada_id is not null      then 'descricao'
        when citou and renumerada_id is not null  then 'descricao_renumerado'
        when citou                                then 'descricao_sem_id'
        else 'registro_camara'
    end                                         as metodo,
    r_id                                        as registro_camara_id,
    r_sigla || ' ' || r_numero || '/' || r_ano  as registro_camara
from resolvida
