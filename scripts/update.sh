#!/bin/sh
# Open Mail Relay — Update-Helfer fuer alle Server.
#
# Holt die neueste Version von GitHub, baut geaenderte Images neu und
# erstellt die Container neu. Laufzeit-Dateien (.env, postfix/main.cf,
# mynetworks, dovecot-users, client_access, dkim/ ...) sind gitignored
# und bleiben unangetastet. DB-Migrationen laufen automatisch beim
# Start des Admin-Panels (Alembic).
#
# Aufruf:   ./scripts/update.sh
set -e

cd "$(dirname "$0")/.."

echo "==> Hole neueste Version von GitHub..."
git fetch origin
if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ]; then
    echo "    Bereits aktuell ($(git rev-parse --short HEAD))."
else
    git log --oneline HEAD..origin/main
    git pull --ff-only origin main
fi

echo "==> Baue Images..."
docker compose build

echo "==> Erstelle Container neu (nur geaenderte)..."
docker compose up -d --remove-orphans

echo "==> Status:"
docker compose ps

VERSION=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' admin/frontend/package.json | head -1)
echo
echo "==> Fertig. Version: ${VERSION}"
echo "    Migrationshinweise: CHANGELOG.md"
