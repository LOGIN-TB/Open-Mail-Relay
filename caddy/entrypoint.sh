#!/bin/sh
# Liest MAIL_HOSTNAME aus postfix/main.cf und startet Caddy
export MAIL_HOSTNAME=$(grep "^myhostname" /etc/postfix-config/main.cf | sed 's/.*= *//')

if [ -z "$MAIL_HOSTNAME" ]; then
    echo "ERROR: myhostname nicht in main.cf gefunden" >&2
    exit 1
fi

echo "Caddy: MAIL_HOSTNAME=${MAIL_HOSTNAME}"
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
