"""Esquemas Pydantic: forma de los datos que entran y salen de la API."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from presupuestos_backend.models import (
    FORMA_PAGO_DEFAULT,
    MATERIALES_DEFAULT,
    OBSERVACIONES_DEFAULT,
    VIGENCIA_DEFAULT,
)

# Topes para que el total siempre entre en la columna de dinero (Numeric(14, 2)).
IMPORTE_MAXIMO = 999_999_999
MAX_ITEMS = 200


class ItemIn(BaseModel):
    descripcion: str = Field(min_length=1, max_length=500)
    unidad: str = Field(default="", max_length=50)
    cantidad: float = Field(gt=0)
    importe: float = Field(ge=0, le=IMPORTE_MAXIMO)


class ItemOut(ItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PresupuestoIn(BaseModel):
    cliente_obra: str = Field(min_length=1, max_length=200)
    direccion: str = Field(default="", max_length=300)
    fecha_emision: dt.date
    vigencia_dias: int = Field(default=VIGENCIA_DEFAULT, ge=1, le=365)
    plazo_obra: str = Field(default="", max_length=200)
    forma_pago: str = Field(default=FORMA_PAGO_DEFAULT, max_length=300)
    materiales_a_cargo: str = Field(default=MATERIALES_DEFAULT, max_length=100)
    observaciones: str = Field(default=OBSERVACIONES_DEFAULT, max_length=2000)
    # Opcionales: los presupuestos viejos no tienen cliente ni obra elegidos de la lista.
    cliente_id: int | None = None
    obra_id: int | None = None
    items: list[ItemIn] = Field(min_length=1, max_length=MAX_ITEMS)


class PresupuestoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    cliente_obra: str
    direccion: str
    fecha_emision: dt.date
    vigencia_dias: int
    plazo_obra: str
    forma_pago: str
    materiales_a_cargo: str
    observaciones: str
    total: float
    creado_en: dt.datetime
    estado: str
    cliente_id: int | None
    obra_id: int | None
    trabajo_id: int | None  # el trabajo vigente (no cancelado), si ya se pasó a trabajo
    items: list[ItemOut]


class PresupuestoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    cliente_obra: str
    fecha_emision: dt.date
    total: float
    estado: str
    trabajo_id: int | None  # el trabajo vigente, si ya se pasó a trabajo


class EstadoIn(BaseModel):
    estado: Literal["borrador", "enviado", "aprobado", "rechazado"]


# --- Asistente IA: borrador que devuelve Gemini a partir del pedido del cliente ---
# Todo es opcional (null = "no lo dijo el cliente"); el frontend solo pisa lo que venga.


class BorradorItem(BaseModel):
    descripcion: str = Field(
        description="Trabajo a realizar, redactado de forma profesional para el cliente."
    )
    unidad: str | None = Field(description="Unidad de medida: m2, ml, gl (global), u, día...")
    cantidad: float | None = Field(description="Cantidad en esa unidad. 1 si es global.")
    importe: float | None = Field(
        description="Importe total del trabajo en pesos, SOLO si el texto lo menciona."
    )


class BorradorPresupuesto(BaseModel):
    # A propósito no hay cliente ni dirección: los elige una persona de la lista de clientes, así
    # la IA nunca pone ni crea un cliente equivocado.
    vigencia_dias: int | None = Field(description="Días de validez del presupuesto.")
    plazo_obra: str | None = Field(description="Duración estimada. Ej: '5 días hábiles'.")
    forma_pago: str | None = Field(description="Forma de pago acordada.")
    materiales_a_cargo: Literal["Cliente", "Obras Demo", "A convenir"] | None = Field(
        description="Quién pone los materiales."
    )
    observaciones: str | None = Field(
        description="Aclaraciones particulares de este trabajo. Sin el texto legal estándar."
    )
    items: list[BorradorItem] = Field(description="Un ítem por cada trabajo pedido.")


class AsistenteIn(BaseModel):
    mensaje: str = Field(min_length=3, max_length=4000)
