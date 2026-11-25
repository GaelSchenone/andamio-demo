"""Corre las migraciones de Alembic (cambios de esquema de la base de datos).

La app las aplica sola al arrancar, así una base nueva o vieja queda siempre al día.
También se pueden correr a mano desde `backend/`: `uv run alembic upgrade head`.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection

CARPETA_MIGRACIONES = Path(__file__).resolve().parents[2] / "alembic"


def aplicar_migraciones(conexion: Connection | None = None, revision: str = "head") -> None:
    """Lleva la base al último esquema (o a `revision`, para los tests de migración).

    Sin `conexion`, usa la base configurada en DATABASE_URL.
    """
    config = Config()
    config.set_main_option("script_location", str(CARPETA_MIGRACIONES))
    if conexion is not None:
        config.attributes["connection"] = conexion
    command.upgrade(config, revision)
