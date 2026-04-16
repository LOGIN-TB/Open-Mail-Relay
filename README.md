# Open Mail Relay mit Admin-Panel

Ein selbst gehosteter Open-Mail-Relay-Dienst (Smarthost) mit webbasiertem Admin-Panel. Basiert auf Postfix, verwaltet durch eine moderne Vue 3 + FastAPI Oberflaeche mit automatischem TLS via Let's Encrypt.

## Features

- **Postfix Open Mail Relay** - Leitet E-Mails fuer konfigurierte Netzwerke an Ziel-MX-Server weiter
- **Zwei SMTP-Ports** - Port 25 (SMTP, STARTTLS optional) und Port 587 (Submission, STARTTLS erzwungen)
- **Erzwungenes TLS ausgehend** - Alle ausgehenden Mails werden TLS-verschluesselt (min. TLS 1.2)
- **Admin-Panel** - Webbasierte Verwaltung mit Dashboard, Netzwerk-Whitelist, Benutzerverwaltung und Serverkonfiguration
- **Automatisches TLS** - Caddy beschafft und erneuert Let's Encrypt-Zertifikate automatisch. Synchronisierung nach Postfix alle 6 Stunden
- **IP-basierte Autorisierung** - Relay nur fuer konfigurierte Netzwerke (CIDR), verwaltbar ueber das Admin-Panel. Jedes Netzwerk kann einem Inhaber zugeordnet werden
- **SMTP-Benutzer-Authentifizierung (SASL)** - Zusaetzlich zur IP-Whitelist koennen SMTP-Benutzer mit Benutzername/Passwort von beliebigen IPs relayen. Dovecot-basiertes SASL, verwaltbar ueber das Admin-Panel inkl. PDF-Konfigurationsblatt
- **Automatische IP-Sperre mit Firewall-Blocking** - Erkennt Brute-Force-Versuche (SASL-Auth-Fehler, Relay-Ablehnungen) und sperrt IPs automatisch mit progressiver Dauer (30 Min → 6 Std → 24 Std → 7 Tage). Admins koennen IPs auch manuell sperren/entsperren. Zwei Verteidigungslinien: **iptables/ipset** droppt Pakete gesperrter IPs auf Netzwerkebene (kein TCP-Handshake moeglich), Postfix CIDR Access Map als Fallback
- **Mail-Drosselung & IP-Warmup** - Outbound-Rate-Limiting mit automatischem 4-Phasen-Warmup fuer neue IPs. Per-Domain Transport-Drosselung (Gmail, Outlook, Yahoo etc.) und konfigurierbarer Batch-Worker fuer kontrollierte Zustellung
- **Echtzeit-Monitoring** - Dashboard mit Zustellstatistiken, Queue-Status, Aktivitaetslog und Verlaufsdiagramm
- **Quellenverfolgung** - Jedes Mail-Event zeigt Client-IP und SMTP-Benutzer mit farbcodierten Badges (Protokoll + Dashboard)
- **Konfigurierbare Zeitzone** - Zeitzone fuer die Anzeige aller Zeitstempel im Admin-Panel einstellbar (intern bleibt alles UTC). Container-Zeitzone per `TZ` Umgebungsvariable konfigurierbar
- **RBL-Blacklist-Checker** - Automatische Pruefung der Server-IP gegen 22 DNS-Blacklists (Spamhaus, Barracuda, SpamCop, SORBS u.v.m.) mit konfigurierbarem Pruefintervall und E-Mail-Alarm bei Listings. Eigene Server-IP wird automatisch aus der Postfix-Konfiguration gelesen. RBL-Status-Indikator auf dem Dashboard
- **DNS-Record-Pruefung (SPF, DMARC, DKIM)** - Validierung aller mail-relevanten DNS-Records mit Copy-Paste-Vorlagen fuer fehlende Eintraege. SPF-Check mit rekursiver `include:`-Aufloesung. DKIM-Selector automatisch pro Server (Multi-Server-faehig). Dashboard-Statusindikator
- **DKIM-Signing** - Automatische DKIM-Signierung ausgehender E-Mails via OpenDKIM. 2048-Bit RSA-Schluessel wird beim ersten Start generiert. Selector automatisch aus Hostname abgeleitet (Multi-Server-faehig). Public Key im Admin-Panel anzeigbar
- **Oeffentliche Abuse-Seite** - Professionelle Abuse- & Postmaster-Infoseite unter dem Mail-Hostnamen (RFC 2142 konform), mit admin-pflegbaren Kontaktdaten, Systeminformationen und Impressum-Link. Zweisprachig (DE/EN) mit Sprachwechsel im Header
- **Einklappbare Seitenleiste** - Sidebar per Toggle-Button ein-/ausklappbar, Zustand wird gespeichert
- **Docker-basiert** - Vier Container (Caddy, Admin-Panel, Open-Mail-Relay, Firewall), einfach zu deployen

