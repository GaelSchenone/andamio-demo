"""Configuración común de los tests.

Las variables de entorno se fijan ANTES de importar la app (la base y la clave se leen al
importar). Cada ejecución usa una base SQLite propia en una carpeta temporal, así que los
tests nunca tocan datos reales ni un `.env` local (python-dotenv no pisa variables ya definidas).
"""

import os
import tempfile

_CARPETA = tempfile.mkdtemp(prefix="andamio-tests-")
DUENO = "dueno-test"
PASSWORD_DUENO = "clave-de-prueba-123"

os.environ["DATABASE_URL"] = f"sqlite:///{_CARPETA}/test.db"
os.environ["SECRET_KEY"] = "s" * 48
os.environ["ENV"] = "development"
os.environ["DUENO_USUARIO"] = DUENO
os.environ["DUENO_PASSWORD"] = PASSWORD_DUENO
os.environ["DUENO_NOMBRE"] = "Dueño de Prueba"
for _variable in (
    "GEMINI_API_KEY",
    "NEGOCIO_RESPONSABLE",
    "NEGOCIO_TELEFONO",
    "NEGOCIO_INSTAGRAM",
):
    os.environ[_variable] = ""

import pytest  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from presupuestos_backend import passwords  # noqa: E402

# Argon2 con parámetros mínimos: en los tests importa que funcione, no que sea lento.
passwords._hasher = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)

PASSWORD_EMPLEADO = "clave-de-ana-123"


@pytest.fixture(scope="session")
def client():
    from presupuestos_backend.main import app

    # El `with` ejecuta el arranque: valida la config, migra la base y crea al dueño.
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def estado_limpio(client):
    """Cada test arranca sin sesión, sin intentos de login previos y con datos de fábrica."""
    from presupuestos_backend.auth import limite_login
    from presupuestos_backend.bootstrap import crear_dueno_inicial
    from presupuestos_backend.database import SessionLocal
    from presupuestos_backend.models import (
        Cliente,
        Cobro,
        DiaSinTrabajo,
        ItemPresupuesto,
        Obra,
        Presupuesto,
        Reprogramacion,
        Trabajo,
        Usuario,
    )
    from presupuestos_backend.routers.agente import limite as limite_agente

    client.cookies.clear()
    limite_login.reiniciar_todo()
    limite_agente.reiniciar_todo()
    yield
    with SessionLocal() as db:
        db.execute(delete(Cobro))
        db.execute(delete(DiaSinTrabajo))
        db.execute(delete(Reprogramacion))  # dependen de los trabajos, y estos de los presupuestos
        db.execute(delete(Trabajo))
        db.execute(delete(ItemPresupuesto))
        db.execute(delete(Presupuesto))
        db.execute(delete(Obra))  # primero las obras: dependen de los clientes
        db.execute(delete(Cliente))
        db.execute(delete(Usuario))
        db.commit()
    crear_dueno_inicial()  # vuelve a dejar solo al dueño de prueba, como al arrancar


@pytest.fixture
def iniciar_sesion(client):
    """Devuelve una función que cierra cualquier sesión y entra con ese usuario."""

    def _iniciar(usuario: str, password: str):
        client.cookies.clear()
        return client.post("/api/auth/login", json={"usuario": usuario, "password": password})

    return _iniciar


@pytest.fixture
def autenticado(client, iniciar_sesion):
    """Cliente con la sesión del dueño iniciada."""
    assert iniciar_sesion(DUENO, PASSWORD_DUENO).status_code == 200
    return client


@pytest.fixture
def empleado(autenticado, iniciar_sesion):
    """Crea al empleado 'ana' (como dueño) y deja la sesión cerrada; se entra con iniciar_sesion."""
    r = autenticado.post(
        "/api/usuarios",
        json={
            "nombre": "Ana",
            "usuario": "ana",
            "password": PASSWORD_EMPLEADO,
            "rol": "empleado",
        },
    )
    assert r.status_code == 201
    autenticado.cookies.clear()
    return r.json()


def presupuesto_valido(**cambios):
    datos = {
        "cliente_obra": "Juan Pérez - Depto en Palermo",
        "direccion": "Av. Siempre Viva 123",
        "fecha_emision": "2026-11-19",
        "items": [
            {"descripcion": "Pintura de living", "unidad": "gl", "cantidad": 1, "importe": 1000}
        ],
    }
    datos.update(cambios)
    return datos
