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
from app.models import Base, User
from app.auth import get_password_hash
from app.routers import auth_router, dashboard_router, network_router, config_router, logs_router
from app.routers import smtp_users_router
from app.routers import throttle_router
from app.services.stats_collector import StatsCollector
from app.services.sasl_service import sync_dovecot_users
from app.services.policy_server import PolicyServer
from app.services.batch_worker import BatchWorker
from app.services.throttle_service import seed_default_data

logger = logging.getLogger(__name__)

stats_collector: StatsCollector | None = None
policy_server: PolicyServer | None = None
batch_worker: BatchWorker | None = None


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    create_default_admin()

    # Sync Dovecot users from DB (regenerate passwd-file on every start)
    db = SessionLocal()
    try:
        sync_dovecot_users(db)
    except Exception as e:
        logger.warning(f"Initial dovecot user sync failed: {e}")
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

    global stats_collector, policy_server, batch_worker
    stats_collector = StatsCollector()
    collector_task = asyncio.create_task(stats_collector.run())

    # Start policy server and batch worker
    policy_server = PolicyServer()
    await policy_server.start()

    batch_worker = BatchWorker()
    worker_task = asyncio.create_task(batch_worker.run())

    yield

    # Shutdown
    from app.services.log_broadcaster import broadcaster
    broadcaster.stop()

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard_router.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(network_router.router, prefix="/api/networks", tags=["networks"])
app.include_router(config_router.router, prefix="/api/config", tags=["config"])
app.include_router(logs_router.router, prefix="/api/logs", tags=["logs"])
app.include_router(smtp_users_router.router, prefix="/api/smtp-users", tags=["smtp-users"])
app.include_router(throttle_router.router, prefix="/api/throttling", tags=["throttling"])

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
