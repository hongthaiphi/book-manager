"""
Stats endpoints:
  GET /api/stats/summary   — total books, by status, read this year/month
  GET /api/stats/reading   — monthly reading counts (12 months)
  GET /api/stats/lending   — lending summary
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models import Loan, User, UserBook
from app.db.session import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
async def stats_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    today = date.today()

    # Total + by status
    result = await db.execute(
        select(UserBook.status, func.count().label("cnt"))
        .where(UserBook.user_id == current_user.id)
        .group_by(UserBook.status)
    )
    rows = result.all()
    by_status = {r.status: r.cnt for r in rows}
    total = sum(by_status.values())

    # Read this year
    year_result = await db.execute(
        select(func.count()).select_from(UserBook).where(
            UserBook.user_id == current_user.id,
            UserBook.status == "read",
            extract("year", UserBook.finished_at) == today.year,
        )
    )
    read_this_year = year_result.scalar() or 0

    # Read this month
    month_result = await db.execute(
        select(func.count()).select_from(UserBook).where(
            UserBook.user_id == current_user.id,
            UserBook.status == "read",
            extract("year", UserBook.finished_at) == today.year,
            extract("month", UserBook.finished_at) == today.month,
        )
    )
    read_this_month = month_result.scalar() or 0

    return {
        "total_books": total,
        "by_status": by_status,
        "read_this_year": read_this_year,
        "read_this_month": read_this_month,
    }


@router.get("/reading")
async def stats_reading(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Monthly finished books for the past 12 months."""
    today = date.today()
    since = today.replace(day=1) - timedelta(days=365)

    result = await db.execute(
        select(
            extract("year", UserBook.finished_at).label("year"),
            extract("month", UserBook.finished_at).label("month"),
            func.count().label("cnt"),
        )
        .where(
            UserBook.user_id == current_user.id,
            UserBook.status == "read",
            UserBook.finished_at >= since,
        )
        .group_by("year", "month")
        .order_by("year", "month")
    )
    rows = result.all()

    monthly = [
        {"month": f"{int(r.year):04d}-{int(r.month):02d}", "count": r.cnt}
        for r in rows
    ]
    return {"monthly": monthly}


@router.get("/lending")
async def stats_lending(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Total lent out
    lent_result = await db.execute(
        select(func.count()).select_from(Loan).where(
            Loan.lender_id == current_user.id,
            Loan.status.in_(["returned", "lost"]),
        )
    )
    total_lent = lent_result.scalar() or 0

    # Total borrowed
    borrowed_result = await db.execute(
        select(func.count()).select_from(Loan).where(
            Loan.borrower_id == current_user.id,
            Loan.status.in_(["returned", "lost"]),
        )
    )
    total_borrowed = borrowed_result.scalar() or 0

    # On-time rate (returned before or on due_at)
    returned_result = await db.execute(
        select(
            func.count().label("total"),
            func.sum(
                case((Loan.returned_at <= Loan.due_at, 1), else_=0)
            ).label("on_time"),
        ).where(
            Loan.lender_id == current_user.id,
            Loan.status == "returned",
            Loan.due_at.isnot(None),
            Loan.returned_at.isnot(None),
        )
    )
    row = returned_result.one()
    on_time_rate = round((row.on_time or 0) / max(row.total or 1, 1) * 100, 1)

    # Most lent books (top 5)
    top_result = await db.execute(
        select(
            Loan.user_book_id,
            func.count().label("times"),
        )
        .where(Loan.lender_id == current_user.id)
        .group_by(Loan.user_book_id)
        .order_by(func.count().desc())
        .limit(5)
    )
    most_lent = [{"user_book_id": str(r.user_book_id), "times": r.times} for r in top_result.all()]

    return {
        "total_lent": total_lent,
        "total_borrowed": total_borrowed,
        "on_time_rate": on_time_rate,
        "most_lent_books": most_lent,
    }
