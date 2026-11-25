"""Operaciones sobre la base de datos para clientes y obras."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from presupuestos_backend.errores import ReglaDeNegocio
from presupuestos_backend.models import Cliente, Obra, Presupuesto
from presupuestos_backend.schemas_clientes import ClienteIn, ObraIn


def _patron(texto: str) -> str:
    """Texto a buscar con comodines; los '%' y '_' que escriba el usuario no valen como comodín."""
    escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


def listar_clientes(db: Session, buscar: str | None = None) -> list[tuple[Cliente, int]]:
    """Clientes con su cantidad de obras. Se busca por nombre, teléfono o dirección de sus obras."""
    stmt = (
        select(Cliente, func.count(Obra.id))
        .outerjoin(Obra, Obra.cliente_id == Cliente.id)
        .group_by(Cliente.id)
        .order_by(func.lower(Cliente.nombre), Cliente.id)
    )
    texto = (buscar or "").strip()
    if texto:
        patron = _patron(texto)
        en_obras = select(Obra.cliente_id).where(
            or_(
                Obra.direccion.ilike(patron, escape="\\"),
                Obra.referencia.ilike(patron, escape="\\"),
            )
        )
        stmt = stmt.where(
            or_(
                Cliente.nombre.ilike(patron, escape="\\"),
                Cliente.telefono.ilike(patron, escape="\\"),
                Cliente.id.in_(en_obras),
            )
        )
    return [(cliente, cantidad) for cliente, cantidad in db.execute(stmt).all()]


def obtener_cliente(db: Session, cliente_id: int) -> Cliente | None:
    return db.get(Cliente, cliente_id)


def crear_cliente(db: Session, datos: ClienteIn) -> Cliente:
    cliente = Cliente(**datos.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def actualizar_cliente(db: Session, cliente: Cliente, datos: ClienteIn) -> Cliente:
    for campo, valor in datos.model_dump().items():
        setattr(cliente, campo, valor)
    db.commit()
    db.refresh(cliente)
    return cliente


def _cantidad_de_presupuestos(db: Session, **filtro: int) -> int:
    condiciones = [getattr(Presupuesto, campo) == valor for campo, valor in filtro.items()]
    return db.scalar(select(func.count(Presupuesto.id)).where(*condiciones)) or 0


def eliminar_cliente(db: Session, cliente: Cliente) -> None:
    if cliente.obras:
        raise ReglaDeNegocio("Este cliente tiene obras cargadas. Borrá primero sus obras.")
    if _cantidad_de_presupuestos(db, cliente_id=cliente.id):
        raise ReglaDeNegocio(
            "Este cliente tiene presupuestos asociados, por eso no se puede borrar."
        )
    db.delete(cliente)
    db.commit()


def obtener_obra(db: Session, obra_id: int) -> Obra | None:
    return db.get(Obra, obra_id)


def crear_obra(db: Session, cliente: Cliente, datos: ObraIn) -> Obra:
    obra = Obra(cliente_id=cliente.id, **datos.model_dump())
    db.add(obra)
    db.commit()
    db.refresh(obra)
    return obra


def actualizar_obra(db: Session, obra: Obra, datos: ObraIn) -> Obra:
    for campo, valor in datos.model_dump().items():
        setattr(obra, campo, valor)
    db.commit()
    db.refresh(obra)
    return obra


def eliminar_obra(db: Session, obra: Obra) -> None:
    if _cantidad_de_presupuestos(db, obra_id=obra.id):
        raise ReglaDeNegocio("Esta obra tiene presupuestos asociados, por eso no se puede borrar.")
    db.delete(obra)
    db.commit()
