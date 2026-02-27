# Changelog

Alle relevanten Aenderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [1.5.0] - 2026-02-27

### Hinzugefuegt
- **Oeffentliche Abuse- & Postmaster-Seite** - Unter dem Mail-Hostnamen (z.B. `https://relay2.spamgo.de`) ist eine professionelle Abuse/Postmaster-Infoseite erreichbar (RFC 2142 konform)
  - Dark-Theme mit IBM Plex Fonts und responsivem Layout
  - Kontaktblock mit Abuse-E-Mail, Postmaster-E-Mail, Verantwortlichem und Telefon
  - Karten fuer Missbrauchsmeldung, Postmaster-Anfragen, Behoerden und Impressum
  - Systeminformationen-Tabelle (Betreiber, Hostname, Nutzungspolitik, SPF/DKIM, Spam-Filterung, Datenhaltung, RFC 2142)
  - Hinweis-Box fuer ISPs und grosse Mailprovider
  - Alle Werte sind HTML-escaped (XSS-Schutz)
- **Admin-pflegbare Abuse-Einstellungen** - Neue Karte "Abuse-Seite" auf der Konfigurationsseite
  - Abuse-E-Mail (Standard: `abuse@{domain}`)
  - Postmaster-E-Mail (Standard: `postmaster@{domain}`)
  - Verantwortlicher / Betreiber
  - Telefon
  - Impressum-URL
  - Texte fuer Datenhaltung, Spam-Filterung und RFC 2142 Konformitaet (mit Vorschlagstexten)
  - Hostname und Domain werden aus `postfix/main.cf` abgeleitet (read-only)
  - Vorschau-Button oeffnet die Abuse-Seite im neuen Tab
- Neue API-Endpunkte:
  - `GET /public/abuse` — Oeffentliche Abuse-Seite (HTML, kein Auth)
  - `GET /api/abuse-settings` — Abuse-Einstellungen lesen (Auth erforderlich)
  - `PUT /api/abuse-settings` — Abuse-Einstellungen aendern (Auth erforderlich)
- Audit-Logging fuer Abuse-Einstellungs-Aenderungen
- Optionale Felder (Verantwortlicher, Telefon, Impressum-URL) werden nur angezeigt wenn konfiguriert

### Geaendert
- **Caddy-Konfiguration** — Mail-Hostname wird jetzt per `rewrite + reverse_proxy` an das Admin-Panel weitergeleitet (statt `respond "Open Mail Relay Server"`)
- Einstellungen werden in der bestehenden `system_settings`-Tabelle gespeichert (keine Migration noetig)

### Behoben
- **Auth-Failed Quellen-Badge** — IP und versuchter Benutzername werden als separate Badges dargestellt (statt zusammen in einem abgeschnittenen Badge)
- **Dashboard Aktivitaetstabelle** — Horizontales Scrollen und Badge-Breite an Protokoll-Ansicht angepasst

## [1.4.2] - 2026-02-27

### Behoben
- **Stats-Collector und Logging komplett ausgefallen** - Alembics `fileConfig()` deaktivierte beim Start alle `app.*`-Logger (Standard: `disable_existing_loggers=True`). Dadurch lief der Stats-Collector zwar, aber alle Log-Ausgaben inkl. Fehlermeldungen wurden verschluckt. Dashboard, Protokolle und SMTP-User "Letzte Nutzung" wurden nicht mehr aktualisiert.
  - `alembic/env.py`: `disable_existing_loggers=False` gesetzt
  - `main.py`: Logging-Setup nach Alembic-Migrations verschoben, deaktivierte Logger werden explizit reaktiviert
  - `app_logger.propagate = False` verhindert doppelte Log-Ausgabe
- **Log-Parser Regex korrigiert** - Komma/Whitespace-Matching in `STATUS_RE` und `FROM_RE` an echtes Postfix-Log-Format angepasst
- **Stats-Collector Performance** - Batch-Verarbeitung von bis zu 200 Zeilen pro Zyklus (statt einzeln), Poll-Intervall auf 0.2s reduziert
- **Ban-Service Rolling-Window** - Fehlversuche werden bei Fenster-Ablauf halbiert statt zurueckgesetzt, damit hartnäckige Angreifer kumulativ gesperrt werden
- **PYTHONUNBUFFERED=1** im Dockerfile fuer sofortige Log-Ausgabe

