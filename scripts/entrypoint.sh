#!/bin/bash
set -e

# Bind-mounted Konfiguration aus Staging-Verzeichnis nach /etc/postfix kopieren
if [ -d /etc/postfix-config ]; then
    cp /etc/postfix-config/main.cf /etc/postfix/main.cf
    cp /etc/postfix-config/master.cf /etc/postfix/master.cf
    cp /etc/postfix-config/mynetworks /etc/postfix/mynetworks
fi

# Hostname aus main.cf lesen (Single Source of Truth)
MAIL_HOSTNAME=$(postconf -h myhostname 2>/dev/null)
if [ -z "$MAIL_HOSTNAME" ] || [ "$MAIL_HOSTNAME" = "localhost" ]; then
    echo "ERROR: myhostname ist nicht in main.cf konfiguriert. Abbruch." >&2
    exit 1
fi
echo "Mail hostname: ${MAIL_HOSTNAME}"

# TLS-Zertifikate von Caddy synchronisieren
sync_certs() {
    CERT_BASE="/etc/caddy-data/caddy/certificates/acme-v02.api.letsencrypt.org-directory"
    CERT_DIR="${CERT_BASE}/${MAIL_HOSTNAME}"
    TLS_DIR="/etc/postfix/tls"

    mkdir -p "$TLS_DIR"

    if [ -f "${CERT_DIR}/${MAIL_HOSTNAME}.crt" ] && [ -f "${CERT_DIR}/${MAIL_HOSTNAME}.key" ]; then
        cp "${CERT_DIR}/${MAIL_HOSTNAME}.crt" "${TLS_DIR}/cert.pem"
        cp "${CERT_DIR}/${MAIL_HOSTNAME}.key" "${TLS_DIR}/key.pem"
        chmod 600 "${TLS_DIR}/key.pem"
        chmod 644 "${TLS_DIR}/cert.pem"
        postconf -e "smtpd_tls_cert_file = ${TLS_DIR}/cert.pem"
        postconf -e "smtpd_tls_key_file = ${TLS_DIR}/key.pem"
        echo "TLS certificates synced from Caddy"
    else
        # Keine Zertifikate vorhanden - TLS-Zertifikatspfade entfernen
        postconf -# "smtpd_tls_cert_file" 2>/dev/null || true
        postconf -# "smtpd_tls_key_file" 2>/dev/null || true
        echo "No TLS certificates found, STARTTLS will not advertise certs"
    fi
}

sync_certs

# Postfix-Verzeichnisse sicherstellen
postfix set-permissions 2>/dev/null || true

# Konfiguration pruefen
postfix check

# Hintergrund-Task: Zertifikate synchronisieren
# - Beim Start: Alle 30s pruefen bis Zertifikat da ist (max 5 Minuten)
# - Danach: Alle 6 Stunden synchronisieren
(
    # Warte auf Zertifikat falls Caddy es noch nicht bereit hat
    CERT_BASE="/etc/caddy-data/caddy/certificates/acme-v02.api.letsencrypt.org-directory"
    CERT_FILE="${CERT_BASE}/${MAIL_HOSTNAME}/${MAIL_HOSTNAME}.crt"
    ATTEMPTS=0
    MAX_ATTEMPTS=10
    while [ ! -f "$CERT_FILE" ] && [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
        ATTEMPTS=$((ATTEMPTS + 1))
        echo "Waiting for TLS certificate from Caddy (attempt ${ATTEMPTS}/${MAX_ATTEMPTS})..."
        sleep 30
    done
    if [ -f "$CERT_FILE" ]; then
        sync_certs
        postfix reload 2>/dev/null || true
    fi

    # Danach regelmaessig alle 6 Stunden synchronisieren
    while true; do
        sleep 21600  # 6 Stunden
        sync_certs
        postfix reload 2>/dev/null || true
    done
) &

# Graceful Shutdown: auf SIGTERM reagieren
trap "echo 'Stopping Postfix...'; postfix stop; exit 0" SIGTERM SIGINT SIGQUIT

# Postfix im Vordergrund starten
postfix start-fg &
POSTFIX_PID=$!

# Warten auf Postfix-Prozess
wait $POSTFIX_PID
