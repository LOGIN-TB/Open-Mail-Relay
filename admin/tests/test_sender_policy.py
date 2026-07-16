"""Strict sender binding (R5, portal ADR 0009): sender_policy field,
capability, exempt-map generation and the strict switch guards.

Postfix/Docker side effects are monkeypatched — under test is the DB logic
and the step composition, like test_quota_enforcement.py.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import SmtpUser, SystemSetting
from app.routers import portal_provisioning_router
from app.services import sender_maps_service

VALID_HASH = "{SHA512-CRYPT}$6$saltsalt$" + "x" * 86


@pytest.fixture()
def client(db, monkeypatch):
    monkeypatch.setattr(portal_provisioning_router, "sync_dovecot_users", lambda _db: (True, "ok"))
    monkeypatch.setattr(portal_provisioning_router, "sync_sender_maps", lambda _db: None)

    app = FastAPI()
    app.include_router(portal_provisioning_router.router, prefix="/api/portal/v1")
    app.dependency_overrides[get_db] = lambda: db

    db.add(SystemSetting(key="portal_provisioning_enabled", value="1"))
    db.commit()
    return TestClient(app)


@pytest.fixture()
def no_postfix(db, monkeypatch, tmp_path):
    """Silence container/reload side effects; map files land in tmp_path."""
    monkeypatch.setattr(sender_maps_service, "exec_in_container", lambda _cmd: (0, "OK"))
    monkeypatch.setattr(sender_maps_service, "reload_postfix", lambda: (True, "OK"))
    monkeypatch.setattr(sender_maps_service, "SENDER_MAPS_FILE", tmp_path / "sender_login_maps")
    monkeypatch.setattr(sender_maps_service, "SENDER_MAPS_MARKER", tmp_path / "sender_maps_enabled")
    monkeypatch.setattr(sender_maps_service, "SENDER_EXEMPT_FILE", tmp_path / "sender_policy_exempt")
    monkeypatch.setattr(sender_maps_service, "STRICT_MARKER", tmp_path / "strict_sender_enabled")
    return tmp_path


def test_capabilities_advertise_sender_policy(client):
    features = client.get("/api/portal/v1/capabilities").json()["features"]
    assert "sender_policy" in features


def test_upsert_sets_sender_policy_and_inventory_reports_it(client, db):
    create = client.put("/api/portal/v1/smtp-users/policy-user", json={
        "portal_access_id": "acc-p1",
        "password_hash": VALID_HASH,
        "sender_policy": "strict",
    })
    assert create.status_code == 200, create.text
    user = db.query(SmtpUser).filter(SmtpUser.username == "policy-user").one()
    assert user.sender_policy == "strict"

    # Omitted = untouched.
    client.put("/api/portal/v1/smtp-users/policy-user", json={"portal_access_id": "acc-p1"})
    db.refresh(user)
    assert user.sender_policy == "strict"

    inventory = client.get("/api/portal/v1/smtp-users").json()
    item = next(i for i in inventory["items"] if i["username"] == "policy-user")
    assert item["sender_policy"] == "strict"


def test_upsert_rejects_invalid_sender_policy(client):
    res = client.put("/api/portal/v1/smtp-users/bad-policy", json={
        "portal_access_id": "acc-p2",
        "password_hash": VALID_HASH,
        "sender_policy": "wildcard",
    })
    assert res.status_code == 422


def test_default_sender_policy_is_unrestricted(client, db):
    client.put("/api/portal/v1/smtp-users/legacy-like", json={
        "portal_access_id": "acc-p3",
        "password_hash": VALID_HASH,
    })
    user = db.query(SmtpUser).filter(SmtpUser.username == "legacy-like").one()
    assert user.sender_policy == "unrestricted"


def test_exempt_lines_only_active_non_strict_users(db):
    db.add(SmtpUser(username="strict-one", sender_policy="strict", is_active=True))
    db.add(SmtpUser(username="open-one", sender_policy="unrestricted", is_active=True))
    db.add(SmtpUser(username="open-off", sender_policy="unrestricted", is_active=False))
    db.commit()

    lines = sender_maps_service.build_sender_exempt_lines(db)
    assert lines == ["open-one soft_sender_policy"]


def test_strict_switch_requires_domain_binding(db, no_postfix):
    steps = sender_maps_service.apply_strict_sender_config(db, True)
    assert steps[0]["success"] is False
    assert sender_maps_service.get_strict_sender_enabled(db) is False


def test_strict_switch_writes_marker_and_map(db, no_postfix):
    db.add(SmtpUser(username="exempt-user", sender_policy="unrestricted", is_active=True))
    db.commit()
    sender_maps_service.set_sender_maps_enabled(db, True)

    steps = sender_maps_service.apply_strict_sender_config(db, True)
    assert all(st["success"] for st in steps), steps
    assert sender_maps_service.get_strict_sender_enabled(db) is True
    assert (no_postfix / "strict_sender_enabled").exists()
    assert "exempt-user soft_sender_policy" in (no_postfix / "sender_policy_exempt").read_text()

    # Disabling removes the marker and the setting.
    steps = sender_maps_service.apply_strict_sender_config(db, False)
    assert all(st["success"] for st in steps), steps
    assert sender_maps_service.get_strict_sender_enabled(db) is False
    assert not (no_postfix / "strict_sender_enabled").exists()


def test_disabling_domain_binding_takes_strict_down(db, no_postfix):
    sender_maps_service.set_sender_maps_enabled(db, True)
    sender_maps_service.apply_strict_sender_config(db, True)
    assert sender_maps_service.get_strict_sender_enabled(db) is True

    steps = sender_maps_service.apply_sender_maps_config(db, False)
    assert sender_maps_service.get_strict_sender_enabled(db) is False
    assert sender_maps_service.get_sender_maps_enabled(db) is False
    # The combined run contains the strict teardown steps first.
    assert steps[0]["step"] == "Strikte Absenderbindung deaktivieren"
