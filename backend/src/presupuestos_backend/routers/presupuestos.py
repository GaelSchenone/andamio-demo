"""Endpoints para crear, listar, editar y generar el PDF de presupuestos."""

import unicodedata
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from presupuestos_backend import crud
from presupuestos_backend.auth import requiere_permiso
from presupuestos_backend.database import get_db
from presupuestos_backend.errores import ReglaDeNegocio, VinculoInvalido
from presupuestos_backend.pdf_generator import generar_pdf
from presupuestos_backend.schemas import (
    EstadoIn,
    PresupuestoIn,
    PresupuestoOut,
    PresupuestoResumen,
)

router = APIRouter(
    prefix="/api/presupuestos",
    tags=["presupuestos"],
    dependencies=[Depends(requiere_permiso("presupuestos:gestionar"))],
)


def _obtener_o_404(db: Session, presupuesto_id: int):
    presupuesto = crud.obtener_presupuesto(db, presupuesto_id)
    if presupuesto is None:
        raise HTTPException(status_code=404, detail="No se encontró ese presupuesto")
    return presupuesto


@router.get("", response_model=list[PresupuestoResumen])
def listar(buscar: str | None = None, db: Session = Depends(get_db)):
    return crud.listar_presupuestos(db, buscar)


@router.post("", response_model=PresupuestoOut, status_code=201)
def crear(datos: PresupuestoIn, db: Session = Depends(get_db)):
    try:
        return crud.crear_presupuesto(db, datos)
    except VinculoInvalido as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/{presupuesto_id}", response_model=PresupuestoOut)
def obtener(presupuesto_id: int, db: Session = Depends(get_db)):
    return _obtener_o_404(db, presupuesto_id)


@router.put("/{presupuesto_id}", response_model=PresupuestoOut)
def actualizar(presupuesto_id: int, datos: PresupuestoIn, db: Session = Depends(get_db)):
    presupuesto = _obtener_o_404(db, presupuesto_id)
    try:
        return crud.actualizar_presupuesto(db, presupuesto, datos)
    except VinculoInvalido as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ReglaDeNegocio as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.put("/{presupuesto_id}/estado", response_model=PresupuestoOut)
def cambiar_estado(presupuesto_id: int, datos: EstadoIn, db: Session = Depends(get_db)):
    presupuesto = _obtener_o_404(db, presupuesto_id)
    try:
        return crud.cambiar_estado(db, presupuesto, datos.estado)
    except ReglaDeNegocio as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.delete("/{presupuesto_id}", status_code=204)
def eliminar(presupuesto_id: int, db: Session = Depends(get_db)):
    presupuesto = _obtener_o_404(db, presupuesto_id)
    try:
        crud.eliminar_presupuesto(db, presupuesto)
    except ReglaDeNegocio as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/{presupuesto_id}/pdf")
def pdf(presupuesto_id: int, db: Session = Depends(get_db)):
    presupuesto = _obtener_o_404(db, presupuesto_id)
    buffer = generar_pdf(presupuesto)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(presupuesto)},
    )


def _content_disposition(presupuesto) -> str:
    """Header para mostrar el PDF con un nombre de archivo que puede llevar tildes o "ñ".

    Los headers HTTP solo admiten latin-1: con otros caracteres (ej. "Łukasz") el servidor
    fallaba. Se manda un nombre ASCII de respaldo y el nombre real en UTF-8 (RFC 6266).
    """
    nombre = f"Presupuesto_{presupuesto.numero}_{presupuesto.cliente_obra}.pdf"
    solo_permitidos = "".join(c for c in nombre if c.isalnum() or c in " _-.").strip()
    ascii_ = unicodedata.normalize("NFKD", solo_permitidos).encode("ascii", "ignore").decode()
    return f"inline; filename=\"{ascii_}\"; filename*=UTF-8''{quote(solo_permitidos)}"