## [1.4.1] - 2026-02-26

### Hinzugefuegt
- **"Gesperrt"-Badge in Dashboard und Protokoll** - Events von aktuell gesperrten IPs werden mit einem dunkelroten "Gesperrt"-Badge (mit Ban-Icon) neben dem Quellen-Badge markiert
  - Dashboard (Letzte Aktivitaet): Badge erscheint neben der Client-IP wenn diese auf der Sperrliste steht
  - Protokoll (Ereignis-Tabelle): Gleiches Badge in der Quellen-Spalte
  - Aktive Sperren werden per `GET /api/ip-bans` geladen (Dashboard: Auto-Refresh alle 30s)
  - Badge verschwindet automatisch nach Entsperrung (bei Seiten-Refresh)
- Neuer i18n-Key `ipBans.banned` fuer "Gesperrt"-Label

## [1.4.0] - 2026-02-26

### Hinzugefuegt
- **Automatische IP-Sperre** - Nach konfigurierbarer Anzahl von Fehlversuchen (Standard: 5 in 10 Minuten) werden IPs automatisch gesperrt
  - Erkennung von SASL-Authentifizierungsfehlern und Relay-Ablehnungen ueber Log-Parsing
  - Progressive Sperrdauer: 30 Min → 6 Std → 24 Std → 7 Tage (konfigurierbar)
  - Whitelisted IPs (mynetworks) werden nie gesperrt (`permit_mynetworks` kommt zuerst)
  - Automatische Entsperrung nach Ablauf der Sperrdauer (Hintergrund-Task alle 60 Sekunden)
- **Manuelle IP-Sperre** - Admins koennen IPs manuell dauerhaft sperren und entsperren
- **Neue Admin-Panel-Seite "IP-Sperren"** mit drei Bereichen:
  - Tabelle aller Sperren (aktive hervorgehoben, mit Status-Badges und Countdown)
  - Formular zum manuellen Sperren einer IP (Adresse + Notizen)
  - Schwellenwerte konfigurieren (Max. Versuche, Zeitfenster, Sperrdauern-Liste)
- **Postfix CIDR Access Map** - Durchsetzung ueber `/etc/postfix/client_access` (Docker-freundlich, kein fail2ban/iptables noetig)
  - `smtpd_client_restrictions = permit_mynetworks, check_client_access cidr:/etc/postfix/client_access, permit`
  - Datei wird aus DB generiert (wie `mynetworks` und `transport`)
- Neue API-Endpunkte unter `/api/ip-bans`:
  - `GET /ip-bans` — Alle Sperren auflisten
  - `POST /ip-bans` — Manuelle Sperre erstellen
  - `PUT /ip-bans/{id}` — Notizen aktualisieren
  - `DELETE /ip-bans/{id}` — Sperre aufheben
  - `GET /ip-bans/settings` — Schwellenwerte lesen
  - `PUT /ip-bans/settings` — Schwellenwerte aendern
- Alembic-Migration 009: `ip_bans`-Tabelle
- Log-Parser: Neues `SASL_FAIL_RE`-Pattern erkennt fehlgeschlagene SASL-Authentifizierungen
- Navigation: Neuer Eintrag "IP-Sperren" mit Ban-Icon zwischen "Netzwerke" und "SMTP-Benutzer"
- Auto-Refresh der IP-Sperren-Tabelle alle 30 Sekunden
- Inline-Bearbeitung von Notizen in der Sperren-Tabelle
- Audit-Logging fuer alle IP-Sperren-Aktionen

### Geaendert
- `scripts/entrypoint.sh` — `smtpd_client_restrictions` und leere `client_access`-Datei beim Container-Start
- Stats-Collector erkennt jetzt SASL-Fehler und Relay-Ablehnungen fuer automatische Sperrung

