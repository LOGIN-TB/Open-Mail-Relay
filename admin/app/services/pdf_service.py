"""PDF service for generating SMTP configuration sheets.

Uses reportlab to create A4 PDF documents with SMTP credentials
and setup instructions.
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak


def generate_config_pdf(username: str, password: str, smtp_host: str,
                        company: str | None = None, service: str | None = None,
                        mail_domain: str | None = None, contact_email: str | None = None,
                        package_name: str | None = None,
                        spf_info: dict | None = None,
                        operator_info: dict | None = None) -> bytes:
    """Generate a PDF configuration sheet with SMTP credentials."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=8 * mm,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=5 * mm,
        spaceAfter=3 * mm,
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )

    mono_style = ParagraphStyle(
        "Mono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=10,
        leading=14,
    )

    elements = []

    # Title
    elements.append(Paragraph("SMTP-Relay Zugangsdaten", title_style))

    # Operator info
    if operator_info:
        op_parts = []
        if operator_info.get("responsible"):
            op_parts.append(["Betreiber", operator_info["responsible"]])
        if operator_info.get("email"):
            op_parts.append(["E-Mail", operator_info["email"]])
        if operator_info.get("phone"):
            op_parts.append(["Telefon", operator_info["phone"]])
        if op_parts:
            elements.append(Paragraph("Relay-Betreiber", heading_style))
            op_data = [["Feld", "Wert"]] + op_parts
            op_table = Table(op_data, colWidths=[55 * mm, 95 * mm])
            op_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            elements.append(op_table)

    # Customer section (only if any metadata is set)
    if company or package_name or mail_domain or contact_email:
        elements.append(Paragraph("Kunde", heading_style))
        assignment_data = [["Feld", "Wert"]]
        if company:
            assignment_data.append(["Firma", company])
        if mail_domain:
            assignment_data.append(["Mail-Domain", mail_domain])
        if contact_email:
            assignment_data.append(["Kontakt-E-Mail", contact_email])
        if package_name:
            assignment_data.append(["Paket", package_name])

        assignment_table = Table(assignment_data, colWidths=[55 * mm, 95 * mm])
        assignment_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(assignment_table)

    # Credentials table
    elements.append(Paragraph("Verbindungsdaten", heading_style))

    table_data = [
        ["Einstellung", "Wert"],
        ["SMTP-Server", smtp_host],
        ["Port", "587 (empfohlen) oder 25 (Legacy)"],
        ["Verschluesselung", "STARTTLS (Pflicht bei 587, optional bei 25)"],
        ["Benutzername", username],
        ["Passwort", password],
    ]

    table = Table(table_data, colWidths=[55 * mm, 95 * mm])
    table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        # Data rows
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 1), (1, -1), "Courier"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)

    # Setup instructions
    elements.append(Paragraph("Einrichtung", heading_style))

    steps = [
        "1. Oeffnen Sie die SMTP-Einstellungen Ihres E-Mail-Programms oder Servers.",
        "2. Tragen Sie als SMTP-Server <b>{}</b> mit Port <b>587</b> ein (empfohlen).".format(smtp_host),
        "3. Waehlen Sie <b>STARTTLS</b> als Verschluesselung.",
        "4. Geben Sie den Benutzernamen <b>{}</b> und das Passwort ein.".format(username),
        "Alternativ: Fuer aeltere Geraete ohne TLS-Unterstuetzung Port <b>25</b> verwenden (Verschluesselung optional).",
    ]

    for step in steps:
        elements.append(Paragraph(step, body_style))
        elements.append(Spacer(1, 1 * mm))

    # SPF record section (only if spf_info provided) — on page 2
    if spf_info:
        elements.append(PageBreak())
        elements.append(Paragraph("SPF-Record Konfiguration", title_style))
        elements.append(Paragraph(
            "Damit E-Mails, die ueber den Relay-Server versendet werden, nicht als Spam "
            "eingestuft werden, muss der SPF-Record (DNS TXT-Eintrag) der Absender-Domain "
            "<b>{}</b> den Relay-Server autorisieren.".format(spf_info["mail_domain"]),
            body_style,
        ))
        elements.append(Spacer(1, 6 * mm))

        spf_ok_style = ParagraphStyle(
            "SpfOk",
            parent=body_style,
            backColor=colors.HexColor("#dcfce7"),
            borderColor=colors.HexColor("#16a34a"),
            borderWidth=1,
            borderPadding=8,
            borderRadius=4,
        )

        spf_warn_style = ParagraphStyle(
            "SpfWarn",
            parent=body_style,
            backColor=colors.HexColor("#fef3c7"),
            borderColor=colors.HexColor("#f59e0b"),
            borderWidth=1,
            borderPadding=8,
            borderRadius=4,
        )

        spf_mono_style = ParagraphStyle(
            "SpfMono",
            parent=body_style,
            fontName="Courier",
            fontSize=8,
            leading=12,
            backColor=colors.HexColor("#f1f5f9"),
            borderColor=colors.HexColor("#e2e8f0"),
            borderWidth=0.5,
            borderPadding=6,
            borderRadius=3,
        )

        if spf_info["status"] == "ok":
            elements.append(Paragraph(
                "Der SPF-Record fuer <b>{}</b> ist korrekt konfiguriert und "
                "enthaelt bereits die Relay-Domain <b>{}</b>.".format(
                    spf_info["mail_domain"], spf_info["relay_domain"]),
                spf_ok_style,
            ))
            elements.append(Spacer(1, 6 * mm))
            elements.append(Paragraph("Aktueller SPF-Record:", body_style))
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(spf_info["current_record"], spf_mono_style))
        elif spf_info["status"] == "needs_update":
            elements.append(Paragraph(
                "Der SPF-Record fuer <b>{}</b> muss erweitert werden. "
                "Bitte fuegen Sie <b>include:spf.{}</b> hinzu.".format(
                    spf_info["mail_domain"], spf_info["relay_domain"]),
                spf_warn_style,
            ))
            elements.append(Spacer(1, 6 * mm))
            elements.append(Paragraph("Aktueller SPF-Record:", body_style))
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(spf_info["current_record"], spf_mono_style))
            elements.append(Spacer(1, 6 * mm))
            elements.append(Paragraph("Empfohlener SPF-Record:", body_style))
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(spf_info["suggested_record"], spf_mono_style))
        elif spf_info["status"] == "missing":
            elements.append(Paragraph(
                "Fuer die Domain <b>{}</b> wurde kein SPF-Record gefunden. "
                "Bitte legen Sie folgenden DNS TXT-Eintrag an:".format(
                    spf_info["mail_domain"]),
                spf_warn_style,
            ))
            elements.append(Spacer(1, 6 * mm))
            elements.append(Paragraph("Empfohlener SPF-Record:", body_style))
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(spf_info["suggested_record"], spf_mono_style))

    # Security notice
    elements.append(Paragraph("Sicherheitshinweis", heading_style))

    notice_style = ParagraphStyle(
        "Notice",
        parent=body_style,
        backColor=colors.HexColor("#fef3c7"),
        borderColor=colors.HexColor("#f59e0b"),
        borderWidth=1,
        borderPadding=8,
        borderRadius=4,
    )
    elements.append(Paragraph(
        "Bewahren Sie dieses Dokument sicher auf. Das Passwort ermoeglicht den "
        "Versand von E-Mails ueber den Relay-Server. Geben Sie die Zugangsdaten "
        "nicht an unbefugte Personen weiter. Bei Verdacht auf Missbrauch "
        "verstaendigen Sie uns umgehend, wir generieren ein neues Passwort fuer Sie.",
        notice_style,
    ))

    doc.build(elements)
    return buffer.getvalue()
