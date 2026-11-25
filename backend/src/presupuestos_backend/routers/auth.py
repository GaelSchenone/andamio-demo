"""Inicio y cierre de sesión, y cambio de la propia contraseña."""

import math

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from presupuestos_backend import crud_usuarios, passwords
from presupuestos_backend.auth import (
    COOKIE_NAME,
    limite_login,
    poner_cookie,
    usuario_actual,
)
from presupuestos_backend.database import get_db
from presupuestos_backend.models import Usuario
from presupuestos_backend.schemas_usuarios import CambiarPasswordIn, LoginIn, UsuarioOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _origen(request: Request) -> str:
    return request.client.host if request.client else "desconocido"


def _bloquear_si_corresponde(clave: str) -> None:
    espera = limite_login.segundos_de_espera(clave)
    if espera:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos fallidos. Probá de nuevo en {math.ceil(espera / 60)} min.",
            headers={"Retry-After": str(espera)},
        )


@router.post("/login", response_model=UsuarioOut)
def login(datos: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    origen = _origen(request)
    _bloquear_si_corresponde(origen)

    usuario = crud_usuarios.obtener_por_usuario(db, datos.usuario)
    # Se verifica siempre (contra un hash falso si no existe) para que tarde lo mismo.
    hash_guardado = usuario.password_hash if usuario else passwords.HASH_FALSO
    correcta = passwords.verificar(datos.password, hash_guardado)

    if usuario is None or not usuario.activo or not correcta:
        limite_login.registrar_fallo(origen)
        # Mismo mensaje para "no existe", "está desactivado" y "contraseña mal".
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos."
        )

    limite_login.reiniciar(origen)
    if passwords.necesita_rehash(usuario.password_hash):
        usuario.password_hash = passwords.hashear(datos.password)
        db.commit()
    poner_cookie(response, usuario)
    return usuario


@router.get("/yo", response_model=UsuarioOut)
def yo(usuario: Usuario = Depends(usuario_actual)):
    return usuario


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/cambiar-password")
def cambiar_password(
    datos: CambiarPasswordIn,
    response: Response,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
) -> dict:
    # Límite propio: alguien con una sesión robada no debería poder adivinar la contraseña actual.
    clave = f"password:{usuario.id}"
    _bloquear_si_corresponde(clave)

    if not passwords.verificar(datos.password_actual, usuario.password_hash):
        limite_login.registrar_fallo(clave)
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")
    if datos.password_nueva == datos.password_actual:
        raise HTTPException(status_code=400, detail="La contraseña nueva tiene que ser distinta.")

    limite_login.reiniciar(clave)
    crud_usuarios.cambiar_password(db, usuario, datos.password_nueva)
    poner_cookie(response, usuario)  # esta sesión sigue abierta; las demás se cierran
    return {"ok": True}
