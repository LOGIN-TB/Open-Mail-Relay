import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from queue import Queue, Empty

from app.database import SessionLocal
from app.models import MailEvent, SmtpUser, StatsHourly
from app.services.docker_service import get_mail_container
from app.services.log_parser import parse_and_enrich

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="log-collector")


class StatsCollector:
    def __init__(self):
        self._running = False
        self._line_queue: Queue[str] = Queue(maxsize=10000)

    def stop(self):
        self._running = False

    async def run(self):
        self._running = True
        logger.info("Stats collector starting")

        await asyncio.sleep(5)

        while self._running:
            try:
                await self._collect_logs()
            except Exception as e:
                logger.error(f"Stats collector error: {e}")
                await asyncio.sleep(10)

    def _blocking_log_reader(self):
        """Runs in a thread – reads Docker log stream and puts lines into a queue."""
        container = get_mail_container()
        if container is None:
            return

        try:
            log_stream = container.logs(stream=True, follow=True, tail=0, timestamps=True)
            for chunk in log_stream:
                if not self._running:
                    break
                line = chunk.decode("utf-8", errors="replace").strip()
                if line:
                    try:
                        self._line_queue.put_nowait(line)
                    except Exception:
                        pass  # Queue full, drop line
        except Exception as e:
            if self._running:
                logger.error(f"Log reader thread error: {e}")

    async def _collect_logs(self):
        container = get_mail_container()
        if container is None:
            logger.warning("Open Mail Relay container not available, retrying in 30s")
            await asyncio.sleep(30)
            return

        logger.info("Starting log stream from open-mail-relay container")

        # Start blocking reader in thread
        loop = asyncio.get_event_loop()
        reader_future = loop.run_in_executor(_executor, self._blocking_log_reader)

        # Process lines from queue without blocking the event loop
        try:
            while self._running:
                processed = 0
                while processed < 200:
                    try:
                        line = self._line_queue.get_nowait()
                        event = parse_and_enrich(line)
                        if event and event.status:
                            self._store_event(event)
                        processed += 1
                    except Empty:
                        break

                # Check if reader thread has finished (container gone, error, etc.)
                if reader_future.done():
                    break

                await asyncio.sleep(0.2)
        except Exception as e:
            if self._running:
                logger.error(f"Log processing error: {e}")

        # Wait for reader thread to finish
        try:
            await asyncio.wait_for(asyncio.shield(reader_future), timeout=2)
        except (asyncio.TimeoutError, Exception):
            pass

        if self._running:
            await asyncio.sleep(10)

    def _record_ban_failure(self, ip_address: str, reason: str):
        """Record a failed attempt for IP ban tracking."""
        db = SessionLocal()
        try:
            from app.services.ban_service import record_failure
            record_failure(db, ip_address, reason)
        except Exception as e:
            logger.error(f"Error recording ban failure: {e}")
            db.rollback()
        finally:
            db.close()

    def _store_event(self, event):
        db = SessionLocal()
        try:
            # Normalize to naive UTC for SQLite compatibility
            if event.timestamp and event.timestamp.tzinfo:
                event.timestamp = event.timestamp.replace(tzinfo=None)

            mail_event = MailEvent(
                timestamp=event.timestamp,
                queue_id=event.queue_id,
                sender=event.sender,
                recipient=event.recipient,
                status=event.status,
                relay=event.relay,
                delay=event.delay,
                dsn=event.dsn,
                size=event.size,
                message=event.message,
                client_ip=event.client_ip,
                sasl_username=event.sasl_username,
            )
            db.add(mail_event)

            # Update hourly stats
            hour_start = event.timestamp.replace(minute=0, second=0, microsecond=0)
            stats = db.query(StatsHourly).filter(StatsHourly.hour_start == hour_start).first()
            if not stats:
                stats = StatsHourly(hour_start=hour_start)
                db.add(stats)
                db.flush()

            if event.status == "sent":
                stats.sent_count += 1
            elif event.status == "deferred":
                stats.deferred_count += 1
            elif event.status == "bounced":
                stats.bounced_count += 1
            elif event.status == "rejected":
                stats.rejected_count += 1
            elif event.status == "auth_failed":
                stats.auth_failed_count += 1

            # Update last_used_at on SMTP user
            if event.sasl_username:
                smtp_user = db.query(SmtpUser).filter(
                    SmtpUser.username == event.sasl_username
                ).first()
                if smtp_user:
                    if not smtp_user.last_used_at or event.timestamp > smtp_user.last_used_at:
                        smtp_user.last_used_at = event.timestamp

            db.commit()

            # Record rejected / auth_failed events for ban tracking
            if event.status == "rejected" and event.client_ip:
                self._record_ban_failure(event.client_ip, "relay_rejected")
            elif event.status == "auth_failed" and event.client_ip:
                self._record_ban_failure(event.client_ip, "sasl_auth_failed")

            self._cleanup_old_events(db)
        except Exception as e:
            logger.error(f"Error storing event: {e}")
            db.rollback()
        finally:
            db.close()

    def _cleanup_old_events(self, db):
        from app.config import settings
        from app.models import SystemSetting
        import random

        if random.random() > 0.01:
            return

        # Read retention settings from DB, fall back to config defaults
        retention_days = settings.LOG_RETENTION_DAYS
        stats_retention_days = settings.STATS_RETENTION_DAYS

        row = db.query(SystemSetting).filter(SystemSetting.key == "retention_days").first()
        if row:
            retention_days = int(row.value)
        row = db.query(SystemSetting).filter(SystemSetting.key == "stats_retention_days").first()
        if row:
            stats_retention_days = int(row.value)

        # Clean old events
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted = db.query(MailEvent).filter(MailEvent.timestamp < cutoff).delete()
        if deleted:
            db.commit()
            logger.info(f"Cleaned up {deleted} old mail events")

        # Clean old hourly stats
        stats_cutoff = datetime.now(timezone.utc) - timedelta(days=stats_retention_days)
        deleted_stats = db.query(StatsHourly).filter(StatsHourly.hour_start < stats_cutoff).delete()
        if deleted_stats:
            db.commit()
            logger.info(f"Cleaned up {deleted_stats} old hourly stats")
