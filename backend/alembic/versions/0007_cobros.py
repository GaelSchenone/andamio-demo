"""Cobros: los pagos (seña y saldo) recibidos por cada trabajo.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cobros",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trabajo_id", sa.Integer(), sa.ForeignKey("trabajos.id"), nullable=False),
        sa.Column("concepto", sa.String(10), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("nota", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("anulado_en", sa.DateTime(), nullable=True),
        sa.Column("anulado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.CheckConstraint("monto > 0", name="ck_cobro_monto_positivo"),
    )
    op.create_index(op.f("ix_cobros_trabajo_id"), "cobros", ["trabajo_id"])


def downgrade() -> None:
    # Sin la tabla de cobros no hay forma de saber si un trabajo está pagado: los "cobrado"
    # vuelven a "terminado", que es el estado anterior a que existieran los cobros.
    op.execute("UPDATE trabajos SET estado = 'terminado' WHERE estado = 'cobrado'")
    op.drop_index(op.f("ix_cobros_trabajo_id"), table_name="cobros")
    op.drop_table("cobros")
