"""Calendario: fechas de los trabajos y el historial de reprogramaciones.

Los trabajos existentes (todos "por agendar") quedan sin fechas, que es lo que corresponde.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FECHAS_COHERENTES = (
    "(fecha_inicio IS NULL AND fecha_fin IS NULL) OR "
    "(fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL AND fecha_fin >= fecha_inicio)"
)


def upgrade() -> None:
    with op.batch_alter_table("trabajos") as batch:
        batch.add_column(sa.Column("fecha_inicio", sa.Date(), nullable=True))
        batch.add_column(sa.Column("fecha_fin", sa.Date(), nullable=True))
        batch.add_column(sa.Column("iniciado_en", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("terminado_en", sa.DateTime(), nullable=True))
        batch.create_check_constraint("ck_trabajo_fechas_coherentes", FECHAS_COHERENTES)

    op.create_table(
        "reprogramaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trabajo_id", sa.Integer(), sa.ForeignKey("trabajos.id"), nullable=False),
        sa.Column("fecha_inicio_anterior", sa.Date(), nullable=False),
        sa.Column("fecha_fin_anterior", sa.Date(), nullable=False),
        sa.Column("fecha_inicio_nueva", sa.Date(), nullable=False),
        sa.Column("fecha_fin_nueva", sa.Date(), nullable=False),
        sa.Column("causa", sa.String(20), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
    )
    op.create_index(op.f("ix_reprogramaciones_trabajo_id"), "reprogramaciones", ["trabajo_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_reprogramaciones_trabajo_id"), table_name="reprogramaciones")
    op.drop_table("reprogramaciones")

    with op.batch_alter_table("trabajos") as batch:
        batch.drop_constraint("ck_trabajo_fechas_coherentes", type_="check")
        batch.drop_column("terminado_en")
        batch.drop_column("iniciado_en")
        batch.drop_column("fecha_fin")
        batch.drop_column("fecha_inicio")
