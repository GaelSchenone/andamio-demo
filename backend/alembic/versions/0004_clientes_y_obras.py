"""Clientes (casa | consorcio) y sus obras (direcciones).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("telefono", sa.String(40), nullable=False),
        sa.Column("notas", sa.Text(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "obras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("direccion", sa.String(300), nullable=False),
        sa.Column("referencia", sa.String(100), nullable=False),
        sa.Column("notas", sa.Text(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
    )
    op.create_index(op.f("ix_obras_cliente_id"), "obras", ["cliente_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_obras_cliente_id"), table_name="obras")
    op.drop_table("obras")
    op.drop_table("clientes")
