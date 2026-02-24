# Changelog

Alle relevanten Aenderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [1.0.2] - 2026-02-24

### Hinzugefuegt
- **Automatischer Caddy-Neustart bei Hostname-Aenderung** - Wenn der Mail-Hostname im Admin-Panel geaendert wird, startet Caddy automatisch neu, beschafft ein neues TLS-Zertifikat und synchronisiert es nach Postfix
- **Fortschrittsanzeige** bei Hostname-Aenderung mit drei Schritten: Postfix Reload → Caddy Neustart → TLS-Synchronisierung
- **Hinweis-Banner** am Hostname-Feld warnt vor Webserver-Neustart bei Aenderung
- `restart_caddy()` und `get_caddy_container()` in `docker_service.py`
- `wait_for_cert()` in `cert_service.py` - pollt bis Caddy das Zertifikat bereitgestellt hat (max. 30s)
- `CADDY_CONTAINER` Setting in `config.py`
- Neue i18n-Keys fuer Hostname-Aenderungsschritte

### Geaendert
- `PUT /api/config` gibt jetzt `steps`-Array mit Schritt-fuer-Schritt-Status zurueck
- `ServerConfig.vue` zeigt Fortschrittsanzeige mit Spinner/Haekchen/Kreuz pro Schritt
- `KonfigurationView.vue` unterscheidet zwischen Voll-Erfolg (success-Toast) und Teil-Erfolg (warn-Toast)
- Dokumentation (`README.md`, `docs/SETUP.md`) um Hostname-Aenderungsablauf ergaenzt

## [1.0.1] - 2026-02-24

### Geaendert
- **MAIL_HOSTNAME aus .env entfernt** - `postfix/main.cf` ist jetzt die Single Source of Truth fuer den Mail-Hostname
- Caddy liest den Hostname ueber neues `caddy/entrypoint.sh` aus `main.cf`
- Postfix-Entrypoint (`scripts/entrypoint.sh`) liest Hostname aus `main.cf` statt aus Umgebungsvariable
- Admin-Panel (`cert_service.py`, `config_router.py`) liest Hostname aus `main.cf` statt aus `settings`
- `docker-compose.yml` vereinfacht: Caddy Entrypoint + main.cf Bind-Mount, keine `MAIL_HOSTNAME` env mehr
- Dokumentation (`README.md`, `docs/SETUP.md`) aktualisiert

### Hinzugefuegt
- `caddy/entrypoint.sh` - Liest `myhostname` aus `main.cf` und startet Caddy
- `_get_mail_hostname()` Helper in `cert_service.py`

### Entfernt
- `MAIL_HOSTNAME` aus `.env.example`, `docker-compose.yml` und `admin/app/config.py`

## [1.0.0] - 2026-02-24

Erster vollstaendiger Release mit Admin-Panel und Submission-Port.

### Hinzugefuegt

#### Open Mail Relay (Postfix)
- Postfix Mail-Relay auf Debian Bookworm Slim
- **Port 25 (SMTP)** mit optionalem STARTTLS
- **Port 587 (Submission)** mit erzwungenem STARTTLS
- IP-basierte Autorisierung ueber `mynetworks` (CIDR)
- Geschuetzte Netzwerke (127.0.0.0/8, 172.16.0.0/12), die nicht entfernt werden koennen
- Opportunistisches TLS fuer ausgehende Verbindungen
- Persistente Queue ueber Docker Named Volume
- Logging auf stdout (Docker-native)
- Queue-Monitoring-Skript (`check-queue.sh`)
- 50 MB maximale Nachrichtengroesse

#### TLS / Zertifikate
- Automatische TLS-Zertifikatsbeschaffung via Caddy + Let's Encrypt
- Automatische Erneuerung vor Ablaufdatum durch Caddy
- Automatische Synchronisierung der Zertifikate von Caddy nach Postfix (alle 6 Stunden)
- Manuelle Zertifikat-Synchronisierung ueber Admin-Panel
- TLS-Status-Anzeige fuer Caddy und Postfix im Admin-Panel

#### Admin-Panel (Backend)
- FastAPI REST-API mit JWT-Authentifizierung (HS256, 8h Gueltigkeitsdauer)
- bcrypt-Passwort-Hashing
- Rate-Limiting beim Login (5 Versuche / 5 Minuten)
- SQLite-Datenbank mit Alembic-Migrationen
- API-Endpunkte:
  - `POST /api/auth/login` - Anmeldung
  - `GET /api/dashboard/stats` - Tagesstatistiken
  - `GET /api/dashboard/chart` - Verlaufsdaten (24h)
  - `GET /api/dashboard/activity` - Letzte Aktivitaet
  - `GET /api/dashboard/queue` - Warteschlange
  - `GET/POST/DELETE /api/networks` - Netzwerkverwaltung
  - `GET/PUT /api/config` - Serverkonfiguration
  - `GET /api/config/tls` - TLS-Status
  - `POST /api/config/tls/sync` - Zertifikat-Sync ausloesen
  - `GET /api/config/connection` - Verbindungseinstellungen
  - `POST /api/config/reload` - Postfix neu laden
  - `GET/POST/PUT/DELETE /api/auth/users` - Benutzerverwaltung
  - `WS /api/logs/ws` - Echtzeit-Log-Stream
- Hintergrund-Task fuer Echtzeit-Log-Parsing und Statistik-Erfassung
- Audit-Log fuer alle administrativen Aktionen
- Docker-Socket-Zugriff fuer Container-Management

#### Admin-Panel (Frontend)
- Vue 3 Single-Page-Application mit TypeScript
- PrimeVue UI-Komponentenbibliothek
- Deutsche Lokalisierung (i18n)
- Responsive Design
- Seiten:
  - **Dashboard** - Statistik-Karten, Zustellungsverlauf (Chart.js), Queue-Status, Aktivitaets-Feed
  - **Netzwerke** - CIDR-Whitelist mit Hinzufuegen/Entfernen, Schutz fuer System-Netzwerke
  - **Konfiguration** - Hostname/Domain bearbeiten, TLS-Status mit Sync, Verbindungseinstellungen mit Kopier-Funktion
  - **Benutzer** - CRUD fuer Admin-Benutzer
  - **Login** - JWT-basierte Anmeldung

#### Infrastruktur
- Docker Compose mit 3 Services (Caddy, Admin-Panel, Open-Mail-Relay)
- Caddy als Reverse Proxy mit automatischem HTTPS
- Multi-Stage Docker Build fuer Admin-Panel (Node Build + Python Runtime)
- Health-Check fuer Open-Mail-Relay-Container
- Docker Named Volumes fuer Persistenz (Queue, Datenbank, Zertifikate)
- Bridge-Netzwerk fuer Service-Kommunikation
