# Setup-Anleitung

Schritt-fuer-Schritt-Anleitung zur Installation und Konfiguration des Open-Mail-Relays mit Admin-Panel.

## Voraussetzungen

- **Server** mit oeffentlicher IP-Adresse (VPS, Dedicated, etc.)
- **Docker** >= 20.10 und **Docker Compose** >= 2.0
- **Zwei DNS-Eintraege** (A-Records), die auf den Server zeigen:
  - Einer fuer den Mail-Server (z.B. `relay.example.com`)
  - Einer fuer das Admin-Panel (z.B. `admin.example.com`)
- **Ports** 25, 80, 443 und 587 muessen von aussen erreichbar sein

### DNS konfigurieren

Bevor die Container gestartet werden, muessen die DNS-Eintraege gesetzt sein, da Caddy sonst keine TLS-Zertifikate beschaffen kann.

```
relay.example.com.   A   203.0.113.10
admin.example.com.   A   203.0.113.10
```

**Wichtig:** Der reverse DNS (PTR) Eintrag der Server-IP **muss** auf den Mail-Hostname zeigen:

```
10.113.0.203.in-addr.arpa.   PTR   relay.example.com.
```

Postfix verwendet den `myhostname` (aus `postfix/main.cf`) als EHLO/HELO-Greeting bei ausgehenden Verbindungen. Empfangende Mailserver pruefen, ob der EHLO-Hostname zum PTR-Record der absendenden IP passt. Stimmen diese nicht ueberein, werden Mails haeufig als Spam eingestuft oder abgelehnt.

> **Hinweis:** Der PTR-Record wird beim Hosting-Provider der Server-IP konfiguriert (nicht beim Domain-Registrar).

## 1. Repository klonen

```bash
git clone https://github.com/LOGIN-TB/Open-Mail-Relay.git
cd Open-Mail-Relay
```

## 2. Konfigurationsdateien erstellen

```bash
# Umgebungsvariablen
cp .env.example .env
nano .env

# Postfix-Konfiguration
cp postfix/main.cf.example postfix/main.cf
cp postfix/mynetworks.example postfix/mynetworks
```

`.env` ausfuellen:

```ini
# FQDN des Admin-Panels (muss per DNS auf diesen Server zeigen)
ADMIN_HOSTNAME=admin.example.com

# Geheimer Schluessel fuer JWT-Token (mindestens 32 Zeichen, zufaellig)
ADMIN_SECRET_KEY=hier-einen-langen-zufaelligen-string-eingeben

# Initiales Admin-Passwort (nach erstem Login im Panel aendern)
ADMIN_DEFAULT_PASSWORD=ein-sicheres-passwort

# E-Mail fuer Let's Encrypt (Ablaufwarnungen)
LETSENCRYPT_EMAIL=admin@example.com
```

> **Tipp:** Sicheren Secret Key generieren: `openssl rand -hex 32`

### Mail-Hostname konfigurieren

Den Hostname des Mail-Relays in `postfix/main.cf` anpassen:

```ini
myhostname = relay.example.com
mydomain = example.com
```

Dieser kann spaeter auch ueber das Admin-Panel geaendert werden. Bei einer Hostname-Aenderung im Admin-Panel wird automatisch:
1. Postfix neu geladen
2. Caddy neu gestartet (um ein neues TLS-Zertifikat zu beschaffen)
3. Das Zertifikat nach Postfix synchronisiert

Der Fortschritt wird im Admin-Panel Schritt fuer Schritt angezeigt.

## 3. Container bauen und starten

```bash
docker compose up -d --build
```

Beim ersten Start passiert folgendes:

1. **Caddy** startet und beschafft automatisch TLS-Zertifikate fuer beide Hostnames
2. **Open-Mail-Relay** (Postfix) startet und synchronisiert die Zertifikate von Caddy
3. **Admin-Panel** startet, erstellt die Datenbank und den Standard-Admin-Benutzer