## Architektur

```
                    ┌─────────────────────────────────────────┐
                    │              Docker Host                 │
                    │                                         │
                    │   Firewall (iptables/ipset)              │
                    │      └── DOCKER-USER Chain: DROP         │
                    │          gesperrte IPs auf Port 25/587   │
                    │                                         │
  HTTPS :443 ──────┤──► Caddy (Reverse Proxy + Auto-TLS)     │
  HTTP  :80  ──────┤──►   ├── admin.example.com ──► Admin    │
                    │      └── mail.example.com  ──► Abuse    │
                    │                                         │
  SMTP  :25  ──────┤──► Postfix Open Mail Relay               │
  Sub.  :587 ──────┤──►   ├── STARTTLS (optional / erzwungen)│
                    │      ├── IP-Whitelist (mynetworks)      │
                    │      ├── SMTP-Auth / SASL (Dovecot)     │
                    │      ├── DKIM-Signing (OpenDKIM)        │
                    │      └── Weiterleitung an Ziel-MX       │
                    │                                         │
                    │   Admin-Panel (FastAPI + Vue 3)          │
                    │      ├── Dashboard & Statistiken        │
                    │      ├── Netzwerk-/IP-Verwaltung        │
                    │      ├── SMTP-Benutzerverwaltung        │
                    │      ├── IP-Sperren (Firewall + Postfix)│
                    │      ├── Mail-Drosselung & IP-Warmup    │
                    │      ├── RBL-Blacklist-Checker           │
                    │      ├── TLS-Zertifikat-Status          │
                    │      └── Benutzer- & Konfiguration      │
                    └─────────────────────────────────────────┘
```

## Schnellstart

```bash
# 1. Repository klonen
git clone https://github.com/LOGIN-TB/Open-Mail-Relay.git
cd Open-Mail-Relay

# 2. Konfiguration erstellen
cp .env.example .env
cp postfix/main.cf.example postfix/main.cf
cp postfix/mynetworks.example postfix/mynetworks

# 3. Anpassen (Hostname, Passwort, etc.)
nano .env
nano postfix/main.cf

# 4. Container bauen und starten
docker compose up -d --build
```

Das Admin-Panel ist danach unter `https://ADMIN_HOSTNAME` erreichbar.
Standard-Login: `admin` / (Wert aus `ADMIN_DEFAULT_PASSWORD`)

> Detaillierte Anleitung: [docs/SETUP.md](docs/SETUP.md)

## Update

```bash
cd /opt/open-mail-relay   # oder das Verzeichnis, in das geklont wurde
git pull
docker compose up -d --build
```

Datenbank-Migrationen laufen beim Start des `admin-panel`-Containers automatisch — kein weiterer Schritt noetig.

## Umgebungsvariablen (.env)

| Variable | Beschreibung | Beispiel |
|---|---|---|
| `ADMIN_HOSTNAME` | FQDN des Admin-Panels | `admin.example.com` |
| `ADMIN_SECRET_KEY` | Geheimer Schluessel fuer JWT-Token-Signierung | `ein-langer-zufaelliger-string` |
| `ADMIN_DEFAULT_PASSWORD` | Initiales Passwort fuer den `admin`-Benutzer | `mein-sicheres-passwort` |
| `LETSENCRYPT_EMAIL` | E-Mail-Adresse fuer Let's Encrypt-Benachrichtigungen | `admin@example.com` |
| `TZ` | Zeitzone fuer Container-Logs (Postfix, Caddy) | `Europe/Berlin` |

