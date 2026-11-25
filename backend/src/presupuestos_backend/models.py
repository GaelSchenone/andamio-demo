"""Modelos de la base de datos: un Presupuesto tiene varios Items."""

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from presupuestos_backend.database import Base

FORMA_PAGO_DEFAULT = "50% al iniciar y 50% al finalizar"
MATERIALES_DEFAULT = "Cliente"
OBSERVACIONES_DEFAULT = (
    "El presupuesto contempla exclusivamente los trabajos detallados anteriormente.\n"
    "Cualquier trabajo adicional será presupuestado por separado."
)
VIGENCIA_DEFAULT = 15

# Estados de un presupuesto: se mueve libremente entre ellos, con las reglas de crud.cambiar_estado.
ESTADO_BORRADOR = "borrador"
ESTADO_APROBADO = "aprobado"
ESTADOS_PRESUPUESTO = (ESTADO_BORRADOR, "enviado", ESTADO_APROBADO, "rechazado")

# Estados de un trabajo. Hoy solo se crea "por agendar" y se puede cancelar; el resto
# (agendado, en curso, terminado, cobrado) se usa desde el calendario (punto 4 del roadmap).
ESTADO_TRABAJO_POR_AGENDAR = "por_agendar"
ESTADO_TRABAJO_CANCELADO = "cancelado"
ESTADO_TRABAJO_AGENDADO = "agendado"
ESTADO_TRABAJO_EN_CURSO = "en_curso"
ESTADO_TRABAJO_TERMINADO = "terminado"
ESTADO_TRABAJO_COBRADO = "cobrado"  # terminado y pagado por completo (lo asigna crud_cobros)
ESTADOS_TRABAJO = (
    ESTADO_TRABAJO_POR_AGENDAR,
    ESTADO_TRABAJO_AGENDADO,
    ESTADO_TRABAJO_EN_CURSO,
    ESTADO_TRABAJO_TERMINADO,
    ESTADO_TRABAJO_COBRADO,
    ESTADO_TRABAJO_CANCELADO,
)
CONCEPTOS_COBRO = ("sena", "saldo")
# Por qué se movió un trabajo de fecha (para el historial y, más adelante, reportes).
CAUSAS_REPROGRAMACION = ("clima", "cliente", "materiales", "otra")

# Dinero: hasta 999.999.999.999,99 con dos decimales exactos (no usar Float para plata).
DINERO = Numeric(14, 2)


def _ahora_utc() -> dt.datetime:
    """Hora UTC sin zona horaria: es lo que guarda la columna (mismo criterio que antes)."""
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


ahora_utc = _ahora_utc  # nombre público, para los servicios que registran cuándo pasó algo


class Presupuesto(Base):
    __tablename__ = "presupuestos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_obra: Mapped[str] = mapped_column(String(200))
    direccion: Mapped[str] = mapped_column(String(300), default="")
    fecha_emision: Mapped[dt.date] = mapped_column(Date)
    vigencia_dias: Mapped[int] = mapped_column(Integer, default=VIGENCIA_DEFAULT)
    plazo_obra: Mapped[str] = mapped_column(String(200), default="")
    forma_pago: Mapped[str] = mapped_column(String(300), default=FORMA_PAGO_DEFAULT)
    materiales_a_cargo: Mapped[str] = mapped_column(String(100), default=MATERIALES_DEFAULT)
    observaciones: Mapped[str] = mapped_column(Text, default=OBSERVACIONES_DEFAULT)
    total: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=_ahora_utc)
    estado: Mapped[str] = mapped_column(
        String(20), default=ESTADO_BORRADOR, server_default=ESTADO_BORRADOR
    )
    # Vínculo con el cliente y la obra. Opcional: los presupuestos viejos solo tienen el texto libre
    # `cliente_obra`. Para aprobar un presupuesto sí hace falta (ver crud.cambiar_estado).
    cliente_id: Mapped[int | None] = mapped_column(
        ForeignKey("clientes.id"), default=None, index=True
    )
    obra_id: Mapped[int | None] = mapped_column(ForeignKey("obras.id"), default=None, index=True)

    items: Mapped[list["ItemPresupuesto"]] = relationship(
        back_populates="presupuesto",
        cascade="all, delete-orphan",
        order_by="ItemPresupuesto.orden",
    )

    trabajos: Mapped[list["Trabajo"]] = relationship(
        back_populates="presupuesto", order_by="Trabajo.id"
    )
    cliente: Mapped["Cliente | None"] = relationship()
    obra: Mapped["Obra | None"] = relationship()

    @property
    def numero(self) -> str:
        return f"{self.id:04d}"

    @property
    def trabajo_id(self) -> int | None:
        """El trabajo vigente de este presupuesto (el que no fue cancelado), si lo hay."""
        for trabajo in self.trabajos:
            if trabajo.estado != ESTADO_TRABAJO_CANCELADO:
                return trabajo.id
        return None


