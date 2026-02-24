# Open Mail Relay mit Admin-Panel

Ein selbst gehosteter Open-Mail-Relay-Dienst (Smarthost) mit webbasiertem Admin-Panel. Basiert auf Postfix, verwaltet durch eine moderne Vue 3 + FastAPI Oberflaeche mit automatischem TLS via Let's Encrypt.

## Features

- **Postfix Open Mail Relay** - Leitet E-Mails fuer konfigurierte Netzwerke an Ziel-MX-Server weiter
- **Zwei SMTP-Ports** - Port 25 (SMTP, STARTTLS optional) und Port 587 (Submission, STARTTLS erzwungen)
- **Erzwungenes TLS ausgehend** - Alle ausgehenden Mails werden TLS-verschluesselt (min. TLS 1.2)
- **Admin-Panel** - Webbasierte Verwaltung mit Dashboard, Netzwerk-Whitelist, Benutzerverwaltung und Serverkonfiguration
- **Automatisches TLS** - Caddy beschafft und erneuert Let's Encrypt-Zertifikate automatisch. Synchronisierung nach Postfix alle 6 Stunden
- **IP-basierte Autorisierung** - Relay nur fuer konfigurierte Netzwerke (CIDR), verwaltbar ueber das Admin-Panel
- **Echtzeit-Monitoring** - Dashboard mit Zustellstatistiken, Queue-Status, Aktivitaetslog und Verlaufsdiagramm
- **Einklappbare Seitenleiste** - Sidebar per Toggle-Button ein-/ausklappbar, Zustand wird gespeichert
- **Docker-basiert** - Drei Container (Caddy, Admin-Panel, Open-Mail-Relay), einfach zu deployen

## Architektur

```
                    ┌─────────────────────────────────────────┐
                    │              Docker Host                 │
                    │                                         │
  HTTPS :443 ──────┤──► Caddy (Reverse Proxy + Auto-TLS)     │
  HTTP  :80  ──────┤──►   ├── admin.example.com ──► Admin    │
                    │      └── mail.example.com  ──► (Info)   │
                    │                                         │
  SMTP  :25  ──────┤──► Postfix Open Mail Relay                   │
  Sub.  :587 ──────┤──►   ├── STARTTLS (optional / erzwungen)│
                    │      ├── IP-Whitelist (mynetworks)      │
                    │      └── Weiterleitung an Ziel-MX       │
                    │                                         │
                    │   Admin-Panel (FastAPI + Vue 3)          │
                    │      ├── Dashboard & Statistiken        │
                    │      ├── Netzwerk-/IP-Verwaltung        │
                    │      ├── TLS-Zertifikat-Status          │
                    │      └── Benutzer- & Konfiguration      │
                    └─────────────────────────────────────────┘
```

## Schnellstart

```bash
# 1. Repository klonen
git clone https://github.com/LOGIN-TB/Open-Mail-Relay.git
cd Open-Mail-Relay

# 2. Umgebungsvariablen konfigurieren
cp .env.example .env
nano .env

# 3. Container bauen und starten
docker compose up -d
```

Das Admin-Panel ist danach unter `https://ADMIN_HOSTNAME` erreichbar.
Standard-Login: `admin` / (Wert aus `ADMIN_DEFAULT_PASSWORD`)

> Detaillierte Anleitung: [docs/SETUP.md](docs/SETUP.md)

## Umgebungsvariablen (.env)

| Variable | Beschreibung | Beispiel |
|---|---|---|
| `ADMIN_HOSTNAME` | FQDN des Admin-Panels | `admin.example.com` |
| `ADMIN_SECRET_KEY` | Geheimer Schluessel fuer JWT-Token-Signierung | `ein-langer-zufaelliger-string` |
| `ADMIN_DEFAULT_PASSWORD` | Initiales Passwort fuer den `admin`-Benutzer | `mein-sicheres-passwort` |
| `LETSENCRYPT_EMAIL` | E-Mail-Adresse fuer Let's Encrypt-Benachrichtigungen | `admin@example.com` |

> **Hinweis:** Der Mail-Relay-Hostname (`myhostname`) wird direkt in `postfix/main.cf` konfiguriert und ueber das Admin-Panel verwaltet - nicht in der `.env`-Datei.

## SMTP-Ports

| Port | Protokoll | TLS | Zertifikat erforderlich |
|------|-----------|-----|-------------------------|
| 25   | SMTP      | STARTTLS optional (eingehend) | Nein (funktioniert auch ohne) |
| 587  | Submission | STARTTLS erzwungen (eingehend) | Ja |

Ausgehende Verbindungen zu Ziel-Mailservern werden **immer TLS-verschluesselt** (mindestens TLS 1.2). Mails an Server ohne TLS-Unterstuetzung werden nicht zugestellt.

Beide Ports erlauben Relay ausschliesslich fuer Absender-IPs aus den konfigurierten Netzwerken. Es wird keine SASL-Authentifizierung verwendet - die Autorisierung erfolgt rein IP-basiert.

## Admin-Panel

### Dashboard
- Tagesstatistiken (gesendet, verzoegert, zurueckgewiesen, abgelehnt)
- Erfolgsrate
- Zustellungsverlauf als Diagramm (letzte 24h)
- Aktuelle Warteschlange
- Letzte Aktivitaet (Live-Feed)

### Netzwerke
- CIDR-basierte IP-Whitelist verwalten
- Geschuetzte Netzwerke (127.0.0.0/8, 172.16.0.0/12) koennen nicht entfernt werden
- Aenderungen werden sofort in Postfix uebernommen

