"""RBL background worker — periodically checks server IPs against DNS blacklists."""

import asyncio
import logging

from app.database import SessionLocal
from app.services.rbl_service import get_rbl_settings, run_rbl_check

logger = logging.getLogger(__name__)


class RblWorker:
    def __init__(self):
        self._running = False

    def stop(self):
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("RBL worker starting")
        await asyncio.sleep(60)  # Initial delay

        while self._running:
            try:
                interval_hours = self._get_interval()
                enabled = self._is_enabled()

                if enabled:
                    logger.info("RBL worker: running scheduled check")
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._do_check)

                # Sleep in small increments for responsive shutdown
                sleep_seconds = interval_hours * 3600
                while sleep_seconds > 0 and self._running:
                    await asyncio.sleep(min(sleep_seconds, 10))
                    sleep_seconds -= 10

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"RBL worker error: {e}")
                await asyncio.sleep(300)

    def _is_enabled(self) -> bool:
        try:
            db = SessionLocal()
            try:
                settings = get_rbl_settings(db)
                return settings.get("rbl_enabled", "false") == "true"
            finally:
                db.close()
        except Exception:
            return False

    def _get_interval(self) -> int:
        try:
            db = SessionLocal()
            try:
                settings = get_rbl_settings(db)
                return max(1, int(settings.get("rbl_check_interval_hours", "6")))
            finally:
                db.close()
        except Exception:
            return 6

    @staticmethod
    def _do_check() -> None:
        db = SessionLocal()
        try:
            run_rbl_check(db)
        except Exception as e:
            logger.error(f"RBL check failed: {e}")
        finally:
            db.close()
