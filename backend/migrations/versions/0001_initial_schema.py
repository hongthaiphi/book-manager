"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-09 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── buildings ───────────────────────────────────────────────────────────
    op.create_table(
        "buildings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("invite_code", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code"),
    )

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("google_sub", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("profile_slug", sa.String(50), nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_sub"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("profile_slug"),
    )

    # ── phone_otps ───────────────────────────────────────────────────────────
    op.create_table(
        "phone_otps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("otp_hash", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── book_catalog ─────────────────────────────────────────────────────────
    op.create_table(
        "book_catalog",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("isbn", sa.String(20), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("authors", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("publisher", sa.String(200), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="vi"),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("genres", postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("isbn"),
    )

    # ── user_books ───────────────────────────────────────────────────────────
    op.create_table(
        "user_books",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("catalog_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="want_to_read"),
        sa.Column("started_at", sa.Date(), nullable=True),
        sa.Column("finished_at", sa.Date(), nullable=True),
        sa.Column("acquired_how", sa.String(20), nullable=True, server_default="bought"),
        sa.Column("gift_from", sa.String(100), nullable=True),
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("purchase_where", sa.String(200), nullable=True),
        sa.Column("purchase_reason", sa.Text, nullable=True),
        sa.Column("personal_rating", sa.SmallInteger(), nullable=True),
        sa.Column("met_expectations", sa.Boolean(), nullable=True),
        sa.Column("personal_note", sa.Text, nullable=True),
        sa.Column("physical_cover_url", sa.String(500), nullable=True),
        sa.Column("can_lend", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deposit_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("lend_note", sa.Text, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(50)), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("personal_rating >= 1 AND personal_rating <= 5", name="rating_range"),
        sa.ForeignKeyConstraint(["catalog_id"], ["book_catalog.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "catalog_id", name="uq_user_catalog"),
    )

    # ── loan_requests ────────────────────────────────────────────────────────
    op.create_table(
        "loan_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_book_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("borrower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["borrower_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["lender_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_book_id"], ["user_books.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── loans ────────────────────────────────────────────────────────────────
    op.create_table(
        "loans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("loan_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_book_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("borrower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["borrower_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["lender_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["loan_request_id"], ["loan_requests.id"]),
        sa.ForeignKeyConstraint(["user_book_id"], ["user_books.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── borrower_ratings ─────────────────────────────────────────────────────
    op.create_table(
        "borrower_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rater_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rated_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_positive", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"]),
        sa.ForeignKeyConstraint(["rated_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rater_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("loan_id", "rater_id", name="uq_loan_rater"),
    )

    # ── borrower_blacklist ───────────────────────────────────────────────────
    op.create_table(
        "borrower_blacklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("borrower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["borrower_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["lender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lender_id", "borrower_id", name="uq_blacklist"),
    )

    # ── notifications ────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("borrower_blacklist")
    op.drop_table("borrower_ratings")
    op.drop_table("loans")
    op.drop_table("loan_requests")
    op.drop_table("user_books")
    op.drop_table("book_catalog")
    op.drop_table("phone_otps")
    op.drop_table("users")
    op.drop_table("buildings")
