"""
Centralised helper for creating Notification records.
Used by loan routes, scheduler, and any other place that needs to notify users.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: str | None = None,
    actor_id: uuid.UUID | None = None,
    content_type: str | None = None,
    content_id: uuid.UUID | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        actor_id=actor_id,
        content_type=content_type,
        content_id=content_id,
    )
    db.add(notif)
    # Caller is responsible for commit
    return notif
