#!/bin/sh
# Firewall sidecar — manages ipset + iptables for IP bans at network level.
# Runs with network_mode=host and NET_ADMIN capability.

set -e

# Install iptables and ipset
apk add --no-cache iptables ipset > /dev/null 2>&1

# Create ipset for banned IPs (hash:net supports both single IPs and CIDR)
ipset create omr-banned hash:net -exist

# Add iptables rule to DOCKER-USER chain (skip if already exists)
if ! iptables -C DOCKER-USER -m set --match-set omr-banned src -p tcp -m multiport --dports 25,587 -j DROP 2>/dev/null; then
    iptables -I DOCKER-USER -m set --match-set omr-banned src -p tcp -m multiport --dports 25,587 -j DROP
    echo "iptables rule added to DOCKER-USER chain"
fi

# Load existing bans from client_access file (shared volume)
CLIENT_ACCESS="/etc/postfix-config/client_access"
if [ -f "$CLIENT_ACCESS" ]; then
    count=0
    grep -v '^#' "$CLIENT_ACCESS" | grep -v '^$' | awk '{print $1}' | while read -r ip; do
        if [ -n "$ip" ]; then
            ipset add omr-banned "$ip" -exist 2>/dev/null && count=$((count + 1))
        fi
    done
    echo "Loaded banned IPs from client_access"
fi

echo "Firewall ready — ipset omr-banned active"

# Keep container alive
exec sleep infinity
