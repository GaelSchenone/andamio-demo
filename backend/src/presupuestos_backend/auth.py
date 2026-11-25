"""Sesión de usuarios: cookie firmada y control de permisos por endpoint.

La cookie lleva `id.version.vencimiento.firma` (firma HMAC con SECRET_KEY). En cada pedido se
busca al usuario en la base: si fue desactivado o cambió su contraseña (`version_sesion` distinta),
la cookie deja de valer aunque la firma sea correcta.
"""

import hashlib
import hmac
import os
import time

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from presupuestos_backend.database import get_db
from presupuestos_backend.models import Usuario
from presupuestos_backend.permisos import tiene_permiso
from presupuestos_backend.ratelimit import LimiteIntentos

SECRET_KEY_POR_DEFECTO = "clave-de-desarrollo-cambiar-en-produccion"
SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY_POR_DEFECTO)
ES_PRODUCCION = os.environ.get("ENV", "development") == "production"
COOKIE_NAME = "obras_demo_sesion"
DURACION_SEGUNDOS = 60 * 60 * 24 * 30  # 30 días

MAX_FALLOS_LOGIN = 5
VENTANA_LOGIN_SEGUNDOS = 15 * 60
limite_login = LimiteIntentos(MAX_FALLOS_LOGIN, VENTANA_LOGIN_SEGUNDOS)

LARGO_MINIMO_SECRET_KEY = 32


def validar_configuracion(es_produccion: bool, secret_key: str) -> None:
    """En producción, corta el arranque si la clave que firma las sesiones es débil."""
    if not es_produccion:
        return
    if secret_key == SECRET_KEY_POR_DEFECTO or len(secret_key) < LARGO_MINIMO_SECRET_KEY:
        raise RuntimeError(
            "Configuración insegura para producción: SECRET_KEY tiene que ser propia y de al "
            f"menos {LARGO_MINIMO_SECRET_KEY} caracteres (generala con: openssl rand -hex 32)."
        )


def _firmar(mensaje: str) -> str:
    return hmac.new(SECRET_KEY.encode(), mensaje.encode(), hashlib.sha256).hexdigest()


def crear_token(usuario_id: int, version_sesion: int) -> str:
    vencimiento = int(time.time()) + DURACION_SEGUNDOS
    carga = f"{usuario_id}.{version_sesion}.{vencimiento}"
    return f"{carga}.{_firmar(carga)}"


def leer_token(token: str | None) -> tuple[int, int] | None:
    """Devuelve (id de usuario, versión de sesión) si el token es auténtico y no venció."""
    if not token:
        return None
    partes = token.split(".")
    if len(partes) != 4:
        return None
    usuario_id, version, vencimiento, firma = partes
    # Se compara en bytes: con texto, una cookie con tildes haría fallar la comparación.
    if not hmac.compare_digest(firma.encode(), _firmar(".".join(partes[:3])).encode()):
        return None
    try:
        if int(vencimiento) <= time.time():
            return None
        return int(usuario_id), int(version)
    except ValueError:
        return None


def poner_cookie(response: Response, usuario: Usuario) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=crear_token(usuario.id, usuario.version_sesion),
        max_age=DURACION_SEGUNDOS,
        httponly=True,
        samesite="lax",
        secure=ES_PRODUCCION,
    )


def usuario_actual(
    sesion: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
) -> Usuario:
    sin_sesion = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")
    datos = leer_token(sesion)
    if datos is None:
        raise sin_sesion
    usuario_id, version = datos
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo or usuario.version_sesion != version:
        raise sin_sesion
    return usuario


def requiere_permiso(permiso: str):
    """Dependencia de FastAPI: exige sesión iniciada y que el rol tenga el permiso."""

    def dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if not tiene_permiso(usuario.rol, permiso):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="No tenés permiso para hacer esto."
            )
        return usuario

    return dependencia
