"""
Buildings / Community endpoints:
  POST /api/buildings              — create building + auto-join
  POST /api/buildings/join         — join by invite_code
  GET  /api/buildings/me           — my building info
  GET  /api/buildings/books        — lendable books in my building
  GET  /api/buildings/members      — members of my building
"""

import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.models import BookCatalog, Building, BorrowerBlacklist, Loan, User, UserBook
from app.db.session import get_db
from app.schemas.community import BuildingCreate, BuildingJoin, BuildingOut, CommunityBookOut, MemberOut

router = APIRouter(prefix="/buildings", tags=["community"])


def _gen_invite_code() -> str:
    return secrets.token_urlsafe(6)[:8].upper()


# ---------------------------------------------------------------------------
# Create building
# ---------------------------------------------------------------------------

@router.post("", response_model=BuildingOut, status_code=status.HTTP_201_CREATED)
async def create_building(
    payload: BuildingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Building:
    # Generate unique invite code
    for _ in range(5):
        code = _gen_invite_code()
        exists_result = await db.execute(select(Building).where(Building.invite_code == code))
        if not exists_result.scalar_one_or_none():
            break

    building = Building(name=payload.name, address=payload.address, invite_code=code)
    db.add(building)
    await db.flush()

    current_user.building_id = building.id
    await db.commit()
    await db.refresh(building)
    return building


# ---------------------------------------------------------------------------
# Join building
# ---------------------------------------------------------------------------

@router.post("/join", response_model=BuildingOut)
async def join_building(
    payload: BuildingJoin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Building:
    result = await db.execute(
        select(Building).where(Building.invite_code == payload.invite_code.upper())
    )
    building = result.scalar_one_or_none()
    if not building:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    current_user.building_id = building.id
    await db.commit()
    await db.refresh(building)
    return building


# ---------------------------------------------------------------------------
# My building info
# ---------------------------------------------------------------------------

@router.get("/me", response_model=BuildingOut)
async def my_building(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Building:
    if not current_user.building_id:
        raise HTTPException(status_code=404, detail="You are not in any building")
    result = await db.execute(select(Building).where(Building.id == current_user.building_id))
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Community books
# ---------------------------------------------------------------------------

@router.get("/books", response_model=list[CommunityBookOut])
async def community_books(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    if not current_user.building_id:
        raise HTTPException(status_code=403, detail="Join a building first")

    # Sub-query: has active loan?
    active_loan_sub = (
        select(Loan.user_book_id)
        .where(Loan.status == "active")
        .scalar_subquery()
    )

    stmt = (
        select(UserBook, User, BookCatalog)
        .join(User, User.id == UserBook.user_id)
        .join(BookCatalog, BookCatalog.id == UserBook.catalog_id)
        .where(
            UserBook.can_lend == True,  # noqa: E712
            UserBook.user_id != current_user.id,
            User.building_id == current_user.building_id,
            UserBook.id.not_in(active_loan_sub),
        )
        .order_by(UserBook.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )

    rows = (await db.execute(stmt)).all()

    # Fetch blacklist entries for current_user (lender → blocked current_user)
    bl_result = await db.execute(
        select(BorrowerBlacklist.lender_id).where(
            BorrowerBlacklist.blocked_user_id == current_user.id
        )
    )
    blocked_by: set[uuid.UUID] = {row[0] for row in bl_result.all()}

    books = []
    for user_book, owner, catalog in rows:
        books.append({
            "id": user_book.id,
            "owner_id": owner.id,
            "owner_name": owner.name,
            "owner_avatar": owner.avatar_url,
            "catalog_id": catalog.id,
            "title": catalog.title,
            "authors": catalog.authors,
            "cover_url": user_book.physical_cover_url or catalog.cover_url,
            "deposit_amount": float(user_book.deposit_amount),
            "lend_note": user_book.lend_note,
            "is_blocked": owner.id in blocked_by,
        })

    return books


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@router.get("/members", response_model=list[MemberOut])
async def building_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    if not current_user.building_id:
        raise HTTPException(status_code=403, detail="Join a building first")

    result = await db.execute(
        select(User)
        .where(User.building_id == current_user.building_id)
        .order_by(User.name)
    )
    return list(result.scalars().all())
