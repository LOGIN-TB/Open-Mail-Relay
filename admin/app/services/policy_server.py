"""Postfix policy server for rate-limiting via HOLD mechanism.

Listens on TCP port 9998 and speaks the Postfix Policy Delegation Protocol.
Fail-open: any error results in DUNNO (mail is never blocked by a bug).
"""
import asyncio
import logging

from app.database import SessionLocal
from app.services.quota_service import get_quota_enforcement_enabled, quota_checker
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
        """Evaluate per-user quota + warmup rate limits. Fail-open on any error.

        Order matters: the per-user quota check (R1) answers DEFER — the
        client queue retries and delivery resumes automatically once the
        portal raises the limit. The warmup throttle keeps its HOLD semantics.
        """
        try:
            db = SessionLocal()
            try:
                throttle_on = get_throttle_enabled(db)
                quota_on = get_quota_enforcement_enabled(db)
                if not throttle_on and not quota_on:
                    return "DUNNO"

                # --- Per-user monthly quota (R1) ---
                sasl_username = attrs.get("sasl_username", "").strip().lower()
                if quota_on and sasl_username:
                    verdict = quota_checker.check(db, sasl_username)
                    if verdict is not None:
                        exceeded, used, limit = verdict
                        if exceeded:
                            logger.info(
                                f"DEFER: monthly quota reached for {sasl_username} "
                                f"({used}/{limit})"
                            )
                            return (
                                "DEFER 4.7.1 Monatskontingent erreicht - "
                                "Zusatzpakete im Portal freigeben oder Paket wechseln"
                            )

                phase = get_current_warmup_phase(db) if throttle_on else None
            finally:
                db.close()

            # --- Global warmup throttle (unchanged) ---
            if phase is not None:
                hour_count, day_count = throttle_counter.get_counts()

                if hour_count >= phase.max_per_hour or day_count >= phase.max_per_day:
                    sender = attrs.get("sender", "unknown")
                    recipient = attrs.get("recipient", "unknown")
                    logger.info(
                        f"HOLD: rate limit reached (hour={hour_count}/{phase.max_per_hour}, "
                        f"day={day_count}/{phase.max_per_day}) for {sender} -> {recipient}"
                    )
                    return "HOLD Rate limit - Aufwaermphase"

                # Under limits — count it and let it through
                throttle_counter.increment()

                # Trigger DB sync if needed
                if throttle_counter.should_sync():
                    throttle_counter.sync_from_db()

            # Mail passes — keep the cached quota counter warm.
            if sasl_username:
                quota_checker.register_sent(sasl_username)

            return "DUNNO"

        except Exception as e:
            # FAIL-OPEN: never block mail due to internal errors
            logger.error(f"Policy evaluation error (fail-open): {e}")
            return "DUNNO"
