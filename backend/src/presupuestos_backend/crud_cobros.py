"""Cobros: la plata recibida por cada trabajo.

Lo que se cobra es el total del presupuesto. Según el negocio se paga 50% al empezar (seña) y
50% al terminar (saldo): el sistema lo sugiere, pero acepta otros montos. Un trabajo pasa a
"cobrado" cuando está terminado y pagado por completo. Todo es con `Decimal`, nunca con `float`.
"""

import datetime as dt
import threading
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from presupuestos_backend.crud import CENTAVOS, a_dinero
from presupuestos_backend.errores import ReglaDeNegocio
from presupuestos_backend.formato import moneda
from presupuestos_backend.models import (
    ESTADO_TRABAJO_CANCELADO,
    ESTADO_TRABAJO_COBRADO,
    ESTADO_TRABAJO_TERMINADO,
    Cobro,
    Presupuesto,
    Trabajo,
    Usuario,
    ahora_utc,
)

CERO = Decimal("0.00")

# Mientras la app corra en un solo proceso (como hoy), este candado hace que "ver cuánto falta
# cobrar" y "guardar el cobro" sean una sola operación: no se cobra de más con dos pedidos a la vez.
_candado_cobros = threading.Lock()


def vigentes(trabajo: Trabajo) -> list[Cobro]:
    """Los cobros que cuentan: los anulados no."""
    return [c for c in trabajo.cobros if not c.anulado]


def total_a_cobrar(trabajo: Trabajo) -> Decimal:
    return trabajo.presupuesto.total


def total_cobrado(trabajo: Trabajo) -> Decimal:
    return sum((c.monto for c in vigentes(trabajo)), CERO)


def pendiente(trabajo: Trabajo) -> Decimal:
    return total_a_cobrar(trabajo) - total_cobrado(trabajo)


@dataclass(frozen=True)
class Resumen:
    total: Decimal
    cobrado: Decimal
    pendiente: Decimal
    sugerido_sena: Decimal
    sugerido_saldo: Decimal
    cobros: list[Cobro]


def resumen(trabajo: Trabajo) -> Resumen:
    total = total_a_cobrar(trabajo)
    falta = pendiente(trabajo)
    mitad = (total / 2).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    sena_cobrada = sum((c.monto for c in vigentes(trabajo) if c.concepto == "sena"), CERO)
    # La seña sugerida es la mitad que todavía no se cobró como seña, sin pasarse de lo que falta.
    sugerido_sena = max(CERO, min(mitad - sena_cobrada, falta))
    return Resumen(total, total_cobrado(trabajo), falta, sugerido_sena, falta, list(trabajo.cobros))


def recalcular_estado(db: Session, trabajo: Trabajo) -> None:
    """Un trabajo terminado y pagado por completo pasa a "cobrado"; si deja de estarlo, vuelve."""
    db.expire(trabajo, ["cobros"])  # que vea los cobros que acaban de guardarse
    if trabajo.estado == ESTADO_TRABAJO_TERMINADO and pendiente(trabajo) <= 0:
        trabajo.estado = ESTADO_TRABAJO_COBRADO
    elif trabajo.estado == ESTADO_TRABAJO_COBRADO and pendiente(trabajo) > 0:
        trabajo.estado = ESTADO_TRABAJO_TERMINADO
    else:
        return
    db.commit()
    db.refresh(trabajo)


def registrar(
    db: Session,
    trabajo: Trabajo,
    concepto: str,
    monto: float,
    fecha: dt.date,
    nota: str,
    usuario: Usuario,
) -> Trabajo:
    if trabajo.estado == ESTADO_TRABAJO_CANCELADO:
        raise ReglaDeNegocio("No se pueden registrar cobros en un trabajo cancelado.")
    importe = a_dinero(monto)
    if importe <= 0:
        raise ReglaDeNegocio("El monto tiene que ser mayor a cero.")
    if fecha > ahora_utc().date():
        raise ReglaDeNegocio("La fecha del cobro no puede ser futura.")

    with _candado_cobros:
        db.expire(trabajo, ["cobros"])  # por si otro pedido cobró mientras tanto
        falta = pendiente(trabajo)
        if importe > falta:
            raise ReglaDeNegocio(f"El cobro supera lo que falta cobrar ($ {moneda(falta)}).")
        db.add(
            Cobro(
                trabajo_id=trabajo.id,
                concepto=concepto,
                monto=importe,
                fecha=fecha,
                nota=nota,
                usuario_id=usuario.id,
            )
        )
        db.commit()
    db.refresh(trabajo)
    recalcular_estado(db, trabajo)
    return trabajo


def obtener_cobro(db: Session, cobro_id: int) -> Cobro | None:
    return db.get(Cobro, cobro_id)


def anular(db: Session, cobro: Cobro, usuario: Usuario) -> Trabajo:
    """Anula un cobro cargado por error (o devuelto). Queda registrado y deja de contar."""
    if cobro.anulado:
        raise ReglaDeNegocio("Este cobro ya estaba anulado.")
    cobro.anulado_en = ahora_utc()
    cobro.anulado_por_id = usuario.id
    db.commit()
    trabajo = cobro.trabajo
    db.refresh(trabajo)
    recalcular_estado(db, trabajo)
    return trabajo


def pendientes(db: Session) -> list[Trabajo]:
    """Trabajos a los que todavía les falta cobrar algo: primero los ya terminados (se deben ya)."""
    trabajos = db.scalars(
        select(Trabajo)
        .options(
            selectinload(Trabajo.cobros),
            selectinload(Trabajo.presupuesto).selectinload(Presupuesto.cliente),
            selectinload(Trabajo.presupuesto).selectinload(Presupuesto.obra),
        )
        .where(Trabajo.estado.not_in([ESTADO_TRABAJO_CANCELADO, ESTADO_TRABAJO_COBRADO]))
    )
    con_saldo = [t for t in trabajos if pendiente(t) > 0]
    con_saldo.sort(
        key=lambda t: (
            0 if t.estado == ESTADO_TRABAJO_TERMINADO else 1,
            t.fecha_inicio or dt.date.max,
            t.id,
        )
    )
    return con_saldo
