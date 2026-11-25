"""Usuarios con rol (dueño | empleado), que reemplazan la clave de acceso compartida.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("usuario", sa.String(40), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("version_sesion", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
    )
    op.create_index(op.f("ix_usuarios_usuario"), "usuarios", ["usuario"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_usuarios_usuario"), table_name="usuarios")
    op.drop_table("usuarios")
