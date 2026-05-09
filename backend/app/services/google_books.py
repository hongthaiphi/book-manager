"""
Google Books API service.
Docs: https://developers.google.com/books/docs/v1/reference/volumes/list
"""

from datetime import date
from typing import Any

import httpx

from app.core.config import settings

BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"


def _parse_volume(volume: dict) -> dict:
    """Normalise a Google Books volume into our schema format."""
    info = volume.get("volumeInfo", {})

    # Parse published date — may be "2020", "2020-05", or "2020-05-12"
    published_at: date | None = None
    raw_date = info.get("publishedDate", "")
    if raw_date:
        parts = raw_date.split("-")
        try:
            if len(parts) == 3:
                published_at = date(int(parts[0]), int(parts[1]), int(parts[2]))
            elif len(parts) == 2:
                published_at = date(int(parts[0]), int(parts[1]), 1)
            else:
                published_at = date(int(parts[0]), 1, 1)
        except (ValueError, IndexError):
            published_at = None

    # Extract ISBN-13 preferably, fall back to ISBN-10
    isbn: str | None = None
    for identifier in info.get("industryIdentifiers", []):
        if identifier.get("type") == "ISBN_13":
            isbn = identifier["identifier"]
            break
    if not isbn:
        for identifier in info.get("industryIdentifiers", []):
            if identifier.get("type") == "ISBN_10":
                isbn = identifier["identifier"]
                break

    # Cover image (prefer extraLarge → large → thumbnail)
    image_links = info.get("imageLinks", {})
    cover_url = (
        image_links.get("extraLarge")
        or image_links.get("large")
        or image_links.get("medium")
        or image_links.get("thumbnail")
    )
    # Remove Google's zoom/curl parameters for cleaner URL
    if cover_url:
        cover_url = cover_url.replace("&edge=curl", "").replace("http://", "https://")

    return {
        "google_books_id": volume.get("id"),
        "isbn": isbn,
        "title": info.get("title", "Unknown Title"),
        "authors": info.get("authors", []),
        "publisher": info.get("publisher"),
        "published_at": published_at,
        "cover_url": cover_url,
        "language": info.get("language", "vi"),
        "page_count": info.get("pageCount"),
        "description": info.get("description"),
        "genres": info.get("categories", []),
        "source": "google_books",
    }


async def lookup_by_isbn(isbn: str) -> dict | None:
    """Return first match for a given ISBN, or None if not found."""
    params: dict[str, Any] = {"q": f"isbn:{isbn}", "maxResults": 1}
    if settings.GOOGLE_BOOKS_API_KEY:
        params["key"] = settings.GOOGLE_BOOKS_API_KEY

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(BOOKS_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    items = data.get("items", [])
    if not items:
        return None
    return _parse_volume(items[0])


async def search_books(query: str, max_results: int = 10) -> list[dict]:
    """Full-text search against Google Books API."""
    params: dict[str, Any] = {"q": query, "maxResults": min(max_results, 40)}
    if settings.GOOGLE_BOOKS_API_KEY:
        params["key"] = settings.GOOGLE_BOOKS_API_KEY

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(BOOKS_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    return [_parse_volume(item) for item in data.get("items", [])]
