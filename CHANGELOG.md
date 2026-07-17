# Changelog

Alle relevanten Aenderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefuegt
- **Deterministische Zuordnungs-Bestätigung (Portal-API 2.8.1)** — Das v1-Inventar liefert je Benutzer zusaetzlich `smtp_user_id`, und `GET /api/portal/v1/smtp-users/{username}` liefert das Einzeldetail. Das Portal bestaetigt damit einen gepushten Zugang direkt per Benutzername statt ueber die Kontakt-E-Mail-Suche — die schlaegt fehl, wenn die relay-seitige Kontaktadresse von der Kundenadresse abweicht (Zugang blieb dann in der Kundenliste unsichtbar).
- **Kontingent-Durchsetzung je SMTP-Benutzer (R1, Portal-API 2.7.0)** — Neuer Schalter „Kontingent-Durchsetzung" in den Portal-API-Einstellungen (Default: aus). Aktiviert prueft der bestehende Policy-Server (Port 9998) je Mail das Monatslimit des SASL-Benutzers: Portal-Override (`smtp_users.monthly_limit_override`, Migration 018 — Trial-Deckel, Planlimit inkl. freigegebener Zusatzpakete) vor Paketlimit; ohne beides unbegrenzt. Ueberschreitung antwortet `DEFER 4.7.1` — Absender-Systeme stellen erneut zu, sobald das Portal das Limit erhoeht (kein Mailverlust). 30-s-Cache mit Mitzaehlung erlaubter Mails; Fail-open bleibt erhalten. Der Policy-Hook wird unabhaengig von der Drosselung gesetzt (geteilter `smtpd_end_of_data_restrictions`, Marker `quota_enforcement_enabled`, entrypoint-persistent); die Quota-Anzeige (`get_user_quota`) beruecksichtigt den Override auch ohne Paket.
- **Monatsbericht-Flag je Benutzer (R3)** — `smtp_users.monthly_report_enabled` (Migration 018, Default an). Das Portal sendet `false`, sobald seine eigenen Berichte aktiv sind — der betroffene Benutzer faellt aus den automatischen Nutzungsberichten dieses Relays (wirksam = `receive_reports` UND `monthly_report_enabled`; manueller Einzelversand im Admin bleibt moeglich). Capability `monthly_report_flag` in `/api/portal/v1/capabilities`.
- **Zustellbarkeits-Lese-API fuer das Portal (R4, Portal-API 2.7.0)** — Neue read-only Endpunkte unter `/api/portal`: `GET /provider-blocks` (aktive + kuerzlich geloeste Provider-Sperren inkl. Delisting-Anleitung), `GET /throttle-status` (Drosselung, Warmup-Phase, Tages-/Stundenzaehler, Kontingent-Schalter), `GET /ip-bans` (aktive Bans, optional `include_inactive`). Schreibende Aktionen bleiben bewusst im Admin-Panel (Notfallweg).
- **Auslastungs-Endpunkt (R5)** — `GET /api/portal/load` liefert aktive/gesamte SMTP-Benutzer, 30-Tage-Sendevolumen (StatsHourly) und Tageszaehler fuer die Relay-Zuweisung nach Auslastung im Portal. Neue Provisioning-Capabilities: `limit_override`, `quota_enforcement`, `load_metric`.
- **Upsert-Erweiterung (v1)** — `PUT /api/portal/v1/smtp-users/{username}` akzeptiert `monthly_limit_override` (explizites `null` loescht den Override) und `monthly_report_enabled`; das Inventar (`GET /v1/smtp-users`) liefert beide Felder fuer die Reconciliation.
- **Tests** — Erste pytest-Suite (`admin/tests/`, 18 Tests: Quota-Aufloesung/Policy-Verdikt, Upsert-Felder, Lese-Endpunkte, Berichts-Filter). Ausfuehren: `pip install -r admin/requirements-dev.txt && cd admin && pytest tests/`.
- **Domain-Bindung (sender_login_maps, Portal-API 2.6.0)** — Neuer Schalter „Domain-Bindung" in den Portal-API-Einstellungen (Default: aus). Aktiviert generiert `sender_maps_service` aus den vom Portal ERZWUNGENEN Domains (`smtp_users.enforced_domains`, Migration 017) eine Postfix-Hash-Map `@domain user1,user2` und setzt `smtpd_sender_restrictions = reject_known_sender_login_mismatch`: Nur gemappte Domains werden durchgesetzt, alle anderen Absender bleiben unbehelligt (Monitor). Leere Map = No-Op. Regeneration bei jeder Benutzer-Mutation (Admin-Panel und v1-API); `entrypoint.sh` stellt die Konfiguration nach Container-Neustart wieder her (Marker-Datei, Muster wie Drosselung).
- **Phase-F-Werkzeug `app.tools.purge_plaintext`** — loescht (nach Dry-Run + `--yes`) die reversiblen Klartext-Passwoerter portal-verwalteter Benutzer; Legacy `config-pdf`/`reset-password` antworten fuer solche Benutzer danach mit 410 statt 500.

### Behoben
- **Strikte Absenderbindung sperrte auch Ausnahme-Benutzer aus** — Die Restriction-Klasse `soft_sender_policy` bestand nur aus `reject_known_sender_login_mismatch`. Sendete ein Ausnahme-Benutzer (`sender_policy` unrestricted, z. B. „Alle Domains"-Zugaenge) von einer NICHT gemappten Domain, lieferte die Klasse kein Urteil (DUNNO) — Postfix wertete die aeussere Liste weiter aus und `reject_sender_login_mismatch` lehnte ab („Sender address rejected: not owned by user …"). Faktisch war jeder Benutzer strikt, die Ausnahme-Map wirkungslos. Fix: Klasse endet jetzt mit `permit` — in `sender_maps_service` (Schalter) UND `entrypoint.sh` (Restore nach Neustart). **Nach dem Update auf bereits umgestellten Relays einmal „Strikte Absenderbindung" aus- und wieder einschalten** (oder Container neu starten), damit die korrigierte postconf-Zeile aktiv wird.
- **`scripts/update.sh` blieb still stehen** — Wenn der Fast-Forward nicht moeglich war (lokale Aenderungen an versionierten Dateien, server-lokale Commits, detached HEAD), zeigte das Script nur die neuen Commits an und brach dann wegen `set -e` kommentarlos ab; Build und Neustart liefen nie. Jetzt: Vorab-Pruefungen (Branch, Working Tree) und klare Fehlermeldungen mit dem jeweiligen Loesungsweg (`git checkout main`, `git stash`, `git reset --hard origin/main`).
- **Aussperr-Bug bei Legacy-Passwort-Reset** — `regenerate-password` (Admin) und `POST /api/portal/reset-password/{id}` setzten bei hash-authentifizierten Benutzern (portal-verwaltet) nur `password_encrypted`; Dovecot prueft aber `password_hash` zuerst → neues Passwort haette nie funktioniert. Beide Wege aktualisieren jetzt auch den Hash.

