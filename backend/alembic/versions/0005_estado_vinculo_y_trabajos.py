"""Presupuestos con estado y vínculo opcional a cliente y obra, y los trabajos.

Los presupuestos que ya existen quedan como "borrador" y sin vínculo (siguen con su texto libre).
Un presupuesto tiene a lo sumo un trabajo vigente (no cancelado): lo garantiza un índice único
parcial.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOLO_VIGENTES = "estado != 'cancelado'"


def upgrade() -> None:
    with op.batch_alter_table("presupuestos") as batch:
        batch.add_column(
            sa.Column("estado", sa.String(20), nullable=False, server_default="borrador")
        )
        batch.add_column(sa.Column("cliente_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("obra_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_presupuestos_cliente_id", "clientes", ["cliente_id"], ["id"])
        batch.create_foreign_key("fk_presupuestos_obra_id", "obras", ["obra_id"], ["id"])
        batch.create_index(op.f("ix_presupuestos_cliente_id"), ["cliente_id"])
        batch.create_index(op.f("ix_presupuestos_obra_id"), ["obra_id"])

    op.create_table(
        "trabajos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("presupuesto_id", sa.Integer(), sa.ForeignKey("presupuestos.id"), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "uq_trabajo_vigente_por_presupuesto",
        "trabajos",
        ["presupuesto_id"],
        unique=True,
        sqlite_where=sa.text(SOLO_VIGENTES),
        postgresql_where=sa.text(SOLO_VIGENTES),
    )


def downgrade() -> None:
    op.drop_index("uq_trabajo_vigente_por_presupuesto", table_name="trabajos")
    op.drop_table("trabajos")

    with op.batch_alter_table("presupuestos") as batch:
        batch.drop_index(op.f("ix_presupuestos_obra_id"))
        batch.drop_index(op.f("ix_presupuestos_cliente_id"))
        batch.drop_constraint("fk_presupuestos_obra_id", type_="foreignkey")
        batch.drop_constraint("fk_presupuestos_cliente_id", type_="foreignkey")
        batch.drop_column("obra_id")
        batch.drop_column("cliente_id")
        batch.drop_column("estado")
