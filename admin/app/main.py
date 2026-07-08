import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, SessionLocal
from app.models import Base, IpBan, User
from app.auth import get_password_hash
from app.routers import auth_router, dashboard_router, network_router, config_router, logs_router
from app.routers import smtp_users_router
from app.routers import throttle_router
from app.routers import ip_bans_router
from app.routers.abuse_router import public_router as abuse_public_router, admin_router as abuse_admin_router
from app.routers import rbl_router
from app.routers import provider_block_router
from app.routers import dns_check_router
from app.routers import billing_router
from app.routers import portal_router
from app.routers import portal_provisioning_router
from app.routers.portal_common import portal_auth_middleware
from app.routers.portal_settings_router import settings_router as portal_settings_router
from app.services.stats_collector import StatsCollector
from app.services.sasl_service import sync_dovecot_users
from app.services.policy_server import PolicyServer
from app.services.batch_worker import BatchWorker
from app.services.rbl_worker import RblWorker
from app.services.provider_block_worker import ProviderBlockWorker
from app.services.billing_worker import BillingWorker
from app.services.cert_worker import CertWorker
from app.services.throttle_service import seed_default_data

logger = logging.getLogger(__name__)

stats_collector: StatsCollector | None = None
policy_server: PolicyServer | None = None
batch_worker: BatchWorker | None = None
rbl_worker: RblWorker | None = None
provider_block_worker: ProviderBlockWorker | None = None
billing_worker: BillingWorker | None = None
cert_worker: CertWorker | None = None


