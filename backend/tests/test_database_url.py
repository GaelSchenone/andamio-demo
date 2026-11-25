"""La URL de la base: los servicios de Postgres la entregan sin el driver y hay que agregárselo."""

import pytest
from sqlalchemy.engine import make_url

from presupuestos_backend.database import url_para_sqlalchemy


@pytest.mark.parametrize(
    ("entrada", "esperada"),
    [
        ("postgresql://u:p@db:5432/andamio", "postgresql+psycopg://u:p@db:5432/andamio"),
        ("postgres://u:p@db:5432/andamio", "postgresql+psycopg://u:p@db:5432/andamio"),
        # Neon pide SSL por parámetro: tiene que sobrevivir.
        (
            "postgresql://u:p@ep-x.neon.tech/db?sslmode=require",
            "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require",
        ),
        # Lo que ya está bien no se toca.
        ("postgresql+psycopg://u:p@db/andamio", "postgresql+psycopg://u:p@db/andamio"),
        ("sqlite:///./presupuestos.db", "sqlite:///./presupuestos.db"),
    ],
)
def test_agrega_el_driver_solo_cuando_falta(entrada, esperada):
    assert url_para_sqlalchemy(entrada) == esperada


def test_la_url_convertida_usa_el_driver_psycopg_3():
    url = make_url(url_para_sqlalchemy("postgresql://u:p%40ss@db:5432/andamio"))
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "p@ss"  # una contraseña con caracteres especiales no se rompe
    # El driver tiene que estar instalado: si no, create_engine fallaría recién al arrancar en producción.
    from sqlalchemy import create_engine

    create_engine(url)  # no conecta: solo carga el driver
