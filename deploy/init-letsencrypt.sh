#!/bin/bash
# Corre esto UNA sola vez en el VPS (no en local) para emitir el certificado
# real de Let's Encrypt. Requiere que el dominio ya apunte a la IP del VPS
# y que los puertos 80/443 estén abiertos.
set -e

cd "$(dirname "$0")/.."

domain="asunto.miagentepersonal.me"
rsa_key_size=4096
data_path="./deploy/certbot"
email="20191217@lamolina.edu.pe"   # cambia aquí si quieres otro correo para avisos de vencimiento
staging=0                           # pon 1 para probar sin gastar el límite semanal de Let's Encrypt

if [ -d "$data_path/conf/live/$domain" ]; then
  read -p "Ya existe un certificado para $domain. ¿Reemplazarlo? (y/N) " decision
  if [ "$decision" != "y" ] && [ "$decision" != "Y" ]; then
    exit
  fi
fi

if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "### Descargando configuración TLS recomendada de Certbot ..."
  mkdir -p "$data_path/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
fi

echo "### Creando certificado dummy para $domain (para que nginx pueda arrancar) ..."
mkdir -p "$data_path/conf/live/$domain"
docker compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1 \
    -keyout '/etc/letsencrypt/live/$domain/privkey.pem' \
    -out '/etc/letsencrypt/live/$domain/fullchain.pem' \
    -subj '/CN=localhost'" certbot

echo "### Arrancando nginx ..."
docker compose up --force-recreate -d nginx

echo "### Borrando certificado dummy ..."
docker compose run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$domain && \
  rm -Rf /etc/letsencrypt/archive/$domain && \
  rm -Rf /etc/letsencrypt/renewal/$domain.conf" certbot

echo "### Pidiendo el certificado real de Let's Encrypt para $domain ..."
staging_arg=""
if [ "$staging" != "0" ]; then
  staging_arg="--staging"
fi

docker compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    -d $domain \
    --email $email \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal" certbot

echo "### Recargando nginx con el certificado real ..."
docker compose exec nginx nginx -s reload

echo "### Listo. https://$domain debería estar sirviendo con HTTPS válido."
