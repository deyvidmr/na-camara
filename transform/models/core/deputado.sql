{{ config(indexes=[{'columns': ['deputado_id'], 'unique': True}]) }}

select * from {{ ref('stg_camara__deputados') }}