> **Hinweis:** Der Mail-Relay-Hostname (`myhostname`) wird direkt in `postfix/main.cf` konfiguriert und ueber das Admin-Panel verwaltet - nicht in der `.env`-Datei.

## SMTP-Ports

| Port | Protokoll | TLS | Zertifikat erforderlich |
|------|-----------|-----|-------------------------|
| 25   | SMTP      | STARTTLS optional (eingehend) | Nein (funktioniert auch ohne) |
| 587  | Submission | STARTTLS erzwungen (eingehend) | Ja |

Ausgehende Verbindungen zu Ziel-Mailservern werden **immer TLS-verschluesselt** (mindestens TLS 1.2). Mails an Server ohne TLS-Unterstuetzung werden nicht zugestellt.

Beide Ports erlauben Relay fuer Absender-IPs aus den konfigurierten Netzwerken (IP-basiert) **oder** fuer authentifizierte SMTP-Benutzer (SASL). Auf Port 587 ist TLS Pflicht. Auf Port 25 ist SMTP-Auth auch ohne TLS moeglich (fuer aeltere Geraete ohne TLS-Unterstuetzung). Empfehlung: Port 587 mit TLS verwenden, wenn moeglich.

## Admin-Panel

### Dashboard
- Tagesstatistiken (gesendet, verzoegert, zurueckgewiesen, abgelehnt)
- Erfolgsrate
- **RBL-Status-Indikator** — Zeigt aktuellen Blacklist-Status (CLEAN/LISTINGS/nicht geprueft), Klick navigiert zur RBL-Pruefung
- **DNS-Status-Indikator** — Zeigt SPF/DMARC/DKIM Status (alle OK/Probleme/nicht geprueft), Klick navigiert zur DNS-Pruefung
- Zustellungsverlauf als Diagramm (letzte 24h)
- Aktuelle Warteschlange
- Letzte Aktivitaet (Live-Feed) mit Quellenverfolgung (Client-IP / SMTP-Benutzer) und aufklappbaren Details

### Netzwerke
- CIDR-basierte IP-Whitelist verwalten mit optionalem Inhaber-Feld
- Inhaber nachtraeglich per Inline-Editing aenderbar
- Geschuetzte Netzwerke (127.0.0.0/8, 172.16.0.0/12) koennen nicht entfernt werden
- Aenderungen werden sofort in Postfix uebernommen

