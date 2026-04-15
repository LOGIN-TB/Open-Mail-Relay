#!/bin/bash
# Open Mail Relay — Update-Skript
#
# Holt den aktuellen Stand aus dem Repo, baut die Container neu und
# startet den Dienst. Datenbank-Migrationen laufen automatisch beim
# Start des admin-panel Containers (siehe admin/app/main.py).
#
# Aufruf auf dem Relay-Server:
#     cd /opt/open-mail-relay
#     sudo ./scripts/update.sh
#
# Optional: Branch uebergeben (default: main)
#     sudo ./scripts/update.sh feat/portal-api-extensions

set -e

BRANCH="${1:-main}"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "==> Update im Verzeichnis: $REPO_DIR"
echo "==> Branch: $BRANCH"

if [ ! -f .env ]; then
    echo "FEHLER: .env nicht gefunden in $REPO_DIR" >&2
    exit 1
fi

echo "==> Lokale Aenderungen sichern..."
git stash push --include-untracked --message "update.sh autostash $(date -Iseconds)" >/dev/null 2>&1 || true

echo "==> Repository aktualisieren..."
git fetch --all --prune
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "==> Container neu bauen..."
docker compose build --pull

echo "==> Dienst neu starten..."
docker compose up -d --remove-orphans

echo "==> Warte auf admin-panel (Health-Check + Migrationen)..."
for i in $(seq 1 30); do
    if docker compose exec -T admin-panel curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
        echo "==> admin-panel ist bereit."
        break
    fi
    if [ "$i" = "30" ]; then
        echo "WARNUNG: admin-panel antwortet nach 60s nicht. Pruefen Sie: docker compose logs admin-panel" >&2
        exit 1
    fi
    sleep 2
done

echo ""
echo "==> Installierte Version:"
docker compose exec -T admin-panel python -c "from app.routers.portal_router import VERSION; print(VERSION)" 2>/dev/null || true

echo ""
echo "==> Update abgeschlossen."