### Konfiguration
- Hostname und Domain aendern
- **Automatischer Caddy-Neustart bei Hostname-Aenderung** - Neues TLS-Zertifikat wird automatisch beschafft und nach Postfix synchronisiert
- Fortschrittsanzeige bei Hostname-Aenderung (Postfix Reload → Caddy Neustart → TLS-Sync)
- TLS-Zertifikat-Status (Let's Encrypt + Postfix)
- Verbindungseinstellungen zum Kopieren (SMTP-Host, Ports, TLS-Status)
- Manuelle Zertifikat-Synchronisierung und Postfix-Reload

### Benutzerverwaltung
- Admin-Benutzer anlegen, bearbeiten, loeschen
- JWT-basierte Authentifizierung
- Audit-Log fuer alle Aktionen

## TLS-Zertifikate

Caddy beschafft und erneuert TLS-Zertifikate automatisch via Let's Encrypt. Die Zertifikate werden alle 6 Stunden automatisch nach Postfix synchronisiert. Eine manuelle Synchronisierung ist jederzeit ueber das Admin-Panel moeglich.

Bei einer **Hostname-Aenderung** ueber das Admin-Panel wird Caddy automatisch neu gestartet, um ein neues Zertifikat zu beschaffen. Anschliessend wird das Zertifikat automatisch nach Postfix synchronisiert.

**Voraussetzungen:**
- DNS A-Records fuer den Mail-Hostname (aus `postfix/main.cf`) und `ADMIN_HOSTNAME` muessen auf den Server zeigen
- **PTR-Record** (reverse DNS) der Server-IP muss auf den Mail-Hostname zeigen (Postfix verwendet `myhostname` als EHLO-Greeting - empfangende Server pruefen, ob EHLO und PTR uebereinstimmen)
- Port 80 und 443 muessen von aussen erreichbar sein (fuer Let's Encrypt HTTP-01 Challenge)

## Queue-Management

```bash
# Queue anzeigen
docker compose exec open-mail-relay postqueue -p

# Queue-Monitoring (Warnung bei > 100 Mails)
docker compose exec open-mail-relay check-queue.sh

# Alle Mails erneut zustellen
docker compose exec open-mail-relay postqueue -f

# Alle Mails aus der Queue loeschen
docker compose exec open-mail-relay postsuper -d ALL
```

## Logging

```bash
# Logs live verfolgen
docker compose logs -f open-mail-relay

# Letzte 100 Zeilen
docker compose logs --tail 100 open-mail-relay

# Nur Admin-Panel-Logs
docker compose logs -f admin-panel
```

## Firewall

Port 25 und 587 sollten auf Netzwerk-Ebene zusaetzlich abgesichert werden:

```bash
# ufw
ufw allow from 203.0.113.0/24 to any port 25 proto tcp
ufw allow from 203.0.113.0/24 to any port 587 proto tcp
ufw deny 25
ufw deny 587

# iptables
iptables -A INPUT -p tcp --dport 25 -s 203.0.113.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 587 -s 203.0.113.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 25 -j DROP
iptables -A INPUT -p tcp --dport 587 -j DROP
```

## Testen

```bash
apt install swaks

# Test ueber Port 25 (SMTP)
swaks --to empfaenger@zieldomain.de \
      --from absender@quelldomain.de \
      --server relay.example.com \
      --port 25

# Test ueber Port 587 (Submission mit STARTTLS)
swaks --to empfaenger@zieldomain.de \
      --from absender@quelldomain.de \
      --server relay.example.com \
      --port 587 \
      --tls

# Test von nicht-erlaubter IP → erwartet "Relay access denied"
```

## Tech-Stack

| Komponente | Technologie |
|------------|-------------|
| Mail-Server | Postfix auf Debian Bookworm Slim |
| Reverse Proxy | Caddy 2 (Auto-TLS) |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Frontend | Vue 3, TypeScript, PrimeVue, Chart.js |
| Datenbank | SQLite |
| Auth | JWT (HS256) + bcrypt |
| Container | Docker Compose |

## Projektstruktur

```
Open-Mail-Relay/
├── docker-compose.yml          # Service-Orchestrierung
├── Dockerfile                  # Postfix Mail-Relay Image
├── .env.example                # Vorlage fuer Umgebungsvariablen
├── admin/
│   ├── Dockerfile              # Admin-Panel Image (Multi-Stage)
│   ├── requirements.txt        # Python-Abhaengigkeiten
│   ├── alembic.ini             # Datenbank-Migrationen
│   ├── alembic/                # Migrations-Skripte
│   ├── app/
│   │   ├── main.py             # FastAPI-Einstiegspunkt
│   │   ├── models.py           # SQLAlchemy-Modelle
│   │   ├── schemas.py          # Pydantic-Schemas
│   │   ├── routers/            # API-Endpunkte
│   │   └── services/           # Business-Logik
│   └── frontend/
│       ├── src/
│       │   ├── views/          # Seiten (Dashboard, Netzwerke, ...)
│       │   ├── components/     # UI-Komponenten
│       │   ├── stores/         # Pinia State Management
│       │   ├── router/         # Vue Router
│       │   └── i18n/           # Uebersetzungen (Deutsch)
│       └── vite.config.ts      # Build-Konfiguration
├── caddy/
│   └── Caddyfile               # Reverse-Proxy-Konfiguration
├── postfix/
│   ├── main.cf                 # Postfix-Hauptkonfiguration
│   ├── master.cf               # Postfix-Dienste (SMTP + Submission)
│   └── mynetworks              # Erlaubte Netzwerke
└── scripts/
    ├── entrypoint.sh           # Container-Start + TLS-Sync
    └── check-queue.sh          # Queue-Monitoring
```

## Lizenz

MIT - siehe [LICENSE](LICENSE)
