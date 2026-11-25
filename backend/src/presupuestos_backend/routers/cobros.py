"""Cobros de los trabajos. Todo es solo del dueño (permiso `cobros:gestionar`)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from presupuestos_backend import crud_cobros, crud_trabajos
from presupuestos_backend.auth import requiere_permiso
from presupuestos_backend.database import get_db
from presupuestos_backend.errores import ReglaDeNegocio
from presupuestos_backend.models import Trabajo, Usuario
from presupuestos_backend.schemas_cobros import (
    CobroIn,
    CobroOut,
    PendienteOut,
    PendientesOut,
    ResumenDeCobros,
)

GESTIONAR = "cobros:gestionar"

router_trabajo = APIRouter(prefix="/api/trabajos", tags=["cobros"])
router = APIRouter(prefix="/api/cobros", tags=["cobros"])


def _resumen_out(trabajo: Trabajo) -> ResumenDeCobros:
    r = crud_cobros.resumen(trabajo)
    return ResumenDeCobros(
        trabajo_id=trabajo.id,
        estado_trabajo=trabajo.estado,
        total=r.total,
        cobrado=r.cobrado,
        pendiente=r.pendiente,
        sugerido_sena=r.sugerido_sena,
        sugerido_saldo=r.sugerido_saldo,
        cobros=[
            CobroOut(
                id=c.id,
                concepto=c.concepto,
                monto=c.monto,
                fecha=c.fecha,
                nota=c.nota,
                usuario_nombre=c.usuario.nombre,
                creado_en=c.creado_en,
                anulado=c.anulado,
                anulado_en=c.anulado_en,
            )
            for c in r.cobros
        ],
    )


def _trabajo_o_404(db: Session, trabajo_id: int) -> Trabajo:
    trabajo = crud_trabajos.obtener(db, trabajo_id)
    if trabajo is None:
        raise HTTPException(status_code=404, detail="No se encontró ese trabajo.")
    return trabajo


@router_trabajo.get(
    "/{trabajo_id}/cobros",
    response_model=ResumenDeCobros,
    dependencies=[Depends(requiere_permiso(GESTIONAR))],
)
def ver_cobros(trabajo_id: int, db: Session = Depends(get_db)):
    return _resumen_out(_trabajo_o_404(db, trabajo_id))


@router_trabajo.post("/{trabajo_id}/cobros", response_model=ResumenDeCobros, status_code=201)
def registrar_cobro(
    trabajo_id: int,
    datos: CobroIn,
    usuario: Usuario = Depends(requiere_permiso(GESTIONAR)),
    db: Session = Depends(get_db),
):
    trabajo = _trabajo_o_404(db, trabajo_id)
    try:
        crud_cobros.registrar(
            db, trabajo, datos.concepto, datos.monto, datos.fecha, datos.nota, usuario
        )
    except ReglaDeNegocio as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _resumen_out(trabajo)


@router.get(
    "/pendientes",
    response_model=PendientesOut,
    dependencies=[Depends(requiere_permiso(GESTIONAR))],
)
def pendientes(db: Session = Depends(get_db)):
    """Lo que falta cobrar, trabajo por trabajo, con el total."""
    trabajos = crud_cobros.pendientes(db)
    filas = []
    for t in trabajos:
        presupuesto = t.presupuesto
        filas.append(
            PendienteOut(
                trabajo_id=t.id,
                cliente=presupuesto.cliente.nombre,
                direccion=presupuesto.obra.direccion,
                referencia=presupuesto.obra.referencia,
                estado=t.estado,
                fecha_inicio=t.fecha_inicio,
                fecha_fin=t.fecha_fin,
                total=crud_cobros.total_a_cobrar(t),
                cobrado=crud_cobros.total_cobrado(t),
                pendiente=crud_cobros.pendiente(t),
            )
        )
    return PendientesOut(
        total_pendiente=sum((f.pendiente for f in filas), 0.0),
        trabajos=filas,
    )


@router.post("/{cobro_id}/anular", response_model=ResumenDeCobros)
def anular_cobro(
    cobro_id: int,
    usuario: Usuario = Depends(requiere_permiso(GESTIONAR)),
    db: Session = Depends(get_db),
):
    cobro = crud_cobros.obtener_cobro(db, cobro_id)
    if cobro is None:
        raise HTTPException(status_code=404, detail="No se encontró ese cobro.")
    try:
        trabajo = crud_cobros.anular(db, cobro, usuario)
    except ReglaDeNegocio as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _resumen_out(trabajo)
