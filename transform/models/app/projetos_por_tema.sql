-- Projetos com votação nominal do texto principal no Plenário, por tema do cidadão.
-- Uma linha por tema e projeto, com a primeira votação do texto principal na Câmara
-- (as seguintes costumam ser o segundo turno ou a volta do Senado).
-- São candidatos: os temas oficiais são amplos e a curadoria fina vem depois.
with votadas as (
    select
        vp.proposicao_id,
        v.votacao_id, v.data, v.aprovada, v.votos_sim, v.votos_nao, v.votos_outros, v.descricao
    from {{ ref('votacao') }} v
    join {{ ref('votacao_proposicao') }} vp using (votacao_id)
    where v.plenario and v.nominal and not v.secreta
      and v.tipo = 'texto_principal'
      and vp.proposicao_id is not null
)

select distinct on (tc.tema_slug, p.proposicao_id)
    tc.tema_slug,
    tc.nome                         as tema,
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
    pt.tema                         as tema_oficial
from votadas vt
join {{ ref('proposicao') }} p using (proposicao_id)
join {{ ref('proposicao_tema') }} pt using (proposicao_id)
join {{ ref('tema_cidadao_tema_oficial') }} m on m.cod_tema = pt.cod_tema
join {{ ref('tema_cidadao') }} tc on tc.tema_slug = m.tema_slug
order by tc.tema_slug, p.proposicao_id, vt.data, vt.votacao_id