## 4. Admin-Panel aufrufen

Oeffne `https://ADMIN_HOSTNAME` im Browser.

- **Benutzername:** `admin`
- **Passwort:** Der Wert aus `ADMIN_DEFAULT_PASSWORD`

### Erster Login - Empfohlene Schritte

1. **Passwort aendern** - Unter "Benutzer" das Admin-Passwort aendern
2. **Netzwerke pruefen** - Unter "Netzwerke" die erlaubten IP-Bereiche kontrollieren
3. **TLS pruefen** - Unter "Konfiguration" den TLS-Status pruefen. Ist das Zertifikat vorhanden und in Postfix geladen?
4. **Test-Mail senden** - Siehe Abschnitt "Testen" weiter unten

## 5. Netzwerke (IP-Whitelist) konfigurieren

Das Open-Mail-Relay akzeptiert nur E-Mails von IPs aus den konfigurierten Netzwerken. Standardmaessig sind nur die geschuetzten System-Netzwerke aktiv:

- `127.0.0.0/8` (Localhost)
- `172.16.0.0/12` (Docker-intern)

Eigene Netzwerke im Admin-Panel unter **Netzwerke** hinzufuegen, z.B.:

| CIDR | Beschreibung |
|------|-------------|
| `203.0.113.0/24` | Webserver-Netz |
| `10.0.0.0/24` | Internes VPN |

Aenderungen werden sofort wirksam - Postfix laedt die neue `mynetworks`-Datei automatisch.

## 6. SMTP-Benutzer einrichten (optional)

Neben der IP-basierten Autorisierung koennen SMTP-Benutzer angelegt werden, die sich per Benutzername/Passwort authentifizieren. Das ist besonders nuetzlich, wenn Clients von wechselnden IPs senden muessen.

1. Im Admin-Panel unter **SMTP-Benutzer** → **SMTP-Benutzer anlegen**
2. Benutzernamen eingeben (4-16 Zeichen: Buchstaben, Ziffern, Bindestrich und Unterstrich; Gross/Kleinschreibung egal)
3. Das Passwort wird automatisch generiert und angezeigt
4. **PDF-Konfigurationsblatt herunterladen** mit allen Zugangsdaten und Einrichtungsanleitung

> **Hinweis:** Auf Port 587 ist TLS Pflicht - Zugangsdaten werden immer verschluesselt uebertragen. Auf Port 25 ist SMTP-Auth auch ohne TLS moeglich, damit aeltere Geraete ohne TLS-Unterstuetzung den Relay nutzen koennen. Empfehlung: Port 587 verwenden, wenn moeglich.

## 7. Mail-Drosselung & IP-Warmup einrichten (empfohlen)

Bei neuen Server-IPs ohne bestehende Reputation ist es wichtig, das Sendevolumen langsam zu steigern. Das Open-Mail-Relay bietet dafuer ein integriertes Drosselungs- und Warmup-System.

### Funktionsweise

- Mails werden **immer** angenommen (250 OK), aber bei Ueberschreitung der Limits intern in eine HOLD-Queue gelegt
- Ein **Batch-Worker** gibt gehaltene Mails zeitgesteuert frei (Standard: alle 10 Minuten)
- Das System durchlaeuft 4 Phasen mit steigenden Limits:

| Phase | Zeitraum | Max/Stunde | Max/Tag | Burst |
|-------|----------|-----------|---------|-------|
| 1 — Woche 1-2 | Tag 1-14 | 20 | 500 | 10 |
| 2 — Woche 3-4 | Tag 15-28 | 50 | 2.000 | 25 |
| 3 — Woche 5-6 | Tag 29-42 | 100 | 5.000 | 50 |
| 4 — Etabliert | ab Tag 43 | 500 | 50.000 | 200 |

Zusaetzlich wird der Versand an grosse Provider gedrosselt (Per-Domain Transport-Regeln):

