from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RateRequest(BaseModel):
    is_positive: bool
    note: Optional[str] = None
    block_user: bool = False


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    loan_id: uuid.UUID
    lender_id: uuid.UUID
    borrower_id: uuid.UUID
    is_positive: bool
    note: Optional[str] = None
    created_at: datetime


class BlacklistCreate(BaseModel):
    blocked_user_id: uuid.UUID
    reason: Optional[str] = None


class BlacklistEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    lender_id: uuid.UUID
    blocked_user_id: uuid.UUID
    reason: Optional[str] = None
    created_at: datetime
    blocked_user_name: str
    blocked_user_avatar: Optional[str] = None
