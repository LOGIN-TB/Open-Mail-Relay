"""detect_block: Provider-Sperren von gewoehnlichen Empfaenger-Bounces trennen.

Kernfall: Exchange Online lehnt nicht existierende Postfaecher per
Directory-Based Edge Blocking mit '550 5.4.1 Recipient address rejected:
Access denied' ab — das ist KEINE Sende-IP-Sperre, obwohl 'Access denied'
wie ein Block-Keyword aussieht.
"""
from app.services.provider_block_service import detect_block

MS_RELAY = "login-online-com.mail.protection.outlook.com"

DBEB_REJECT = (
    "550 5.4.1 Recipient address rejected: Access denied. "
    "For more information see https://aka.ms/EXOSmtpErrors "
    "[AM3PEPF0000A790.eurprd04.prod.outlook.com 2026-07-13T04:51:53.988Z "
    "08DEE00200AEDCFC] (in reply to RCPT TO command)"
)

CONSUMER_BLOCK = (
    "host hotmail-com.olc.protection.outlook.com[52.101.41.23] said: "
    "550 5.7.1 Unfortunately, messages from [49.12.162.229] weren't sent. "
    "Please contact your Internet service provider since part of their "
    "network is on our block list (S3140)."
)

EOP_BLOCK = (
    "550 5.7.606 Access denied, banned sending IP [49.12.162.229]. "
    "To request removal from this list please visit "
    "https://sender.office.com/ and follow the directions."
)


def test_dbeb_recipient_reject_is_not_a_block():
    assert detect_block(DBEB_REJECT, "5.4.1", MS_RELAY) is None


def test_postfix_recipient_access_reject_is_not_a_block():
    text = "554 5.7.1 <foo@example.org>: Recipient address rejected: Access denied"
    assert detect_block(text, "5.7.1", "mx.example.org") is None


def test_ordinary_user_unknown_is_not_a_block():
    text = "550 5.1.1 <nobody@example.com>: Recipient address rejected: User unknown"
    assert detect_block(text, "5.1.1", MS_RELAY) is None


def test_consumer_block_still_detected():
    match = detect_block(CONSUMER_BLOCK, "5.7.1", "hotmail-com.olc.protection.outlook.com")
    assert match is not None
    assert match["provider"] == "microsoft"
    assert match["code"] == "S3140"


def test_eop_banned_ip_still_detected():
    match = detect_block(EOP_BLOCK, "5.7.606", MS_RELAY)
    assert match is not None
    assert match["provider"] == "microsoft"
