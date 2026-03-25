"""Billing background worker — hourly usage refresh, monthly report auto-send, weekly customer usage reports."""

import asyncio
import logging
from datetime import datetime

from app.database import SessionLocal
from app.services.billing_service import (
    refresh_monthly_usage,
    send_billing_report,
    send_usage_reports,
    get_billing_settings,
)

logger = logging.getLogger(__name__)

DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


class BillingWorker:
    def __init__(self):
        self._running = False
        self._last_report_month: str | None = None
        self._last_usage_report_week: str | None = None

    def stop(self):
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("Billing worker starting")
        # Initial delay
        await asyncio.sleep(120)

        # Initialize to avoid sending on first start
        self._last_report_month = datetime.now().strftime("%Y-%m")
        self._last_usage_report_week = datetime.now().strftime("%G-W%V")

        while self._running:
            try:
                # Refresh current month usage
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._refresh_usage)

                # Check if we need to send a monthly report (1st of month)
                await loop.run_in_executor(None, self._check_monthly_report)

                # Check if we need to send weekly usage reports
                await loop.run_in_executor(None, self._check_usage_reports)

                # Sleep 1 hour in small increments
                sleep_seconds = 3600
                while sleep_seconds > 0 and self._running:
                    await asyncio.sleep(min(sleep_seconds, 10))
                    sleep_seconds -= 10

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Billing worker error: {e}")
                await asyncio.sleep(300)

    @staticmethod
    def _refresh_usage() -> None:
        db = SessionLocal()
        try:
            refresh_monthly_usage(db)
        except Exception as e:
            logger.error(f"Billing usage refresh failed: {e}")
        finally:
            db.close()

    def _check_monthly_report(self) -> None:
        now = datetime.now()
        current_month = now.strftime("%Y-%m")

        # Only send on the 1st of the month, and only once
        if now.day != 1 or current_month == self._last_report_month:
            return

        # Calculate previous month
        if now.month == 1:
            prev_month = f"{now.year - 1}-12"
        else:
            prev_month = f"{now.year}-{now.month - 1:02d}"

        db = SessionLocal()
        try:
            settings = get_billing_settings(db)
            if settings.get("billing_report_email"):
                logger.info("Billing worker: sending monthly report for %s", prev_month)
                send_billing_report(db, prev_month)
            self._last_report_month = current_month
        except Exception as e:
            logger.error(f"Billing monthly report failed: {e}")
        finally:
            db.close()

    def _check_usage_reports(self) -> None:
        now = datetime.now()
        current_week = now.strftime("%G-W%V")

        # Only send once per week
        if current_week == self._last_usage_report_week:
            return

        db = SessionLocal()
        try:
            settings = get_billing_settings(db)

            # Check if enabled
            if settings.get("usage_report_enabled", "true") != "true":
                return

            # Check if today is the configured day
            report_day = settings.get("usage_report_day", "monday").lower()
            target_weekday = DAY_MAP.get(report_day, 0)
            if now.weekday() != target_weekday:
                return

            logger.info("Billing worker: sending weekly usage reports")
            refresh_monthly_usage(db)
            count = send_usage_reports(db)
            logger.info("Billing worker: sent %d usage reports", count)
            self._last_usage_report_week = current_week
        except Exception as e:
            logger.error(f"Usage reports failed: {e}")
        finally:
            db.close()
