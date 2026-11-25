"""Operaciones sobre la base de datos para trabajos y su calendario.

Ciclo de un trabajo:  por agendar -> agendado -> en curso -> terminado   (y "cancelado" mientras
no empezó). "Cobrado" lo asigna el módulo de cobros, que todavía no existe.
"""

import datetime as dt
import threading

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from presupuestos_backend import crud_cobros
from presupuestos_backend.errores import ReglaDeNegocio
from presupuestos_backend.formato import fecha_larga
from presupuestos_backend.models import (
    ESTADO_APROBADO,
    ESTADO_TRABAJO_AGENDADO,
    ESTADO_TRABAJO_CANCELADO,
    ESTADO_TRABAJO_EN_CURSO,
    ESTADO_TRABAJO_POR_AGENDAR,
    ESTADO_TRABAJO_TERMINADO,
    DiaSinTrabajo,
    Presupuesto,
    Reprogramacion,
    Trabajo,
    Usuario,
    ahora_utc,
)

YA_TIENE_TRABAJO = "Este presupuesto ya tiene un trabajo."
MAX_DIAS_DE_TRABAJO = 366

# Mientras la app corra en un solo proceso (como hoy), este candado hace que "revisar si la agenda
# está libre" y "guardar las fechas" sean una sola operación. Con más de un proceso haría falta una
# restricción de exclusión en la base de datos (ver docs/architecture.md, deuda técnica).
_candado_agenda = threading.Lock()


def _cargar_relaciones():
    return (
        selectinload(Trabajo.presupuesto).selectinload(Presupuesto.items),
        selectinload(Trabajo.presupuesto).selectinload(Presupuesto.cliente),
        selectinload(Trabajo.presupuesto).selectinload(Presupuesto.obra),
        selectinload(Trabajo.dias_sin_trabajo),
    )


def listar(
    db: Session,
    incluir_cancelados: bool = False,
    desde: dt.date | None = None,
    hasta: dt.date | None = None,
) -> list[Trabajo]:
    """Trabajos más nuevos primero; con `desde`/`hasta`, los que caen en ese rango, por fecha."""
    stmt = select(Trabajo).options(*_cargar_relaciones())
    if not incluir_cancelados:
        stmt = stmt.where(Trabajo.estado != ESTADO_TRABAJO_CANCELADO)
    if desde is not None:
        stmt = stmt.where(Trabajo.fecha_fin >= desde)  # sin fechas (por agendar) queda afuera
    if hasta is not None:
        stmt = stmt.where(Trabajo.fecha_inicio <= hasta)
    if desde is not None or hasta is not None:
        stmt = stmt.order_by(Trabajo.fecha_inicio, Trabajo.id)
    else:
        stmt = stmt.order_by(Trabajo.id.desc())
    return list(db.scalars(stmt))


def obtener(db: Session, trabajo_id: int) -> Trabajo | None:
    return db.get(Trabajo, trabajo_id)


def crear_desde_presupuesto(db: Session, presupuesto: Presupuesto) -> Trabajo:
    """Pasa un presupuesto aprobado a trabajo (queda "por agendar")."""
    if presupuesto.estado != ESTADO_APROBADO:
        raise ReglaDeNegocio("Solo se puede pasar a trabajo un presupuesto aprobado.")
    if presupuesto.trabajo_id is not None:
        raise ReglaDeNegocio(YA_TIENE_TRABAJO)

    trabajo = Trabajo(presupuesto_id=presupuesto.id, estado=ESTADO_TRABAJO_POR_AGENDAR)
    db.add(trabajo)
    try:
        db.commit()
    except IntegrityError as e:
        # Dos pedidos a la vez: el índice único de la base dejó pasar solo al primero.
        db.rollback()
        raise ReglaDeNegocio(YA_TIENE_TRABAJO) from e
    db.refresh(trabajo)
    return trabajo


# --- Calendario ---------------------------------------------------------------------------------


def _dias_entre(inicio: dt.date, fin: dt.date) -> list[dt.date]:
    return [inicio + dt.timedelta(days=n) for n in range((fin - inicio).days + 1)]


