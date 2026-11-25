"""Los importes pasan de Float a Numeric(14, 2): dinero con centavos exactos.

En Postgres los valores existentes se redondean a 2 decimales al convertirlos.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("presupuestos") as batch:
        batch.alter_column(
            "total",
            existing_type=sa.Float(),
            type_=sa.Numeric(14, 2),
            existing_nullable=False,
            postgresql_using="ROUND(total::numeric, 2)",
        )
    with op.batch_alter_table("items_presupuesto") as batch:
        batch.alter_column(
            "importe",
            existing_type=sa.Float(),
            type_=sa.Numeric(14, 2),
            existing_nullable=False,
            postgresql_using="ROUND(importe::numeric, 2)",
        )


def downgrade() -> None:
    with op.batch_alter_table("items_presupuesto") as batch:
        batch.alter_column(
            "importe",
            existing_type=sa.Numeric(14, 2),
            type_=sa.Float(),
            existing_nullable=False,
            postgresql_using="importe::double precision",
        )
    with op.batch_alter_table("presupuestos") as batch:
        batch.alter_column(
            "total",
            existing_type=sa.Numeric(14, 2),
            type_=sa.Float(),
            existing_nullable=False,
            postgresql_using="total::double precision",
        )
