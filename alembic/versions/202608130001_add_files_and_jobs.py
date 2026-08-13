"""add files and jobs

Revision ID: 202608130001
Revises:
Create Date: 2026-08-13 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202608130001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fileMetadata",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ownerType", sa.Enum("guest", "user", "product", "system", name="file_owner_type"), nullable=False),
        sa.Column("ownerId", sa.Uuid(), nullable=True),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("originalName", sa.String(length=255), nullable=False),
        sa.Column("contentType", sa.String(length=100), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("visibility", sa.Enum("private", "public", name="file_visibility"), nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fileMetadata")),
    )
    op.create_index("ix_fileMetadata_expiresAt", "fileMetadata", ["expiresAt"], unique=False)
    op.create_index("ix_fileMetadata_ownerType_ownerId", "fileMetadata", ["ownerType", "ownerId"], unique=False)

    op.create_table(
        "job",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("userId", sa.Uuid(), nullable=True),
        sa.Column("guestSessionId", sa.Uuid(), nullable=True),
        sa.Column("type", sa.Enum("avatarTryOn", "photoTryOn", "diagnosis", name="job_type"), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "succeeded", "failed", name="job_status"), nullable=False),
        sa.Column("progress", sa.SmallInteger(), nullable=False),
        sa.Column("resultJson", sa.JSON(), nullable=True),
        sa.Column("errorJson", sa.JSON(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            '(("userId" IS NOT NULL AND "guestSessionId" IS NULL) OR ("userId" IS NULL AND "guestSessionId" IS NOT NULL))',
            name=op.f("ck_job_job_owner_xor"),
        ),
        sa.CheckConstraint('"progress" >= 0 AND "progress" <= 100', name=op.f("ck_job_job_progress_range")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job")),
    )
    op.create_index("ix_job_expiresAt", "job", ["expiresAt"], unique=False)
    op.create_index("ix_job_guestSessionId_createdAt", "job", ["guestSessionId", "createdAt"], unique=False)
    op.create_index("ix_job_userId_createdAt", "job", ["userId", "createdAt"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_userId_createdAt", table_name="job")
    op.drop_index("ix_job_guestSessionId_createdAt", table_name="job")
    op.drop_index("ix_job_expiresAt", table_name="job")
    op.drop_table("job")

    op.drop_index("ix_fileMetadata_ownerType_ownerId", table_name="fileMetadata")
    op.drop_index("ix_fileMetadata_expiresAt", table_name="fileMetadata")
    op.drop_table("fileMetadata")

    sa.Enum(name="job_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="job_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="file_visibility").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="file_owner_type").drop(op.get_bind(), checkfirst=True)
