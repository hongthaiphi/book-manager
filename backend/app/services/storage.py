"""
Cloudinary image upload service.
"""

import cloudinary
import cloudinary.uploader

from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


async def upload_image(file_bytes: bytes, content_type: str, folder: str = "book-manager") -> str:
    """
    Upload image bytes to Cloudinary and return the secure URL.
    Raises ValueError for invalid file type or size.
    """
    if content_type not in ALLOWED_TYPES:
        raise ValueError(f"Invalid image type: {content_type}. Allowed: {ALLOWED_TYPES}")
    if len(file_bytes) > MAX_SIZE_BYTES:
        raise ValueError(f"File too large. Max size: {MAX_SIZE_BYTES // (1024*1024)} MB")

    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type="image",
        transformation=[
            {"width": 800, "crop": "limit"},
            {"quality": "auto:good"},
            {"fetch_format": "auto"},
        ],
    )
    return result["secure_url"]


async def upload_book_cover(file_bytes: bytes, content_type: str) -> str:
    return await upload_image(file_bytes, content_type, folder="book-manager/covers")


async def upload_avatar(file_bytes: bytes, content_type: str) -> str:
    return await upload_image(file_bytes, content_type, folder="book-manager/avatars")