## [1.3.5] - 2026-02-26

### Hinzugefuegt
- **Inhaber-Feld fuer Netzwerke / IP-Whitelist** - Jedes Netzwerk kann jetzt einem Inhaber zugeordnet werden (z.B. Firma, Dienst)
  - Netzwerke werden in der Datenbank gespeichert (statt als reine Textdatei) — gleiches Muster wie SMTP-Benutzer und Transport-Regeln
  - Neues Feld "Inhaber" beim Hinzufuegen von Netzwerken und nachtraeglich per Inline-Editing aenderbar
  - Neue Spalten in der Netzwerk-Tabelle: CIDR, Inhaber, Erstellt, Aktion
  - Geschuetzte Netze (127.0.0.0/8, 172.16.0.0/12) mit Inhaber "System" und Loeschsperre
  - `DELETE /api/networks/{id}` nutzt jetzt DB-ID statt CIDR-Pfad-Parameter
  - `PUT /api/networks/{id}` — Neuer Endpunkt zum Aktualisieren des Inhabers
  - Bestehende Netzwerke aus der mynetworks-Datei werden bei der Migration automatisch uebernommen
- Alembic-Migration 008: `networks`-Tabelle mit Datenmigration aus bestehender mynetworks-Datei

### Geaendert
- `postfix/mynetworks` wird jetzt aus der Datenbank generiert (wie `postfix/transport` und `postfix/dovecot-users`)
- Config-Router liest Netzwerk-Anzahl und erlaubte Netzwerke aus der Datenbank statt aus der Datei

## [1.3.4] - 2026-02-26

### Hinzugefuegt
- **Letzte Nutzung fuer SMTP-Benutzer** - Neue Spalte "Letzte Nutzung" in der SMTP-Benutzer-Tabelle zeigt, wann ein Benutzer zuletzt eine Mail versendet hat
  - Automatische Aktualisierung bei jedem Mail-Versand ueber SASL-Authentifizierung
  - Bestehende Daten werden bei der Migration aus vorhandenen Mail-Events nachgetragen
- Alembic-Migration 007: `last_used_at` Spalte in `smtp_users` mit Backfill aus `mail_events`

## [1.3.3] - 2026-02-26

### Hinzugefuegt
- **Quellenverfolgung fuer Mail-Events** - Jedes Mail-Event zeigt jetzt die Quelle an (Client-IP und/oder SMTP-Benutzer)
  - Neue Spalte "Quelle" in Dashboard (Letzte Aktivitaet) und Protokoll-Tabelle
  - Farbcodierte Badges: SMTP-Benutzer (blau), IP-Adresse (grau), abgelehnte IP (rot)
  - Client-IP und SASL-Benutzername werden aus Postfix-Logs extrahiert und in der Datenbank gespeichert
- **Aufklappbare Detailzeilen im Dashboard** - Klick auf ein Event in der Letzten Aktivitaet zeigt Queue-ID, Groesse, DSN, Client-IP und SMTP-Benutzer
- **Erweiterte Suche** - Protokoll-Suche findet jetzt auch nach Client-IP und SMTP-Benutzername
- **CSV-Export erweitert** - Exportierte Events enthalten jetzt Client-IP und SASL-Benutzer
- Alembic-Migration 006: `client_ip` und `sasl_username` Spalten in `mail_events`
- Log-Parser: Neues `CLIENT_RE`-Pattern extrahiert Client-IP und SASL-Benutzername aus `client=` Zeilen
- Log-Parser: `REJECT_RE`-Pattern extrahiert jetzt auch die Client-IP bei abgelehnten Mails
- i18n: Neue Uebersetzungsschluessel fuer Quellen-Spalte (`colSource`, `sourceSmtp`, `sourceIp`, `sourceUnknown`)

### Geaendert
- `postfix/master.cf`: Throttled-Transports fuer Gmail, Outlook, Yahoo und Default hinzugefuegt
- Auto-generierte Dateien `postfix/throttle_enabled` und `postfix/transport` in `.gitignore` aufgenommen

## [1.3.2] - 2026-02-26

