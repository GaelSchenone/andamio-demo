"""Esquemas de cobros. Solo los ve el dueño: el empleado nunca ve plata."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from presupuestos_backend.schemas import IMPORTE_MAXIMO

Concepto = Literal["sena", "saldo"]


class CobroIn(BaseModel):
    concepto: Concepto
    monto: float = Field(gt=0, le=IMPORTE_MAXIMO)
    fecha: dt.date
    nota: str = Field(default="", max_length=500)

    @field_validator("nota", mode="before")
    @classmethod
    def _sin_espacios_de_mas(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor


class CobroOut(BaseModel):
    id: int
    concepto: Concepto
    monto: float
    fecha: dt.date
    nota: str
    usuario_nombre: str  # quién lo registró
    creado_en: dt.datetime
    anulado: bool
    anulado_en: dt.datetime | None


class ResumenDeCobros(BaseModel):
    trabajo_id: int
    estado_trabajo: str
    total: float  # lo que hay que cobrar: el total del presupuesto
    cobrado: float
    pendiente: float
    sugerido_sena: float  # la mitad que todavía no se cobró como seña
    sugerido_saldo: float  # todo lo que falta
    cobros: list[CobroOut]


class PendienteOut(BaseModel):
    trabajo_id: int
    cliente: str
    direccion: str
    referencia: str
    estado: str
    fecha_inicio: dt.date | None
    fecha_fin: dt.date | None
    total: float
    cobrado: float
    pendiente: float


class PendientesOut(BaseModel):
    total_pendiente: float
    trabajos: list[PendienteOut]
