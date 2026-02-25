"""Batch worker — periodically releases HOLD-queued mail in controlled batches."""
import asyncio
import logging
import re

from app.database import SessionLocal
from app.services.throttle_service import (
    get_throttle_enabled,
    get_config,
    get_current_warmup_phase,
    get_sent_today,
    get_sent_this_hour,
)
from app.services.docker_service import exec_in_container

logger = logging.getLogger(__name__)


class BatchWorker:
    def __init__(self):
        self._running = False

    def stop(self):
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("Batch worker starting")
        await asyncio.sleep(30)  # Initial delay

        while self._running:
            try:
                interval = self._get_interval()
                await self._process_batch()
                await asyncio.sleep(interval * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch worker error: {e}")
                await asyncio.sleep(60)

    def _get_interval(self) -> int:
        """Get batch interval in minutes from config."""
        try:
            db = SessionLocal()
            try:
                val = get_config(db, "batch_interval_minutes", "10")
                return max(1, int(val))
            finally:
                db.close()
        except Exception:
            return 10

    async def _process_batch(self) -> None:
        db = SessionLocal()
        try:
            if not get_throttle_enabled(db):
                # Throttling disabled: release everything
                held_ids = self._get_hold_queue_ids()
                if held_ids:
                    logger.info(f"Throttling disabled — releasing all {len(held_ids)} held mails")
                    exit_code, _ = exec_in_container(
                        "sh -c 'postsuper -H ALL 2>/dev/null; postqueue -f 2>/dev/null; true'"
                    )
                return

            # Get current phase limits
            phase = get_current_warmup_phase(db)
            sent_hour = get_sent_this_hour(db)
            sent_day = get_sent_today(db)

            hour_remaining = max(0, phase.max_per_hour - sent_hour)
            day_remaining = max(0, phase.max_per_day - sent_day)
            batch_size = min(hour_remaining, day_remaining, phase.burst_limit)

            if batch_size <= 0:
                logger.debug("Batch worker: no capacity to release mails")
                return

            # Get HOLD queue IDs
            held_ids = self._get_hold_queue_ids()
            if not held_ids:
                return

            release_count = min(batch_size, len(held_ids))
            logger.info(
                f"Releasing {release_count}/{len(held_ids)} held mails "
                f"(hour: {sent_hour}/{phase.max_per_hour}, day: {sent_day}/{phase.max_per_day})"
            )

            # Release one by one
            for queue_id in held_ids[:release_count]:
                exec_in_container(f"postsuper -H {queue_id}")

            # Flush queue to trigger delivery
            exec_in_container("postqueue -f")

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
        finally:
            db.close()

    @staticmethod
    def _get_hold_queue_ids() -> list[str]:
        """Parse mailq output for HOLD entries. HOLD entries have '!' after queue ID."""
        try:
            exit_code, output = exec_in_container("mailq")
            if exit_code != 0 or "Mail queue is empty" in output:
                return []

            ids = []
            for line in output.splitlines():
                # HOLD entries: queue_id followed by '!'
                # Example: "AB1234CD56EF!    1234 Mon Feb 25 10:00:00  sender@example.com"
                match = re.match(r"^([0-9A-F]+)!\s", line)
                if match:
                    ids.append(match.group(1))
            return ids
        except Exception:
            return []