### Hinzugefuegt (v2.5.0)
- **Portal-Provisionierungs-API v1** (`/api/portal/v1/*`, Portal-API 2.5.0) — Das zentrale MailBridge-Portal (Control Plane) kann SMTP-Benutzer auf diesem Relay provisionieren: `GET /capabilities` (Versionserkennung), `GET /smtp-users` (paginiertes Inventar mit `updated_since` fuer inkrementelle Reconciliation, nie Passwortmaterial), `GET /packages` (read-only Spiegel), `PUT /smtp-users/{username}` (idempotenter Upsert), `POST .../adopt` (uebernimmt bestehenden lokalen Benutzer: Bestandspasswort wird RELAY-LOKAL aus Fernet-Klartext gehasht, Zugangsdaten bleiben gueltig), `POST .../credentials` (Rotation), `DELETE` (Soft-Disable). Auth wie bisher (API-Key + IP-Whitelist); **alle Writes zusaetzlich hinter dem neuen Schalter „Portal-Provisionierung" in den Portal-API-Einstellungen (Standard: aus — Deploy ist wirkungslos, bis pro Relay bewusst aktiviert)**. Jeder Write landet im Audit-Log (`[portal]`-Prefix).
- **Hash-only-Zugangsdaten** — `smtp_users.password_hash` ({SHA512-CRYPT}); der Dovecot-Sync schreibt Hash-Benutzer als `{SHA512-CRYPT}`-Zeile und Legacy-Benutzer weiter als `{PLAIN}` (gemischte Datei, Dovecot-nativ). Portal-provisionierte Benutzer haben keinen reversiblen Klartext mehr auf dem Relay.
- **Provisionierungs-Metadaten** — `smtp_users`: `origin` (local/portal), `portal_managed`, `portal_access_id`, `allowed_domains` (JSON), `enforcement_mode` (monitor/enforce, Vorbereitung Domain-Bindung), `updated_at` (bei jeder Mutation, Basis der Reconciliation). Migration 016; `password_encrypted` ist jetzt nullable. Admin-UI zeigt portal-verwaltete Benutzer mit Badge und warnt beim Bearbeiten (Notfallweg bleibt voll moeglich, Aenderungen werden beim naechsten Abgleich vom Portal ueberschrieben).
- **Portal-API: Kontingent pro Account** — `GET /api/portal/stats/{id}` und `/api/portal/smtp-users/{username}/stats` liefern jetzt ein `quota`-Objekt (Paketname, Kategorie, Monatslimit, Verbrauch im laufenden Monat, verbleibend, Overage) statt `null`, sofern dem SMTP-Benutzer ein Paket zugeordnet ist. Verbrauch wird live aus `mail_events` gezaehlt (deckt sich mit der Abrechnung). Ermoeglicht die monatliche Budget-Anzeige im Kundenportal.

## [2.8.1] - 2026-06-11

### Sicherheit
- **JWT raus aus der WebSocket-URL** — Der Live-Log-Stream authentifiziert jetzt ueber das WebSocket-Subprotocol (`["omr.bearer", <token>]`) statt ueber `?token=...` in der URL; Query-Tokens landeten in Proxy-/Server-Logs. Der alte Query-Weg ist deaktiviert (Frontend+Backend werden im selben Image ausgeliefert, daher kein Kompatibilitaetsfenster noetig).
- **Security-Header** — Das Admin-Panel sendet jetzt `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Permissions-Policy` sowie `Strict-Transport-Security` (nur hinter TLS/Caddy).

### Hinzugefuegt
- **Healthchecks fuer admin-panel und caddy** — Neuer unauthentifizierter Endpoint `GET /api/health` (Liveness); Caddy wird ueber seine Admin-API (`:2019/config/`) geprueft. Alle vier Container melden jetzt einen Health-Status.

### Geaendert
- **Caddy-Image gepinnt** — `caddy:2-alpine` (floating) -> `caddy:2.11-alpine` (Patch-Updates innerhalb 2.11, reproduzierbar ueber alle Server).

### Geprueft, bewusst nicht umgesetzt
- **Docker-Socket-Proxy**: Das Panel braucht exec/restart/logs auf den Containern — mit diesen Rechten bietet ein Socket-Proxy kaum zusaetzliche Isolation; der Socket bleibt read-only gemountet.
- **Debian trixie** fuer das Relay-Image: bookworm erhaelt noch bis 2028 LTS-Updates; der Sprung (Postfix 3.10, Dovecot 2.4 mit neuem Config-Format!) ist ein eigenes Projekt und wird separat geplant.

### Migrationshinweise (Server 2 / weitere Server)
- `./scripts/update.sh` reicht (zieht auch das neue Caddy-Image). Kurzer Caddy-Neustart beim Image-Wechsel (~2 s, TLS-Zertifikate bleiben im Volume). Browser mit Strg+F5 neu laden, damit der Live-Log den neuen WebSocket-Weg nutzt.

## [2.8.0] - 2026-06-11

### Geaendert (Code-Qualitaet, kein Funktionsunterschied)
- **Backend-Robustheit** — Fehlgeschlagene Alembic-Migration bricht den Start jetzt ab statt still auf `create_all()` zurueckzufallen (verhindert halbmigrierte Schemata). Verschluckte Exceptions in Stats-Collector, Cert-Service und Log-WebSocket loggen jetzt volle Stacktraces.
- **Portal-Auth gehaertet** — Settings werden 30 s gecacht statt pro Request per DB-Session geladen (Invalidierung bei Aenderung); `X-Forwarded-For` wird nur noch akzeptiert, wenn der direkte Peer privat ist (Caddy im Docker-Netz) — blockiert IP-Whitelist-Spoofing per Header; API-Key-Vergleich in konstanter Zeit; Brute-Force-Schutz: 30 Fehlversuche/60 s pro IP -> 429.
- **portal_router aufgeteilt** — Die 800-Zeilen-Datei ist jetzt `portal_common.py` (Auth/Helfer), `portal_settings_router.py` (Admin-Endpoints) und `portal_router.py` (oeffentliche Endpoints). Routenliste vor/nach identisch verifiziert (111 Routen).
- **Frontend: zentrales `useApi()`-Composable** — Die in ~20 Views/Komponenten duplizierten `try/catch`+Toast-Bloecke laufen jetzt ueber `composables/useApi.ts` (`call` mit Erfolgs-/Fehler-Toast, `silent` fuer Polling). Toast-Texte und Verhalten unveraendert.
- **Frontend: Typisierung** — Neue `types/api.ts` (AdminUser, SmtpUser, IpBan, Network, MailEvent) plus lokale Interfaces ersetzen alle `: any`/`catch (e: any)` (0 verbleibend); `noUnusedLocals`/`noUnusedParameters` in tsconfig aktiviert.

