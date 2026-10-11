-- Projetos com votação nominal do texto principal no Plenário: os que podem ter
-- a pergunta "como você votaria?". Uma linha por projeto, com a primeira votação do texto
-- principal na Câmara (as seguintes costumam ser o segundo turno ou a volta do Senado).
with votadas as (
    select
        vp.proposicao_id,
        v.votacao_id, v.data, v.aprovada, v.votos_sim, v.votos_nao, v.votos_outros
    from {{ ref('votacao') }} v
    join {{ ref('votacao_proposicao') }} vp using (votacao_id)
    where v.plenario and v.nominal and not v.secreta
      and v.tipo = 'texto_principal'
      and vp.proposicao_id is not null
)

select distinct on (p.proposicao_id)
    p.proposicao_id,
    p.nome                          as projeto,
    p.ementa,
    p.situacao,
    vt.votacao_id,
    vt.data                         as data_votacao,
    vt.aprovada,
    vt.votos_sim,
    vt.votos_nao,
    vt.votos_outros,
    -- quanto mais perto de 50%, mais o Plenário se dividiu
    round(100.0 * vt.votos_sim / nullif(vt.votos_sim + vt.votos_nao, 0), 1) as pct_sim,
    (select string_agg(pt.tema, '; ' order by pt.tema)
     from {{ ref('proposicao_tema') }} pt
     where pt.proposicao_id = p.proposicao_id)                             as temas_oficiais
from votadas vt
join {{ ref('proposicao') }} p using (proposicao_id)
order by p.proposicao_id, vt.data, vt.votacao_id
