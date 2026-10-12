# Cabeçalhos de segurança comuns a todas as respostas.
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
# navegador passa a usar só HTTPS neste domínio por 6 meses
add_header Strict-Transport-Security "max-age=15552000" always;