### Migrationshinweise (Server 2 / weitere Server)
- `./scripts/update.sh` reicht; kein manueller Schritt. Browser einmal mit Strg+F5 neu laden.

## [2.7.3] - 2026-06-11

### Geaendert
- **Frontend-Toolchain aktualisiert** — Vite 6 -> 8, TypeScript 5.7 -> 6.0, vue-tsc 2 -> 3.3, @vitejs/plugin-vue 5 -> 6, vue-router 4 -> 5, Pinia 2 -> 3, PrimeVue 4.3 -> 4.5, Vue 3.5.38, axios 1.17, chart.js 4.5. Keine Code-Aenderungen noetig (Standard-APIs, Composition API durchgaengig); Type-Check und Build laufen sauber durch. `package-lock.json` neu generiert (Node 22 / npm 10).

### Migrationshinweise (Server 2 / weitere Server)
- `./scripts/update.sh` reicht. Nach dem Update einmal das Admin-Panel im Browser neu laden (Strg+F5), damit die neuen Assets gezogen werden.

## [2.7.2] - 2026-06-11

### Geaendert
- **Backend-Abhaengigkeiten aktualisiert** — FastAPI 0.115 -> 0.136 (Starlette 1.3), uvicorn 0.34 -> 0.49, websockets 14 -> 16, SQLAlchemy 2.0.36 -> 2.0.50, Alembic 1.14 -> 1.18, pydantic-settings 2.7 -> 2.14, python-multipart 0.0.20 -> 0.0.32. Bisher ungepinnte Pakete (`cryptography`, `reportlab`, `dnspython`) sind jetzt exakt gepinnt — identische, reproduzierbare Builds auf allen Servern.
- **passlib entfernt, bcrypt direkt** — `passlib` 1.7.4 ist seit 2020 unbetreut und erzwang den veralteten Pin `bcrypt==4.0.1`. Passwort-Hashing (`auth.py`) nutzt jetzt `bcrypt` 5.0 direkt. Format unveraendert (`$2b$12$`) — **alle bestehenden Login-Passwoerter funktionieren weiter** (verifiziert gegen passlib-erzeugte Hashes).
- **Frontend-Build auf Node 22** — `node:20-alpine` ist seit April 2026 EOL (keine Sicherheitsupdates mehr); Build-Stage nutzt jetzt `node:22-alpine` (LTS). `npm install` -> `npm ci` (deterministisch aus `package-lock.json`).
- **`.dockerignore` ergaenzt** (Root + admin/) — kleinere Build-Kontexte, keine lokalen Artefakte (node_modules, DBs, Logs) im Image-Build.

### Migrationshinweise (Server 2 / weitere Server)
- `./scripts/update.sh` reicht. Kein manueller Schritt noetig; Sessions und Passwoerter bleiben gueltig. Verifiziert: Login/JWT, WebSocket-Live-Log, alle API-Router, Firewall-Sync.

## [2.7.1] - 2026-06-11

### Sicherheit
- **JWT-Bibliothek getauscht: python-jose -> PyJWT** — `python-jose` 3.3.0 hat bekannte Schwachstellen (CVE-2024-33663 Algorithm-Confusion, CVE-2024-33664 JWE-DoS) und wird kaum noch gepflegt. Die Token-Erstellung/-Pruefung (`auth.py`) laeuft jetzt ueber das aktiv gepflegte `PyJWT` 2.13. Gleicher Algorithmus (HS256), gleicher Secret — **bestehende Sessions bleiben gueltig**.
- **CORS eingeschraenkt** — Bisher `allow_origins=["*"]` zusammen mit `allow_credentials=True` (CSRF-Risiko). Jetzt sind nur noch `https://<ADMIN_HOSTNAME>` und der Vite-Dev-Server (`http://localhost:5173`) erlaubt. Die SPA selbst wird same-origin ausgeliefert und braucht kein CORS.
- **Firewall-Service validiert IPs** — `block_ip`/`unblock_ip`/`sync_bans` pruefen Eingaben jetzt mit `ipaddress` und kanonisieren sie, bevor sie in den `ipset`-Befehl im Firewall-Container interpoliert werden (Defense-in-Depth gegen Command-Injection; bisher schuetzte nur der Schema-Validator am API-Rand).
- **Warnung bei schwachem ADMIN_SECRET_KEY** — Beim Start wird geprueft, ob der Default (`change-me-in-production`) aktiv oder der Key kuerzer als 32 Zeichen ist; dann erscheint eine deutliche Warnung im Log. Aus dem Secret wird auch der Fernet-Schluessel fuer die SMTP-Passwoerter abgeleitet — deshalb gibt es fuer den Wechsel ein Rotations-Tool (siehe unten).

### Hinzugefuegt
- **Rotations-Tool fuer ADMIN_SECRET_KEY** (`app/tools/rotate_secret_key.py`) — verschluesselt alle gespeicherten SMTP-Passwoerter vom alten auf den neuen Key um. Ohne dieses Tool waeren die Passwoerter nach einem Key-Wechsel unlesbar. Anwendung: `docker exec -it open-mail-relay-admin python -m app.tools.rotate_secret_key '<ALT>' '<NEU>'`, danach `.env` anpassen und `docker compose up -d admin-panel`. Admin-Sessions werden dabei invalidiert (erneuter Login), SMTP-Versand laeuft unterbrechungsfrei weiter.
- **Update-Skript `scripts/update.sh`** — einheitlicher Update-Weg fuer alle Server: `git pull --ff-only` + `docker compose build` + `up -d`. Laufzeit-Dateien bleiben unangetastet, Alembic-Migrationen laufen automatisch beim Start.

### Geaendert
- **`postfix/client_access` aus Git entfernt** — Die Datei wird zur Laufzeit aus der DB generiert (und vom Entrypoint angelegt, falls sie fehlt). Als getrackte Datei blockierte sie auf jedem Server mit lokalen Sperren das `git pull`. Sie war bereits in `.gitignore` gelistet, aber noch aus der Anfangszeit getrackt.

