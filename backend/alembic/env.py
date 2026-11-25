"""Entorno de Alembic: usa la misma base de datos y los mismos modelos que la app."""

from dotenv import load_dotenv

load_dotenv()

from alembic import context  # noqa: E402
from sqlalchemy.engine import Connection  # noqa: E402

from presupuestos_backend import models  # noqa: E402, F401  (registra las tablas)
from presupuestos_backend.database import Base, engine  # noqa: E402

target_metadata = Base.metadata


def _migrar(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # SQLite no puede alterar columnas: Alembic recrea la tabla ("batch").
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Las migraciones en modo offline (--sql) no están soportadas.")

# La app (y los tests) pueden pasar una conexión ya abierta; si no, se usa la de DATABASE_URL.
conexion = context.config.attributes.get("connection")
if conexion is not None:
    _migrar(conexion)
else:
    with engine.connect() as connection:
        _migrar(connection)