| Provider | Max. Verbindungen | Verzoegerung |
|----------|-------------------|-------------|
| Gmail | 3 | 3s |
| Outlook/Hotmail/Live | 2 | 5s |
| Yahoo | 3 | 3s |
| Standard | 5 | 1s |

### Aktivierung

1. Im Admin-Panel unter **Drosselung** den Toggle auf **Aktiv** setzen
2. Das System konfiguriert automatisch Transport-Maps, Policy-Server und Postfix
3. Der Warmup startet sofort mit Phase 1

### Anpassungen

- **Phasen-Limits** koennen individuell angepasst werden (Inline-Bearbeitung in der Tabelle)
- **Transport-Regeln** koennen hinzugefuegt, bearbeitet oder geloescht werden
- **Batch-Intervall** ist konfigurierbar (Standard: 10 Minuten)
- **Phase manuell setzen** oder **Warmup zuruecksetzen** bei Bedarf

### Dashboard

Wenn die Drosselung aktiv ist, zeigt das Dashboard eine Warmup-Statuskarte mit Phasenname, Fortschrittsbalken und der Anzahl zurueckgehaltener Mails.

### Sicherheit

- **Fail-Open-Design**: Der Policy-Server gibt bei Fehler oder Timeout immer DUNNO zurueck — Mails werden nie durch einen Bug blockiert
- Bei Deaktivierung der Drosselung werden alle gehaltenen Mails sofort freigegeben

## 8. Sendenden Server konfigurieren

Auf dem Server, der Mails ueber das Relay versenden soll, die SMTP-Einstellungen konfigurieren:

### Variante A: IP-basiert (ohne Authentifizierung)

| Einstellung | Wert |
|-------------|------|
| SMTP-Server | `relay.example.com` |
| Port | `25` (SMTP) oder `587` (Submission) |
| Authentifizierung | Keine (IP muss in Whitelist sein) |
| Verschluesselung | STARTTLS (bei Port 587 Pflicht, bei Port 25 optional) |

### Variante B: SMTP-Auth (Benutzername/Passwort)

| Einstellung | Wert |
|-------------|------|
| SMTP-Server | `relay.example.com` |
| Port | `587` (empfohlen, TLS Pflicht) oder `25` (TLS optional, fuer Legacy-Geraete) |
| Authentifizierung | PLAIN oder LOGIN |
| Benutzername | (aus Admin-Panel / PDF) |
| Passwort | (aus Admin-Panel / PDF) |
| Verschluesselung | STARTTLS (Pflicht bei Port 587, optional bei Port 25) |

> **Hinweis:** Alle ausgehenden Mails vom Relay zum Ziel-Mailserver werden immer TLS-verschluesselt (mindestens TLS 1.2). Mails an Server ohne TLS werden nicht zugestellt.

### Beispiel: PHP (php.ini)

```ini
sendmail_path = /usr/sbin/sendmail -t -i
# oder mit msmtp:
sendmail_path = /usr/bin/msmtp -t
```

### Beispiel: msmtp (IP-basiert)

```ini
account default
host relay.example.com
port 587
tls on
tls_starttls on
auth off
```

### Beispiel: msmtp (mit SMTP-Auth)

```ini
account default
host relay.example.com
port 587
tls on
tls_starttls on
auth plain
user smtpuser
password xxxx-xxxxxx-xxxx
```

### Beispiel: Postfix als Client (IP-basiert)

```ini
relayhost = [relay.example.com]:587
smtp_tls_security_level = encrypt
```

### Beispiel: Postfix als Client (mit SMTP-Auth)

```ini
relayhost = [relay.example.com]:587
smtp_tls_security_level = encrypt
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_sasl_security_options = noanonymous
```

Datei `/etc/postfix/sasl_passwd`:
```
[relay.example.com]:587 smtpuser:xxxx-xxxxxx-xxxx
```

Danach: `postmap /etc/postfix/sasl_passwd && chmod 600 /etc/postfix/sasl_passwd*`

