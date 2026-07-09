#!/bin/sh
# Open Mail Relay — Update-Helfer fuer alle Server.
#
# Holt die neueste Version von GitHub, baut geaenderte Images neu und
# erstellt die Container neu. Laufzeit-Dateien (.env, postfix/main.cf,
# mynetworks, dovecot-users, client_access, dkim/ ...) sind gitignored
# und bleiben unangetastet. DB-Migrationen laufen automatisch beim
# Start des Admin-Panels (Alembic).
#
# Bricht mit klarer Fehlermeldung ab statt still stehenzubleiben, wenn
# der Fast-Forward nicht moeglich ist (lokale Aenderungen an versionierten
# Dateien, abgewichener Branch, detached HEAD).
#
# Aufruf:   ./scripts/update.sh
set -e

cd "$(dirname "$0")/.."

fail() {
    echo >&2
    echo "FEHLER: $1" >&2
    shift
    for line in "$@"; do
        echo "        $line" >&2
    done
    echo >&2
    echo "        Danach ./scripts/update.sh erneut ausfuehren." >&2
    exit 1
}

echo "==> Hole neueste Version von GitHub..."
git fetch origin main

# 1. Auf einem Branch? (detached HEAD laesst 'git pull' scheitern)
BRANCH=$(git symbolic-ref --short -q HEAD || true)
if [ -z "$BRANCH" ]; then
    fail "Kein Branch ausgecheckt (detached HEAD: $(git rev-parse --short HEAD))." \
         "Beheben mit:  git checkout main"
fi
if [ "$BRANCH" != "main" ]; then
    fail "Aktueller Branch ist '$BRANCH', erwartet wird 'main'." \
         "Beheben mit:  git checkout main"
fi

# 2. Lokale Aenderungen an versionierten Dateien? (blockieren den Pull)
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    git status --short --untracked-files=no >&2
    fail "Lokale Aenderungen an versionierten Dateien (siehe oben)." \
         "Verwerfen mit:      git checkout -- <datei>" \
         "oder aufheben mit:  git stash"
fi

# 3. Fast-Forward auf origin/main
if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ]; then
    echo "    Bereits aktuell ($(git rev-parse --short HEAD))."
else
    echo "    Neue Commits:"
    git log --oneline HEAD..origin/main
    if ! git merge --ff-only origin/main; then
        git log --oneline origin/main..HEAD >&2
        fail "Fast-Forward nicht moeglich — dieser Server hat eigene Commits (siehe oben)." \
             "Wenn die lokalen Commits verzichtbar sind:  git reset --hard origin/main" \
             "(vorher sichern mit:  git branch lokal-backup)"
    fi
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