### Hinzugefuegt
- **Konfigurierbare Zeitzone** - Zeitzone fuer die Anzeige aller Zeitstempel im Admin-Panel einstellbar
  - Neue Karte "Zeitzone" auf der Konfigurationsseite mit Dropdown (27 gaengige Zeitzonen)
  - Intern wird alles in UTC gespeichert, die Zeitzone wird nur bei der Anzeige angewendet
  - Alle Zeitstempel im Panel (Dashboard, Protokoll, Benutzer, SMTP-Benutzer, TLS) nutzen die zentrale Zeitzone
  - Standard: `Europe/Berlin`
- API-Endpunkte: `GET /api/config/timezone`, `PUT /api/config/timezone`
- Pinia Store `settings.ts` fuer globale Einstellungen (Zeitzone)
- Zentrale Datums-Formatierungsfunktionen in `utils/dateFormat.ts`
- `TZ` Umgebungsvariable fuer Container-Zeitzone (Postfix-Logs, Caddy-Logs)

### Geaendert
- Alle 5 Komponenten mit lokaler Datumsformatierung auf zentrale Utility-Funktionen umgestellt
- `docker-compose.yml`: `TZ` Umgebungsvariable fuer `caddy` und `open-mail-relay` Container
- `.env.example`: `TZ=Europe/Berlin` hinzugefuegt

## [1.3.1] - 2026-02-26

### Hinzugefuegt
- **Firma & Dienst fuer SMTP-Benutzer** - Optionale Felder "Firma" und "Dienst" zur Zuordnung von SMTP-Zugaengen zu Unternehmen und Anwendungszwecken
  - Beim Anlegen eines SMTP-Benutzers koennen Firma und Dienst angegeben werden
  - Nachtraegliche Inline-Bearbeitung direkt in der Tabelle (Klick auf Zelle → Eingabefeld → Enter/Blur speichert)
  - PDF-Konfigurationsblatt zeigt Zuordnungs-Abschnitt (Firma/Dienst) wenn vorhanden
- Alembic-Migration 005: `company` und `service` Spalten in `smtp_users`
- `PUT /api/smtp-users/{id}` akzeptiert jetzt auch `company` und `service`

## [1.3.0] - 2026-02-25

### Hinzugefuegt
- **Mail-Drosselung & IP-Warmup** - Outbound-Rate-Limiting mit automatischem Warmup-Tracking fuer neue IP-Adressen
  - 4 Aufwaerm-Phasen (Woche 1-2, 3-4, 5-6, Etabliert) mit konfigurierbaren Limits pro Stunde/Tag
  - Automatische Phasen-Eskalation basierend auf dem Startdatum
  - Mails werden immer angenommen (250 OK), bei Limit-Ueberschreitung intern in HOLD-Queue gelegt
  - Batch-Worker gibt gehaltene Mails zeitgesteuert in kontrollierten Batches frei
- **Postfix Policy Server** (Port 9998) — Async TCP-Server im Admin-Container, prueft Rate-Limits per Postfix Policy Protocol
- **Per-Domain Transport-Drosselung** — Separate Concurrency- und Rate-Limits fuer Gmail, Outlook, Yahoo etc.
  - Transport-Map und master.cf werden automatisch aus der Datenbank generiert
- **Neue Admin-Panel-Seite "Drosselung"** mit vier Bereichen:
  - Uebersicht: Toggle aktiv/inaktiv, Warmup-Fortschrittsbalken, Echtzeit-Metriken
  - Aufwaerm-Phasen: Tabelle mit Inline-Bearbeitung, manuelle Phase setzen, Warmup zuruecksetzen
  - Transport-Regeln: CRUD-Tabelle fuer Per-Domain-Drosselung
  - Einstellungen: Batch-Intervall konfigurieren
