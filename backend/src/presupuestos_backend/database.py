"""Conexión a la base de datos.

Usa SQLite en desarrollo (un archivo local) y Postgres en producción,
según la variable de entorno DATABASE_URL. Si no está definida, se usa
un archivo SQLite local para que el proyecto funcione sin configurar nada.
"""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def url_para_sqlalchemy(url: str) -> str:
    """Los servicios de Postgres (Dokploy, Neon, Render) entregan `postgresql://` o `postgres://`.

    SQLAlchemy abriría esas URL con el driver `psycopg2`, que este proyecto no usa (usa `psycopg`
    3), así que se las convierte. Cualquier otra URL (SQLite, o una que ya nombre el driver) queda
    igual.
    """
    for prefijo in ("postgresql://", "postgres://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url.removeprefix(prefijo)
    return url


DATABASE_URL = url_para_sqlalchemy(os.environ.get("DATABASE_URL", "sqlite:///./presupuestos.db"))

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
