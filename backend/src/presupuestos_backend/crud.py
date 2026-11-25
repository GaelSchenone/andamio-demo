"""Operaciones sobre la base de datos para presupuestos."""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from presupuestos_backend.errores import ReglaDeNegocio, VinculoInvalido
from presupuestos_backend.models import (
    ESTADO_APROBADO,
    ESTADOS_PRESUPUESTO,
    Cliente,
    ItemPresupuesto,
    Obra,
    Presupuesto,
)
from presupuestos_backend.schemas import PresupuestoIn

CENTAVOS = Decimal("0.01")


def a_dinero(valor: float) -> Decimal:
    """Pasa un importe que llega como número a pesos con 2 decimales exactos.

    Se parte del texto del número (no de su representación binaria) y se redondea
    "como a mano": 10.005 -> 10.01.
    """
    return Decimal(str(valor)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _calcular_items(data: PresupuestoIn) -> tuple[list[ItemPresupuesto], Decimal]:
    items = []
    total = Decimal("0")
    for orden, item in enumerate(data.items):
        importe = a_dinero(item.importe)
        total += importe
        items.append(
            ItemPresupuesto(
                orden=orden,
                descripcion=item.descripcion,
                unidad=item.unidad,
                cantidad=item.cantidad,
                importe=importe,
            )
        )
    return items, total


def _validar_vinculo(db: Session, cliente_id: int | None, obra_id: int | None) -> None:
    """El cliente y la obra son opcionales, pero si vienen tienen que existir y corresponderse."""
    if cliente_id is None and obra_id is None:
        return
    if cliente_id is None:
        raise VinculoInvalido("Para elegir una obra hay que elegir primero el cliente.")
    if db.get(Cliente, cliente_id) is None:
        raise VinculoInvalido("El cliente elegido no existe.")
    if obra_id is not None:
        obra = db.get(Obra, obra_id)
        if obra is None or obra.cliente_id != cliente_id:
            raise VinculoInvalido("La obra elegida no existe o no es de ese cliente.")


def crear_presupuesto(db: Session, data: PresupuestoIn) -> Presupuesto:
    _validar_vinculo(db, data.cliente_id, data.obra_id)
    items, total = _calcular_items(data)
    presupuesto = Presupuesto(
        cliente_id=data.cliente_id,
        obra_id=data.obra_id,
        cliente_obra=data.cliente_obra,
        direccion=data.direccion,
        fecha_emision=data.fecha_emision,
        vigencia_dias=data.vigencia_dias,
        plazo_obra=data.plazo_obra,
        forma_pago=data.forma_pago,
        materiales_a_cargo=data.materiales_a_cargo,
        observaciones=data.observaciones,
        total=total,
        items=items,
    )
    db.add(presupuesto)
    db.commit()
    db.refresh(presupuesto)
    return presupuesto


def actualizar_presupuesto(
    db: Session, presupuesto: Presupuesto, data: PresupuestoIn
) -> Presupuesto:
    if presupuesto.estado == ESTADO_APROBADO:
        raise ReglaDeNegocio(
            "Un presupuesto aprobado no se puede editar. "
            "Pasalo a otro estado si hay que modificarlo."
        )
    _validar_vinculo(db, data.cliente_id, data.obra_id)
    items, total = _calcular_items(data)
    presupuesto.cliente_id = data.cliente_id
    presupuesto.obra_id = data.obra_id
    presupuesto.cliente_obra = data.cliente_obra
    presupuesto.direccion = data.direccion
    presupuesto.fecha_emision = data.fecha_emision
    presupuesto.vigencia_dias = data.vigencia_dias
    presupuesto.plazo_obra = data.plazo_obra
    presupuesto.forma_pago = data.forma_pago
    presupuesto.materiales_a_cargo = data.materiales_a_cargo
    presupuesto.observaciones = data.observaciones
    presupuesto.total = total
    presupuesto.items = items
    db.commit()
    db.refresh(presupuesto)
    return presupuesto


def listar_presupuestos(db: Session, buscar: str | None = None) -> list[Presupuesto]:
    # Se cargan los trabajos de una vez: el listado muestra si cada presupuesto ya tiene uno.
    stmt = (
        select(Presupuesto)
        .options(selectinload(Presupuesto.trabajos))
        .order_by(Presupuesto.id.desc())
    )
    if buscar:
        stmt = stmt.where(Presupuesto.cliente_obra.ilike(f"%{buscar}%"))
    return list(db.scalars(stmt))


def obtener_presupuesto(db: Session, presupuesto_id: int) -> Presupuesto | None:
    return db.get(Presupuesto, presupuesto_id)


def eliminar_presupuesto(db: Session, presupuesto: Presupuesto) -> None:
    if presupuesto.estado == ESTADO_APROBADO:
        raise ReglaDeNegocio(
            "Un presupuesto aprobado no se puede eliminar. Pasalo a otro estado primero."
        )
    if presupuesto.trabajos:
        raise ReglaDeNegocio(
            "Este presupuesto tiene trabajos asociados, por eso no se puede eliminar."
        )
    db.delete(presupuesto)
    db.commit()


def cambiar_estado(db: Session, presupuesto: Presupuesto, estado: str) -> Presupuesto:
    """Mueve el presupuesto a otro estado. Se puede pasar libremente de uno a otro, salvo:

    - para aprobarlo hace falta cliente y obra (todo trabajo tiene que tener adónde ir);
    - si ya tiene un trabajo vigente, no se le puede sacar la aprobación (primero se cancela
      el trabajo).
    """
    if estado not in ESTADOS_PRESUPUESTO:
        raise ReglaDeNegocio("Estado desconocido.")
    if estado == presupuesto.estado:
        return presupuesto
    if estado == ESTADO_APROBADO and presupuesto.obra_id is None:
        raise ReglaDeNegocio("Para aprobar el presupuesto elegí primero el cliente y la obra.")
    if presupuesto.estado == ESTADO_APROBADO and presupuesto.trabajo_id is not None:
        raise ReglaDeNegocio(
            "Este presupuesto ya tiene un trabajo. Cancelá el trabajo antes de cambiarle el estado."
        )
    presupuesto.estado = estado
    db.commit()
    db.refresh(presupuesto)
    return presupuesto