- **Dashboard-Integration** — Warmup-Statuskarte auf dem Dashboard (nur wenn Drosselung aktiv)
- Neue API-Endpunkte unter `/api/throttling`:
  - `GET/PUT /config` — Drosselungs-Einstellungen
  - `GET /warmup` — Warmup-Status
  - `PUT /warmup/phase` — Phase manuell setzen
  - `PUT /warmup/reset` — Warmup zuruecksetzen
  - `GET/PUT /warmup/phases` — Phasen-Definitionen verwalten
  - `GET/POST/PUT/DELETE /transports` — Transport-Regeln CRUD
  - `GET /metrics` — Echtzeit-Metriken (gesendet/gehalten/Limits)
- Alembic-Migration 004 fuer `throttle_config`, `transport_rules`, `warmup_phases` mit Default-Daten
- Navigation: Neuer Eintrag "Drosselung" mit Gauge-Icon
- Fail-Open-Design: Policy Server gibt bei Fehler/Timeout immer DUNNO zurueck

### Geaendert
- `smtpd_client_connection_rate_limit` von 100 auf 500 erhoeht (Inbound-Akzeptanz)
- `scripts/entrypoint.sh` — Transport-Map und Policy-Service Konfiguration beim Container-Start

## [1.2.1] - 2026-02-25

### Geaendert
- **SMTP-Auth ohne TLS auf Port 25** - SASL-Authentifizierung ist jetzt auch ohne STARTTLS auf Port 25 moeglich (`smtpd_tls_auth_only=no` per master.cf-Override). Aeltere Geraete ohne TLS-Unterstuetzung koennen sich damit per Benutzername/Passwort authentifizieren. Port 587 erzwingt weiterhin TLS.
- PDF-Konfigurationsblatt zeigt jetzt beide Ports (587 empfohlen, 25 fuer Legacy-Geraete)
- Dokumentation (README, SETUP.md) und Frontend-Hinweistexte aktualisiert

## [1.2.0] - 2026-02-25

### Geaendert
- **Erweiterte SMTP-Benutzernamen** - Neben Kleinbuchstaben und Ziffern sind jetzt auch Grossbuchstaben, Bindestriche (`-`) und Unterstriche (`_`) erlaubt (4-16 Zeichen). Benutzernamen werden intern lowercase gespeichert.
- **Case-insensitive SMTP-Anmeldung** - Dovecot normalisiert den Login-Benutzernamen automatisch zu Kleinbuchstaben (`auth_username_format = %Lu`). Ob der Client `MailUser`, `MAILUSER` oder `mailuser` sendet, ist egal.
- Hinweistext im Frontend und SETUP-Dokumentation aktualisiert

## [1.1.2] - 2026-02-24

### Behoben
- **Sticky Tabellenueberschriften** - In der Protokoll-Ansicht und im Dashboard (Letzte Aktivitaet) bleiben die Spaltenueberschriften (Zeitpunkt, Status, Absender, ...) beim Scrollen sichtbar. Nur die Tabellenzeilen scrollen, Header bleibt fixiert.

## [1.1.1] - 2026-02-24

### Behoben
- **Sidebar und TopBar scrollen nicht mehr mit** - Bei vielen Eintraegen im Dashboard oder Protokoll scrollte die gesamte Seite inkl. Navigation nach oben. Jetzt scrollt nur noch der Content-Bereich, Sidebar und TopBar bleiben fixiert.

## [1.1.0] - 2026-02-24

### Hinzugefuegt
- **SMTP-Benutzer-Authentifizierung (SASL)** - Clients koennen sich jetzt per Benutzername/Passwort authentifizieren und von beliebigen IPs relayen (zusaetzlich zur IP-Whitelist)
- **Dovecot Auth-Only** im Postfix-Container - SASL-Backend ohne IMAP/POP3-Listener, nur Auth-Socket fuer Postfix
- **SMTP-Benutzerverwaltung** im Admin-Panel (neue Seite "SMTP-Benutzer")
  - Benutzer anlegen mit automatischer Passwort-Generierung (Format: xxxx-xxxxxx-xxxx)
  - Aktivieren/Deaktivieren einzelner Benutzer
  - Passwort regenerieren (altes wird sofort ungueltig)
  - Benutzer loeschen
  - **PDF-Konfigurationsblatt** mit Zugangsdaten, Einrichtungsanleitung und Sicherheitshinweis