### Migrationshinweise (Server 2 / weitere Server)
1. `./scripts/update.sh` (oder manuell: `git pull --ff-only && docker compose build && docker compose up -d`). Falls `git pull` wegen lokaler `postfix/client_access`-Aenderungen scheitert: `git checkout -- postfix/client_access` (Datei wird beim naechsten Panel-Start aus der DB neu generiert) und erneut pullen.
2. Optional, aber empfohlen: `ADMIN_SECRET_KEY` rotieren, falls er schwach ist (siehe Rotations-Tool oben). Neuen Key erzeugen mit `openssl rand -hex 32`.

## [2.7.0] - 2026-06-11

### Hinzugefuegt
- **Provider-Sperren-Monitoring** — Neue Ansicht „Provider-Sperren": erkennt provider-interne Versandsperren (z. B. Outlook-/Gmail-spezifische Ablehnungscodes) aus den Mail-Logs, gruppiert sie nach Fehlertyp und zeigt fehlertyp-spezifische Delisting-Anleitungen samt Status-Tracking an (`provider_block_service/worker/router`, Migration 015, Dashboard-Integration). *(Eintrag nachgetragen.)*

## [2.6.0] - 2026-06-03

### Hinzugefuegt
- **Automatische MX-basierte Transport-Erkennung** — Empfaengerdomains, die bei Microsoft 365, Google Workspace oder Yahoo *gehostet* sind (erkennbar am MX-Eintrag, z. B. `*.mail.protection.outlook.com`), werden jetzt automatisch dem passenden gedrosselten Transport (`outlook_throttled` / `gmail_throttled` / `yahoo_throttled`) zugeordnet — nicht mehr nur die Consumer-Domains (outlook.com, gmail.com …). Bisher fielen geschaeftliche M365-Domains in `*  default_throttled` (Concurrency 5), wodurch sich ueber viele Tenants hinweg zu viele gleichzeitige Verbindungen gegen denselben Microsoft-„resource forest" stauten und Microsoft mit `421 4.3.2 The maximum number of concurrent connections per resource forest has exceeded a limit` drosselte (stundenlange Queue-Verzoegerungen). Neues Modul `mx_detection.py`: ermittelt die tatsaechlich bedienten Empfaengerdomains aus `mail_events`, klassifiziert sie per echtem MX-Lookup (dnspython) mit Fallback auf den real verwendeten `relay`-Host, und speist das Ergebnis in `generate_transport_map()` ein. Manuell angelegte Transport-Regeln haben immer Vorrang; der Provider→Transport-Name wird aus den vorhandenen Regeln abgeleitet (keine Zuordnung zu undefinierten Transports). MX-Ergebnisse werden auf Platte zwischengespeichert (positiv 14 Tage / negativ 2 Tage), damit das Neu-Generieren der Map kein DNS-Bombardement ausloest.
- **Toggle `mx_autodetect`** (Default: an) in der Drosselungs-Konfiguration (`PUT /throttle/config`); Aenderung baut die Transport-Map bei aktiver Drosselung sofort neu und wird im Audit-Log protokolliert.
- **Vorschau-Endpoint** `GET /throttle/transports/auto-detected` — listet die automatisch erkannten Domains samt Provider, Ziel-Transport und Erkennungsquelle (`mx` / `relay` / `cache`), ohne die Map zu veraendern.

## [2.5.2] - 2026-06-02

### Behoben
- **„Jetzt erneuern" scheiterte mit „server block without any key …"** — Der in v2.5.1 eingefuehrte `caddy reload` lief per `docker exec` und scheiterte beim Adaptieren des Caddyfiles, weil `{$MAIL_HOSTNAME}` leer war: Diese Variable wird nicht ueber Compose gesetzt, sondern erst im Caddy-Entrypoint aus `main.cf` abgeleitet (`caddy/entrypoint.sh`) und ist daher im exec-Kontext nicht vorhanden. Ein leerer Hostname macht den Mail-Site-Block zu einem Block ohne Key (= globale Optionen, nicht an erster Stelle) -> Adaptierungsfehler. `reload_caddy()` injiziert `MAIL_HOSTNAME` jetzt explizit beim exec (aus `_get_mail_hostname()`/`main.cf`); `ADMIN_HOSTNAME` und `LETSENCRYPT_EMAIL` kommen weiterhin aus der Container-Umgebung. Verifiziert via `caddy adapt`: ohne Variable exit 1 (Fehler), mit Variable exit 0.

## [2.5.1] - 2026-06-02

### Behoben
- **„Jetzt erneuern" meldete faelschlich einen Fehler** — `renew_certs()` startete den Caddy-**Container neu** (`restart_caddy`). Da das Admin-Panel selbst durch Caddy geproxyt wird (`reverse_proxy admin-panel:8000`), kappte der Neustart die laufende HTTP-Verbindung des Browsers mitten im `POST /config/tls/renew` — die 200-Antwort erreichte das Frontend nie, es zeigte einen Fehler, obwohl die Erneuerung serverseitig erfolgreich war. `renew_certs()` nutzt jetzt einen **graceful `caddy reload`** (neue Funktion `reload_caddy()` in `docker_service.py`, via Caddy-Admin-API, Zero-Downtime): bestehende Verbindungen bleiben erhalten, eine erneute Zertifikatsverwaltung wird angestossen, anschliessend wird nach Postfix synchronisiert. Betrifft auch die automatische Erneuerung im `CertWorker` (kein kurzer TLS-Ausfall mehr bei Auto-Renew).

## [2.5.0] - 2026-06-02

### Hinzugefuegt
- **TLS-Zertifikate: Uebersicht aller Zertifikate, automatische & manuelle Erneuerung** — Die Sektion „TLS-Zertifikat" (Konfiguration) zeigt jetzt **alle** von Caddy verwalteten Relay-Zertifikate (Mail- **und** Admin-Hostname) mit farbigem Status (`gueltig` / `laeuft bald ab` / `abgelaufen`), Resttagen, Aussteller und Subject; das in Postfix aktive Zertifikat ist markiert (`TlsStatus.vue`, `get_all_certs()` in `cert_service.py`, neues Schema `CertInfo`).
- **Manuelle Erneuerung** — Neuer Button „Jetzt erneuern" (`POST /config/tls/renew` → `renew_certs()`): startet Caddy neu (erneuert faellige/abgelaufene Zertifikate; No-op bei gueltigen, kein Rate-Limit-Risiko) und synchronisiert anschliessend nach Postfix.
- **Taeglicher Monitoring-Worker** (`cert_worker.py`) — prueft taeglich alle Zertifikate; bei Ablauf/Restlaufzeit <30 Tagen wird automatisch eine Erneuerung ausgeloest (gedrosselt auf max. 1x/12h) und eine Warn-E-Mail an `LETSENCRYPT_EMAIL` (Fallback `rbl_mail_to`) versendet (max. 1 Mail pro Zertifikat/Tag).

