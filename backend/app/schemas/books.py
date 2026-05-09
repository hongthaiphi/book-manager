from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# BookCatalog
# ---------------------------------------------------------------------------

class BookCatalogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    isbn: Optional[str] = None
    title: str
    authors: Optional[list[str]] = None
    publisher: Optional[str] = None
    published_at: Optional[date] = None
    cover_url: Optional[str] = None
    language: str
    page_count: Optional[int] = None
    description: Optional[str] = None
    genres: Optional[list[str]] = None
    source: Optional[str] = None


class BookLookupResult(BaseModel):
    """Result from Google Books API — not yet in DB."""
    google_books_id: Optional[str] = None
    isbn: Optional[str] = None
    title: str
    authors: list[str] = []
    publisher: Optional[str] = None
    published_at: Optional[date] = None
    cover_url: Optional[str] = None
    language: str = "vi"
    page_count: Optional[int] = None
    description: Optional[str] = None
    genres: list[str] = []
    source: str = "google_books"


# ---------------------------------------------------------------------------
# UserBook
# ---------------------------------------------------------------------------

class UserBookCreate(BaseModel):
    # Can provide either catalog_id (existing) or book metadata to create catalog entry
    catalog_id: Optional[uuid.UUID] = None

    # If catalog_id is None, provide book data
    isbn: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[list[str]] = None
    publisher: Optional[str] = None
    published_at: Optional[date] = None
    cover_url: Optional[str] = None
    language: str = "vi"
    page_count: Optional[int] = None
    description: Optional[str] = None
    genres: Optional[list[str]] = None
    source: str = "manual"

    # User book fields
    status: str = "want_to_read"
    acquired_how: Optional[str] = None
    gift_from: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    purchase_where: Optional[str] = None
    purchase_reason: Optional[str] = None
    personal_rating: Optional[int] = Field(None, ge=1, le=5)
    met_expectations: Optional[bool] = None
    personal_note: Optional[str] = None
    can_lend: bool = False
    deposit_amount: Decimal = Decimal("0")
    lend_note: Optional[str] = None
    tags: Optional[list[str]] = None
    is_public: bool = True


class UserBookUpdate(BaseModel):
    status: Optional[str] = None
    started_at: Optional[date] = None
    finished_at: Optional[date] = None
    acquired_how: Optional[str] = None
    gift_from: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    purchase_where: Optional[str] = None
    purchase_reason: Optional[str] = None
    personal_rating: Optional[int] = Field(None, ge=1, le=5)
    met_expectations: Optional[bool] = None
    personal_note: Optional[str] = None
    physical_cover_url: Optional[str] = None
    can_lend: Optional[bool] = None
    deposit_amount: Optional[Decimal] = None
    lend_note: Optional[str] = None
    tags: Optional[list[str]] = None
    is_public: Optional[bool] = None


class UserBookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    catalog: BookCatalogOut
    status: str
    started_at: Optional[date] = None
    finished_at: Optional[date] = None
    acquired_how: Optional[str] = None
    gift_from: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    purchase_where: Optional[str] = None
    purchase_reason: Optional[str] = None
    personal_rating: Optional[int] = None
    met_expectations: Optional[bool] = None
    personal_note: Optional[str] = None
    physical_cover_url: Optional[str] = None
    can_lend: bool
    deposit_amount: Decimal
    lend_note: Optional[str] = None
    tags: Optional[list[str]] = None
    is_public: bool
    created_at: datetime
    updated_at: datetime
