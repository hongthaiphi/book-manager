from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BuildingCreate(BaseModel):
    name: str
    address: Optional[str] = None


class BuildingJoin(BaseModel):
    invite_code: str


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    address: Optional[str] = None
    invite_code: Optional[str] = None
    created_at: datetime


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    avatar_url: Optional[str] = None
    profile_slug: Optional[str] = None
    phone_verified: bool


class CommunityBookOut(BaseModel):
    """A user_book available for borrowing in the community."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    owner_name: str
    owner_avatar: Optional[str]
    catalog_id: uuid.UUID
    title: str
    authors: Optional[list[str]]
    cover_url: Optional[str]
    deposit_amount: float
    lend_note: Optional[str]
    is_blocked: bool  # True if current_user is blacklisted by this lender
