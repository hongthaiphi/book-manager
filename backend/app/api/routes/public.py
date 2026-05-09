"""
Public profile endpoints (no auth required):
  GET /api/public/users/{slug}         — profile + stats
  GET /api/public/users/{slug}/books   — public books of this user
  PUT /api/profile/me                  — update own profile (slug, bio, is_public)
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.models import BookCatalog, Loan, User, UserBook
from app.db.session import get_db
from app.schemas.books import BookCatalogOut

router = APIRouter(tags=["public"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PublicBookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    catalog: BookCatalogOut
    status: str
    personal_rating: Optional[int] = None
    can_lend: bool
    deposit_amount: float
    tags: Optional[list[str]] = None


class PublicProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    avatar_url: Optional[str] = None
    profile_slug: Optional[str] = None
    bio: Optional[str] = None
    total_books: int
    books_read: int
    books_lending: int


class ProfileUpdate(BaseModel):
    profile_slug: Optional[str] = None
    bio: Optional[str] = None
    is_public: Optional[bool] = None
    name: Optional[str] = None


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@router.get("/public/users/{slug}", response_model=PublicProfileOut)
async def get_public_profile(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(User).where(User.profile_slug == slug))
    user = result.scalar_one_or_none()

    if not user or not user.is_public:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Stats
    books_result = await db.execute(
        select(func.count()).select_from(UserBook).where(UserBook.user_id == user.id, UserBook.is_public == True)  # noqa: E712
    )
    total_books = books_result.scalar() or 0

    read_result = await db.execute(
        select(func.count()).select_from(UserBook).where(
            UserBook.user_id == user.id,
            UserBook.status == "read",
            UserBook.is_public == True,  # noqa: E712
        )
    )
    books_read = read_result.scalar() or 0

    lending_result = await db.execute(
        select(func.count()).select_from(UserBook).where(
            UserBook.user_id == user.id,
            UserBook.can_lend == True,  # noqa: E712
            UserBook.is_public == True,  # noqa: E712
        )
    )
    books_lending = lending_result.scalar() or 0

    return {
        "id": user.id,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "profile_slug": user.profile_slug,
        "bio": user.bio,
        "total_books": total_books,
        "books_read": books_read,
        "books_lending": books_lending,
    }


@router.get("/public/users/{slug}/books", response_model=list[PublicBookOut])
async def get_public_books(
    slug: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[UserBook]:
    user_result = await db.execute(select(User).where(User.profile_slug == slug))
    user = user_result.scalar_one_or_none()

    if not user or not user.is_public:
        raise HTTPException(status_code=404, detail="Profile not found")

    stmt = (
        select(UserBook)
        .where(UserBook.user_id == user.id, UserBook.is_public == True)  # noqa: E712
        .options(selectinload(UserBook.catalog))
        .limit(limit)
        .offset(offset)
    )
    if status:
        stmt = stmt.where(UserBook.status == status)

    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Own profile management (auth required)
# ---------------------------------------------------------------------------

@router.put("/profile/me", response_model=PublicProfileOut)
async def update_own_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if payload.profile_slug is not None:
        # Check uniqueness
        slug = payload.profile_slug.lower().strip()
        existing = await db.execute(
            select(User).where(User.profile_slug == slug, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Slug already taken")
        current_user.profile_slug = slug

    if payload.bio is not None:
        current_user.bio = payload.bio
    if payload.is_public is not None:
        current_user.is_public = payload.is_public
    if payload.name is not None:
        current_user.name = payload.name

    await db.commit()
    await db.refresh(current_user)

    # Return stats too
    books_result = await db.execute(
        select(func.count()).select_from(UserBook).where(UserBook.user_id == current_user.id)
    )
    total_books = books_result.scalar() or 0

    read_result = await db.execute(
        select(func.count()).select_from(UserBook).where(
            UserBook.user_id == current_user.id, UserBook.status == "read"
        )
    )
    books_read = read_result.scalar() or 0

    lending_result = await db.execute(
        select(func.count()).select_from(UserBook).where(
            UserBook.user_id == current_user.id, UserBook.can_lend == True  # noqa: E712
        )
    )
    books_lending = lending_result.scalar() or 0

    return {
        "id": current_user.id,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
        "profile_slug": current_user.profile_slug,
        "bio": current_user.bio,
        "total_books": total_books,
        "books_read": books_read,
        "books_lending": books_lending,
    }
