-- Projetos que aparecem para quem escolhe cada tema: os que a IA avaliou com grau 2 ou 3,
-- mais os confirmados por revisão humana, menos os rejeitados por ela.
{% set prompt_versao = 'relevancia-v2' %}

select
    t.tema_slug,
    t.nome                  as tema,
    p.proposicao_id,
    p.projeto,
    p.ementa,
    r.grau,
    r.justificativa,
    r.revisao_humana,
    p.votacao_id,
    p.data_votacao,
    p.aprovada,
    p.votos_sim,
    p.votos_nao,
    p.votos_outros,
    p.pct_sim
from {{ source('ia', 'relevancia_tema') }} r
join {{ ref('projetos_votados') }} p using (proposicao_id)
join {{ ref('tema_cidadao') }} t using (tema_slug)
where r.prompt_versao = '{{ prompt_versao }}'
  and r.status = 'ok'
  and coalesce(r.revisao_humana, '') <> 'rejeitado'
  and (r.grau >= 2 or r.revisao_humana = 'confirmado')
