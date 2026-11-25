"""Trabajos que no son de corrido: los días del tramo en los que no se trabaja.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Sin filas, un trabajo ocupa todo su tramo: los trabajos que ya existen no cambian.
    op.create_table(
        "trabajo_dias_sin_trabajo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trabajo_id", sa.Integer(), sa.ForeignKey("trabajos.id"), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.UniqueConstraint("trabajo_id", "fecha", name="uq_dia_sin_trabajo"),
    )
    op.create_index(
        op.f("ix_trabajo_dias_sin_trabajo_trabajo_id"), "trabajo_dias_sin_trabajo", ["trabajo_id"]
    )


def downgrade() -> None:
    # Al volver atrás, los trabajos con huecos pasan a ocupar todo su tramo (de corrido).
    op.drop_index(
        op.f("ix_trabajo_dias_sin_trabajo_trabajo_id"), table_name="trabajo_dias_sin_trabajo"
    )
    op.drop_table("trabajo_dias_sin_trabajo")
