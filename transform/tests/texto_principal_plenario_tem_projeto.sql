-- Toda votação nominal do texto principal no Plenário precisa estar ligada a um projeto.
-- Sem isso, ela não aparece no site.
{{ config(severity = 'warn') }}

select v.votacao_id, v.data, left(v.descricao, 150) as descricao
from {{ ref('votacao') }} v
left join {{ ref('votacao_proposicao') }} vp using (votacao_id)
where v.plenario
  and v.nominal
  and v.tipo = 'texto_principal'
  and vp.proposicao_id is null
