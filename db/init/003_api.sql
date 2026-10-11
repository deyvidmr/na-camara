-- Usuário só de leitura para a API. A senha é definida por deploy/criar_usuario_api.sh,
-- a partir do .env, para não ficar no repositório.
do $$
begin
    if not exists (select from pg_roles where rolname = 'api_leitura') then
        create role api_leitura login;
    end if;
end $$;

grant usage on schema app, core, editorial, ia to api_leitura;
grant select on all tables in schema app, core, editorial, ia to api_leitura;
-- tabelas e views que o dbt recriar no futuro também ficam legíveis
alter default privileges in schema app, core, editorial, ia grant select on tables to api_leitura;