### Behoben
- **Abgelaufenes Zertifikat wurde angezeigt, obwohl ggf. ein gueltiges existierte** — `cert_service.py` und `scripts/entrypoint.sh` lasen nur das Let's-Encrypt-Verzeichnis bzw. nahmen das *erste* gefundene `.crt`. Caddy nutzt standardmaessig mehrere Aussteller (Let's Encrypt + ZeroSSL) mit je eigenem Verzeichnis; ein abgelaufenes Cert konnte ein gueltiges verdecken. Es wird nun ueber **alle** Aussteller-Verzeichnisse gesucht und das Cert mit dem spaetesten Ablaufdatum (bzw. in `entrypoint.sh` das neueste) verwendet.

## [2.4.4] - 2026-05-04

### Behoben
- **Kontingent-Berichte doppelt verschickt** — `send_usage_reports()` iterierte pro `SmtpUser` und sendete eine separate E-Mail je Datensatz. Hatten mehrere SMTP-Benutzer derselben Kunden dieselbe `contact_email` (typisch bei einem Kunden mit getrennten Trans-/Newsletter-Paketen oder mehreren Logins), bekam diese Adresse N quasi-identische E-Mails gleichzeitig (im Postfix-Log z. B. dreifacher Versand an `dbe@login-online.com` am 17.04.). Die Funktion gruppiert Empfaenger jetzt nach `contact_email` (case-insensitive); pro Adresse geht eine E-Mail mit einem Abschnitt je SMTP-Benutzer (Username, Paket, Limit, Versand, Restkontingent, Fortschrittsbalken, ggf. Warnung) raus. Template `_build_usage_report_html` akzeptiert eine Liste von User-Daten; pro-User-Block wurde nach `_build_user_section_html` ausgelagert. Einzelversand aus der Admin-UI (`send_single_usage_report`) nutzt dasselbe Template mit einer Ein-Element-Liste.

## [2.4.3] - 2026-04-16

### Behoben
- **DKIM-Signierung fuer Kundendomaenen** — OpenDKIM war hart auf eine einzige Domain (`mydomain` aus `main.cf`, z. B. `spamgo.de`) verdrahtet; Mails mit From-Domain wie `hsgm.com` wurden still uebersprungen (`dkim=none (message not signed)`). Die OpenDKIM-Konfiguration in `scripts/entrypoint.sh` nutzt jetzt `KeyTable`/`SigningTable` mit dem `%`-Platzhalter: derselbe Relay-Schluessel (`<selector>.private`) signiert **jede** From-Domain, das `d=`-Feld wird zur Laufzeit aus der From-Adresse abgeleitet. Passt zum bereits bestehenden CNAME-Delegationsmodell (Kunde setzt `<selector>._domainkey.<kundendomain>` CNAME auf `<selector>._domainkey.<relaydomain>`, vgl. Konfigurations-PDF v2.4.0).

## [2.4.2] - 2026-04-16

### Behoben
- **Protokoll-Benutzerfilter zeigt nur registrierte SMTP-Benutzer** — Das Dropdown „Benutzer" in der Protokoll-Ansicht listete bisher alle jemals in Postfix-Logs aufgetauchten `sasl_username`-Werte (inkl. fehlgeschlagener Auth-Versuche mit willkuerlichen Benutzernamen). Der Endpunkt `GET /api/logs/events/usernames` liefert jetzt ausschliesslich Benutzernamen aus der Tabelle `smtp_users` — konsistent mit der Liste in der SMTP-Benutzer-Ansicht.

## [2.4.1] - 2026-04-16

### Behoben
- **DKIM-Sektion fehlte im Admin-UI Konfigurations-PDF** — Der in v2.4.0 eingefuehrte DKIM-CNAME-Check wurde nur im Portal-Router (`/api/portal/config-pdf/{id}`) aufgerufen, nicht aber im Admin-UI-Endpunkt (`/api/smtp-users/{id}/config-pdf`). PDFs, die aus der Admin-Oberflaeche heruntergeladen wurden, enthielten daher keine DKIM-Informationen. `_build_config_pdf()` in `smtp_users_router.py` ruft jetzt ebenfalls `check_customer_dkim_cname()` auf und uebergibt `dkim_info` an den PDF-Generator.

## [2.4.0] - 2026-04-16

### Hinzugefuegt
- **DKIM-CNAME-Pruefung im Kunden-Konfigurations-PDF** — Beim Generieren des SMTP-Konfigurations-PDFs (`/portal/config-pdf/{smtp_user_id}`) wird zusaetzlich zum bestehenden SPF-Check eine DNS-Abfrage gegen `<servername>._domainkey.<kundendomain>` durchgefuehrt und als eigene Sektion auf Seite 2 dargestellt. Drei Status (`ok` / `needs_update` / `missing`) mit identischer Farbgebung wie die SPF-Sektion: gruener Hinweis bei korrektem CNAME, gelber Hinweis mit aktuellem und empfohlenem Eintrag bei falschem Ziel oder fehlender CNAME. Empfohlener Eintrag hat die Form `<selector>._domainkey.<kundendomain>  CNAME  <selector>._domainkey.<relay-domain>`, wobei der Selector dem ersten Hostname-Label des Relays entspricht (z. B. `relay2`). Sektion wird wie SPF uebersprungen, wenn beim SMTP-User keine `mail_domain` hinterlegt ist.
- Neue Service-Funktion `check_customer_dkim_cname()` in `spf_check_service.py` mit `_resolve_cname()`-Helper (dnspython, Lifetime 5 s, NXDOMAIN/NoAnswer/NoNameservers tolerant).

## [2.3.2] - 2026-04-16

### Entfernt
- **Portal-Konfigurationsblock in der Admin-UI** — Der Hinweisblock "Diesen Block in die Portal-Konfiguration einfuegen" (mit `RELAY_API_URL`, `RELAY_API_KEY`, `RELAY_SERVER`) wurde aus der Sektion Portal-API entfernt, da er nicht mehr benoetigt wird. Die zugehoerigen ungenutzten i18n-Keys (`portalCopyConfig`, `portalConfigCopied`, `portalConfigHint`) wurden aufgeraeumt.

## [2.3.1] - 2026-04-16

