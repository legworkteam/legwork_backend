"""add diagnosis and repairs

Revision ID: 202608130004
Revises: 202608130003
Create Date: 2026-08-13 18:10:00

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "202608130004"
down_revision: str | None = "202608130003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


diagnosis_provider = sa.Enum("mock", name="diagnosis_provider")
damage_severity = sa.Enum("low", "medium", "high", name="damage_severity")
repair_reservation_status = sa.Enum(
    "confirmed",
    "completed",
    "cancelled",
    name="repair_reservation_status",
)


def upgrade() -> None:
    op.create_table(
        "diagnosis",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("userId", sa.Uuid(), nullable=False),
        sa.Column("registeredProductId", sa.Uuid(), nullable=False),
        sa.Column("jobId", sa.Uuid(), nullable=False),
        sa.Column("sourceFileId", sa.Uuid(), nullable=False),
        sa.Column("provider", diagnosis_provider, nullable=False),
        sa.Column("repairNeeded", sa.Boolean(), nullable=False),
        sa.Column("overallCondition", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["jobId"], ["job.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registeredProductId"], ["registeredProduct.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["userId"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jobId"),
    )
    op.create_index("ix_diagnosis_userId_createdAt", "diagnosis", ["userId", "createdAt"], unique=False)
    op.create_index(
        "ix_diagnosis_registeredProductId_createdAt",
        "diagnosis",
        ["registeredProductId", "createdAt"],
        unique=False,
    )

    op.create_table(
        "damage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("diagnosisId", sa.Uuid(), nullable=False),
        sa.Column("damageType", sa.String(length=80), nullable=False),
        sa.Column("area", sa.String(length=80), nullable=False),
        sa.Column("severity", damage_severity, nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("repairNeeded", sa.Boolean(), nullable=False),
        sa.Column("sortOrder", sa.Integer(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["diagnosisId"], ["diagnosis.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_damage_diagnosisId_sortOrder", "damage", ["diagnosisId", "sortOrder"], unique=False)

    op.create_table(
        "repairReservation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("diagnosisId", sa.Uuid(), nullable=False),
        sa.Column("storeId", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", repair_reservation_status, nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("cancelledAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["diagnosisId"], ["diagnosis.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["storeId"], ["store.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repairReservation_diagnosisId_createdAt",
        "repairReservation",
        ["diagnosisId", "createdAt"],
        unique=False,
    )
    op.create_index(
        "ix_repairReservation_storeId_slot_status",
        "repairReservation",
        ["storeId", "slot", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_repairReservation_storeId_slot_status", table_name="repairReservation")
    op.drop_index("ix_repairReservation_diagnosisId_createdAt", table_name="repairReservation")
    op.drop_table("repairReservation")

    op.drop_index("ix_damage_diagnosisId_sortOrder", table_name="damage")
    op.drop_table("damage")

    op.drop_index("ix_diagnosis_registeredProductId_createdAt", table_name="diagnosis")
    op.drop_index("ix_diagnosis_userId_createdAt", table_name="diagnosis")
    op.drop_table("diagnosis")
