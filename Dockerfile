FROM debian:bookworm-slim

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        postfix \
        dovecot-core \
        ca-certificates \
        openssl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY postfix/main.cf /etc/postfix/main.cf
COPY postfix/master.cf /etc/postfix/master.cf
COPY postfix/mynetworks /etc/postfix/mynetworks
COPY dovecot/dovecot-sasl.conf /etc/dovecot/dovecot.conf
COPY scripts/entrypoint.sh /entrypoint.sh
COPY scripts/check-queue.sh /usr/local/bin/check-queue.sh

RUN chmod +x /entrypoint.sh /usr/local/bin/check-queue.sh

EXPOSE 25 587

ENTRYPOINT ["/entrypoint.sh"]
