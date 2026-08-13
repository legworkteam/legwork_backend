"""add avatar and try_on

Revision ID: 202608130002
Revises: 1938b1e76060
Create Date: 2026-08-13 12:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202608130002"
down_revision: str | None = "1938b1e76060"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "avatar",
        sa.Column("userId", sa.Uuid(), nullable=False),
        sa.Column("heightCm", sa.Numeric(), nullable=False),
        sa.Column("weightKg", sa.Numeric(), nullable=False),
        sa.Column("gender", sa.Enum("female", "male", "neutral", name="gender", create_type=False), nullable=False),
        sa.Column("previewFileId", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"heightCm" >= 100 AND "heightCm" <= 230', name="ck_avatar_height_range"),
        sa.CheckConstraint('"weightKg" >= 30 AND "weightKg" <= 200', name="ck_avatar_weight_range"),
        sa.ForeignKeyConstraint(["userId"], ["user.id"], name=op.f("fk_avatar_userId_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_avatar")),
        sa.UniqueConstraint("userId", name="uq_avatar_userId"),
    )
    op.create_index("ix_avatar_previewFileId", "avatar", ["previewFileId"], unique=False)

    op.create_table(
        "tryOn",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("userId", sa.Uuid(), nullable=True),
        sa.Column("guestSessionId", sa.Uuid(), nullable=True),
        sa.Column("jobId", sa.Uuid(), nullable=False),
        sa.Column(
            "scope",
            sa.Enum("productOnly", "fullCoordi", name="try_on_scope"),
            nullable=False,
        ),
        sa.Column("productId", sa.Uuid(), nullable=True),
        sa.Column("savedCoordiId", sa.Uuid(), nullable=True),
        sa.Column("resultFileId", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            sa.Enum("mock", name="try_on_provider"),
            nullable=False,
        ),
        sa.Column("requestJson", sa.JSON(), nullable=True),
        sa.Column("savedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            '(("userId" IS NOT NULL AND "guestSessionId" IS NULL) OR ("userId" IS NULL AND "guestSessionId" IS NOT NULL))',
            name=op.f("ck_tryOn_try_on_owner_xor"),
        ),
        sa.ForeignKeyConstraint(["guestSessionId"], ["guestSession.id"], name=op.f("fk_tryOn_guestSessionId_guestSession"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["jobId"], ["job.id"], name=op.f("fk_tryOn_jobId_job"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["productId"], ["product.id"], name=op.f("fk_tryOn_productId_product")),
        sa.ForeignKeyConstraint(["userId"], ["user.id"], name=op.f("fk_tryOn_userId_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tryOn")),
        sa.UniqueConstraint("jobId", name=op.f("uq_tryOn_jobId")),
    )
    op.create_index("ix_tryOn_userId_createdAt", "tryOn", ["userId", "createdAt"], unique=False)
    op.create_index("ix_tryOn_guestSessionId_createdAt", "tryOn", ["guestSessionId", "createdAt"], unique=False)
    op.create_index("ix_tryOn_savedAt", "tryOn", ["savedAt"], unique=False)
    op.create_index("ix_tryOn_expiresAt", "tryOn", ["expiresAt"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tryOn_expiresAt", table_name="tryOn")
    op.drop_index("ix_tryOn_savedAt", table_name="tryOn")
    op.drop_index("ix_tryOn_guestSessionId_createdAt", table_name="tryOn")
    op.drop_index("ix_tryOn_userId_createdAt", table_name="tryOn")
    op.drop_table("tryOn")

    op.drop_index("ix_avatar_previewFileId", table_name="avatar")
    op.drop_table("avatar")

    sa.Enum(name="try_on_provider").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="try_on_scope").drop(op.get_bind(), checkfirst=True)
