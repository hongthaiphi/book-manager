"""
Goodreads CSV import service.

Goodreads export columns (relevant ones):
  Book Id, Title, Author, Author l-f, Additional Authors,
  ISBN, ISBN13, My Rating, Average Rating,
  Publisher, Binding, Number of Pages, Year Published, Original Publication Year,
  Date Read, Date Added, Bookshelves, Bookshelves with positions,
  Exclusive Shelf, My Review, Spoiler, Private Notes, Read Count, Recommended For, Recommended By, Owned Copies

Shelf mapping:
  read          → "read"
  currently-reading → "reading"
  to-read       → "want_to_read"
  did-not-finish → "did_not_finish"
  (anything else) → "read" if Date Read else "want_to_read"

Rating mapping: 0 → None, 1-5 → personal_rating
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BookCatalog, UserBook

# ---------------------------------------------------------------------------
# Goodreads shelf → our status
# ---------------------------------------------------------------------------

_SHELF_MAP: dict[str, str] = {
    "read": "read",
    "currently-reading": "reading",
    "to-read": "want_to_read",
    "did-not-finish": "did_not_finish",
}


def _map_status(exclusive_shelf: str, bookshelves: str, date_read: str) -> str:
    shelf = exclusive_shelf.strip().lower()
    if shelf in _SHELF_MAP:
        return _SHELF_MAP[shelf]
    # Check bookshelves column for custom shelf names
    for s in bookshelves.split(","):
        s = s.strip().lower()
        if s in _SHELF_MAP:
            return _SHELF_MAP[s]
    # Fallback
    return "read" if date_read.strip() else "want_to_read"


def _parse_isbn(raw: str) -> Optional[str]:
    """Strip Goodreads '=""..."" wrapping and non-digits."""
    cleaned = re.sub(r'[^0-9X]', '', raw.upper())
    if len(cleaned) in (10, 13):
        return cleaned
    return None


def _parse_rating(raw: str) -> Optional[int]:
    try:
        r = int(raw.strip())
        return r if 1 <= r <= 5 else None
    except (ValueError, TypeError):
        return None


def _parse_date(raw: str) -> Optional[date]:
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return date.fromisoformat(raw.strip().replace("/", "-")) if "-" in raw else \
                   __import__("datetime").datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            pass
    return None


def _parse_pages(raw: str) -> Optional[int]:
    try:
        return int(raw.strip()) or None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core import function
# ---------------------------------------------------------------------------

async def import_goodreads_csv(
    csv_bytes: bytes,
    user_id,
    db: AsyncSession,
) -> ImportResult:
    result = ImportResult()

    try:
        text = csv_bytes.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        text = csv_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        result.errors.append("CSV appears empty or has no header row.")
        return result

    # Normalize field names (strip whitespace + lowercase for lookup)
    fieldnames_norm = [f.strip() for f in reader.fieldnames]

    def get(row: dict, *keys: str) -> str:
        for k in keys:
            v = row.get(k, "").strip()
            if v:
                return v
            # Try normalized
            for fn in fieldnames_norm:
                if fn.lower() == k.lower() and fn in row:
                    return row[fn].strip()
        return ""

    for i, raw_row in enumerate(reader, start=2):  # row 2+ (1 = header)
        # Re-key with stripped fieldnames to be safe
        row = {k.strip(): v for k, v in raw_row.items() if k}

        title = get(row, "Title", "title")
        if not title:
            result.errors.append(f"Row {i}: missing title, skipped.")
            result.skipped += 1
            continue

        # --- Resolve catalog ---
        isbn13_raw = get(row, "ISBN13", "isbn13")
        isbn_raw   = get(row, "ISBN",   "isbn")
        isbn13 = _parse_isbn(isbn13_raw)
        isbn10 = _parse_isbn(isbn_raw)
        isbn   = isbn13 or isbn10  # prefer ISBN-13

        catalog: Optional[BookCatalog] = None

        # Try by ISBN first
        if isbn:
            res = await db.execute(select(BookCatalog).where(BookCatalog.isbn == isbn))
            catalog = res.scalar_one_or_none()

        # Try by title + first author if no ISBN match
        if not catalog:
            author_raw = get(row, "Author", "author")
            res = await db.execute(
                select(BookCatalog).where(
                    BookCatalog.title == title,
                    BookCatalog.authors.contains([author_raw]) if author_raw else BookCatalog.title == title,  # type: ignore[arg-type]
                )
            )
            catalog = res.scalar_one_or_none()

        if not catalog:
            # Build authors list
            primary = get(row, "Author", "author")
            additional = get(row, "Additional Authors", "additional authors")
            authors = [a.strip() for a in ([primary] + additional.split(",")) if a.strip()]

            # Published year
            pub_year = get(row, "Original Publication Year", "Year Published", "year published")
            pub_date: Optional[date] = None
            if pub_year:
                try:
                    pub_date = date(int(pub_year), 1, 1)
                except ValueError:
                    pass

            catalog = BookCatalog(
                isbn=isbn,
                title=title,
                authors=authors if authors else None,
                publisher=get(row, "Publisher", "publisher") or None,
                published_at=pub_date,
                page_count=_parse_pages(get(row, "Number of Pages", "number of pages")),
                source="goodreads",
            )
            db.add(catalog)
            await db.flush()

        # --- Check duplicate user_book ---
        dup_res = await db.execute(
            select(UserBook).where(
                UserBook.user_id == user_id,
                UserBook.catalog_id == catalog.id,
            )
        )
        if dup_res.scalar_one_or_none():
            result.skipped += 1
            continue

        # --- Map fields ---
        exclusive_shelf = get(row, "Exclusive Shelf", "exclusive shelf")
        bookshelves     = get(row, "Bookshelves", "bookshelves")
        date_read_raw   = get(row, "Date Read", "date read")
        book_status     = _map_status(exclusive_shelf, bookshelves, date_read_raw)

        personal_rating = _parse_rating(get(row, "My Rating", "my rating"))

        user_book = UserBook(
            user_id=user_id,
            catalog_id=catalog.id,
            status=book_status,
            personal_rating=personal_rating,
            personal_note=get(row, "My Review", "my review") or None,
            acquired_how="bought",  # Goodreads doesn't track this
        )
        db.add(user_book)
        result.imported += 1

    try:
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        result.errors.append(f"Database error: {exc}")
        result.imported = 0

    return result
