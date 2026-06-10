"""Provider-block background worker — periodically scans bounces for provider blocks."""

import asyncio
import logging

from app.database import SessionLocal
from app.services.provider_block_service import get_settings, run_scan

logger = logging.getLogger(__name__)


class ProviderBlockWorker:
    def __init__(self):
        self._running = False

    def stop(self):
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("Provider block worker starting")
        await asyncio.sleep(90)  # Initial delay (after stats_collector has warmed up)

        while self._running:
            try:
                interval_hours = self._get_interval()
                if self._is_enabled():
                    logger.info("Provider block worker: running scheduled scan")
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._do_scan)

                sleep_seconds = interval_hours * 3600
                while sleep_seconds > 0 and self._running:
                    await asyncio.sleep(min(sleep_seconds, 10))
                    sleep_seconds -= 10

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Provider block worker error: {e}")
                await asyncio.sleep(300)

    def _is_enabled(self) -> bool:
        try:
            db = SessionLocal()
            try:
                return get_settings(db).get("provider_block_enabled", "false") == "true"
            finally:
                db.close()
        except Exception:
            return False

    def _get_interval(self) -> int:
        try:
            db = SessionLocal()
            try:
                return max(1, int(get_settings(db).get("provider_block_scan_interval_hours", "6")))
            finally:
                db.close()
        except Exception:
            return 6

    @staticmethod
    def _do_scan() -> None:
        db = SessionLocal()
        try:
            run_scan(db)
        except Exception as e:
            logger.error(f"Provider block scan failed: {e}")
        finally:
            db.close()