### Behoben
- **DKIM-Signierung fuer alle autorisierten Absender** — Ausgehende E-Mails von externen mynetworks-IPs und SASL-authentifizierten Benutzern (Port 587) wurden nicht DKIM-signiert, da OpenDKIM's `InternalHosts` nur private Netzwerke enthielt. Korrektur: `InternalHosts` auf `0.0.0.0/0` gesetzt, da Postfix bereits ueber `smtpd_relay_restrictions` sicherstellt, dass nur autorisierte Nachrichten den Milter erreichen.

## [2.3.0] - 2026-04-15

### Hinzugefuegt
- **Portal-API Erweiterung fuer Kundendashboard** — Neue Endpunkte unter `/api/portal/smtp-users` fuer das Spamgo-Kundenportal (my.spamgo.de)
  - `GET /api/portal/smtp-users?domain=...` — Suche nach SMTP-Benutzern anhand der `mail_domain` (Onboarding-Matching nach OAuth-Login)
  - `GET /api/portal/smtp-users/{username}/stats` — Zustellstatistiken pro SMTP-Benutzername (analog zum bestehenden ID-basierten Endpunkt)
  - `GET /api/portal/smtp-users/{username}/logs` — Paginiertes Protokoll mit Filtern (Status, Datumsbereich, Freitextsuche)
  - `GET /api/portal/smtp-users/{username}/logs.csv` — CSV-Export des gefilterten Protokolls (max. 10.000 Zeilen)
  - `GET /api/portal/smtp-users/{username}/bounces` — Paginierte Liste von Bounces/Deferred/Rejected mit DSN-Details
- **Erweiterte Bounce-Informationen in MailEvent** — Neue Spalten `dsn_code` und `remote_response` fuer strukturierte Bounce-Analyse
  - Ermoeglicht dem Kundenportal, detaillierte DSN-Codes und Remote-Server-Antworten anzuzeigen
  - Felder sind nullable und werden bei bestehenden Eintraegen leer gelassen
- Neue Datenbank-Migration: 014 (dsn_code, remote_response auf mail_events)
- **Log-Parser extrahiert Bounce-Details** — `dsn_code` und `remote_response` werden automatisch aus der Postfix-Statuszeile erkannt (Muster `said: NNN ...` und `refused to talk to me: NNN ...`) und bei neuen Mail-Events befuellt

### Geaendert
- `MailEventOut`-Schema um `dsn_code` und `remote_response` erweitert
- CSV-Export im Kundenportal enthaelt neue DSN-Spalten
- README um kurzen Abschnitt "Update" ergaenzt (`git pull` + `docker compose up -d --build`)

## [2.2.0] - 2026-04-15

### Hinzugefuegt
- **SMTP-Benutzer-Filter im Protokoll** — Neues Dropdown im Protokoll-Bereich zum Filtern nach SMTP-Benutzer (Quelle/Kunde)
  - Dedizierter Filter neben dem Status-Filter fuer gezielte Analyse aller Mail-Aktionen eines Kunden
  - Neuer API-Endpoint `GET /api/logs/events/usernames` liefert alle aktiven SMTP-Benutzernamen
  - Filter wird auch beim CSV-Export beruecksichtigt
  - Benutzerliste wird automatisch aus den vorhandenen Log-Eintraegen geladen

## [2.1.0] - 2026-03-26

### Hinzugefuegt
- **Portal-API fuer externes Kundenportal** — Neuer API-Router (`/api/portal`) mit 7 Endpunkten fuer das externe Kundenportal (my.spamgo.de)
  - `GET /api/portal/health` — Health-Check mit Server-Hostname und Version
  - `GET /api/portal/lookup?email=...` — Kundensuche per Kontakt-E-Mail (case-insensitive, aktive + inaktive Benutzer)
  - `GET /api/portal/stats/{id}` — Zustellstatistiken pro SMTP-Benutzer (heute, 24h-Verlauf stuendlich, 30-Tage-Verlauf taeglich)
  - `GET /api/portal/dns-check/{id}` — SPF/DKIM/DMARC-Pruefung fuer die Mail-Domain des SMTP-Benutzers
  - `POST /api/portal/reset-password/{id}` — SMTP-Passwort zuruecksetzen mit Dovecot-Synchronisierung
  - `GET /api/portal/config-pdf/{id}` — PDF-Konfigurationsblatt als Download
  - `GET /api/portal/rbl-status` — Aktueller RBL-Blacklist-Status des Servers
- **Portal-API Absicherung** — Doppelte Authentifizierung per IP-Whitelist und API-Key (Header `X-Portal-API-Key`)
- **Portal-API Einstellungen im Admin-UI** — Neue Settings-Card auf der Konfigurationsseite
  - API-Schluessel Generator (64-Zeichen Hex-Token)
  - IP-Whitelist Verwaltung (kommaseparierte Liste)
  - Kopierbarer Konfigurations-Block (`RELAY_API_URL`, `RELAY_API_KEY`, `RELAY_SERVER`) fuer fehlerfreie Uebertragung ins Portal
  - Alle Einstellungen in der Datenbank gespeichert (kein Container-Neustart noetig)
- Neuer Service: `portal_router.py` — Portal-API Endpunkte und Admin-Settings-Verwaltung via SystemSetting
- Neue Frontend-Komponente: `PortalApiSettings.vue` — Settings-Card mit Key-Generator und Copy-to-Clipboard

## [2.0.0] - 2026-03-25

### Hinzugefuegt
- **Erweiterte SMTP-Benutzerverwaltung** — Neue Felder fuer Kunden-Mail-Domain (`mail_domain`) und Kontakt-E-Mail (`contact_email`) pro SMTP-Benutzer
  - Einheitlicher PrimeVue-Dialog fuer Neuanlage und Bearbeitung (ersetzt separates Formular und Inline-Editing)
  - Bearbeiten-Button (Stift-Icon) in der Aktionsspalte
  - Neues Feld `receive_reports` (Checkbox) — steuert ob Kunde woechentliche Kontingent-Berichte erhaelt
- **SPF-Record Pruefung im PDF** — Bei SMTP-Benutzern mit hinterlegter Mail-Domain wird beim PDF-Download live der SPF-Record geprueft
  - Drei Faelle: SPF fehlt (Vorschlag), SPF muss erweitert werden (aktueller + empfohlener Record), SPF korrekt (Bestaetigung)
  - Eigene Seite 2 im PDF mit farbcodierten Hinweisboxen
- **Betreiber-Info im PDF** — Relay-Betreiber (Name, E-Mail, Telefon) aus Konfiguration wird im PDF-Konfigurationsblatt angezeigt
- **Zugangsdaten per E-Mail versenden** — Neuer Button (Briefumschlag-Icon) sendet SMTP-Zugangsdaten inkl. PDF-Anhang direkt an die Kontakt-E-Mail des Kunden
  - HTML-E-Mail mit Betreiber-Signatur, Sicherheitshinweis und PDF-Attachment
  - Nur aktiv wenn Kontakt-E-Mail hinterlegt
