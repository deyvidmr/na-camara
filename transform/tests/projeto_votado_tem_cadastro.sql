-- Todo projeto ligado a uma votação nominal do texto principal no Plenário precisa ter cadastro
-- em core.proposicao (nome, ementa, situação). Sem isso ele some do site sem aviso.
-- Correção: o coletor baixa o arquivo anual de projetos do ano que falta (fontes.py).
select vp.votacao_id, vp.proposicao_id, vp.sigla_tipo || ' ' || vp.numero || '/' || vp.ano as projeto
from {{ ref('votacao_proposicao') }} vp
join {{ ref('votacao') }} v using (votacao_id)
where v.plenario and v.nominal and v.tipo = 'texto_principal'
  and vp.proposicao_id is not null
  and not exists (select 1 from {{ ref('proposicao') }} p where p.proposicao_id = vp.proposicao_id)
