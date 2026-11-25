"""Operaciones sobre la base de datos para usuarios."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from presupuestos_backend import passwords
from presupuestos_backend.models import Usuario
from presupuestos_backend.permisos import ROL_DUENO


class UsuarioDuplicado(Exception):
    """Ya existe un usuario con ese nombre de acceso."""


class UltimoDueno(Exception):
    """La operación dejaría al sistema sin ningún dueño activo."""


def obtener(db: Session, usuario_id: int) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def obtener_por_usuario(db: Session, usuario: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.usuario == usuario))


def listar(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.id)))


def hay_usuarios(db: Session) -> bool:
    return (db.scalar(select(func.count(Usuario.id))) or 0) > 0


def _duenos_activos(db: Session) -> int:
    return (
        db.scalar(
            select(func.count(Usuario.id)).where(Usuario.rol == ROL_DUENO, Usuario.activo.is_(True))
        )
        or 0
    )


def crear(db: Session, nombre: str, usuario: str, password: str, rol: str) -> Usuario:
    if obtener_por_usuario(db, usuario) is not None:
        raise UsuarioDuplicado(usuario)
    nuevo = Usuario(
        nombre=nombre,
        usuario=usuario,
        password_hash=passwords.hashear(password),
        rol=rol,
        activo=True,
        version_sesion=1,
    )
    db.add(nuevo)
    try:
        db.commit()
    except IntegrityError as e:  # otro pedido lo creó justo antes: el índice único lo frena
        db.rollback()
        raise UsuarioDuplicado(usuario) from e
    db.refresh(nuevo)
    return nuevo


def actualizar(
    db: Session,
    usuario: Usuario,
    nombre: str | None = None,
    rol: str | None = None,
    activo: bool | None = None,
) -> Usuario:
    deja_de_ser_dueno_activo = (
        usuario.rol == ROL_DUENO
        and usuario.activo
        and ((rol is not None and rol != ROL_DUENO) or activo is False)
    )
    if deja_de_ser_dueno_activo and _duenos_activos(db) <= 1:
        raise UltimoDueno

    if nombre is not None:
        usuario.nombre = nombre
    if rol is not None:
        usuario.rol = rol
    if activo is not None:
        if usuario.activo and not activo:
            usuario.version_sesion += 1  # cierra las sesiones que tuviera abiertas
        usuario.activo = activo
    db.commit()
    db.refresh(usuario)
    return usuario


def cambiar_password(db: Session, usuario: Usuario, nueva: str) -> Usuario:
    usuario.password_hash = passwords.hashear(nueva)
    usuario.version_sesion += 1  # las demás sesiones abiertas dejan de valer
    db.commit()
    db.refresh(usuario)
    return usuario
