"""Phase F: purge reversible plaintext passwords for portal-managed users.

Portal-managed SMTP users authenticate via password_hash ({SHA512-CRYPT});
their Fernet-encrypted plaintext (password_encrypted) only remains as a
legacy fallback for the relay-local config PDF. Purging it completes the
hash-only credential model (ADR 0006): after this, no plaintext exists
anywhere — credentials can only be rotated, never re-displayed.

Run this ONLY once BOTH relays run stable in "managed" mode and customers
use the portal for PDFs/rotation. The legacy config-pdf/reset endpoints
answer 410 for purged users.

Usage (inside the admin container):

    docker compose exec admin-panel python -m app.tools.purge_plaintext            # dry run
    docker compose exec admin-panel python -m app.tools.purge_plaintext --yes      # purge

Irreversible (that is the point). Take a DB backup first — see
docs/runbooks/relay-cutover.md in the portal repo.
"""
import sys

from app.database import SessionLocal
from app.models import SmtpUser


def main() -> int:
    apply = "--yes" in sys.argv

    db = SessionLocal()
    try:
        candidates = (
            db.query(SmtpUser)
            .filter(
                SmtpUser.portal_managed == True,  # noqa: E712
                SmtpUser.password_hash.isnot(None),
                SmtpUser.password_encrypted.isnot(None),
            )
            .order_by(SmtpUser.username)
            .all()
        )

        if not candidates:
            print("Nichts zu tun: kein portal-verwalteter Benutzer mit Klartext-Passwort.")
            return 0

        print(f"{len(candidates)} portal-verwaltete Benutzer mit Klartext-Passwort:")
        for user in candidates:
            print(f"  - {user.username}")

        if not apply:
            print("\nDry-Run — nichts geaendert. Zum Ausfuehren: --yes anhaengen.")
            return 0

        for user in candidates:
            user.password_encrypted = None
        db.commit()
        print(f"\n{len(candidates)} Klartext-Passwoerter geloescht (unwiderruflich).")
        print("Legacy config-pdf/reset antworten fuer diese Benutzer jetzt mit 410.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
