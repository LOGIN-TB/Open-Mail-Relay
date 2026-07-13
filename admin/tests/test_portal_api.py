"""Provisioning v1 fields (R1/R3) + deliverability/load read endpoints (R4/R5).

The routers are mounted on a bare test app WITHOUT the auth middleware —
auth lives in main.py middleware and is not under test here.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import IpBan, MailEvent, SmtpUser, StatsHourly, SystemSetting
from app.routers import portal_provisioning_router, portal_router

VALID_HASH = "{SHA512-CRYPT}$6$saltsalt$" + "x" * 86


@pytest.fixture()
def client(db, monkeypatch):
    # File syncs need the Docker socket — not under test.
    monkeypatch.setattr(portal_provisioning_router, "sync_dovecot_users", lambda _db: (True, "ok"))
    monkeypatch.setattr(portal_provisioning_router, "sync_sender_maps", lambda _db: None)

    app = FastAPI()
    app.include_router(portal_provisioning_router.router, prefix="/api/portal/v1")
    app.include_router(portal_router.router, prefix="/api/portal")
    app.dependency_overrides[get_db] = lambda: db

    db.add(SystemSetting(key="portal_provisioning_enabled", value="1"))
    db.commit()
    return TestClient(app)


def test_capabilities_advertise_new_features(client):
    features = client.get("/api/portal/v1/capabilities").json()["features"]
    for feature in ("monthly_report_flag", "limit_override", "quota_enforcement", "load_metric"):
        assert feature in features


def test_upsert_sets_and_clears_override_and_report_flag(client, db):
    create = client.put("/api/portal/v1/smtp-users/quota-user", json={
        "portal_access_id": "acc-1",
        "password_hash": VALID_HASH,
        "monthly_limit_override": 100,
        "monthly_report_enabled": False,
    })
    assert create.status_code == 200, create.text
    user = db.query(SmtpUser).filter(SmtpUser.username == "quota-user").one()
    assert user.monthly_limit_override == 100
    assert user.monthly_report_enabled is False

    # Omitted field = untouched.
    client.put("/api/portal/v1/smtp-users/quota-user", json={
        "portal_access_id": "acc-1",
        "company": "Neu GmbH",
    })
    db.refresh(user)
    assert user.monthly_limit_override == 100

    # Explicit null clears the override.
    client.put("/api/portal/v1/smtp-users/quota-user", json={
        "portal_access_id": "acc-1",
        "monthly_limit_override": None,
    })
    db.refresh(user)
    assert user.monthly_limit_override is None


def test_upsert_rejects_negative_override(client):
    res = client.put("/api/portal/v1/smtp-users/bad-user", json={
        "portal_access_id": "acc-2",
        "password_hash": VALID_HASH,
        "monthly_limit_override": -5,
    })
    assert res.status_code == 422


def test_inventory_exposes_new_fields(client):
    client.put("/api/portal/v1/smtp-users/inv-user", json={
        "portal_access_id": "acc-3",
        "password_hash": VALID_HASH,
        "monthly_limit_override": 2500,
    })
    items = client.get("/api/portal/v1/smtp-users").json()["items"]
    row = next(i for i in items if i["username"] == "inv-user")
    assert row["monthly_limit_override"] == 2500
    assert row["monthly_report_enabled"] is True


def test_load_metric(client, db):
    from datetime import datetime, timedelta
    db.add(SmtpUser(username="load-a", is_active=True))
    db.add(SmtpUser(username="load-b", is_active=False))
    db.add(StatsHourly(hour_start=datetime.now() - timedelta(hours=2), sent_count=120))
    db.add(StatsHourly(hour_start=datetime.now() - timedelta(days=40), sent_count=999))
    db.commit()

    data = client.get("/api/portal/load").json()
    assert data["active_users"] == 1
    assert data["total_users"] == 2
    assert data["sent_30d"] == 120


def test_ip_bans_read_endpoint(client, db):
    from datetime import datetime
    db.add(IpBan(ip_address="203.0.113.9", reason="auth_failed", ban_count=2, is_active=True, banned_at=datetime.now()))
    db.add(IpBan(ip_address="203.0.113.10", reason="expired", ban_count=1, is_active=False, banned_at=datetime.now()))
    db.commit()

    active = client.get("/api/portal/ip-bans").json()["items"]
    assert [b["ip_address"] for b in active] == ["203.0.113.9"]

    everything = client.get("/api/portal/ip-bans", params={"include_inactive": True}).json()["items"]
    assert len(everything) == 2


def test_throttle_status_and_provider_blocks(client, db):
    status = client.get("/api/portal/throttle-status").json()
    assert status["enabled"] is False
    assert status["quota_enforcement_enabled"] is False
    assert status["phase"] is None

    blocks = client.get("/api/portal/provider-blocks").json()
    assert blocks["items"] == []
    assert "status" in blocks


def test_usage_report_query_respects_monthly_report_flag(db):
    """R3: the weekly usage-report query must skip portal-muted users."""
    from app.models import Package
    pkg = Package(name="P", category="transaction", monthly_limit=100)
    db.add(pkg)
    db.flush()
    db.add(SmtpUser(username="rep-on", is_active=True, contact_email="a@b.de", package_id=pkg.id))
    db.add(SmtpUser(username="rep-off", is_active=True, contact_email="a@b.de", package_id=pkg.id, monthly_report_enabled=False))
    db.commit()

    eligible = (
        db.query(SmtpUser)
        .filter(
            SmtpUser.receive_reports == True,  # noqa: E712
            SmtpUser.monthly_report_enabled == True,  # noqa: E712
            SmtpUser.contact_email.isnot(None),
            SmtpUser.contact_email != "",
            SmtpUser.package_id.isnot(None),
            SmtpUser.is_active == True,  # noqa: E712
        )
        .all()
    )
    assert [u.username for u in eligible] == ["rep-on"]


def test_package_sync_creates_adopts_and_renames(client, db):
    """Portal plan mirror: create new, adopt same-name local, rename via plan_code."""
    from app.models import Package
    db.add(Package(name="Bridge 500", category="transaction", monthly_limit=400))
    db.commit()

    res = client.put("/api/portal/v1/packages/sync", json={"items": [
        {"plan_code": "s", "name": "Bridge 500", "monthly_limit": 500},
        {"plan_code": "m", "name": "Bridge 1.000", "monthly_limit": 1000, "description": "Mittel"},
    ]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["adopted"] == 1 and body["created"] == 1 and body["errors"] == []

    adopted = db.query(Package).filter(Package.portal_plan_code == "s").one()
    assert adopted.name == "Bridge 500"
    assert adopted.monthly_limit == 500  # portal wins over the local 400
    assert adopted.category == "transaction"  # local category preserved on adopt
    created = db.query(Package).filter(Package.portal_plan_code == "m").one()
    assert created.category == "portal"

    # Rename + deactivate follow the plan_code, not the name.
    res = client.put("/api/portal/v1/packages/sync", json={"items": [
        {"plan_code": "m", "name": "Bridge 1K", "monthly_limit": 1200, "is_active": False},
    ]})
    assert res.json()["updated"] == 1
    db.refresh(created)
    assert created.name == "Bridge 1K"
    assert created.monthly_limit == 1200
    assert created.is_active is False


def test_package_sync_reports_name_conflicts(client, db):
    from app.models import Package
    db.add(Package(name="Belegt", category="transaction", monthly_limit=100))
    db.commit()
    client.put("/api/portal/v1/packages/sync", json={"items": [
        {"plan_code": "a", "name": "Plan A", "monthly_limit": 100},
    ]})

    # Renaming plan 'a' onto a name owned by another package must not clobber it.
    res = client.put("/api/portal/v1/packages/sync", json={"items": [
        {"plan_code": "a", "name": "Belegt", "monthly_limit": 100},
    ]})
    body = res.json()
    assert body["updated"] == 0
    assert len(body["errors"]) == 1
    belegt = db.query(Package).filter(Package.name == "Belegt").one()
    assert belegt.portal_plan_code is None


def test_package_sync_requires_provisioning_switch(client, db):
    db.query(SystemSetting).filter(SystemSetting.key == "portal_provisioning_enabled").update({"value": "0"})
    db.commit()
    res = client.put("/api/portal/v1/packages/sync", json={"items": []})
    assert res.status_code == 403


def test_upsert_resolves_synced_package_by_name(client, db):
    """A user push referencing a synced plan name lands on the mirrored package."""
    from app.models import Package
    client.put("/api/portal/v1/packages/sync", json={"items": [
        {"plan_code": "l", "name": "Bridge 2.500", "monthly_limit": 2500},
    ]})
    res = client.put("/api/portal/v1/smtp-users/plan-user", json={
        "portal_access_id": "acc-9",
        "password_hash": VALID_HASH,
        "package_name": "Bridge 2.500",
    })
    assert res.status_code == 200, res.text
    user = db.query(SmtpUser).filter(SmtpUser.username == "plan-user").one()
    pkg = db.query(Package).filter(Package.id == user.package_id).one()
    assert pkg.portal_plan_code == "l"