def dias_trabajados(trabajo: Trabajo) -> list[dt.date]:
    """Los días en que el trabajo ocupa la agenda: su tramo menos los días sin trabajo."""
    if trabajo.fecha_inicio is None or trabajo.fecha_fin is None:
        return []
    libres = {d.fecha for d in trabajo.dias_sin_trabajo}
    return [d for d in _dias_entre(trabajo.fecha_inicio, trabajo.fecha_fin) if d not in libres]


def _resolver_dias(inicio: dt.date, fin: dt.date, dias: list[dt.date] | None) -> set[dt.date]:
    """Los días de trabajo pedidos. Sin lista, el trabajo es de corrido de `inicio` a `fin`."""
    _validar_fechas(inicio, fin)
    if dias is None:
        return set(_dias_entre(inicio, fin))
    elegidos = set(dias)
    if (
        inicio not in elegidos
        or fin not in elegidos
        or min(elegidos) < inicio
        or max(elegidos) > fin
    ):
        raise ReglaDeNegocio(
            "El primer y el último día del trabajo tienen que ser días de trabajo."
        )
    return elegidos


def _guardar_dias(
    db: Session, trabajo: Trabajo, inicio: dt.date, fin: dt.date, dias: set[dt.date]
) -> None:
    trabajo.fecha_inicio = inicio
    trabajo.fecha_fin = fin
    sin_trabajo = sorted(set(_dias_entre(inicio, fin)) - dias)
    # Primero se borran los días anteriores: si no, al insertar los nuevos chocarían con la
    # restricción de únicos (la base ejecuta los INSERT antes que los DELETE).
    trabajo.dias_sin_trabajo.clear()
    db.flush()
    trabajo.dias_sin_trabajo = [DiaSinTrabajo(fecha=d) for d in sin_trabajo]


def _validar_fechas(inicio: dt.date, fin: dt.date) -> None:
    if fin < inicio:
        raise ReglaDeNegocio("La fecha de fin no puede ser anterior a la de inicio.")
    if (fin - inicio).days + 1 > MAX_DIAS_DE_TRABAJO:
        raise ReglaDeNegocio(f"Un trabajo no puede durar más de {MAX_DIAS_DE_TRABAJO} días.")


def _verificar_agenda_libre(db: Session, trabajo: Trabajo, dias: set[dt.date]) -> None:
    """Agenda única: dos trabajos no pueden compartir ningún día (los extremos cuentan).

    Un trabajo que termina el 10 y otro que empieza el 11 no se pisan, ni uno que trabaja el 13 y el
    14 con otro que trabaja el 15. Los cancelados y los que todavía no tienen fechas no ocupan
    lugar.
    Si Q-01 de docs/decisiones.md cambia (por ejemplo, permitir dos trabajos chicos el mismo día),
    este es el único lugar a tocar.
    """
    candidatos = db.scalars(
        select(Trabajo)
        .options(*_cargar_relaciones())
        .where(
            Trabajo.id != trabajo.id,
            Trabajo.estado != ESTADO_TRABAJO_CANCELADO,
            Trabajo.fecha_inicio.is_not(None),
            Trabajo.fecha_inicio <= max(dias),
            Trabajo.fecha_fin >= min(dias),
        )
        .order_by(Trabajo.fecha_inicio)
    ).all()
    for otro in candidatos:
        if dias & set(dias_trabajados(otro)):
            presupuesto = otro.presupuesto
            raise ReglaDeNegocio(
                f"Esas fechas se superponen con el trabajo de {presupuesto.cliente.nombre} en "
                f"{presupuesto.obra.direccion} (del {fecha_larga(otro.fecha_inicio)} "
                f"al {fecha_larga(otro.fecha_fin)})."
            )


def agendar(
    db: Session,
    trabajo: Trabajo,
    inicio: dt.date,
    fin: dt.date,
    dias: list[dt.date] | None = None,
) -> Trabajo:
    if trabajo.estado == ESTADO_TRABAJO_CANCELADO:
        raise ReglaDeNegocio("Un trabajo cancelado no se puede agendar.")
    if trabajo.estado != ESTADO_TRABAJO_POR_AGENDAR:
        raise ReglaDeNegocio("Este trabajo ya fue agendado. Para cambiarle la fecha, reprogramalo.")
    elegidos = _resolver_dias(inicio, fin, dias)
    with _candado_agenda:
        _verificar_agenda_libre(db, trabajo, elegidos)
        _guardar_dias(db, trabajo, inicio, fin, elegidos)
        trabajo.estado = ESTADO_TRABAJO_AGENDADO
        db.commit()
    db.refresh(trabajo)
    return trabajo


