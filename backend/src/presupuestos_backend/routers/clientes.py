"""Clientes y sus obras. Leer: dueño y empleado. Crear, editar y borrar: solo el dueño."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from presupuestos_backend import crud_clientes
from presupuestos_backend.auth import requiere_permiso
from presupuestos_backend.database import get_db
from presupuestos_backend.errores import ReglaDeNegocio
from presupuestos_backend.models import Cliente, Obra
from presupuestos_backend.schemas_clientes import (
    ClienteIn,
    ClienteOut,
    ClienteResumen,
    ObraIn,
    ObraOut,
)

VER = Depends(requiere_permiso("clientes:ver"))
GESTIONAR = Depends(requiere_permiso("clientes:gestionar"))

router = APIRouter(prefix="/api/clientes", tags=["clientes"])
router_obras = APIRouter(prefix="/api/obras", tags=["obras"])


def _cliente_o_404(db: Session, cliente_id: int) -> Cliente:
    cliente = crud_clientes.obtener_cliente(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="No se encontró ese cliente.")
    return cliente


def _obra_o_404(db: Session, obra_id: int) -> Obra:
    obra = crud_clientes.obtener_obra(db, obra_id)
    if obra is None:
        raise HTTPException(status_code=404, detail="No se encontró esa obra.")
    return obra


@router.get("", response_model=list[ClienteResumen], dependencies=[VER])
def listar(buscar: str | None = None, db: Session = Depends(get_db)):
    return [
        ClienteResumen(
            id=c.id, nombre=c.nombre, tipo=c.tipo, telefono=c.telefono, cantidad_obras=cantidad
        )
        for c, cantidad in crud_clientes.listar_clientes(db, buscar)
    ]


@router.post("", response_model=ClienteOut, status_code=201, dependencies=[GESTIONAR])
def crear(datos: ClienteIn, db: Session = Depends(get_db)):
    return crud_clientes.crear_cliente(db, datos)


@router.get("/{cliente_id}", response_model=ClienteOut, dependencies=[VER])
def obtener(cliente_id: int, db: Session = Depends(get_db)):
    return _cliente_o_404(db, cliente_id)


@router.put("/{cliente_id}", response_model=ClienteOut, dependencies=[GESTIONAR])
def actualizar(cliente_id: int, datos: ClienteIn, db: Session = Depends(get_db)):
    return crud_clientes.actualizar_cliente(db, _cliente_o_404(db, cliente_id), datos)


@router.delete("/{cliente_id}", status_code=204, dependencies=[GESTIONAR])
def eliminar(cliente_id: int, db: Session = Depends(get_db)):
    try:
        crud_clientes.eliminar_cliente(db, _cliente_o_404(db, cliente_id))
    except ReglaDeNegocio as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post(
    "/{cliente_id}/obras", response_model=ObraOut, status_code=201, dependencies=[GESTIONAR]
)
def crear_obra(cliente_id: int, datos: ObraIn, db: Session = Depends(get_db)):
    return crud_clientes.crear_obra(db, _cliente_o_404(db, cliente_id), datos)


@router_obras.put("/{obra_id}", response_model=ObraOut, dependencies=[GESTIONAR])
def actualizar_obra(obra_id: int, datos: ObraIn, db: Session = Depends(get_db)):
    return crud_clientes.actualizar_obra(db, _obra_o_404(db, obra_id), datos)


@router_obras.delete("/{obra_id}", status_code=204, dependencies=[GESTIONAR])
def eliminar_obra(obra_id: int, db: Session = Depends(get_db)):
    try:
        crud_clientes.eliminar_obra(db, _obra_o_404(db, obra_id))
    except ReglaDeNegocio as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
