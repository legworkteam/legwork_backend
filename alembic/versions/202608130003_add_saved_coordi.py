"""add saved coordi

Revision ID: 202608130003
Revises: 202608130002
Create Date: 2026-08-13 13:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202608130003"
down_revision: str | None = "202608130002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "savedCoordi",
        sa.Column("userId", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("thumbnailFileId", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deletedAt", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["userId"], ["user.id"], name=op.f("fk_savedCoordi_userId_user"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_savedCoordi")),
    )
    op.create_index(
        "ix_savedCoordi_userId_deletedAt_createdAt",
        "savedCoordi",
        ["userId", "deletedAt", "createdAt"],
        unique=False,
    )

    op.create_table(
        "savedCoordiItem",
        sa.Column("savedCoordiId", sa.Uuid(), nullable=False),
        sa.Column("productId", sa.Uuid(), nullable=False),
        sa.Column("variantId", sa.Uuid(), nullable=True),
        sa.Column("sortOrder", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["productId"], ["product.id"], name=op.f("fk_savedCoordiItem_productId_product")),
        sa.ForeignKeyConstraint(["savedCoordiId"], ["savedCoordi.id"], name=op.f("fk_savedCoordiItem_savedCoordiId_savedCoordi"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variantId"], ["productVariant.id"], name=op.f("fk_savedCoordiItem_variantId_productVariant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_savedCoordiItem")),
    )
    op.create_index(
        "ix_savedCoordiItem_savedCoordiId_sortOrder",
        "savedCoordiItem",
        ["savedCoordiId", "sortOrder"],
        unique=False,
    )

    op.create_foreign_key(
        op.f("fk_tryOn_savedCoordiId_savedCoordi"),
        "tryOn",
        "savedCoordi",
        ["savedCoordiId"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_tryOn_savedCoordiId_savedCoordi"), "tryOn", type_="foreignkey")
    op.drop_index("ix_savedCoordiItem_savedCoordiId_sortOrder", table_name="savedCoordiItem")
    op.drop_table("savedCoordiItem")
    op.drop_index("ix_savedCoordi_userId_deletedAt_createdAt", table_name="savedCoordi")
    op.drop_table("savedCoordi")
