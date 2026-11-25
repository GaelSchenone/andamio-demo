"""Gestión de usuarios (solo el dueño)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from presupuestos_backend import crud_usuarios
from presupuestos_backend.auth import requiere_permiso
from presupuestos_backend.database import get_db
from presupuestos_backend.models import Usuario
from presupuestos_backend.schemas_usuarios import (
    PasswordNuevaIn,
    UsuarioIn,
    UsuarioOut,
    UsuarioPatch,
)

router = APIRouter(
    prefix="/api/usuarios",
    tags=["usuarios"],
    dependencies=[Depends(requiere_permiso("usuarios:gestionar"))],
)

ULTIMO_DUENO = "Tiene que quedar al menos un dueño activo."


def _obtener_o_404(db: Session, usuario_id: int) -> Usuario:
    usuario = crud_usuarios.obtener(db, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="No se encontró ese usuario.")
    return usuario


@router.get("", response_model=list[UsuarioOut])
def listar(db: Session = Depends(get_db)):
    return crud_usuarios.listar(db)


@router.post("", response_model=UsuarioOut, status_code=201)
def crear(datos: UsuarioIn, db: Session = Depends(get_db)):
    try:
        return crud_usuarios.crear(db, datos.nombre, datos.usuario, datos.password, datos.rol)
    except crud_usuarios.UsuarioDuplicado as e:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese nombre.") from e


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def actualizar(usuario_id: int, datos: UsuarioPatch, db: Session = Depends(get_db)):
    usuario = _obtener_o_404(db, usuario_id)
    try:
        return crud_usuarios.actualizar(
            db, usuario, nombre=datos.nombre, rol=datos.rol, activo=datos.activo
        )
    except crud_usuarios.UltimoDueno as e:
        raise HTTPException(status_code=409, detail=ULTIMO_DUENO) from e


@router.post("/{usuario_id}/password", response_model=UsuarioOut)
def restablecer_password(usuario_id: int, datos: PasswordNuevaIn, db: Session = Depends(get_db)):
    """El dueño le pone una contraseña nueva a alguien (por ejemplo, si se la olvidó)."""
    usuario = _obtener_o_404(db, usuario_id)
    return crud_usuarios.cambiar_password(db, usuario, datos.password_nueva)
