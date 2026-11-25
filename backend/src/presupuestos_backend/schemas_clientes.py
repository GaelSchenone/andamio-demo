"""Esquemas Pydantic de clientes y obras."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TipoCliente = Literal["casa", "consorcio"]


class _EntradaLimpia(BaseModel):
    """Saca los espacios de más de todos los textos que llegan."""

    @field_validator("*", mode="before")
    @classmethod
    def _sin_espacios_de_mas(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor


class ObraIn(_EntradaLimpia):
    direccion: str = Field(min_length=1, max_length=300)
    referencia: str = Field(default="", max_length=100)
    notas: str = Field(default="", max_length=1000)


class ObraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    direccion: str
    referencia: str
    notas: str
    creado_en: dt.datetime


class ClienteIn(_EntradaLimpia):
    nombre: str = Field(min_length=1, max_length=150)
    tipo: TipoCliente
    telefono: str = Field(default="", max_length=40)
    notas: str = Field(default="", max_length=1000)


class ClienteResumen(BaseModel):
    id: int
    nombre: str
    tipo: TipoCliente
    telefono: str
    cantidad_obras: int


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo: TipoCliente
    telefono: str
    notas: str
    creado_en: dt.datetime
    obras: list[ObraOut]
