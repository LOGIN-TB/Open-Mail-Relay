#!/bin/bash
# Queue-Monitoring-Script fuer den Mail-Relay
# Kann per Cronjob oder manuell aufgerufen werden

QUEUE_COUNT=$(mailq 2>/dev/null | tail -n 1 | grep -oP '\d+(?= Request)')

if [ -z "$QUEUE_COUNT" ]; then
    QUEUE_COUNT=0
fi

echo "Mails in Queue: $QUEUE_COUNT"

if [ "$QUEUE_COUNT" -gt 100 ]; then
    echo "WARNUNG: Mehr als 100 Mails in der Queue! ($QUEUE_COUNT)"
    exit 1
fi

exit 0