class ItemPresupuesto(Base):
    __tablename__ = "items_presupuesto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuestos.id"))
    orden: Mapped[int] = mapped_column(Integer, default=0)
    descripcion: Mapped[str] = mapped_column(String(500))
    unidad: Mapped[str] = mapped_column(String(50), default="")
    cantidad: Mapped[float] = mapped_column(Float, default=1)
    importe: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))

    presupuesto: Mapped[Presupuesto] = relationship(back_populates="items")


class Usuario(Base):
    """Quien entra a la app. No se borra: se desactiva (así queda la historia de quién hizo qué)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    # Nombre para entrar: minúsculas, sin tildes ni espacios (ver schemas_usuarios.PATRON_USUARIO).
    usuario: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Va dentro de la cookie de sesión: al subirlo, todas las sesiones abiertas de este usuario
    # dejan de valer (cambio de contraseña, desactivación).
    version_sesion: Mapped[int] = mapped_column(Integer, default=1)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=_ahora_utc)


class Cliente(Base):
    """Persona o consorcio que contrata trabajos. Son datos personales (Ley 25.326): lo mínimo."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    tipo: Mapped[str] = mapped_column(String(20))  # "casa" | "consorcio"
    telefono: Mapped[str] = mapped_column(String(40), default="")
    notas: Mapped[str] = mapped_column(Text, default="")
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=_ahora_utc)

    obras: Mapped[list["Obra"]] = relationship(back_populates="cliente", order_by="Obra.id")


class Obra(Base):
    """Lugar donde se trabaja (la dirección). Un cliente puede tener varias."""

    __tablename__ = "obras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    direccion: Mapped[str] = mapped_column(String(300))
    # Para distinguir obras del mismo cliente: "Depto 3B", "Hall y escaleras", "Fondo".
    referencia: Mapped[str] = mapped_column(String(100), default="")
    # Datos útiles en obra: "timbre roto, llamar", "llave con el encargado".
    notas: Mapped[str] = mapped_column(Text, default="")
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=_ahora_utc)

    cliente: Mapped[Cliente] = relationship(back_populates="obras")


