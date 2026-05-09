from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------

class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    invite_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="building")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_slug: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    building_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    building: Mapped[Optional["Building"]] = relationship("Building", back_populates="users")
    user_books: Mapped[list["UserBook"]] = relationship("UserBook", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user")
    loans_as_lender: Mapped[list["Loan"]] = relationship("Loan", foreign_keys="Loan.lender_id", back_populates="lender")
    loans_as_borrower: Mapped[list["Loan"]] = relationship("Loan", foreign_keys="Loan.borrower_id", back_populates="borrower")
    blacklist_entries: Mapped[list["BorrowerBlacklist"]] = relationship("BorrowerBlacklist", foreign_keys="BorrowerBlacklist.lender_id", back_populates="lender")


# ---------------------------------------------------------------------------
# Book Catalog
# ---------------------------------------------------------------------------

class BookCatalog(Base):
    __tablename__ = "book_catalog"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isbn: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    published_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cover_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="vi")
    page_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    genres: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(100)), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'google_books' | 'manual'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    user_books: Mapped[list["UserBook"]] = relationship("UserBook", back_populates="catalog")


# ---------------------------------------------------------------------------
# User Books
# ---------------------------------------------------------------------------

class UserBook(Base):
    __tablename__ = "user_books"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    catalog_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_catalog.id"), nullable=False)

    # Reading status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="want_to_read")
    # 'want_to_read' | 'reading' | 'read' | 'did_not_finish'
    started_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    finished_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Acquisition info
    acquired_how: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'bought' | 'gift' | 'other'
    gift_from: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purchase_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    purchase_where: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    purchase_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Personal review (private)
    personal_rating: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    met_expectations: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    personal_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Physical cover
    physical_cover_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Lending
    can_lend: Mapped[bool] = mapped_column(Boolean, default=False)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    lend_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(50)), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "catalog_id", name="uq_user_catalog"),
        CheckConstraint("personal_rating BETWEEN 1 AND 5", name="ck_personal_rating_range"),
    )

    # relationships
    user: Mapped["User"] = relationship("User", back_populates="user_books")
    catalog: Mapped["BookCatalog"] = relationship("BookCatalog", back_populates="user_books")
    loan_requests: Mapped[list["LoanRequest"]] = relationship("LoanRequest", back_populates="user_book", cascade="all, delete-orphan")
    loans: Mapped[list["Loan"]] = relationship("Loan", back_populates="user_book", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Loan Requests
# ---------------------------------------------------------------------------

class LoanRequest(Base):
    __tablename__ = "loan_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_books.id", ondelete="CASCADE"), nullable=False)
    lender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    borrower_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # 'pending' | 'approved' | 'rejected' | 'cancelled'

    agreed_deposit: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    meet_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agreed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    user_book: Mapped["UserBook"] = relationship("UserBook", back_populates="loan_requests")
    lender: Mapped["User"] = relationship("User", foreign_keys=[lender_id])
    borrower: Mapped["User"] = relationship("User", foreign_keys=[borrower_id])
    loan: Mapped[Optional["Loan"]] = relationship("Loan", back_populates="loan_request", uselist=False)


# ---------------------------------------------------------------------------
# Loans
# ---------------------------------------------------------------------------

class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("loan_requests.id"), nullable=False)
    user_book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_books.id", ondelete="CASCADE"), nullable=False)
    lender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    borrower_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    lent_at: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    due_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    returned_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="active")
    # 'active' | 'returned' | 'overdue' | 'lost'

    lender_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    loan_request: Mapped["LoanRequest"] = relationship("LoanRequest", back_populates="loan")
    user_book: Mapped["UserBook"] = relationship("UserBook", back_populates="loans")
    lender: Mapped["User"] = relationship("User", foreign_keys=[lender_id], back_populates="loans_as_lender")
    borrower: Mapped["User"] = relationship("User", foreign_keys=[borrower_id], back_populates="loans_as_borrower")
    rating: Mapped[Optional["BorrowerRating"]] = relationship("BorrowerRating", back_populates="loan", uselist=False)


# ---------------------------------------------------------------------------
# Borrower Ratings
# ---------------------------------------------------------------------------

class BorrowerRating(Base):
    __tablename__ = "borrower_ratings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("loans.id"), nullable=False, unique=True)
    lender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    borrower_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_positive: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    loan: Mapped["Loan"] = relationship("Loan", back_populates="rating")
    lender: Mapped["User"] = relationship("User", foreign_keys=[lender_id])
    borrower: Mapped["User"] = relationship("User", foreign_keys=[borrower_id])


# ---------------------------------------------------------------------------
# Borrower Blacklist
# ---------------------------------------------------------------------------

class BorrowerBlacklist(Base):
    __tablename__ = "borrower_blacklist"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    blocked_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("lender_id", "blocked_user_id", name="uq_blacklist"),
        CheckConstraint("lender_id != blocked_user_id", name="ck_no_self_block"),
    )

    # relationships
    lender: Mapped["User"] = relationship("User", foreign_keys=[lender_id], back_populates="blacklist_entries")
    blocked_user: Mapped["User"] = relationship("User", foreign_keys=[blocked_user_id])


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # 'loan_request_received' | 'loan_request_approved' | 'loan_request_rejected'
    # | 'loan_due_soon' | 'loan_overdue'
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'loan_request' | 'loan'
    content_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_id])


# ---------------------------------------------------------------------------
# Phone OTPs
# ---------------------------------------------------------------------------

class PhoneOTP(Base):
    __tablename__ = "phone_otps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
