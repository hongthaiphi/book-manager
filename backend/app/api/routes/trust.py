"""
Trust system endpoints:
  POST   /api/loans/{id}/rate       — lender rates borrower after loan ends
  GET    /api/blacklist              — my blacklist
  POST   /api/blacklist              — block a user
  DELETE /api/blacklist/{user_id}   — unblock
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.models import BorrowerBlacklist, BorrowerRating, Loan, LoanRequest, User
from app.db.session import get_db
from app.schemas.trust import BlacklistCreate, BlacklistEntryOut, RateRequest, RatingOut

router = APIRouter(tags=["trust"])


# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------

@router.post("/loans/{loan_id}/rate", response_model=RatingOut, status_code=201)
async def rate_borrower(
    loan_id: uuid.UUID,
    payload: RateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BorrowerRating:
    result = await db.execute(
        select(Loan).where(Loan.id == loan_id, Loan.lender_id == current_user.id)
    )
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.status not in ("returned", "lost"):
        raise HTTPException(status_code=409, detail="Can only rate after loan is returned or lost")

    # Unique check
    existing = await db.execute(
        select(BorrowerRating).where(BorrowerRating.loan_id == loan_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already rated this loan")

    rating = BorrowerRating(
        loan_id=loan_id,
        lender_id=current_user.id,
        borrower_id=loan.borrower_id,
        is_positive=payload.is_positive,
        note=payload.note,
    )
    db.add(rating)

    # Optional block
    if payload.block_user:
        dup_bl = await db.execute(
            select(BorrowerBlacklist).where(
                BorrowerBlacklist.lender_id == current_user.id,
                BorrowerBlacklist.blocked_user_id == loan.borrower_id,
            )
        )
        if not dup_bl.scalar_one_or_none():
            bl = BorrowerBlacklist(
                lender_id=current_user.id,
                blocked_user_id=loan.borrower_id,
                reason=payload.note,
            )
            db.add(bl)
            # Cancel any pending requests from this user
            await db.execute(
                update(LoanRequest)
                .where(
                    LoanRequest.lender_id == current_user.id,
                    LoanRequest.borrower_id == loan.borrower_id,
                    LoanRequest.status == "pending",
                )
                .values(status="cancelled")
            )

    await db.commit()
    await db.refresh(rating)
    return rating


# ---------------------------------------------------------------------------
# Blacklist
# ---------------------------------------------------------------------------

@router.get("/blacklist", response_model=list[BlacklistEntryOut])
async def list_blacklist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(BorrowerBlacklist, User)
        .join(User, User.id == BorrowerBlacklist.blocked_user_id)
        .where(BorrowerBlacklist.lender_id == current_user.id)
        .order_by(BorrowerBlacklist.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": bl.id,
            "lender_id": bl.lender_id,
            "blocked_user_id": bl.blocked_user_id,
            "reason": bl.reason,
            "created_at": bl.created_at,
            "blocked_user_name": user.name,
            "blocked_user_avatar": user.avatar_url,
        }
        for bl, user in rows
    ]


@router.post("/blacklist", response_model=BlacklistEntryOut, status_code=201)
async def block_user(
    payload: BlacklistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if payload.blocked_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")

    dup = await db.execute(
        select(BorrowerBlacklist).where(
            BorrowerBlacklist.lender_id == current_user.id,
            BorrowerBlacklist.blocked_user_id == payload.blocked_user_id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already blocked")

    # Fetch blocked user for response
    user_result = await db.execute(select(User).where(User.id == payload.blocked_user_id))
    blocked_user = user_result.scalar_one_or_none()
    if not blocked_user:
        raise HTTPException(status_code=404, detail="User not found")

    bl = BorrowerBlacklist(
        lender_id=current_user.id,
        blocked_user_id=payload.blocked_user_id,
        reason=payload.reason,
    )
    db.add(bl)

    # Cancel pending requests from this user
    await db.execute(
        update(LoanRequest)
        .where(
            LoanRequest.lender_id == current_user.id,
            LoanRequest.borrower_id == payload.blocked_user_id,
            LoanRequest.status == "pending",
        )
        .values(status="cancelled")
    )
    await db.commit()
    await db.refresh(bl)

    return {
        "id": bl.id,
        "lender_id": bl.lender_id,
        "blocked_user_id": bl.blocked_user_id,
        "reason": bl.reason,
        "created_at": bl.created_at,
        "blocked_user_name": blocked_user.name,
        "blocked_user_avatar": blocked_user.avatar_url,
    }


@router.delete("/blacklist/{blocked_user_id}", status_code=204)
async def unblock_user(
    blocked_user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(BorrowerBlacklist).where(
            BorrowerBlacklist.lender_id == current_user.id,
            BorrowerBlacklist.blocked_user_id == blocked_user_id,
        )
    )
    bl = result.scalar_one_or_none()
    if not bl:
        raise HTTPException(status_code=404, detail="Not in blacklist")
    await db.delete(bl)
    await db.commit()
