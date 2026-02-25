"""Postfix policy server for rate-limiting via HOLD mechanism.

Listens on TCP port 9998 and speaks the Postfix Policy Delegation Protocol.
Fail-open: any error results in DUNNO (mail is never blocked by a bug).
"""
import asyncio
import logging

from app.database import SessionLocal
from app.services.throttle_service import (
    get_throttle_enabled,
    get_current_warmup_phase,
    throttle_counter,
)

logger = logging.getLogger(__name__)

POLICY_PORT = 9998


class PolicyServer:
    def __init__(self):
        self._server: asyncio.Server | None = None
        self._running = False
        self._sync_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        try:
            self._server = await asyncio.start_server(
                self._handle_client, "0.0.0.0", POLICY_PORT
            )
            logger.info(f"Policy server listening on port {POLICY_PORT}")
            self._sync_task = asyncio.create_task(self._periodic_sync())
            # Initial sync
            throttle_counter.sync_from_db()
        except Exception as e:
            logger.error(f"Failed to start policy server: {e}")

    async def stop(self) -> None:
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Policy server stopped")

    async def _periodic_sync(self) -> None:
        """Periodically sync counters from database."""
        while self._running:
            try:
                await asyncio.sleep(30)
                if self._running:
                    throttle_counter.sync_from_db()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic sync error: {e}")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a single Postfix policy delegation request."""
        try:
            attrs: dict[str, str] = {}
            while True:
                line_bytes = await asyncio.wait_for(reader.readline(), timeout=10)
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    # Empty line = end of request
                    action = self._evaluate(attrs)
                    response = f"action={action}\n\n"
                    writer.write(response.encode("utf-8"))
                    await writer.drain()
                    attrs = {}
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    attrs[key.strip()] = value.strip()
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Policy client error: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _evaluate(self, attrs: dict[str, str]) -> str:
        """Evaluate rate limits. Returns HOLD or DUNNO. Fail-open on any error."""
        try:
            # Check if throttling is enabled
            db = SessionLocal()
            try:
                if not get_throttle_enabled(db):
                    return "DUNNO"

                phase = get_current_warmup_phase(db)
            finally:
                db.close()

            # Get current counts
            hour_count, day_count = throttle_counter.get_counts()

            # Check limits
            if hour_count >= phase.max_per_hour or day_count >= phase.max_per_day:
                sender = attrs.get("sender", "unknown")
                recipient = attrs.get("recipient", "unknown")
                logger.info(
                    f"HOLD: rate limit reached (hour={hour_count}/{phase.max_per_hour}, "
                    f"day={day_count}/{phase.max_per_day}) for {sender} -> {recipient}"
                )
                return "HOLD Rate limit - Aufwaermphase"

            # Check burst
            if hour_count >= phase.burst_limit:
                # Burst limit is a softer per-evaluation check
                # Only hold if we've hit the burst within recent evaluations
                pass

            # Under limits — count it and let it through
            throttle_counter.increment()

            # Trigger DB sync if needed
            if throttle_counter.should_sync():
                throttle_counter.sync_from_db()

            return "DUNNO"

        except Exception as e:
            # FAIL-OPEN: never block mail due to internal errors
            logger.error(f"Policy evaluation error (fail-open): {e}")
            return "DUNNO"
