"""Trabajos y su calendario.

- Ver: dueño y empleado (sin precios).
- Iniciar y terminar: dueño y empleado (el empleado lo hace desde la obra).
- Crear, agendar, reprogramar, cancelar y ver el historial de cambios: solo el dueño.
"""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from presupuestos_backend import crud, crud_trabajos
from presupuestos_backend.auth import requiere_permiso
from presupuestos_backend.database import get_db
from presupuestos_backend.errores import ReglaDeNegocio
from presupuestos_backend.models import Trabajo, Usuario
from presupuestos_backend.schemas_trabajos import (
    AgendarIn,
    ClienteDelTrabajo,
    ObraDelTrabajo,
    ReprogramacionOut,
    ReprogramarIn,
    TareaDelTrabajo,
    TrabajoOut,
)

VER = Depends(requiere_permiso("agenda:ver"))
GESTIONAR = Depends(requiere_permiso("trabajos:gestionar"))
CAMBIAR_ESTADO = Depends(requiere_permiso("trabajos:cambiar_estado"))

router = APIRouter(prefix="/api/trabajos", tags=["trabajos"])
router_desde_presupuesto = APIRouter(prefix="/api/presupuestos", tags=["trabajos"])


def _armar_salida(trabajo: Trabajo) -> TrabajoOut:
    """Arma la respuesta eligiendo campo por campo: así nunca viaja un importe."""
    presupuesto = trabajo.presupuesto
    return TrabajoOut(
        id=trabajo.id,
        estado=trabajo.estado,
        creado_en=trabajo.creado_en,
        fecha_inicio=trabajo.fecha_inicio,
        fecha_fin=trabajo.fecha_fin,
        dias=crud_trabajos.dias_trabajados(trabajo),
        presupuesto_id=presupuesto.id,
        presupuesto_numero=presupuesto.numero,
        cliente=ClienteDelTrabajo.model_validate(presupuesto.cliente),
        obra=ObraDelTrabajo.model_validate(presupuesto.obra),
        tareas=[TareaDelTrabajo.model_validate(item) for item in presupuesto.items],
        plazo_obra=presupuesto.plazo_obra,
        materiales_a_cargo=presupuesto.materiales_a_cargo,
    )


def _trabajo_o_404(db: Session, trabajo_id: int) -> Trabajo:
    trabajo = crud_trabajos.obtener(db, trabajo_id)
    if trabajo is None:
        raise HTTPException(status_code=404, detail="No se encontró ese trabajo.")
    return trabajo


def _aplicar(operacion, *args) -> TrabajoOut:
    """Corre una operación del calendario y responde 409 con el mensaje si una regla la frena."""
    try:
        return _armar_salida(operacion(*args))
    except ReglaDeNegocio as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("", response_model=list[TrabajoOut], dependencies=[VER])
def listar(
    incluir_cancelados: bool = False,
    desde: dt.date | None = None,
    hasta: dt.date | None = None,
    db: Session = Depends(get_db),
):
    """Sin fechas: todos, los más nuevos primero. Con `desde`/`hasta`: los del rango, por fecha."""
    trabajos = crud_trabajos.listar(db, incluir_cancelados, desde, hasta)
    return [_armar_salida(t) for t in trabajos]


@router.get("/{trabajo_id}", response_model=TrabajoOut, dependencies=[VER])
def obtener(trabajo_id: int, db: Session = Depends(get_db)):
    return _armar_salida(_trabajo_o_404(db, trabajo_id))


@router.post("/{trabajo_id}/agendar", response_model=TrabajoOut, dependencies=[GESTIONAR])
def agendar(trabajo_id: int, datos: AgendarIn, db: Session = Depends(get_db)):
    trabajo = _trabajo_o_404(db, trabajo_id)
    return _aplicar(
        crud_trabajos.agendar, db, trabajo, datos.fecha_inicio, datos.fecha_fin, datos.dias
    )


@router.post("/{trabajo_id}/reprogramar", response_model=TrabajoOut)
def reprogramar(
    trabajo_id: int,
    datos: ReprogramarIn,
    usuario: Usuario = Depends(requiere_permiso("trabajos:gestionar")),
    db: Session = Depends(get_db),
):
    trabajo = _trabajo_o_404(db, trabajo_id)
    return _aplicar(
        crud_trabajos.reprogramar,
        db,
        trabajo,
        datos.fecha_inicio,
        datos.fecha_fin,
        datos.causa,
        datos.motivo,
        usuario,
        datos.dias,
    )


@router.get(
    "/{trabajo_id}/reprogramaciones",
    response_model=list[ReprogramacionOut],
    dependencies=[GESTIONAR],
)
def historial(trabajo_id: int, db: Session = Depends(get_db)):
    trabajo = _trabajo_o_404(db, trabajo_id)
    return [
        ReprogramacionOut(
            id=r.id,
            fecha_inicio_anterior=r.fecha_inicio_anterior,
            fecha_fin_anterior=r.fecha_fin_anterior,
            fecha_inicio_nueva=r.fecha_inicio_nueva,
            fecha_fin_nueva=r.fecha_fin_nueva,
            causa=r.causa,
            motivo=r.motivo,
            usuario_nombre=r.usuario.nombre,
            creado_en=r.creado_en,
        )
        for r in crud_trabajos.historial(trabajo)
    ]


@router.post("/{trabajo_id}/iniciar", response_model=TrabajoOut, dependencies=[CAMBIAR_ESTADO])
def iniciar(trabajo_id: int, db: Session = Depends(get_db)):
    return _aplicar(crud_trabajos.iniciar, db, _trabajo_o_404(db, trabajo_id))


@router.post("/{trabajo_id}/terminar", response_model=TrabajoOut, dependencies=[CAMBIAR_ESTADO])
def terminar(trabajo_id: int, db: Session = Depends(get_db)):
    return _aplicar(crud_trabajos.terminar, db, _trabajo_o_404(db, trabajo_id))


@router.post("/{trabajo_id}/cancelar", response_model=TrabajoOut, dependencies=[GESTIONAR])
def cancelar(trabajo_id: int, db: Session = Depends(get_db)):
    return _aplicar(crud_trabajos.cancelar, db, _trabajo_o_404(db, trabajo_id))


@router_desde_presupuesto.post(
    "/{presupuesto_id}/trabajo",
    response_model=TrabajoOut,
    status_code=201,
    dependencies=[GESTIONAR],
)
def crear_desde_presupuesto(presupuesto_id: int, db: Session = Depends(get_db)):
    presupuesto = crud.obtener_presupuesto(db, presupuesto_id)
    if presupuesto is None:
        raise HTTPException(status_code=404, detail="No se encontró ese presupuesto")
    return _aplicar(crud_trabajos.crear_desde_presupuesto, db, presupuesto)
