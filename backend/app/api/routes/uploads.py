"""
Image upload endpoints:
  POST /api/uploads/book-cover  — upload book cover, returns URL
  POST /api/uploads/avatar      — upload user avatar, returns URL + updates user record
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models import User, UserBook
from app.db.session import get_db
from app.services.storage import upload_avatar, upload_book_cover

router = APIRouter()


@router.post("/uploads/book-cover")
async def upload_cover(
    file: UploadFile,
    book_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    content_type = file.content_type or "image/jpeg"
    file_bytes = await file.read()

    try:
        url = await upload_book_cover(file_bytes, content_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Optionally link to a user_book
    if book_id:
        result = await db.execute(
            select(UserBook).where(UserBook.id == book_id, UserBook.user_id == current_user.id)
        )
        book = result.scalar_one_or_none()
        if book:
            book.physical_cover_url = url
            await db.commit()

    return {"url": url}


@router.post("/uploads/avatar")
async def upload_user_avatar(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    content_type = file.content_type or "image/jpeg"
    file_bytes = await file.read()

    try:
        url = await upload_avatar(file_bytes, content_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    current_user.avatar_url = url
    await db.commit()

    return {"url": url}
