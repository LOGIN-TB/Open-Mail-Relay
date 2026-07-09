"""R1: per-user monthly quota — limit resolution, cached checks, policy verdict."""
from datetime import datetime

from app.models import MailEvent, Package, SmtpUser, SystemSetting
from app.services.billing_service import get_user_quota
from app.services.policy_server import PolicyServer
from app.services.quota_service import (
    QuotaChecker,
    effective_monthly_limit,
    quota_checker,
)


def _user(db, username: str, override=None, package=None):
    pkg_id = None
    if package is not None:
        pkg = Package(name=f"pkg-{username}", category="transaction", monthly_limit=package)
        db.add(pkg)
        db.flush()
        pkg_id = pkg.id
    user = SmtpUser(username=username, monthly_limit_override=override, package_id=pkg_id, is_active=True)
    db.add(user)
    db.commit()
    return user


def _sent(db, username: str, count: int):
    for _ in range(count):
        db.add(MailEvent(timestamp=datetime.now(), status="sent", sasl_username=username))
    db.commit()


def test_effective_limit_override_wins(db):
    user = _user(db, "limit-a", override=100, package=500)
    assert effective_monthly_limit(db, user) == 100


def test_effective_limit_falls_back_to_package(db):
    user = _user(db, "limit-b", package=500)
    assert effective_monthly_limit(db, user) == 500


def test_effective_limit_none_means_unlimited(db):
    user = _user(db, "limit-c")
    assert effective_monthly_limit(db, user) is None


def test_get_user_quota_with_override_and_no_package(db):
    user = _user(db, "quota-a", override=100)
    _sent(db, "quota-a", 3)
    quota = get_user_quota(db, user)
    assert quota == {
        "package_name": "Portal-Limit",
        "category": "portal",
        "monthly_limit": 100,
        "used": 3,
        "remaining": 97,
        "overage_emails": 0,
        "overage_units": 0,
        "period": datetime.now().strftime("%Y-%m"),
    }


def test_get_user_quota_override_beats_package(db):
    user = _user(db, "quota-b", override=2000, package=500)
    quota = get_user_quota(db, user)
    assert quota["monthly_limit"] == 2000
    assert quota["package_name"] == "pkg-quota-b"


def test_quota_checker_exceeded_and_register_sent(db):
    checker = QuotaChecker()
    _user(db, "check-a", override=5)
    _sent(db, "check-a", 4)

    exceeded, used, limit = checker.check(db, "check-a")
    assert (exceeded, used, limit) == (False, 4, 5)

    # The 5th allowed mail is counted in the cache — the 6th is blocked
    # without waiting for the TTL.
    checker.register_sent("check-a")
    exceeded, used, limit = checker.check(db, "check-a")
    assert (exceeded, used, limit) == (True, 5, 5)


def test_quota_checker_unlimited_user(db):
    checker = QuotaChecker()
    _user(db, "check-b")
    assert checker.check(db, "check-b") is None


def _enable_quota(db):
    db.add(SystemSetting(key="quota_enforcement_enabled", value="1"))
    db.commit()


def test_policy_defers_when_quota_exceeded(db):
    quota_checker.clear()
    _enable_quota(db)
    _user(db, "policy-a", override=2)
    _sent(db, "policy-a", 2)

    action = PolicyServer()._evaluate({"sasl_username": "policy-a", "sender": "x@y.de"})
    assert action.startswith("DEFER")
    assert "Monatskontingent" in action


def test_policy_allows_under_quota_and_without_enforcement(db):
    quota_checker.clear()
    _enable_quota(db)
    _user(db, "policy-b", override=10)
    _sent(db, "policy-b", 2)
    assert PolicyServer()._evaluate({"sasl_username": "policy-b"}) == "DUNNO"

    # Feature off → DUNNO even for exhausted users.
    db.query(SystemSetting).delete()
    db.commit()
    quota_checker.clear()
    _user(db, "policy-c", override=1)
    _sent(db, "policy-c", 5)
    assert PolicyServer()._evaluate({"sasl_username": "policy-c"}) == "DUNNO"


def test_policy_fails_open_without_username(db):
    quota_checker.clear()
    _enable_quota(db)
    assert PolicyServer()._evaluate({"sender": "x@y.de"}) == "DUNNO"