### Konfiguration
- Hostname und Domain aendern
- **Automatischer Caddy-Neustart bei Hostname-Aenderung** - Neues TLS-Zertifikat wird automatisch beschafft und nach Postfix synchronisiert
- Fortschrittsanzeige bei Hostname-Aenderung (Postfix Reload → Caddy Neustart → TLS-Sync)
- TLS-Zertifikat-Status (Let's Encrypt + Postfix)
- Verbindungseinstellungen zum Kopieren (SMTP-Host, Ports, TLS-Status)
- Manuelle Zertifikat-Synchronisierung und Postfix-Reload
- **Zeitzone** konfigurierbar fuer alle Zeitstempel-Anzeigen im Admin-Panel (Standard: Europe/Berlin)
- **Abuse-Seite** — Pflege der oeffentlichen Abuse- & Postmaster-Informationsseite (Kontaktdaten, Systeminformationen, Texte in DE und EN). Vorschau-Link oeffnet die Seite direkt
- **Container-Verwaltung** — Status-Uebersicht und Neustart-Funktion fuer alle Docker-Container (Mail-Server, Caddy, Firewall) direkt aus dem Admin-Panel

### SMTP-Benutzer (SASL)
- SMTP-Benutzer anlegen, aktivieren/deaktivieren, loeschen
- Optionale Felder **Firma** und **Dienst** zur Zuordnung (inline editierbar)
- Automatische Passwort-Generierung (Format: xxxx-xxxxxx-xxxx)
- Passwort jederzeit regenerierbar
- **PDF-Konfigurationsblatt** mit Zugangsdaten, Zuordnung (Firma/Dienst) und Einrichtungsanleitung. Auf Seite 2 zusaetzlich Live-Pruefung der Kunden-DNS-Eintraege: **SPF-Record** (TXT) und **DKIM-CNAME** (`<servername>._domainkey.<kundendomain>` → `<servername>._domainkey.<relay-domain>`) jeweils mit Status (gruen/gelb), aktuellem Eintrag und kopierbarem Empfehlungstext
- **Letzte Nutzung** - Zeigt an, wann ein SMTP-Benutzer zuletzt eine Mail versendet hat
- Fernet-verschluesselte Passwoerter in der Datenbank
- Automatische Synchronisierung mit Dovecot (SASL-Backend)

### Mail-Drosselung & IP-Warmup
- **Outbound-Rate-Limiting** mit automatischem 4-Phasen-Warmup (Woche 1-2, 3-4, 5-6, Etabliert)
- Mails werden immer angenommen (250 OK), bei Limit-Ueberschreitung intern in HOLD-Queue gelegt
- **Per-Domain Transport-Drosselung** fuer Gmail, Outlook, Yahoo etc. (Concurrency + Rate-Delay)
- **Batch-Worker** gibt gehaltene Mails zeitgesteuert in kontrollierten Batches frei
- Warmup-Fortschrittsanzeige und Echtzeit-Metriken (gesendet/Stunde, gesendet/Tag, zurueckgehalten)
- Alle Limits pro Phase konfigurierbar (Max/Stunde, Max/Tag, Burst)
- Transport-Regeln mit CRUD-Verwaltung
- Fail-Open-Design: Bei Fehler wird Mail nie blockiert
- Warmup-Status auch auf dem Dashboard sichtbar

### RBL-Blacklist-Checker
- **Automatische Pruefung** der Server-IP gegen 22 DNS-Blacklists (Spamhaus ZEN/SBL/XBL/PBL, Barracuda, SpamCop, SORBS, UCEPROTECT 1-3, CBL, PSBL, Mailspike, SpamRATS, JustSpam u.a.)
- Eigener Hostname und IP werden automatisch aus der Postfix-Konfiguration gelesen
- Konfigurierbares Pruefintervall (Standard: alle 6 Stunden), DNS-Timeout einstellbar
- E-Mail-Alarm bei Blacklist-Eintraegen mit detailliertem Report (neue/entfernte Listings, Uebersicht)
- Option "Nur bei Aenderung" — E-Mail nur bei Statuswechsel
- Test-Mail-Funktion zum Pruefen der E-Mail-Konfiguration
- Zusaetzliche Server konfigurierbar fuer Multi-IP-Setups
- False-Positive-Filterung fuer Spamhaus Public-DNS-Resolver-Antworten
- **Dashboard-Indikator** — Clickbare Statuskarte zeigt gruen (CLEAN), rot (LISTINGS) oder grau (nicht geprueft)

### DNS-Record-Pruefung
- **SPF-Check** — Prueft ob die Server-IP im SPF-Record autorisiert ist, inklusive rekursiver Aufloesung von `include:`-Ketten (bis 5 Ebenen, RFC 7208 konform)
- **DMARC-Check** — Prueft Existenz und Gueltigkeit des DMARC-Records (`_dmarc.domain`) inkl. Policy-Parsing
- **DKIM-Check** — Prueft ob ein DKIM-Public-Key-Record fuer den konfigurierten Selector existiert
- Copy-Paste DNS-Eintraege werden automatisch generiert fuer fehlende SPF- und DMARC-Records
- DKIM-Selector automatisch aus Hostname abgeleitet (z.B. `relay2` fuer `relay2.spamgo.de`) — Multi-Server-faehig
- **DKIM-Signing** — OpenDKIM signiert alle ausgehenden Mails. 2048-Bit RSA-Schluessel wird beim ersten Container-Start generiert und im Admin-Panel mit Copy-Button angezeigt. Schluessel loeschen und neu generieren moeglich
- **Dashboard-Indikator** — Clickbare Statuskarte zeigt gruen (alle Records OK), rot (Probleme) oder grau (nicht geprueft)

### Protokoll
- Vollstaendige Mail-Event-Historie mit Filterung nach Status, Zeitraum und Freitextsuche
- **Quellenverfolgung** - Spalte "Quelle" zeigt SMTP-Benutzer (blau) oder Client-IP (grau/rot) mit farbcodierten Badges
- Aufklappbare Detailzeilen mit Queue-ID, Groesse, DSN, Client-IP, SMTP-Benutzer und Nachricht
- Suche nach Client-IP und SMTP-Benutzername
- CSV-Export aller Events inkl. Quell-Informationen
- Konfigurierbare Aufbewahrungsdauer

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

## Firewall (automatische IP-Sperre)

Der `firewall`-Sidecar-Container verwaltet automatisch iptables-Regeln auf dem Docker-Host:

```
Gesperrte IP ──► iptables DOCKER-USER ──► DROP (Paket verworfen)
                                           Kein TCP-Handshake, kein Log-Eintrag
```

- **ipset** (`omr-banned`, Typ `hash:net`) speichert gebannte IPs im Kernel
- Einzelne iptables-Regel in der `DOCKER-USER`-Chain droppt Pakete auf Port 25/587
- Automatische Aktualisierung bei Ban/Unban/Ablauf durch das Admin-Panel
- Bestehende Sperren werden beim Container-Start aus `client_access` geladen
- Postfix CIDR Access Map (`client_access`) bleibt als zweite Verteidigungslinie

Zusaetzlich koennen Port 25 und 587 manuell auf Netzwerk-Ebene abgesichert werden:

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

# Test mit SMTP-Auth (SASL) ueber Port 587 (empfohlen)
swaks --to empfaenger@zieldomain.de \
      --from absender@quelldomain.de \
      --server relay.example.com \
      --port 587 \
      --tls \
      --auth PLAIN \
      --auth-user smtpuser \
      --auth-password xxxx-xxxxxx-xxxx

# Test mit SMTP-Auth (SASL) ueber Port 25 ohne TLS (Legacy-Geraete)
swaks --to empfaenger@zieldomain.de \
      --from absender@quelldomain.de \
      --server relay.example.com \
      --port 25 \
      --auth PLAIN \
      --auth-user smtpuser \
      --auth-password xxxx-xxxxxx-xxxx

# Test von nicht-erlaubter IP ohne Auth → erwartet "Relay access denied"
```

## Tech-Stack

| Komponente | Technologie |
|------------|-------------|
| Mail-Server | Postfix + Dovecot (SASL) + OpenDKIM auf Debian Bookworm Slim |
| Reverse Proxy | Caddy 2 (Auto-TLS) |
| Firewall | iptables/ipset via Alpine-Sidecar (host-Netzwerk) |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Frontend | Vue 3, TypeScript, PrimeVue, Chart.js |
| Datenbank | SQLite |
| Auth | JWT (HS256) + bcrypt |
| Container | Docker Compose |

## Projektstruktur

```
Open-Mail-Relay/
├── docker-compose.yml          # Service-Orchestrierung (4 Container)
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
├── dovecot/
│   └── dovecot-sasl.conf       # Dovecot Auth-Only Konfiguration
├── postfix/
│   ├── main.cf                 # Postfix-Hauptkonfiguration
│   ├── master.cf               # Postfix-Dienste (SMTP + Submission)
│   └── mynetworks              # Erlaubte Netzwerke
└── scripts/
    ├── entrypoint.sh           # Container-Start + TLS-Sync
    ├── check-queue.sh          # Queue-Monitoring
    └── firewall-entrypoint.sh  # Firewall-Sidecar (ipset/iptables)
```

## Lizenz

MIT - siehe [LICENSE](LICENSE)
