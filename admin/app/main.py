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
from app.services.stats_collector import StatsCollector

logger = logging.getLogger(__name__)

stats_collector: StatsCollector | None = None


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

    global stats_collector
    stats_collector = StatsCollector()
    collector_task = asyncio.create_task(stats_collector.run())

    yield

    # Shutdown
    from app.services.log_broadcaster import broadcaster
    broadcaster.stop()

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
