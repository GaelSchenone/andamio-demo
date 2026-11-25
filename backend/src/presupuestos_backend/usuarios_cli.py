"""Gestión de usuarios desde la terminal (útil en local, o si el dueño pierde su contraseña).

Desde `backend/`:
    uv run python -m presupuestos_backend.usuarios_cli crear --usuario ana --nombre "Ana"
    uv run python -m presupuestos_backend.usuarios_cli password --usuario ana

La contraseña se pide por teclado (no se pasa como argumento, para que no quede en el historial
de la terminal). Usa la base de DATABASE_URL.
"""

import argparse
import getpass
import sys

from dotenv import load_dotenv

load_dotenv()

from pydantic import ValidationError  # noqa: E402

from presupuestos_backend import crud_usuarios  # noqa: E402
from presupuestos_backend.database import SessionLocal  # noqa: E402
from presupuestos_backend.migraciones import aplicar_migraciones  # noqa: E402
from presupuestos_backend.permisos import ROL_DUENO, ROLES  # noqa: E402
from presupuestos_backend.schemas_usuarios import PasswordNuevaIn, UsuarioIn  # noqa: E402


def _pedir_password() -> str:
    primera = getpass.getpass("Contraseña (10 a 128 caracteres): ")
    if primera != getpass.getpass("Repetí la contraseña: "):
        raise SystemExit("Las contraseñas no coinciden.")
    return primera


def _crear(args: argparse.Namespace) -> None:
    try:
        datos = UsuarioIn(
            nombre=args.nombre or args.usuario,
            usuario=args.usuario,
            password=_pedir_password(),
            rol=args.rol,
        )
    except ValidationError as e:
        campos = ", ".join(sorted({str(err["loc"][0]) for err in e.errors()}))
        raise SystemExit(f"Datos inválidos (revisá: {campos}).") from None
    with SessionLocal() as db:
        try:
            crud_usuarios.crear(db, datos.nombre, datos.usuario, datos.password, datos.rol)
        except crud_usuarios.UsuarioDuplicado:
            raise SystemExit("Ya existe un usuario con ese nombre.") from None
    print(f"Listo: se creó '{datos.usuario}' con rol {datos.rol}.")


def _cambiar_password(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        usuario = crud_usuarios.obtener_por_usuario(db, args.usuario.strip().lower())
        if usuario is None:
            raise SystemExit("No existe ese usuario.")
        try:
            nueva = PasswordNuevaIn(password_nueva=_pedir_password()).password_nueva
        except ValidationError:
            raise SystemExit("La contraseña tiene que tener entre 10 y 128 caracteres.") from None
        crud_usuarios.cambiar_password(db, usuario, nueva)
    print(f"Listo: se cambió la contraseña de '{args.usuario}' y se cerraron sus sesiones.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="usuarios_cli", description=__doc__.split("\n")[0])
    subcomandos = parser.add_subparsers(dest="comando", required=True)

    crear = subcomandos.add_parser("crear", help="crear un usuario")
    crear.add_argument("--usuario", required=True)
    crear.add_argument("--nombre", default="")
    crear.add_argument("--rol", choices=ROLES, default=ROL_DUENO)
    crear.set_defaults(accion=_crear)

    password = subcomandos.add_parser("password", help="cambiar la contraseña de un usuario")
    password.add_argument("--usuario", required=True)
    password.set_defaults(accion=_cambiar_password)

    args = parser.parse_args(argv)
    aplicar_migraciones()
    args.accion(args)


if __name__ == "__main__":
    sys.exit(main())
