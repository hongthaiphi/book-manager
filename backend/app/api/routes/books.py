"""
Books API:
  GET  /api/catalog/lookup/isbn/{isbn}   - lookup via Google Books
  GET  /api/catalog/search?q=            - search Google Books + internal DB
  POST /api/books                        - add book to my shelf
  GET  /api/books                        - list my books (filter/sort/search)
  GET  /api/books/{id}                   - book detail
  PUT  /api/books/{id}                   - update book info
  DELETE /api/books/{id}                 - remove from shelf
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.models import BookCatalog, User, UserBook
from app.db.session import get_db
from app.schemas.books import (
    BookLookupResult,
    UserBookCreate,
    UserBookOut,
    UserBookUpdate,
)
from app.services import google_books
from app.services.import_service import ImportResult, import_goodreads_csv

router = APIRouter()


# ---------------------------------------------------------------------------
# Catalog lookup (public, no auth needed for search)
# ---------------------------------------------------------------------------

@router.get("/catalog/lookup/isbn/{isbn}", response_model=BookLookupResult)
async def lookup_isbn(isbn: str) -> dict:
    result = await google_books.lookup_by_isbn(isbn)
    if not result:
        raise HTTPException(status_code=404, detail="Book not found for this ISBN")
    return result


@router.get("/catalog/search", response_model=list[BookLookupResult])
async def search_catalog(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=40),
) -> list[dict]:
    return await google_books.search_books(q, max_results=limit)


# ---------------------------------------------------------------------------
# User Books (auth required)
# ---------------------------------------------------------------------------

@router.post("/books", response_model=UserBookOut, status_code=status.HTTP_201_CREATED)
async def add_book(
    payload: UserBookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserBook:
    # Resolve catalog entry
    if payload.catalog_id:
        result = await db.execute(select(BookCatalog).where(BookCatalog.id == payload.catalog_id))
        catalog = result.scalar_one_or_none()
        if not catalog:
            raise HTTPException(status_code=404, detail="Catalog entry not found")
    else:
        # Create or get catalog entry by ISBN or title
        catalog = None
        if payload.isbn:
            result = await db.execute(select(BookCatalog).where(BookCatalog.isbn == payload.isbn))
            catalog = result.scalar_one_or_none()

        if not catalog:
            if not payload.title:
                raise HTTPException(status_code=422, detail="Provide catalog_id or title")
            catalog = BookCatalog(
                isbn=payload.isbn,
                title=payload.title,
                authors=payload.authors,
                publisher=payload.publisher,
                published_at=payload.published_at,
                cover_url=payload.cover_url,
                language=payload.language,
                page_count=payload.page_count,
                description=payload.description,
                genres=payload.genres,
                source=payload.source,
            )
            db.add(catalog)
            await db.flush()  # get catalog.id

    # Check duplicate
    dup = await db.execute(
        select(UserBook).where(UserBook.user_id == current_user.id, UserBook.catalog_id == catalog.id)
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Book already in your shelf")

    user_book = UserBook(
        user_id=current_user.id,
        catalog_id=catalog.id,
        status=payload.status,
        acquired_how=payload.acquired_how,
        gift_from=payload.gift_from,
        purchase_price=payload.purchase_price,
        purchase_where=payload.purchase_where,
        purchase_reason=payload.purchase_reason,
        personal_rating=payload.personal_rating,
        met_expectations=payload.met_expectations,
        personal_note=payload.personal_note,
        can_lend=payload.can_lend,
        deposit_amount=payload.deposit_amount,
        lend_note=payload.lend_note,
        tags=payload.tags,
        is_public=payload.is_public,
    )
    db.add(user_book)
    await db.commit()

    result = await db.execute(
        select(UserBook)
        .where(UserBook.id == user_book.id)
        .options(selectinload(UserBook.catalog))
    )
    return result.scalar_one()


@router.get("/books", response_model=list[UserBookOut])
async def list_books(
    status: Optional[str] = Query(None),
    can_lend: Optional[bool] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserBook]:
    stmt = (
        select(UserBook)
        .where(UserBook.user_id == current_user.id)
        .options(selectinload(UserBook.catalog))
        .limit(limit)
        .offset(offset)
    )
    if status:
        stmt = stmt.where(UserBook.status == status)
    if can_lend is not None:
        stmt = stmt.where(UserBook.can_lend == can_lend)
    if q:
        stmt = stmt.join(BookCatalog).where(
            or_(
                BookCatalog.title.ilike(f"%{q}%"),
                BookCatalog.authors.any(q),  # type: ignore[arg-type]
            )
        )

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/books/{book_id}", response_model=UserBookOut)
async def get_book(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserBook:
    result = await db.execute(
        select(UserBook)
        .where(UserBook.id == book_id, UserBook.user_id == current_user.id)
        .options(selectinload(UserBook.catalog))
    )
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/books/{book_id}", response_model=UserBookOut)
async def update_book(
    book_id: uuid.UUID,
    payload: UserBookUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserBook:
    result = await db.execute(
        select(UserBook)
        .where(UserBook.id == book_id, UserBook.user_id == current_user.id)
        .options(selectinload(UserBook.catalog))
    )
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(book, field, value)

    await db.commit()
    await db.refresh(book, attribute_names=["catalog"])
    return book


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(UserBook).where(UserBook.id == book_id, UserBook.user_id == current_user.id)
    )
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await db.delete(book)
    await db.commit()


# ---------------------------------------------------------------------------
# Goodreads CSV import
# ---------------------------------------------------------------------------

@router.post("/books/import/goodreads", response_model=ImportResult)
async def import_goodreads(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportResult:
    """
    Import books from a Goodreads library export CSV.
    Download your export at: https://www.goodreads.com/review/import
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only .csv files are accepted")

    MAX_SIZE = 5 * 1024 * 1024  # 5 MB
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    return await import_goodreads_csv(contents, current_user.id, db)