- Fernet-verschluesselte Passwoerter in der Datenbank (Schluessel aus ADMIN_SECRET_KEY via PBKDF2)
- Automatische Dovecot-Synchronisierung bei jeder SMTP-Benutzer-Aenderung und beim Admin-Panel-Start
- Neue API-Endpunkte:
  - `GET/POST /api/smtp-users` - SMTP-Benutzer auflisten/anlegen
  - `PUT /api/smtp-users/{id}` - Aktivieren/Deaktivieren
  - `POST /api/smtp-users/{id}/regenerate-password` - Neues Passwort
  - `DELETE /api/smtp-users/{id}` - Benutzer loeschen
  - `GET /api/smtp-users/{id}/config-pdf` - PDF-Konfigurationsblatt
- Navigation: Neuer Eintrag "SMTP-Benutzer" mit Schluessel-Icon
- Alembic-Migration 003 fuer `smtp_users`-Tabelle
- Python-Dependencies: `cryptography`, `reportlab`
- `dovecot/dovecot-sasl.conf` - Dovecot-Konfiguration (Auth-Only)
- Audit-Logging fuer alle SMTP-Benutzer-Aktionen

### Geaendert
- **Postfix Relay-Restrictions** - `permit_sasl_authenticated` hinzugefuegt (IP + Auth)
- **Submission-Port 587** - Akzeptiert jetzt auch SASL-authentifizierte Verbindungen
- `smtpd_tls_auth_only = yes` - AUTH wird nur ueber TLS angeboten (Sicherheit)
- Dockerfile: `dovecot-core` installiert, Dovecot-Config wird kopiert
- Entrypoint: Dovecot-Start, passwd-Datei-Vorbereitung, SASL-postconf, erweitertes Shutdown
- Verbindungseinstellungen zeigen "IP-basiert + SMTP-Auth (SASL)" an
- `.gitignore`: `postfix/dovecot-users` hinzugefuegt

## [1.0.4] - 2026-02-24

### Hinzugefuegt
- **Einklappbare Seitenleiste** - Toggle-Button am unteren Rand klappt die Sidebar ein (72px, nur Icons) und aus (260px, Icons + Labels)
- Smooth CSS-Transition (0.2s) fuer Sidebar und Content-Bereich
- Sidebar-Zustand wird in localStorage gespeichert und bleibt nach Seitenreload erhalten
- **Versionsnummer** im Sidebar-Footer (ausgeklappt sichtbar)
- Neuer Pinia Store `layout.ts` fuer Sidebar-State-Management
- `__APP_VERSION__` Build-Konstante aus `package.json` via Vite Define

### Geaendert
- **RetentionSettings verschoben** von Protokoll-Seite in die Konfiguration-Seite (thematisch passender)
- Retention-Label von "Aufbewahrung" zu "Protokoll-Aufbewahrung" praezisiert
- **Postfix-Konfiguration aus Git-Tracking entfernt** - `postfix/main.cf` und `postfix/mynetworks` werden nicht mehr von Git verfolgt, damit `git pull` nie Benutzerkonfiguration ueberschreibt. Vorlagen liegen als `.example`-Dateien im Repository
- Schnellstart-Anleitung in README und SETUP.md um Kopier-Schritt fuer Postfix-Konfiguration ergaenzt
- Update-Dokumentation mit Persistenz-Tabelle erweitert (was bleibt bei einem Update erhalten)

## [1.0.3] - 2026-02-24

### Geaendert
- **TLS ausgehend erzwungen** - `smtp_tls_security_level` von `may` auf `encrypt` geaendert. Alle ausgehenden Mails werden jetzt immer TLS-verschluesselt
- **TLS 1.2 Minimum** - `smtp_tls_mandatory_protocols = >=TLSv1.2` und `smtp_tls_mandatory_ciphers = high` fuer ausgehende Verbindungen
- Persoenliche Netzwerk- und Hostnamedaten durch Beispieldaten ersetzt (203.0.113.0/24, relay.example.com)
- Dokumentation um ausgehende TLS-Verschluesselung ergaenzt

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