## 9. Testen

### swaks installieren

```bash
apt install swaks
```

### Test ueber Port 25

```bash
swaks --to empfaenger@zieldomain.de \
      --from absender@example.com \
      --server relay.example.com \
      --port 25
```

### Test ueber Port 587 (mit STARTTLS)

```bash
swaks --to empfaenger@zieldomain.de \
      --from absender@example.com \
      --server relay.example.com \
      --port 587 \
      --tls
```

### Test mit SMTP-Auth (SASL) ueber Port 587

```bash
swaks --to empfaenger@zieldomain.de \
      --from absender@example.com \
      --server relay.example.com \
      --port 587 \
      --tls \
      --auth PLAIN \
      --auth-user smtpuser \
      --auth-password xxxx-xxxxxx-xxxx
```

### Test mit SMTP-Auth (SASL) ueber Port 25 ohne TLS (Legacy)

```bash
swaks --to empfaenger@zieldomain.de \
      --from absender@example.com \
      --server relay.example.com \
      --port 25 \
      --auth PLAIN \
      --auth-user smtpuser \
      --auth-password xxxx-xxxxxx-xxxx
```

### SASL im Container pruefen

```bash
# Dovecot-Auth testen
docker compose exec open-mail-relay doveadm auth test smtpuser xxxx-xxxxxx-xxxx
```

### TLS-Verbindung pruefen

```bash
openssl s_client -connect relay.example.com:25 -starttls smtp
openssl s_client -connect relay.example.com:587 -starttls smtp
```

## Firewall-Konfiguration

Es wird empfohlen, die SMTP-Ports auf Netzwerk-Ebene zusaetzlich abzusichern:

### ufw

```bash
# Nur erlaubte IPs auf SMTP-Ports
ufw allow from 203.0.113.0/24 to any port 25 proto tcp
ufw allow from 203.0.113.0/24 to any port 587 proto tcp
ufw deny 25
ufw deny 587

# HTTP/HTTPS fuer Caddy (Let's Encrypt + Admin-Panel)
ufw allow 80/tcp
ufw allow 443/tcp
```

### iptables

```bash
# SMTP nur fuer erlaubte Netze
iptables -A INPUT -p tcp --dport 25 -s 203.0.113.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 587 -s 203.0.113.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 25 -j DROP
iptables -A INPUT -p tcp --dport 587 -j DROP

# HTTP/HTTPS offen lassen
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

## TLS-Zertifikate

### Automatischer Ablauf

1. **Caddy** beschafft Zertifikate automatisch via Let's Encrypt (HTTP-01 Challenge)
2. **Caddy** erneuert Zertifikate automatisch vor Ablauf (ca. 30 Tage vorher)
3. **Entrypoint-Skript** synchronisiert Zertifikate beim Container-Start von Caddy nach Postfix
4. **Hintergrund-Task** wiederholt die Synchronisierung alle 6 Stunden
5. **Admin-Panel** ermoeglicht manuelle Synchronisierung per Klick
6. **Hostname-Aenderung** im Admin-Panel startet Caddy automatisch neu und synchronisiert das neue Zertifikat nach Postfix

### Manuelle Synchronisierung

Falls die automatische Synchronisierung nicht abgewartet werden soll:

- Im Admin-Panel unter **Konfiguration** → **TLS-Zertifikat** → **Zertifikat synchronisieren**

Oder per CLI:

```bash
docker compose exec open-mail-relay sh -c "\
  cp /etc/caddy-data/caddy/certificates/acme-v02.api.letsencrypt.org-directory/relay.example.com/relay.example.com.crt /etc/postfix/tls/cert.pem && \
  cp /etc/caddy-data/caddy/certificates/acme-v02.api.letsencrypt.org-directory/relay.example.com/relay.example.com.key /etc/postfix/tls/key.pem && \
  chmod 600 /etc/postfix/tls/key.pem && \
  postfix reload"
