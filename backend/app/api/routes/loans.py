"""
Loan endpoints:

Loan Requests:
  POST   /api/books/{book_id}/request-loan     — borrower sends request
  GET    /api/loan-requests                    — lender views incoming requests
  GET    /api/loan-requests/sent               — borrower views sent requests
  PUT    /api/loan-requests/{id}/approve       — lender approves
  PUT    /api/loan-requests/{id}/reject        — lender rejects
  DELETE /api/loan-requests/{id}              — borrower cancels (pending only)

Active Loans:
  GET    /api/loans                            — all loans (lender + borrower view)
  PUT    /api/loans/{id}/confirm               — lender confirms handover → active
  PUT    /api/loans/{id}/return                — lender marks returned
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.models import BorrowerBlacklist, Loan, LoanRequest, Notification, User, UserBook
from app.db.session import get_db
from app.schemas.loans import (
    LoanOut,
    LoanRequestApprove,
    LoanRequestCreate,
    LoanRequestOut,
    LoanRequestReject,
)
from app.services.notification_service import create_notification

router = APIRouter(tags=["loans"])

LOAN_REQUEST_DAILY_LIMIT = 10

_LOAN_REQUEST_OPTS = [
    selectinload(LoanRequest.lender),
    selectinload(LoanRequest.borrower),
]

_LOAN_OPTS = [
    selectinload(Loan.lender),
    selectinload(Loan.borrower),
]


# ---------------------------------------------------------------------------
# Loan Requests
# ---------------------------------------------------------------------------

@router.post("/books/{book_id}/request-loan", response_model=LoanRequestOut, status_code=201)
async def request_loan(
    book_id: uuid.UUID,
    payload: LoanRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoanRequest:
    # Must have verified phone
    if not current_user.phone_verified:
        raise HTTPException(status_code=403, detail="Verify your phone number first")

    # Find the book
    result = await db.execute(
        select(UserBook).where(UserBook.id == book_id, UserBook.can_lend == True)  # noqa: E712
    )
    user_book = result.scalar_one_or_none()
    if not user_book:
        raise HTTPException(status_code=404, detail="Book not found or not lendable")

    # Can't borrow own book
    if user_book.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot borrow your own book")

    lender_id = user_book.user_id

    # Blacklist check
    bl = await db.execute(
        select(BorrowerBlacklist).where(
            BorrowerBlacklist.lender_id == lender_id,
            BorrowerBlacklist.blocked_user_id == current_user.id,
        )
    )
    if bl.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Cannot send request to this lender")

    # Duplicate pending request check
    dup = await db.execute(
        select(LoanRequest).where(
            LoanRequest.user_book_id == book_id,
            LoanRequest.borrower_id == current_user.id,
            LoanRequest.status == "pending",
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You already have a pending request for this book")

    # Daily rate limit
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count()).select_from(LoanRequest).where(
            LoanRequest.borrower_id == current_user.id,
            LoanRequest.created_at >= today_start,
        )
    )
    if (count_result.scalar() or 0) >= LOAN_REQUEST_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Daily loan request limit reached")

    loan_request = LoanRequest(
        user_book_id=book_id,
        lender_id=lender_id,
        borrower_id=current_user.id,
        message=payload.message,
        status="pending",
    )
    db.add(loan_request)
    await db.flush()

    # Notify lender
    await create_notification(
        db,
        user_id=lender_id,
        type="loan_request_received",
        title=f"{current_user.name} muốn mượn sách của bạn",
        body=payload.message,
        actor_id=current_user.id,
        content_type="loan_request",
        content_id=loan_request.id,
    )
    await db.commit()

    result = await db.execute(
        select(LoanRequest).where(LoanRequest.id == loan_request.id).options(*_LOAN_REQUEST_OPTS)
    )
    return result.scalar_one()


@router.get("/loan-requests", response_model=list[LoanRequestOut])
async def list_incoming_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LoanRequest]:
    stmt = (
        select(LoanRequest)
        .where(LoanRequest.lender_id == current_user.id)
        .options(*_LOAN_REQUEST_OPTS)
        .order_by(LoanRequest.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(LoanRequest.status == status_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/loan-requests/sent", response_model=list[LoanRequestOut])
async def list_sent_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LoanRequest]:
    result = await db.execute(
        select(LoanRequest)
        .where(LoanRequest.borrower_id == current_user.id)
        .options(*_LOAN_REQUEST_OPTS)
        .order_by(LoanRequest.created_at.desc())
    )
    return list(result.scalars().all())


@router.put("/loan-requests/{request_id}/approve", response_model=LoanRequestOut)
async def approve_request(
    request_id: uuid.UUID,
    payload: LoanRequestApprove,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoanRequest:
    result = await db.execute(
        select(LoanRequest)
        .where(LoanRequest.id == request_id, LoanRequest.lender_id == current_user.id)
        .options(*_LOAN_REQUEST_OPTS)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already {req.status}")

    req.status = "approved"
    req.agreed_deposit = payload.agreed_deposit
    req.meet_location = payload.meet_location
    req.agreed_at = datetime.now(timezone.utc)

    await create_notification(
        db,
        user_id=req.borrower_id,
        type="loan_request_approved",
        title=f"{current_user.name} đã chấp nhận yêu cầu mượn sách",
        body=f"Địa điểm hẹn: {payload.meet_location}. Tiền cọc: {payload.agreed_deposit:,.0f}đ",
        actor_id=current_user.id,
        content_type="loan_request",
        content_id=req.id,
    )
    await db.commit()
    await db.refresh(req, attribute_names=["lender", "borrower"])
    return req


@router.put("/loan-requests/{request_id}/reject", response_model=LoanRequestOut)
async def reject_request(
    request_id: uuid.UUID,
    payload: LoanRequestReject,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoanRequest:
    result = await db.execute(
        select(LoanRequest)
        .where(LoanRequest.id == request_id, LoanRequest.lender_id == current_user.id)
        .options(*_LOAN_REQUEST_OPTS)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already {req.status}")

    req.status = "rejected"
    req.rejected_reason = payload.reason

    await create_notification(
        db,
        user_id=req.borrower_id,
        type="loan_request_rejected",
        title=f"{current_user.name} đã từ chối yêu cầu mượn sách",
        body=payload.reason,
        actor_id=current_user.id,
        content_type="loan_request",
        content_id=req.id,
    )
    await db.commit()
    await db.refresh(req, attribute_names=["lender", "borrower"])
    return req


@router.delete("/loan-requests/{request_id}", status_code=204)
async def cancel_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(LoanRequest).where(
            LoanRequest.id == request_id,
            LoanRequest.borrower_id == current_user.id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="Can only cancel pending requests")

    req.status = "cancelled"
    await db.commit()


# ---------------------------------------------------------------------------
# Active Loans
# ---------------------------------------------------------------------------

@router.get("/loans", response_model=list[LoanOut])
async def list_loans(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Loan]:
    stmt = (
        select(Loan)
        .where(
            (Loan.lender_id == current_user.id) | (Loan.borrower_id == current_user.id)
        )
        .options(*_LOAN_OPTS)
        .order_by(Loan.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(Loan.status == status_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.put("/loans/{loan_request_id}/confirm", response_model=LoanOut, status_code=201)
async def confirm_handover(
    loan_request_id: uuid.UUID,
    due_days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Loan:
    """Lender confirms they handed over the book — creates the Loan record."""
    result = await db.execute(
        select(LoanRequest).where(
            LoanRequest.id == loan_request_id,
            LoanRequest.lender_id == current_user.id,
            LoanRequest.status == "approved",
        ).options(*_LOAN_REQUEST_OPTS)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Approved request not found")

    # Check no existing loan for this request
    dup = await db.execute(select(Loan).where(Loan.loan_request_id == req.id))
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Loan already confirmed")

    today = date.today()
    loan = Loan(
        loan_request_id=req.id,
        user_book_id=req.user_book_id,
        lender_id=req.lender_id,
        borrower_id=req.borrower_id,
        lent_at=today,
        due_at=today + timedelta(days=due_days),
        status="active",
    )
    db.add(loan)
    req.status = "confirmed"  # type: ignore[assignment]
    await db.flush()

    await create_notification(
        db,
        user_id=req.borrower_id,
        type="loan_confirmed",
        title=f"Sách đã được giao — hẹn trả trước {loan.due_at}",
        body=f"Hạn trả: {loan.due_at}",
        actor_id=current_user.id,
        content_type="loan",
        content_id=loan.id,
    )
    await db.commit()

    result = await db.execute(
        select(Loan).where(Loan.id == loan.id).options(*_LOAN_OPTS)
    )
    return result.scalar_one()


@router.put("/loans/{loan_id}/return", response_model=LoanOut)
async def mark_returned(
    loan_id: uuid.UUID,
    note: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Loan:
    """Lender confirms book was returned."""
    result = await db.execute(
        select(Loan)
        .where(Loan.id == loan_id, Loan.lender_id == current_user.id, Loan.status == "active")
        .options(*_LOAN_OPTS)
    )
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Active loan not found")

    loan.status = "returned"
    loan.returned_at = date.today()
    loan.lender_note = note

    await create_notification(
        db,
        user_id=loan.borrower_id,
        type="loan_returned",
        title="Lender đã xác nhận nhận lại sách",
        actor_id=current_user.id,
        content_type="loan",
        content_id=loan.id,
    )
    await db.commit()
    await db.refresh(loan, attribute_names=["lender", "borrower"])
    return loan