- **Woechentliche Kontingent-Berichte** — Automatischer Versand individueller Nutzungsberichte an Kunden
  - HTML-E-Mail mit Paketname, Limit, aktuellem Verbrauch, verbleibendem Kontingent und visuellem Fortschrittsbalken
  - Farbcodierung: gruen (<75%), gelb (75-90%), rot (>90%) mit Warnhinweis
  - Betreiber-Signatur im Footer
  - Konfigurierbar: Versandtag (Wochentag) und Ein/Aus in den Abrechnungs-Einstellungen
  - Kunden koennen ueber Checkbox "Bericht" in der Benutzerverwaltung abgemeldet werden
- **Manueller Kontingent-Bericht** — Button (Chart-Icon) in der SMTP-Benutzerverwaltung zum sofortigen Versand eines Kontingent-Berichts an einzelne Kunden
- **Abrechnungs-Einstellungen verbessert** — Zwei nebeneinander liegende Bloecke: "Monatsbericht (intern)" und "Kontingent-Berichte (Kunden)" mit Beschreibung des jeweiligen Zwecks
- Neue API-Endpunkte:
  - `POST /api/smtp-users/{id}/send-credentials` — Zugangsdaten per E-Mail senden
  - `POST /api/smtp-users/{id}/send-usage-report` — Kontingent-Bericht manuell senden
- Neue Datenbank-Migrationen: 012 (mail_domain, contact_email), 013 (receive_reports)
- Neuer Service: `spf_check_service.py` — Live-DNS-Lookup fuer Kunden-SPF-Records

### Geaendert
- PDF-Konfigurationsblatt: Titel "SMTP-Relay Zugangsdaten", Betreiber-Block, Kunden-Block mit Paket statt Dienst, SPF-Seite 2, ueberarbeiteter Sicherheitshinweis
- SMTP-Benutzer-Tabelle: Neue Spalten (Mail-Domain, Kontakt-E-Mail), Inline-Editing entfernt, Edit-Button hinzugefuegt
- BillingWorker: Erweitert um woechentlichen Kontingent-Bericht-Versand mit konfigurierbarem Wochentag

## [1.9.0] - 2026-03-25

### Hinzugefuegt
- **Paket- und Abrechnungssystem** — Neues Feature zur Verwaltung von E-Mail-Paketen und monatlicher Abrechnung pro SMTP-Benutzer
  - **Paketverwaltung** — Vordefinierte Pakete fuer Transaktions-E-Mails (Trans-S/M/L) und Newsletter (News-S/M/L/XL) mit konfigurierbaren Monatslimits
  - **Paket-Zuweisung** — Jedem SMTP-Benutzer kann ein Paket zugewiesen werden (Dropdown in Benutzerliste und Erstellformular)
  - **Monatliche E-Mail-Zaehlung** — Automatische stuendliche Aggregation der gesendeten E-Mails pro Benutzer aus den Mail-Events
  - **Ueberschuss-Berechnung** — Bei Ueberschreitung des Paketlimits werden automatisch Ext-1K Zusatzpakete (je 1.000 E-Mails) berechnet
  - **Monatsabrechnung** — Uebersichtsseite mit Monatsauswahl, Benutzer-Verbrauchstabelle, Paketlimits und Zusatzpaket-Anzeige
  - **Automatischer Monatsbericht** — Am 1. jedes Monats wird der Bericht des Vormonats automatisch per HTML-E-Mail an konfigurierbare Adresse gesendet
  - **Manueller Berichtversand** — Berichte koennen jederzeit manuell ueber die Abrechnungsseite versendet werden
  - Eigene Admin-Panel-Seite "Abrechnung" mit drei Bereichen: Pakete, Monatsabrechnung, Einstellungen
- Neue Datenbanktabellen: `packages`, `user_monthly_usage`, `billing_reports`
- Neues Feld `package_id` auf `smtp_users` (FK zu Paketen)
- Neue API-Endpunkte unter `/api/billing`:
  - `GET/POST/PUT/DELETE /api/billing/packages` — Paket-CRUD
  - `GET /api/billing/overview` — Monatsabrechnung mit Ueberschuss
  - `POST /api/billing/overview/refresh` — Zaehlung aktualisieren
  - `POST /api/billing/report/{year_month}/send` — Bericht versenden
  - `GET/PUT /api/billing/settings` — Berichts-E-Mail-Einstellungen
- Background-Worker fuer stuendliche Usage-Aktualisierung und automatischen Monatsversand

## [1.8.0] - 2026-03-23

### Hinzugefuegt
- **DNS-Record-Pruefung (SPF, DMARC, DKIM)** — Neue Admin-Panel-Seite zur Validierung aller relevanten DNS-Records fuer die Mail-Zustellung
  - **SPF-Check** mit rekursiver `include:`-Aufloesung — prueft ob die Server-IP im SPF-Record autorisiert ist, inklusive verschachtelter Include-Ketten (bis 5 Ebenen, RFC 7208 konform)
  - **DMARC-Check** — prueft Existenz und Gueltigkeit des DMARC-Records inkl. Policy-Parsing
  - **DKIM-Check** — prueft ob ein DKIM-Public-Key-Record fuer den konfigurierten Selector existiert
  - Copy-Paste DNS-Eintraege fuer fehlende Records (SPF, DMARC) werden automatisch generiert
  - DKIM-Selector automatisch aus Hostname abgeleitet (z.B. `relay2.spamgo.de` → Selector `relay2`) — ermoeglicht mehrere Mail-Server auf derselben Domain, nicht manuell aenderbar
  - Test beliebig oft wiederholbar per Button
- **DKIM-Signing mit OpenDKIM** — Ausgehende E-Mails werden automatisch DKIM-signiert
  - OpenDKIM als Milter in den Postfix-Container integriert
  - 2048-Bit RSA-Schluessel wird beim ersten Container-Start automatisch generiert
  - Schluessel persistent im Shared Volume (`postfix/dkim/`), ueberlebt Container-Rebuilds
  - DKIM Public Key im Admin-Panel anzeigbar mit Copy-Button fuer DNS-Eintrag
  - Schluessel loeschen und neu generieren ueber Admin-Panel moeglich
