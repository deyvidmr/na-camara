# Rotas do site, incluídas pelo bloco HTTPS (e pelo HTTP enquanto não há certificado).
# Extensão .inc: o nginx carrega só *.conf desta pasta, então este arquivo não vira um site sozinho.

client_max_body_size 1k;
gzip on;
gzip_types text/css application/javascript text/javascript application/json;

# só leitura
if ($request_method !~ ^(GET|HEAD)$) { return 405; }

# add_header de um location substitui os do server, então cada location com cabeçalho próprio repete este include
include /etc/nginx/conf.d/cabecalhos.inc;

proxy_set_header Host $host;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_connect_timeout 5s;
proxy_read_timeout 30s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://api:8000;
}

# documentação da API: o Swagger carrega scripts de CDN, então fica sem a política de conteúdo do site
location ~ ^/(docs|redoc|openapi\.json)$ {
    limit_req zone=api burst=10 nodelay;
    proxy_pass http://api:8000;
}

# Documentação do dbt: tabelas, colunas, testes e linhagem. Só os três arquivos que a página usa.
# Sem a CSP do site: a página do dbt usa scripts embutidos.
location = /dados { return 301 /dados/; }
location = /dados/ { rewrite ^ /dados/index.html last; }
location ~ ^/dados/(index\.html|manifest\.json|catalog\.json)$ {
    limit_req zone=site burst=40 nodelay;
    alias /usr/share/nginx/dados/$1;
}

location / {
    limit_req zone=site burst=40 nodelay;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-attr 'unsafe-inline'; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'" always;
    include /etc/nginx/conf.d/cabecalhos.inc;
    proxy_pass http://api:8000;
}
