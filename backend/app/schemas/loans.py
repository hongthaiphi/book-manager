from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Loan Requests
# ---------------------------------------------------------------------------

class LoanRequestCreate(BaseModel):
    message: Optional[str] = None


class LoanRequestApprove(BaseModel):
    agreed_deposit: Decimal = Decimal("0")
    meet_location: str
    due_days: int = 14  # how many days the borrower gets


class LoanRequestReject(BaseModel):
    reason: Optional[str] = None


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    avatar_url: Optional[str] = None
    phone_verified: bool


class BookSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    cover_url: Optional[str] = None
    authors: Optional[list[str]] = None


class LoanRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_book_id: uuid.UUID
    lender_id: uuid.UUID
    borrower_id: uuid.UUID
    message: Optional[str] = None
    status: str
    agreed_deposit: Optional[Decimal] = None
    meet_location: Optional[str] = None
    agreed_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    lender: UserSummary
    borrower: UserSummary


# ---------------------------------------------------------------------------
# Loans
# ---------------------------------------------------------------------------

class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    loan_request_id: uuid.UUID
    user_book_id: uuid.UUID
    lender_id: uuid.UUID
    borrower_id: uuid.UUID
    lent_at: date
    due_at: Optional[date] = None
    returned_at: Optional[date] = None
    status: str
    lender_note: Optional[str] = None
    created_at: datetime
    lender: UserSummary
    borrower: UserSummary
