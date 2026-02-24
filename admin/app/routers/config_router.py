from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, AuditLog
from app.schemas import ServerConfig, ServerConfigUpdate, TlsStatus, ConnectionInfo, PortInfo
from app.services.postfix_service import (
    read_main_cf,
    update_main_cf,
    read_mynetworks,
)
from app.services.docker_service import reload_postfix, restart_caddy
from app.services.cert_service import get_tls_status, sync_certs_to_postfix, wait_for_cert

router = APIRouter()


@router.get("", response_model=ServerConfig)
def get_config(user: User = Depends(get_current_user)):
    cf = read_main_cf()
    return ServerConfig(
        hostname=cf.get("myhostname", "unknown"),
        domain=cf.get("mydomain", "unknown"),
        relay_domains=cf.get("relay_domains", "*"),
        message_size_limit=int(cf.get("message_size_limit", "52428800")),
        mynetworks_count=len(read_mynetworks()),
    )


@router.get("/connection", response_model=ConnectionInfo)
def get_connection_info(user: User = Depends(get_current_user)):
    cf = read_main_cf()
    tls = get_tls_status()
    networks = read_mynetworks()

    hostname = cf.get("myhostname", "unknown")
    size_bytes = int(cf.get("message_size_limit", "52428800"))

    tls_level = cf.get("smtpd_tls_security_level", "may")
    ports = [
        PortInfo(
            port=25,
            protocol="SMTP",
            tls_mode="STARTTLS (opportunistisch)" if tls_level == "may" else "Keine",
            tls_required=False,
        ),
        PortInfo(
            port=587,
            protocol="Submission",
            tls_mode="STARTTLS (erzwungen)",
            tls_required=True,
        ),
    ]

    return ConnectionInfo(
        smtp_host=hostname,
        ports=ports,
        auth_required=cf.get("smtpd_sasl_auth_enable", "no") == "yes",
        tls_available=tls.postfix_has_cert,
        allowed_networks=networks,
        max_message_size_mb=size_bytes // (1024 * 1024),
    )


@router.put("")
def update_config(
    body: ServerConfigUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Detect if hostname is actually changing
    cf = read_main_cf()
    old_hostname = cf.get("myhostname", "")
    hostname_changed = body.hostname is not None and body.hostname != old_hostname

    changes = []
    if body.hostname:
        update_main_cf("myhostname", body.hostname)
        changes.append(f"hostname={body.hostname}")
    if body.domain:
        update_main_cf("mydomain", body.domain)
        changes.append(f"domain={body.domain}")

    if not changes:
        raise HTTPException(status_code=400, detail="No changes provided")

    steps = []

    # Step 1: Postfix reload
    success, output = reload_postfix()
    steps.append({"step": "postfix_reload", "success": success, "detail": output.strip()})

    # Steps 2+3 only when hostname changed
    if hostname_changed:
        # Step 2: Restart Caddy
        caddy_ok, caddy_msg = restart_caddy()
        steps.append({"step": "caddy_restart", "success": caddy_ok, "detail": caddy_msg})

        # Step 3: Wait for cert + sync TLS
        if caddy_ok:
            cert_ready = wait_for_cert(body.hostname, timeout=30)
            if cert_ready:
                sync_ok, sync_msg = sync_certs_to_postfix()
                steps.append({"step": "tls_sync", "success": sync_ok, "detail": sync_msg})
            else:
                steps.append({"step": "tls_sync", "success": False, "detail": "Zertifikat nicht innerhalb von 30s bereit"})
        else:
            steps.append({"step": "tls_sync", "success": False, "detail": "Uebersprungen (Caddy-Neustart fehlgeschlagen)"})

    db.add(AuditLog(
        user_id=user.id,
        action="config_updated",
        details=f"Updated: {', '.join(changes)}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    all_ok = all(s["success"] for s in steps)
    if hostname_changed:
        message = "Hostname erfolgreich geaendert" if all_ok else "Hostname geaendert, TLS-Zertifikat muss manuell synchronisiert werden"
    else:
        message = "Konfiguration aktualisiert"

    return {"message": message, "steps": steps}


@router.get("/tls", response_model=TlsStatus)
def get_tls(user: User = Depends(get_current_user)):
    return get_tls_status()


@router.post("/tls/sync")
def sync_tls_certs(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success, message = sync_certs_to_postfix()

    db.add(AuditLog(
        user_id=user.id,
        action="tls_cert_sync",
        details=message,
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/reload")
def reload_config(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success, output = reload_postfix()

    db.add(AuditLog(
        user_id=user.id,
        action="postfix_reload",
        details=f"Manual reload: {'success' if success else 'failed'}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    if not success:
        raise HTTPException(status_code=500, detail=f"Reload failed: {output}")
    return {"message": "Postfix reloaded successfully", "output": output}
