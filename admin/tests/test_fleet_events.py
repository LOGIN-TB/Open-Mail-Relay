"""Fleet events (capability 'fleet_events'): relay-wide protocol view for the
portal — /api/portal/events (+ .csv) across ALL SMTP users with an optional
sasl_username filter. Mirrors the JWT-protected admin logs_router."""
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import MailEvent, SystemSetting
from app.routers import portal_provisioning_router, portal_router


@pytest.fixture()
def client(db):
    app = FastAPI()
    app.include_router(portal_router.router, prefix="/api/portal")
    app.include_router(portal_provisioning_router.router, prefix="/api/portal/v1")
    app.dependency_overrides[get_db] = lambda: db

    db.add(SystemSetting(key="portal_provisioning_enabled", value="1"))
    base = datetime(2026, 7, 16, 12, 0, 0)
    db.add_all([
        MailEvent(timestamp=base, status="sent", sender="a@alpha.de",
                  recipient="x@example.org", sasl_username="alpha-user"),
        MailEvent(timestamp=base - timedelta(hours=1), status="bounced", sender="b@beta.de",
                  recipient="y@example.org", sasl_username="beta-user",
                  dsn="5.1.1", remote_response="user unknown"),
        MailEvent(timestamp=base - timedelta(hours=2), status="sent", sender="c@alpha.de",
                  recipient="z@example.org", sasl_username="alpha-user"),
    ])
    db.commit()
    return TestClient(app)


def test_capability_advertises_fleet_events(client):
    features = client.get("/api/portal/v1/capabilities").json()["features"]
    assert "fleet_events" in features


def test_events_span_all_users_newest_first(client):
    data = client.get("/api/portal/events").json()
    assert data["total"] == 3
    assert [i["sasl_username"] for i in data["items"]] == ["alpha-user", "beta-user", "alpha-user"]
    assert data["items"][0]["sender"] == "a@alpha.de"


def test_events_filter_by_sasl_username_and_status(client):
    by_user = client.get("/api/portal/events", params={"sasl_username": "alpha-user"}).json()
    assert by_user["total"] == 2
    assert all(i["sasl_username"] == "alpha-user" for i in by_user["items"])

    bounced = client.get("/api/portal/events", params={"status": "bounced"}).json()
    assert bounced["total"] == 1
    assert bounced["items"][0]["sasl_username"] == "beta-user"


def test_events_date_filter_and_pagination(client):
    windowed = client.get("/api/portal/events", params={
        "date_from": "2026-07-16T11:30:00Z",
    }).json()
    assert windowed["total"] == 1  # only the 12:00 event

    paged = client.get("/api/portal/events", params={"per_page": 2, "page": 2}).json()
    assert paged["pages"] == 2
    assert len(paged["items"]) == 1


def test_events_csv_contains_sasl_column(client):
    res = client.get("/api/portal/events.csv", params={"sasl_username": "beta-user"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    body = res.text
    assert "SASL-Benutzer" in body
    assert "beta-user" in body
    assert "alpha-user" not in body