def reprogramar(
    db: Session,
    trabajo: Trabajo,
    inicio: dt.date,
    fin: dt.date,
    causa: str,
    motivo: str,
    usuario: Usuario,
    dias: list[dt.date] | None = None,
) -> Trabajo:
    """Cambia las fechas de un trabajo agendado o en curso y deja constancia de por qué y quién."""
    if trabajo.estado not in (ESTADO_TRABAJO_AGENDADO, ESTADO_TRABAJO_EN_CURSO):
        raise ReglaDeNegocio("Solo se puede reprogramar un trabajo agendado o en curso.")
    if trabajo.estado == ESTADO_TRABAJO_EN_CURSO and inicio != trabajo.fecha_inicio:
        raise ReglaDeNegocio("El trabajo ya empezó: solo se puede cambiar la fecha de fin.")
    elegidos = _resolver_dias(inicio, fin, dias)
    if elegidos == set(dias_trabajados(trabajo)):
        raise ReglaDeNegocio("Las fechas son las mismas que ya tiene el trabajo.")
    with _candado_agenda:
        _verificar_agenda_libre(db, trabajo, elegidos)
        db.add(
            Reprogramacion(
                trabajo_id=trabajo.id,
                fecha_inicio_anterior=trabajo.fecha_inicio,
                fecha_fin_anterior=trabajo.fecha_fin,
                fecha_inicio_nueva=inicio,
                fecha_fin_nueva=fin,
                causa=causa,
                motivo=motivo,
                usuario_id=usuario.id,
            )
        )
        _guardar_dias(db, trabajo, inicio, fin, elegidos)
        db.commit()
    db.refresh(trabajo)
    return trabajo


def iniciar(db: Session, trabajo: Trabajo) -> Trabajo:
    if trabajo.estado != ESTADO_TRABAJO_AGENDADO:
        raise ReglaDeNegocio("Solo se puede iniciar un trabajo que está agendado.")
    trabajo.estado = ESTADO_TRABAJO_EN_CURSO
    trabajo.iniciado_en = ahora_utc()
    db.commit()
    db.refresh(trabajo)
    return trabajo


def terminar(db: Session, trabajo: Trabajo) -> Trabajo:
    """Se puede terminar un trabajo en curso, o uno agendado si se olvidaron de iniciarlo."""
    if trabajo.estado not in (ESTADO_TRABAJO_AGENDADO, ESTADO_TRABAJO_EN_CURSO):
        raise ReglaDeNegocio("Solo se puede terminar un trabajo agendado o en curso.")
    ahora = ahora_utc()
    trabajo.estado = ESTADO_TRABAJO_TERMINADO
    trabajo.iniciado_en = trabajo.iniciado_en or ahora
    trabajo.terminado_en = ahora
    db.commit()
    db.refresh(trabajo)
    crud_cobros.recalcular_estado(db, trabajo)  # si ya estaba todo pagado, pasa a "cobrado"
    return trabajo


def cancelar(db: Session, trabajo: Trabajo) -> Trabajo:
    """Se cancela mientras no empezó. Al cancelar, las fechas quedan libres para otro trabajo."""
    if trabajo.estado not in (ESTADO_TRABAJO_POR_AGENDAR, ESTADO_TRABAJO_AGENDADO):
        raise ReglaDeNegocio("Solo se puede cancelar un trabajo que todavía no empezó.")
    if crud_cobros.vigentes(trabajo):
        raise ReglaDeNegocio(
            "Este trabajo tiene cobros registrados. Anulalos primero si hay que devolver el dinero."
        )
    trabajo.estado = ESTADO_TRABAJO_CANCELADO
    db.commit()
    db.refresh(trabajo)
    return trabajo


def historial(trabajo: Trabajo) -> list[Reprogramacion]:
    return list(trabajo.reprogramaciones)
