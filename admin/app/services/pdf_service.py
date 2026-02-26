"""PDF service for generating SMTP configuration sheets.

Uses reportlab to create A4 PDF documents with SMTP credentials
and setup instructions.
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def generate_config_pdf(username: str, password: str, smtp_host: str,
                        company: str | None = None, service: str | None = None) -> bytes:
    """Generate a PDF configuration sheet with SMTP credentials."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=6 * mm,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=8 * mm,
        spaceAfter=4 * mm,
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
    elements.append(Paragraph("SMTP-Zugangsdaten", title_style))
    elements.append(Paragraph(
        "Konfigurationsblatt fuer den E-Mail-Versand ueber den SMTP-Relay-Server.",
        body_style,
    ))
    elements.append(Spacer(1, 6 * mm))

    # Assignment section (only if company or service is set)
    if company or service:
        elements.append(Paragraph("Zuordnung", heading_style))
        assignment_data = [["Feld", "Wert"]]
        if company:
            assignment_data.append(["Firma", company])
        if service:
            assignment_data.append(["Dienst", service])

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
        elements.append(Spacer(1, 2 * mm))

    # Security notice
    elements.append(Spacer(1, 6 * mm))
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
        "generieren Sie umgehend ein neues Passwort im Admin-Panel.",
        notice_style,
    ))

    doc.build(elements)
    return buffer.getvalue()