- **Dashboard DNS-Status-Indikator** — Clickbare Statuskarte zeigt gruen (alle Records OK), rot (Probleme) oder grau (nicht geprueft)
- **Container-Verwaltung** — Neue Sektion in der Konfigurationsseite zum Neustart einzelner Docker-Container (Mail-Server, Caddy, Firewall) mit Status-Anzeige und Audit-Logging
  - Restart-Button auch direkt auf der DNS-Pruefung-Seite bei fehlendem DKIM-Schluessel (generiert Key beim Neustart automatisch)
- Neue API-Endpunkte unter `/api/dns-check`:
  - `GET /api/dns-check` — Server-Info und letzte Ergebnisse
  - `POST /api/dns-check/check` — DNS-Pruefung ausfuehren
  - `GET /api/dns-check/status` — Dashboard-Zusammenfassung
  - `GET /api/dns-check/dkim-key` — DKIM Public Key lesen
  - `DELETE /api/dns-check/dkim-key` — DKIM-Schluessel loeschen
- Neue API-Endpunkte unter `/api/config`:
  - `GET /api/config/containers` — Status aller verwalteten Container
  - `POST /api/config/containers/{name}/restart` — Container neu starten
- Neue Abhaengigkeit: `dnspython>=2.6.0` fuer TXT-Record-Abfragen
- Audit-Logging fuer DNS-Pruefungen, DKIM-Key-Loeschung und Container-Neustarts

## [1.7.0] - 2026-03-23

### Hinzugefuegt
- **RBL-Blacklist-Checker** - Automatische Pruefung der Server-IP gegen 22 DNS-Blacklists mit E-Mail-Benachrichtigung bei Listings
  - Eigene Server-IP und Hostname werden automatisch aus der Postfix-Konfiguration gelesen (kein manuelles Eintragen noetig)
  - 22 RBL-Blacklists werden parallel geprueft (Spamhaus, Barracuda, SpamCop, SORBS, UCEPROTECT, CBL, PSBL u.v.m.)
  - Periodische Hintergrund-Pruefung mit konfigurierbarem Intervall (Standard: alle 6 Stunden)
  - E-Mail-Alarm bei Blacklist-Eintraegen mit detailliertem Report (Uebersicht, Details, neue/entfernte Listings)
  - Option "Nur bei Aenderung" — E-Mail nur wenn sich der Listing-Status aendert
  - Test-Mail-Funktion zum Pruefen der E-Mail-Konfiguration
  - Zusaetzliche Server konfigurierbar fuer Multi-IP-Setups
  - False-Positive-Filterung: Spamhaus-Antworten fuer oeffentliche DNS-Resolver (127.255.255.252/254/255) werden ignoriert
- **Dashboard RBL-Status-Indikator** - Clickbare Statuskarte auf dem Dashboard zeigt aktuellen Blacklist-Status
  - Gruen (CLEAN), Rot (LISTINGS) oder Grau (noch nicht geprueft)
  - Letzte Pruefzeit wird angezeigt
  - Klick navigiert direkt zur RBL-Pruefung-Seite
  - Automatischer Refresh alle 30 Sekunden
- Neue Admin-Panel-Seite "RBL-Pruefung" mit Einstellungen, Server-Info, Ergebnis-Tabelle und Listing-Details
- Neuer Hintergrund-Worker `rbl_worker.py` fuer periodische Pruefungen
- E-Mail-Versand ueber den lokalen Postfix-Container (kein externer SMTP noetig)
- Neue API-Endpunkte unter `/api/rbl`:
  - `GET /api/rbl` — Einstellungen lesen
  - `PUT /api/rbl` — Einstellungen aendern
  - `POST /api/rbl/check` — Manuelle Pruefung ausloesen
  - `GET /api/rbl/server-info` — Eigenen Hostnamen und IP abrufen
  - `GET /api/rbl/status` — Status-Zusammenfassung fuer Dashboard
  - `POST /api/rbl/test-email` — Test-Mail senden
- Audit-Logging fuer RBL-Pruefungen, Einstellungsaenderungen und Test-Mails

## [1.6.0] - 2026-03-03

### Hinzugefuegt
- **Firewall-basierte IP-Sperre (iptables/ipset)** - Gesperrte IPs werden jetzt auf Netzwerkebene geblockt, nicht nur per Postfix-REJECT
  - Neuer Docker-Sidecar-Container `firewall` mit `network_mode: host` und `NET_ADMIN` Capability
  - `ipset` (`omr-banned`, Typ `hash:net`) fuer effiziente IP-Verwaltung im Kernel
  - Einzelne iptables-Regel in der `DOCKER-USER`-Chain droppt Pakete gebannter IPs auf Port 25/587 **vor** Docker-Routing
  - Gesperrte IPs koennen keine TCP-Verbindung mehr aufbauen (kein SYN-ACK, kein Postfix-Log-Eintrag)
  - Automatische Synchronisierung: ipset wird bei Ban/Unban/Ablauf und beim Admin-Panel-Start aktualisiert
  - Firewall-Container laedt bestehende Sperren aus `client_access` beim eigenen Start (unabhaengig vom Admin-Panel)
  - Bestehende Postfix-Ebene (`client_access` CIDR Map) bleibt als zweite Verteidigungslinie erhalten
- Neuer Service `firewall_service.py` mit Funktionen `block_ip()`, `unblock_ip()`, `sync_bans()`
- Neues Entrypoint-Skript `scripts/firewall-entrypoint.sh`

### Geaendert
- `docker-compose.yml` — Neuer `firewall`-Service (Alpine 3.21, host-Netzwerk, NET_ADMIN)
- `ban_service.py` — Alle Ban/Unban-Operationen aktualisieren jetzt zusaetzlich das Firewall-ipset
- `main.py` — Firewall-Sync (`sync_bans`) beim Admin-Panel-Start
- `config.py` — Neues Setting `FIREWALL_CONTAINER`

## [1.5.1] - 2026-02-27

### Hinzugefuegt
- **Zweisprachige Abuse-Seite (DE/EN)** - Die oeffentliche Abuse- & Postmaster-Seite unterstuetzt jetzt Deutsch und Englisch
  - Sprachwechsel-Buttons im Header (DE | EN)
  - Sprachauswahl wird im Browser gespeichert (localStorage)
  - CSS-basiertes Umschalten — kein Seitenreload noetig
  - Standardsprache: Deutsch
- **Zweisprachige Admin-Felder** - Die drei editierbaren Textfelder (Datenhaltung, Spam-Filterung, RFC 2142) haben jetzt jeweils eine DE- und EN-Variante
  - Neue Felder im Admin-Panel: Datenhaltung (EN), Spam-Filterung (EN), RFC 2142 (EN)
  - Englische Vorschlagstexte als Standard (GDPR compliant, SPF/DKIM/DMARC, RFC 2142)

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
