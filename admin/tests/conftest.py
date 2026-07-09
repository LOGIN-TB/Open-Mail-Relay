"""Test bootstrap: point the app at a throwaway SQLite file BEFORE any
app import (app.database builds the engine at import time and mkdirs the
default /app/data path, which does not exist outside the container)."""
import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="omr-test-")
os.environ.setdefault("ADMIN_DATABASE_PATH", str(Path(_TMP) / "test.db"))
os.environ.setdefault("ADMIN_POSTFIX_CONFIG_PATH", str(Path(_TMP) / "postfix-config"))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # admin/

import pytest  # noqa: E402

from app.database import Base, engine, SessionLocal  # noqa: E402
import app.models  # noqa: F401,E402 — register all tables


Base.metadata.create_all(bind=engine)


@pytest.fixture()
def db():
    """Fresh session per test; all rows wiped afterwards (shared engine)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()
