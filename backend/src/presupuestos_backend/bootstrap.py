"""Crea el primer dueño al arrancar, cuando todavía no hay ningún usuario.

Se usa porque el hosting no siempre da una consola, y un endpoint de "configuración inicial"
abierto en internet sería una carrera por ser el primero en llegar. Los datos vienen de variables
de entorno (DUENO_USUARIO, DUENO_PASSWORD, DUENO_NOMBRE opcional). Una vez creado, esas variables
ya no se usan y conviene borrarlas: la contraseña se cambia desde la app ("Cuenta").
"""

import logging
import os

from pydantic import ValidationError

from presupuestos_backend import crud_usuarios
from presupuestos_backend.database import SessionLocal
from presupuestos_backend.permisos import ROL_DUENO
from presupuestos_backend.schemas_usuarios import UsuarioIn

log = logging.getLogger(__name__)


def crear_dueno_inicial() -> bool:
    """Devuelve True si creó el dueño. No hace nada si ya existe algún usuario."""
    with SessionLocal() as db:
        if crud_usuarios.hay_usuarios(db):
            return False

        usuario = os.environ.get("DUENO_USUARIO", "")
        password = os.environ.get("DUENO_PASSWORD", "")
        if not usuario or not password:
            log.warning(
                "No hay usuarios y no se definieron DUENO_USUARIO y DUENO_PASSWORD: "
                "nadie va a poder entrar a la app."
            )
            return False

        try:
            datos = UsuarioIn(
                nombre=os.environ.get("DUENO_NOMBRE", "").strip() or usuario,
                usuario=usuario,
                password=password,
                rol=ROL_DUENO,
            )
        except ValidationError as e:
            # Nunca se incluye el valor de la contraseña en el mensaje.
            campos = sorted({str(err["loc"][0]) for err in e.errors()})
            raise RuntimeError(
                f"DUENO_USUARIO / DUENO_PASSWORD no son válidos (revisá: {', '.join(campos)}). "
                "El usuario: 3 a 40 caracteres entre letras sin tildes, números, punto, guion y "
                "guion bajo. La contraseña: 10 a 128 caracteres."
            ) from None

        crud_usuarios.crear(db, datos.nombre, datos.usuario, datos.password, datos.rol)
        log.info("Se creó el usuario dueño inicial '%s'.", datos.usuario)
        return True
