"""
Notification endpoints:
  GET /api/notifications              — latest 50 notifications
  PUT /api/notifications/{id}/read    — mark single read
  PUT /api/notifications/read-all     — mark all read
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models import Notification, User
from app.db.session import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    body: str | None = None
    actor_id: uuid.UUID | None = None
    content_type: str | None = None
    content_id: uuid.UUID | None = None
    is_read: bool
    created_at: str  # ISO string — simpler for frontend

    @classmethod
    def from_orm_dt(cls, obj: Notification) -> "NotificationOut":
        return cls(
            id=obj.id,
            type=obj.type,
            title=obj.title,
            body=obj.body,
            actor_id=obj.actor_id,
            content_type=obj.content_type,
            content_id=obj.content_id,
            is_read=obj.is_read,
            created_at=obj.created_at.isoformat(),
        )


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationOut]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return [NotificationOut.from_orm_dt(n) for n in result.scalars().all()]


@router.put("/read-all", response_model=dict)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}


@router.put("/{notification_id}/read", response_model=dict)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    return {"message": "Marked as read"}