class Trabajo(Base):
    """Un trabajo a realizar, nacido de un presupuesto aprobado.

    No guarda precios ni datos del cliente: se leen del presupuesto, la obra y el cliente. Así la
    API de trabajos (que ve también el empleado) no puede filtrar importes por descuido.
    """

    __tablename__ = "trabajos"
    __table_args__ = (
        # Un presupuesto puede tener varios trabajos a lo largo del tiempo (si se cancela uno se
        # puede crear otro), pero a lo sumo UNO vigente. La base lo garantiza aunque se toque el
        # botón dos veces a la vez.
        Index(
            "uq_trabajo_vigente_por_presupuesto",
            "presupuesto_id",
            unique=True,
            sqlite_where=text("estado != 'cancelado'"),
            postgresql_where=text("estado != 'cancelado'"),
        ),
        # Las dos fechas van juntas (o ninguna: "por agendar") y el fin no puede ser anterior
        # al inicio.
        CheckConstraint(
            "(fecha_inicio IS NULL AND fecha_fin IS NULL) OR "
            "(fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL AND fecha_fin >= fecha_inicio)",
            name="ck_trabajo_fechas_coherentes",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuestos.id"))
    estado: Mapped[str] = mapped_column(String(20), default=ESTADO_TRABAJO_POR_AGENDAR)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=_ahora_utc)
    # Días de trabajo, ambos inclusive. Vacíos mientras el trabajo está "por agendar".
    fecha_inicio: Mapped[dt.date | None] = mapped_column(Date, default=None)
    fecha_fin: Mapped[dt.date | None] = mapped_column(Date, default=None)
    iniciado_en: Mapped[dt.datetime | None] = mapped_column(DateTime, default=None)
    terminado_en: Mapped[dt.datetime | None] = mapped_column(DateTime, default=None)

    presupuesto: Mapped[Presupuesto] = relationship(back_populates="trabajos")
    reprogramaciones: Mapped[list["Reprogramacion"]] = relationship(
        back_populates="trabajo", order_by="Reprogramacion.id"
    )
    cobros: Mapped[list["Cobro"]] = relationship(back_populates="trabajo", order_by="Cobro.id")
    # Días del tramo (de fecha_inicio a fecha_fin) en los que NO se trabaja.
    # Vacío = trabajo de corrido.
    dias_sin_trabajo: Mapped[list["DiaSinTrabajo"]] = relationship(
        back_populates="trabajo",
        order_by="DiaSinTrabajo.fecha",
        cascade="all, delete-orphan",
    )


class DiaSinTrabajo(Base):
    """Un día dentro del tramo de un trabajo en el que no se trabaja (por ejemplo, ocupa otro).

    Un trabajo ocupa los días de `fecha_inicio` a `fecha_fin` menos estos. Así los trabajos que no
    son de corrido (lunes, martes y jueves) caben en la agenda sin pisar a otros.
    """

    __tablename__ = "trabajo_dias_sin_trabajo"
    __table_args__ = (UniqueConstraint("trabajo_id", "fecha", name="uq_dia_sin_trabajo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trabajo_id: Mapped[int] = mapped_column(ForeignKey("trabajos.id"), index=True)
    fecha: Mapped[dt.date] = mapped_column(Date)

    trabajo: Mapped[Trabajo] = relationship(back_populates="dias_sin_trabajo")


class Reprogramacion(Base):
    """Historial de cambios de fecha de un trabajo: de cuándo a cuándo, por qué y quién."""

    __tablename__ = "reprogramaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trabajo_id: Mapped[int] = mapped_column(ForeignKey("trabajos.id"), index=True)
    fecha_inicio_anterior: Mapped[dt.date] = mapped_column(Date)
    fecha_fin_anterior: Mapped[dt.date] = mapped_column(Date)
    fecha_inicio_nueva: Mapped[dt.date] = mapped_column(Date)
    fecha_fin_nueva: Mapped[dt.date] = mapped_column(Date)
    causa: Mapped[str] = mapped_column(String(20))  # una de CAUSAS_REPROGRAMACION
    motivo: Mapped[str] = mapped_column(Text)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=_ahora_utc)

    trabajo: Mapped[Trabajo] = relationship(back_populates="reprogramaciones")
    usuario: Mapped[Usuario] = relationship()


class Cobro(Base):
    """Un pago recibido por un trabajo (seña o saldo).

    No se edita ni se borra: si se cargó mal, se anula (queda registrado quién y cuándo) y deja de
    contar. Así el historial de plata siempre se puede reconstruir.
    """

    __tablename__ = "cobros"
    __table_args__ = (CheckConstraint("monto > 0", name="ck_cobro_monto_positivo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trabajo_id: Mapped[int] = mapped_column(ForeignKey("trabajos.id"), index=True)
    concepto: Mapped[str] = mapped_column(String(10))  # "sena" | "saldo"
    monto: Mapped[Decimal] = mapped_column(DINERO)
    fecha: Mapped[dt.date] = mapped_column(Date)  # cuándo se recibió el pago
    nota: Mapped[str] = mapped_column(Text, default="")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))  # quién lo registró
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=_ahora_utc)
    anulado_en: Mapped[dt.datetime | None] = mapped_column(DateTime, default=None)
    anulado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), default=None)

    trabajo: Mapped[Trabajo] = relationship(back_populates="cobros")
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])

    @property
    def anulado(self) -> bool:
        return self.anulado_en is not None
