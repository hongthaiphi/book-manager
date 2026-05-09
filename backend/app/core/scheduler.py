"""
APScheduler jobs for periodic tasks.
Started in main.py lifespan.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_, select

from app.db.models import Loan, Notification
from app.db.session import AsyncSessionLocal
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _daily_loan_reminders() -> None:
    """
    Run every day at 09:00.
    - due_at == today + 3  → loan_due_soon
    - due_at == today      → loan_due_today
    - due_at < today       → loan_overdue (once per 7 days)
    Avoids duplicates by checking existing notifications for the same loan + type today.
    """
    today = date.today()
    soon = today + timedelta(days=3)

    async with AsyncSessionLocal() as db:
        # Fetch active loans with a due date
        result = await db.execute(
            select(Loan).where(Loan.status == "active", Loan.due_at.isnot(None))
        )
        loans = result.scalars().all()

        for loan in loans:
            due = loan.due_at

            if due == soon:
                notif_type = "loan_due_soon"
                title = f"Sách sẽ đến hạn sau 3 ngày ({due})"
            elif due == today:
                notif_type = "loan_due_today"
                title = f"Hôm nay là ngày trả sách ({due})"
            elif due < today:
                overdue_days = (today - due).days
                # Only fire every 7 days of overdue
                if overdue_days % 7 != 0:
                    continue
                notif_type = "loan_overdue"
                title = f"Sách quá hạn {overdue_days} ngày"
                # Also flip status to overdue
                loan.status = "overdue"
            else:
                continue

            # Dedup: check if we already sent this type today for this loan
            existing = await db.execute(
                select(Notification).where(
                    Notification.content_type == "loan",
                    Notification.content_id == loan.id,
                    Notification.type == notif_type,
                    Notification.user_id == loan.borrower_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            await create_notification(
                db,
                user_id=loan.borrower_id,
                type=notif_type,
                title=title,
                content_type="loan",
                content_id=loan.id,
            )

        await db.commit()
        logger.info("[scheduler] daily_loan_reminders done for %s", today)


def start_scheduler() -> None:
    scheduler.add_job(
        _daily_loan_reminders,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_loan_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] started")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("[scheduler] stopped")
