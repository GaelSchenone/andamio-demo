"""Esquemas de trabajos.

A propósito NO incluyen importes, total ni forma de pago: un trabajo lo ve también el empleado,
que no tiene que ver precios. Al no estar en el esquema, no se pueden filtrar por descuido.
"""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from presupuestos_backend.schemas_clientes import TipoCliente

CausaReprogramacion = Literal["clima", "cliente", "materiales", "otra"]


class ClienteDelTrabajo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo: TipoCliente
    telefono: str


class ObraDelTrabajo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    direccion: str
    referencia: str
    notas: str


class TareaDelTrabajo(BaseModel):
    """Qué hay que hacer (una línea del presupuesto), sin su precio."""

    model_config = ConfigDict(from_attributes=True)

    descripcion: str
    unidad: str
    cantidad: float


class TrabajoOut(BaseModel):
    id: int
    estado: str
    creado_en: dt.datetime
    fecha_inicio: dt.date | None  # vacías mientras está "por agendar"; ambos días inclusive
    fecha_fin: dt.date | None
    # Los días en que de verdad se trabaja (si es de corrido, todos los del tramo).
    # Vacío mientras está "por agendar".
    dias: list[dt.date]
    presupuesto_id: int
    presupuesto_numero: str
    cliente: ClienteDelTrabajo
    obra: ObraDelTrabajo
    tareas: list[TareaDelTrabajo]
    plazo_obra: str
    materiales_a_cargo: str


class AgendarIn(BaseModel):
    """Se piden los días de trabajo (`dias`, pueden no ser seguidos) o un tramo de corrido."""

    fecha_inicio: dt.date | None = None
    fecha_fin: dt.date | None = None
    dias: list[dt.date] | None = Field(default=None, max_length=366)

    @model_validator(mode="after")
    def _completar_el_tramo(self):
        if self.dias is not None:
            if not self.dias:
                raise ValueError("Elegí al menos un día.")
            self.fecha_inicio, self.fecha_fin = min(self.dias), max(self.dias)
        elif self.fecha_inicio is None or self.fecha_fin is None:
            raise ValueError("Faltan los días del trabajo.")
        return self


class ReprogramarIn(AgendarIn):
    causa: CausaReprogramacion
    # El detalle es opcional: se puede reprogramar por cualquier motivo, sin tener que explicarlo.
    # La causa (una elección de un toque) alcanza para que el historial sirva.
    motivo: str = Field(default="", max_length=500)

    @field_validator("motivo", mode="before")
    @classmethod
    def _sin_espacios_de_mas(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor


class ReprogramacionOut(BaseModel):
    id: int
    fecha_inicio_anterior: dt.date
    fecha_fin_anterior: dt.date
    fecha_inicio_nueva: dt.date
    fecha_fin_nueva: dt.date
    causa: CausaReprogramacion
    motivo: str
    usuario_nombre: str
    creado_en: dt.datetime
