-- O placar oficial (votos_sim / votos_nao) deve ser igual à soma dos votos individuais.
-- Votações secretas ficam de fora: nelas o voto de cada deputado não é registrado.
-- Retorna as votações que não batem (o teste passa se não retornar nada).
with contagem as (
    select
        votacao_id,
        count(*) filter (where voto = 'sim') as sim,
        count(*) filter (where voto = 'nao') as nao
    from {{ ref('voto') }}
    group by 1
)

select v.votacao_id, v.votos_sim, c.sim, v.votos_nao, c.nao
from {{ ref('votacao') }} v
join contagem c using (votacao_id)
where not v.secreta
  and (v.votos_sim <> c.sim or v.votos_nao <> c.nao)
