"""Punto de entrada de la aplicación: arma la API y sirve la app web."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from presupuestos_backend.auth import (  # noqa: E402
    ES_PRODUCCION,
    SECRET_KEY,
    validar_configuracion,
)
from presupuestos_backend.bootstrap import crear_dueno_inicial  # noqa: E402
from presupuestos_backend.database import DATABASE_URL  # noqa: E402
from presupuestos_backend.demo import cargar_si_corresponde  # noqa: E402
from presupuestos_backend.logs import instalar_filtro_de_acceso  # noqa: E402
from presupuestos_backend.migraciones import aplicar_migraciones  # noqa: E402
from presupuestos_backend.routers import (  # noqa: E402
    agente,
    asistente,
    auth,
    clientes,
    cobros,
    presupuestos,
    trabajos,
    usuarios,
)
from presupuestos_backend.spa import AplicacionDeUnaPagina  # noqa: E402
from presupuestos_backend.validacion import datos_rechazados  # noqa: E402

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validar_configuracion(ES_PRODUCCION, SECRET_KEY)
    if ES_PRODUCCION and DATABASE_URL.startswith("sqlite") and os.environ.get("DEMO") != "1":
        log.warning(
            "Producción con SQLite: los datos viven dentro del contenedor y se pierden al "
            "redeployar. "
            "Definí DATABASE_URL con un Postgres."
        )
    aplicar_migraciones()
    crear_dueno_inicial()
    cargar_si_corresponde()
    yield


instalar_filtro_de_acceso()

app = FastAPI(title="Obras Demo - Presupuestos", lifespan=lifespan)
app.add_exception_handler(RequestValidationError, datos_rechazados)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(clientes.router)
app.include_router(clientes.router_obras)
app.include_router(presupuestos.router)
app.include_router(trabajos.router_desde_presupuesto)
app.include_router(trabajos.router)
app.include_router(cobros.router_trabajo)
app.include_router(cobros.router)
app.include_router(asistente.router)
app.include_router(agente.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


if FRONTEND_DIST.is_dir():
    app.mount("/", AplicacionDeUnaPagina(directory=FRONTEND_DIST, html=True), name="frontend")
