"""Esquema base: presupuestos e items_presupuesto, tal como lo creaba create_all.

Es "idempotente" a propósito: si la base ya fue creada por la versión anterior de la app
(sin Alembic), las tablas existen y no se tocan; si la base es nueva, se crean.

Revision ID: 0001
Revises:
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existentes = set(sa.inspect(op.get_bind()).get_table_names())

    if "presupuestos" not in existentes:
        op.create_table(
            "presupuestos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cliente_obra", sa.String(200), nullable=False),
            sa.Column("direccion", sa.String(300), nullable=False),
            sa.Column("fecha_emision", sa.Date(), nullable=False),
            sa.Column("vigencia_dias", sa.Integer(), nullable=False),
            sa.Column("plazo_obra", sa.String(200), nullable=False),
            sa.Column("forma_pago", sa.String(300), nullable=False),
            sa.Column("materiales_a_cargo", sa.String(100), nullable=False),
            sa.Column("observaciones", sa.Text(), nullable=False),
            sa.Column("total", sa.Float(), nullable=False),
            sa.Column("creado_en", sa.DateTime(), nullable=False),
        )

    if "items_presupuesto" not in existentes:
        op.create_table(
            "items_presupuesto",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "presupuesto_id", sa.Integer(), sa.ForeignKey("presupuestos.id"), nullable=False
            ),
            sa.Column("orden", sa.Integer(), nullable=False),
            sa.Column("descripcion", sa.String(500), nullable=False),
            sa.Column("unidad", sa.String(50), nullable=False),
            sa.Column("cantidad", sa.Float(), nullable=False),
            sa.Column("importe", sa.Float(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("items_presupuesto")
    op.drop_table("presupuestos")