```

## Updates

```bash
cd Open-Mail-Relay

# Neueste Version holen
git pull

# Container neu bauen und starten
docker compose up -d --build

# Logs pruefen
docker compose logs -f
```

### Was bleibt bei einem Update erhalten?

| Daten | Speicherort | Sicher? |
|-------|-------------|---------|
| Admin-Datenbank (Benutzer, Logs, Statistiken) | Docker Volume `admin-data` | Ja |
| Mail-Queue (Mails in Zustellung) | Docker Volume `postfix-queue` | Ja |
| TLS-Zertifikate | Docker Volume `caddy-data` | Ja |
| Mail-Logs | Docker Volume `mail-log` | Ja |
| Postfix-Konfiguration (`postfix/main.cf`) | Lokale Datei (gitignored) | Ja |
| Netzwerk-Whitelist (`postfix/mynetworks`) | Lokale Datei (gitignored) | Ja |
| SMTP-Benutzer (Passwoerter verschluesselt) | Docker Volume `admin-data` (SQLite) | Ja |
| Drosselungs-Konfiguration (Phasen, Transports) | Docker Volume `admin-data` (SQLite) | Ja |
| Dovecot passwd-Datei (`postfix/dovecot-users`) | Lokale Datei (gitignored) | Wird aus DB regeneriert |
| Umgebungsvariablen (`.env`) | Lokale Datei (gitignored) | Ja |

Die Dateien `postfix/main.cf`, `postfix/mynetworks` und `.env` werden von Git nicht verfolgt und bleiben bei `git pull` **immer** unberuehrt. Alle Benutzerdaten liegen in Docker Named Volumes und ueberleben Container-Neustarts und Image-Rebuilds.

**SMTP-Benutzer**: Die verschluesselten Passwoerter liegen in der SQLite-Datenbank (Docker Volume). Die Dovecot-Passwortdatei (`postfix/dovecot-users`) wird bei jedem Admin-Panel-Start automatisch aus der Datenbank regeneriert.

## Backup

### Datenbank (Admin-Panel)

```bash
docker compose cp admin-panel:/app/data/admin.db ./backup-admin.db
```

### Mail-Queue

```bash
# Queue-Inhalt sichern
docker compose exec open-mail-relay postqueue -p > queue-backup.txt
```

### Konfiguration

```bash
# Lokale Konfiguration sichern
cp .env ./backup-env
cp postfix/main.cf ./backup-main.cf
cp postfix/mynetworks ./backup-mynetworks
```

## Troubleshooting

### Caddy beschafft kein Zertifikat

```bash
docker compose logs caddy
```

Haeufige Ursachen:
- DNS-Eintrag zeigt nicht auf den Server
- Port 80 ist nicht erreichbar (Firewall)
- Rate-Limit bei Let's Encrypt erreicht

### Port 587 lehnt Verbindungen ab

Port 587 erzwingt STARTTLS. Ohne gueltiges Zertifikat in Postfix ist keine Verbindung moeglich. Loesung:
1. Pruefen, ob Caddy ein Zertifikat hat: Admin-Panel → Konfiguration → TLS
2. Zertifikat manuell synchronisieren: **Zertifikat synchronisieren** klicken
3. Postfix-Logs pruefen: `docker compose logs open-mail-relay`

### "Relay access denied"

Die Absender-IP ist nicht in den erlaubten Netzwerken und es wurde keine gueltige SMTP-Authentifizierung durchgefuehrt. Loesung:
1. IP des sendenden Servers pruefen und unter **Netzwerke** das passende CIDR hinzufuegen
2. Oder: SMTP-Auth konfigurieren (unter **SMTP-Benutzer** einen Benutzer anlegen)

### Admin-Panel nicht erreichbar

```bash
docker compose ps          # Container-Status pruefen
docker compose logs caddy  # Reverse-Proxy-Logs
docker compose logs admin-panel  # Backend-Logs
```