def create_default_admin():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            admin = User(
                username="admin",
                password_hash=get_password_hash(settings.ADMIN_DEFAULT_PASSWORD),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Default admin user created")
    finally:
        db.close()


def run_migrations():
    """Run Alembic migrations to bring DB up to date.

    Handles three cases:
    1. Fresh DB (no tables) — create_all + stamp head
    2. Existing DB without alembic_version — stamp to last known + upgrade
    3. Existing DB with alembic_version — just upgrade to head
    """
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import inspect, text

    alembic_dir = Path(__file__).resolve().parent.parent / "alembic"
    alembic_cfg = Config(str(alembic_dir.parent / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(alembic_dir))

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if not tables or "users" not in tables:
        # Case 1: Fresh DB — create all tables, then stamp as current
        Base.metadata.create_all(bind=engine)
        command.stamp(alembic_cfg, "head")
        logger.info("Fresh database created and stamped at head")
    elif "alembic_version" not in tables:
        # Case 2: Existing DB from before Alembic tracking — stamp at 004, then upgrade
        command.stamp(alembic_cfg, "004")
        logger.info("Existing database stamped at 004")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database upgraded to head")
    else:
        # Case 3: Normal upgrade
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — run Alembic migrations (must happen before logging setup
    # because Alembic's fileConfig can reconfigure loggers)
    # A failed migration must abort startup: silently falling back to
    # create_all() can leave a half-migrated schema and corrupt data.
    try:
        run_migrations()
    except Exception:
        logging.exception(
            "Alembic migration failed — refusing to start with an "
            "inconsistent schema. Fix the migration state and restart."
        )
        raise

    # Configure app-level logging AFTER Alembic migrations
    # (Alembic's fileConfig may reconfigure the logging hierarchy)
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False  # prevent duplicate output via root handler
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)-5s %(name)s: %(message)s"))
        app_logger.addHandler(handler)

    # Re-enable any loggers that fileConfig may have disabled
    for name in logging.Logger.manager.loggerDict:
        if name.startswith("app."):
            lg = logging.getLogger(name)
            lg.disabled = False

    # Warn loudly about weak JWT/encryption secrets (also derives the Fernet
    # key for SMTP user passwords — see app/services/crypto_service.py).
    # Rotate with: python -m app.tools.rotate_secret_key <OLD> <NEW>
    if settings.SECRET_KEY == "change-me-in-production":
        logger.critical(
            "ADMIN_SECRET_KEY is not set — using the insecure default! "
            "Set a random value (openssl rand -hex 32) in .env."
        )
    elif len(settings.SECRET_KEY) < 32:
        logger.warning(
            "ADMIN_SECRET_KEY is shorter than 32 characters — consider rotating "
            "to a stronger key via: python -m app.tools.rotate_secret_key"
        )
    create_default_admin()

    # Sync Dovecot users from DB (regenerate passwd-file on every start)
    db = SessionLocal()
    try:
        sync_dovecot_users(db)
    except Exception as e:
        logger.warning(f"Initial dovecot user sync failed: {e}")
    finally:
        db.close()

    # Generate mynetworks file from DB on every start
    from app.services.postfix_service import generate_mynetworks_file
    db = SessionLocal()
    try:
        generate_mynetworks_file(db)
    except Exception as e:
        logger.warning(f"Initial mynetworks sync failed: {e}")
    finally:
        db.close()

    # Seed default throttle data
    db = SessionLocal()
    try:
        seed_default_data(db)
    except Exception as e:
        logger.warning(f"Throttle seed failed: {e}")
    finally:
        db.close()

    # Seed default packages if empty
    from app.services.billing_service import seed_default_packages
    db = SessionLocal()
    try:
        seed_default_packages(db)
    except Exception as e:
        logger.warning(f"Package seed failed: {e}")
    finally:
        db.close()

    # Generate client_access file from DB on every start
    from app.services.ban_service import generate_client_access_file
    db = SessionLocal()
    try:
        generate_client_access_file(db)
    except Exception as e:
        logger.warning(f"Initial client_access sync failed: {e}")
    finally:
        db.close()

    # Sync firewall rules (ipset) from DB on every start
    from app.services.firewall_service import sync_bans
    db = SessionLocal()
    try:
        active_bans = db.query(IpBan).filter(IpBan.is_active == True).all()
        banned_ips = [ban.ip_address for ban in active_bans]
        sync_bans(banned_ips)
    except Exception as e:
        logger.warning(f"Initial firewall sync failed: {e}")
    finally:
        db.close()

    global stats_collector, policy_server, batch_worker, rbl_worker, provider_block_worker, billing_worker, cert_worker
    stats_collector = StatsCollector()
    collector_task = asyncio.create_task(stats_collector.run())

    # Start policy server and batch worker
    policy_server = PolicyServer()
    await policy_server.start()

    batch_worker = BatchWorker()
    worker_task = asyncio.create_task(batch_worker.run())

    rbl_worker = RblWorker()
    rbl_worker_task = asyncio.create_task(rbl_worker.run())

    provider_block_worker = ProviderBlockWorker()
    provider_block_worker_task = asyncio.create_task(provider_block_worker.run())

    billing_worker = BillingWorker()
    billing_worker_task = asyncio.create_task(billing_worker.run())

    cert_worker = CertWorker()
    cert_worker_task = asyncio.create_task(cert_worker.run())

    # Ban expiry background task — check every 60 seconds
    async def ban_expiry_loop():
        from app.services.ban_service import check_expired_bans
        while True:
            await asyncio.sleep(60)
            try:
                db = SessionLocal()
                try:
                    check_expired_bans(db)
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Ban expiry check error: {e}")

    ban_expiry_task = asyncio.create_task(ban_expiry_loop())

    yield

    # Shutdown
    ban_expiry_task.cancel()
    try:
        await ban_expiry_task
    except asyncio.CancelledError:
        pass

    from app.services.log_broadcaster import broadcaster
    broadcaster.stop()

    if cert_worker:
        cert_worker.stop()
    cert_worker_task.cancel()
    try:
        await cert_worker_task
    except asyncio.CancelledError:
        pass

    if billing_worker:
        billing_worker.stop()
    billing_worker_task.cancel()
    try:
        await billing_worker_task
    except asyncio.CancelledError:
        pass

    if rbl_worker:
        rbl_worker.stop()
    rbl_worker_task.cancel()
    try:
        await rbl_worker_task
    except asyncio.CancelledError:
        pass

    if provider_block_worker:
        provider_block_worker.stop()
    provider_block_worker_task.cancel()
    try:
        await provider_block_worker_task
    except asyncio.CancelledError:
        pass

    if batch_worker:
        batch_worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    if policy_server:
        await policy_server.stop()

    if stats_collector:
        stats_collector.stop()
    collector_task.cancel()
    try:
        await collector_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Open Mail Relay Admin",
    version="1.0.0",
    lifespan=lifespan,
)

# The SPA is served same-origin by this app; CORS is only needed for the
# Vite dev server. Never combine a wildcard origin with credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"https://{settings.ADMIN_HOSTNAME}",
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.middleware.base import BaseHTTPMiddleware
app.add_middleware(BaseHTTPMiddleware, dispatch=portal_auth_middleware)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # HSTS only when the request actually came in via TLS (Caddy)
    if request.headers.get("x-forwarded-proto") == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


@app.get("/api/health")
def health():
    """Unauthenticated liveness probe for the Docker healthcheck."""
    return {"status": "ok"}

# API Routers
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard_router.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(network_router.router, prefix="/api/networks", tags=["networks"])
app.include_router(config_router.router, prefix="/api/config", tags=["config"])
app.include_router(logs_router.router, prefix="/api/logs", tags=["logs"])
app.include_router(smtp_users_router.router, prefix="/api/smtp-users", tags=["smtp-users"])
app.include_router(throttle_router.router, prefix="/api/throttling", tags=["throttling"])
app.include_router(ip_bans_router.router, prefix="/api/ip-bans", tags=["ip-bans"])
app.include_router(abuse_admin_router, prefix="/api/abuse-settings", tags=["abuse-settings"])
app.include_router(rbl_router.router, prefix="/api/rbl", tags=["rbl"])
app.include_router(provider_block_router.router, prefix="/api/provider-blocks", tags=["provider-blocks"])
app.include_router(dns_check_router.router, prefix="/api/dns-check", tags=["dns-check"])
app.include_router(billing_router.router, prefix="/api/billing", tags=["billing"])
# v1 first: same auth middleware ("/api/portal" prefix match) protects both.
app.include_router(portal_provisioning_router.router, prefix="/api/portal/v1", tags=["portal-provisioning"])
app.include_router(portal_router.router, prefix="/api/portal", tags=["portal"])
app.include_router(portal_settings_router, prefix="/api/portal-settings", tags=["portal-settings"])

# Public abuse page (must be before the SPA catch-all)
app.include_router(abuse_public_router, tags=["public"])

# Serve Vue.js SPA
static_dir = Path("/app/static")
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
