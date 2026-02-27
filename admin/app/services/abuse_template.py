"""Self-contained HTML template for the public Abuse & Postmaster page."""

ABUSE_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Abuse / Postmaster &ndash; {hostname}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0d1117;
      --surface: #161b22;
      --border: #30363d;
      --accent: #f97316;
      --accent2: #fb923c;
      --text: #e6edf3;
      --muted: #8b949e;
      --green: #3fb950;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'IBM Plex Sans', sans-serif;
      font-weight: 300;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    body::before {{
      content: '';
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(249,115,22,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(249,115,22,0.03) 1px, transparent 1px);
      background-size: 40px 40px;
      pointer-events: none;
      z-index: 0;
    }}
    header {{
      position: relative;
      z-index: 1;
      border-bottom: 1px solid var(--border);
      padding: 0 2rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      height: 60px;
    }}
    .logo-badge {{
      background: var(--accent);
      color: #fff;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      padding: 3px 8px;
      border-radius: 3px;
    }}
    .header-title {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.85rem;
      color: var(--muted);
    }}
    .header-title span {{
      color: var(--text);
    }}
    main {{
      flex: 1;
      position: relative;
      z-index: 1;
      max-width: 860px;
      width: 100%;
      margin: 0 auto;
      padding: 3rem 2rem;
    }}
    .page-eyebrow {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.7rem;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 0.75rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .page-eyebrow::before {{
      content: '';
      width: 24px;
      height: 1px;
      background: var(--accent);
    }}
    h1 {{
      font-size: clamp(1.8rem, 4vw, 2.6rem);
      font-weight: 600;
      line-height: 1.2;
      margin-bottom: 1rem;
      letter-spacing: -0.02em;
    }}
    h1 em {{
      font-style: normal;
      color: var(--accent);
    }}
    .intro {{
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.7;
      max-width: 600px;
      margin-bottom: 3rem;
      border-left: 2px solid var(--accent);
      padding-left: 1rem;
    }}
    .cards {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 3rem;
    }}
    @media (max-width: 600px) {{
      .cards {{ grid-template-columns: 1fr; }}
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.5rem;
      transition: border-color 0.2s;
    }}
    .card:hover {{
      border-color: var(--accent);
    }}
    .card-icon {{
      width: 36px;
      height: 36px;
      background: rgba(249,115,22,0.12);
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 1rem;
      font-size: 1.1rem;
    }}
    .card h3 {{
      font-size: 0.9rem;
      font-weight: 600;
      margin-bottom: 0.4rem;
      letter-spacing: 0.01em;
    }}
    .card p {{
      font-size: 0.82rem;
      color: var(--muted);
      line-height: 1.6;
      margin-bottom: 1rem;
    }}
    .card a {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.8rem;
      color: var(--accent);
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: color 0.15s;
    }}
    .card a:hover {{ color: var(--accent2); }}
    .contact-block {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 2rem;
      margin-bottom: 3rem;
      position: relative;
      overflow: hidden;
    }}
    .contact-block::after {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, var(--accent), transparent);
    }}
    .contact-block h2 {{
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 1.5rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .contact-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1.5rem;
    }}
    .contact-item label {{
      display: block;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.65rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 0.4rem;
    }}
    .contact-item .value {{
      font-size: 0.9rem;
      color: var(--text);
    }}
    .contact-item .value a {{
      color: var(--accent);
      text-decoration: none;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.85rem;
    }}
    .contact-item .value a:hover {{ text-decoration: underline; }}
    .status-row {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 2rem;
    }}
    .status-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 6px var(--green);
      animation: pulse 2s ease-in-out infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.5; }}
    }}
    .status-text {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.75rem;
      color: var(--muted);
    }}
    .info-box {{
      background: rgba(249,115,22,0.06);
      border: 1px solid rgba(249,115,22,0.2);
      border-radius: 6px;
      padding: 1rem 1.25rem;
      margin-bottom: 2rem;
      font-size: 0.84rem;
      line-height: 1.6;
      color: var(--muted);
    }}
    .info-box strong {{ color: var(--text); }}
    .info-box a {{ color: var(--accent); text-decoration: none; }}
    .info-box a:hover {{ text-decoration: underline; }}
    .tech-table {{
      width: 100%;
      border-collapse: collapse;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.78rem;
      margin-top: 1rem;
    }}
    .tech-table td {{
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    .tech-table td:first-child {{
      color: var(--muted);
      white-space: nowrap;
      width: 160px;
    }}
    .tech-table td:last-child {{ color: var(--text); }}
    footer {{
      position: relative;
      z-index: 1;
      border-top: 1px solid var(--border);
      padding: 1.5rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    footer p {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.72rem;
      color: var(--muted);
    }}
    footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
<header>
  <div class="logo-badge">OPEN MAIL RELAY</div>
  <span class="header-title">{hostname} &nbsp;/&nbsp; <span>Abuse &amp; Postmaster</span></span>
</header>
<main>
  <div class="page-eyebrow">Postmaster Information</div>
  <h1>Abuse &amp; <em>Kontakt</em></h1>
  <p class="intro">
    Diese Seite richtet sich an Postmaster, Netzwerkbetreiber und Behoerden, die
    Missbrauchsmeldungen zu E-Mails einreichen moechten, die ueber das Relay-System
    <strong>{hostname}</strong>{responsible_intro} versandt wurden.
  </p>
  <div class="status-row">
    <div class="status-dot"></div>
    <span class="status-text">Abuse-Postfach aktiv &ndash; Reaktionszeit &lt; 24h (Werktage)</span>
  </div>

  <div class="contact-block">
    <h2>Direkter Abuse-Kontakt</h2>
    <div class="contact-grid">
      <div class="contact-item">
        <label>Abuse E-Mail</label>
        <div class="value"><a href="mailto:{abuse_email}">{abuse_email}</a></div>
      </div>
      <div class="contact-item">
        <label>Postmaster E-Mail</label>
        <div class="value"><a href="mailto:{postmaster_email}">{postmaster_email}</a></div>
      </div>
{responsible_section}{phone_section}
    </div>
  </div>

  <div class="cards">
    <div class="card">
      <div class="card-icon">&#x1F4E8;</div>
      <h3>Missbrauchsmeldung einreichen</h3>
      <p>Bitte senden Sie vollstaendige E-Mail-Header (inkl. Received-Zeilen) sowie eine kurze Beschreibung des Vorfalls an unsere Abuse-Adresse.</p>
      <a href="mailto:{abuse_email}?subject=Abuse-Report%20{hostname}">&rarr; {abuse_email}</a>
    </div>
    <div class="card">
      <div class="card-icon">&#x1F4CB;</div>
      <h3>Postmaster-Anfragen</h3>
      <p>Fuer technische Rueckfragen zu Mail-Flows, Reputations-Resets oder Whitelisting-Anfragen wenden Sie sich an den Postmaster.</p>
      <a href="mailto:{postmaster_email}?subject=Postmaster-Anfrage%20{hostname}">&rarr; {postmaster_email}</a>
    </div>
    <div class="card">
      <div class="card-icon">&#x2696;&#xFE0F;</div>
      <h3>Behoerden &amp; Strafverfolgung</h3>
      <p>Anfragen von Behoerden und Strafverfolgungsbehoerden werden gemaess geltendem deutschem Recht bearbeitet.</p>
      <a href="mailto:{abuse_email}?subject=Behoerdenanfrage%20{hostname}">&rarr; Anfrage stellen</a>
    </div>
    <div class="card">
      <div class="card-icon">&#x1F517;</div>
      <h3>Impressum &amp; Datenschutz</h3>
      <p>Vollstaendiges Impressum mit Verantwortlichem sowie Datenschutzerklaerung gemaess DSGVO.</p>
      {imprint_link}
    </div>
  </div>

  <div class="contact-block">
    <h2>Systeminformationen</h2>
    <table class="tech-table">
{responsible_row}
      <tr>
        <td>Hostname</td>
        <td>{hostname}</td>
      </tr>
      <tr>
        <td>Zweck</td>
        <td>Managed Mail-Relay / Smarthost fuer autorisierte Netzwerke und SMTP-Benutzer</td>
      </tr>
      <tr>
        <td>Nutzungspolitik</td>
        <td>Ausschliesslich autorisierte Netzwerke und SMTP-Benutzer; kein offenes Relay</td>
      </tr>
      <tr>
        <td>SPF / DKIM</td>
        <td>Ja &ndash; alle weitergeleiteten Mails werden ueberprueft</td>
      </tr>
      <tr>
        <td>Spam-Filterung</td>
        <td>{abuse_spam_filtering}</td>
      </tr>
      <tr>
        <td>Datenhaltung</td>
        <td>{abuse_data_retention}</td>
      </tr>
      <tr>
        <td>RFC 2142</td>
        <td>{abuse_rfc2142}</td>
      </tr>
    </table>
  </div>

  <div class="info-box">
    <strong>Hinweis fuer ISPs und grosse Mailprovider:</strong> Bei Blocklisten-Eintraegen
    oder Reputationsproblemen kontaktieren Sie uns bitte direkt unter
    <a href="mailto:{postmaster_email}">{postmaster_email}</a>.
    Wir reagieren auf verifizierte Meldungen innerhalb eines Werktages und leiten
    umgehend Massnahmen gegen missbraeuchlich nutzende Kunden ein.
  </div>
</main>
<footer>
  <p>{footer_left}</p>
  <p>{abuse_email} &middot; {postmaster_email}</p>
</footer>
</body>
</html>
"""
