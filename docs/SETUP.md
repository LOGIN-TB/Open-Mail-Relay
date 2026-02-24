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

## 2. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
nano .env
```

Alle Variablen ausfuellen:

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

Der Hostname des Mail-Relays wird in `postfix/main.cf` konfiguriert (nicht in `.env`):

```ini
myhostname = relay.example.com
mydomain = example.com
```

Dieser kann spaeter auch ueber das Admin-Panel geaendert werden.

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
| `88.198.250.128/27` | Webserver-Netz |
| `10.0.0.0/24` | Internes VPN |

Aenderungen werden sofort wirksam - Postfix laedt die neue `mynetworks`-Datei automatisch.

## 6. Sendenden Server konfigurieren

Auf dem Server, der Mails ueber das Relay versenden soll, die SMTP-Einstellungen konfigurieren:

| Einstellung | Wert |
|-------------|------|
| SMTP-Server | `relay.example.com` |
| Port | `25` (SMTP) oder `587` (Submission) |
| Authentifizierung | Keine (IP-basiert) |
| Verschluesselung | STARTTLS (bei Port 587 Pflicht) |

### Beispiel: PHP (php.ini)

```ini
sendmail_path = /usr/sbin/sendmail -t -i
# oder mit msmtp:
sendmail_path = /usr/bin/msmtp -t
```

### Beispiel: msmtp

```ini
account default
host relay.example.com
port 587
tls on
tls_starttls on
auth off
```

### Beispiel: Postfix als Client

```ini
relayhost = [relay.example.com]:587
smtp_tls_security_level = encrypt
```

## 7. Testen

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
ufw allow from 88.198.250.128/27 to any port 25 proto tcp
ufw allow from 88.198.250.128/27 to any port 587 proto tcp
ufw deny 25
ufw deny 587

# HTTP/HTTPS fuer Caddy (Let's Encrypt + Admin-Panel)
ufw allow 80/tcp
ufw allow 443/tcp
```

### iptables

```bash
# SMTP nur fuer erlaubte Netze
iptables -A INPUT -p tcp --dport 25 -s 88.198.250.128/27 -j ACCEPT
iptables -A INPUT -p tcp --dport 587 -s 88.198.250.128/27 -j ACCEPT
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

Die Datenbank (SQLite) und Mail-Queue bleiben ueber Updates hinweg erhalten, da sie in Docker Named Volumes liegen.

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

Alle Konfigurationsdateien liegen im Repository (`postfix/`, `caddy/`, `.env`). Ein Git-Commit sichert diese automatisch.

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

Die Absender-IP ist nicht in den erlaubten Netzwerken. Loesung:
1. IP des sendenden Servers pruefen
2. Im Admin-Panel unter **Netzwerke** das passende CIDR hinzufuegen

### Admin-Panel nicht erreichbar

```bash
docker compose ps          # Container-Status pruefen
docker compose logs caddy  # Reverse-Proxy-Logs
docker compose logs admin-panel  # Backend-Logs
```
