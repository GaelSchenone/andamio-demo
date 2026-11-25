"""Esquemas Pydantic de usuarios y sesión."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from presupuestos_backend.passwords import LARGO_MAXIMO, LARGO_MINIMO

Rol = Literal["dueno", "empleado"]
PATRON_USUARIO = r"^[a-z0-9._-]{3,40}$"


def _limpiar(valor):
    return valor.strip() if isinstance(valor, str) else valor


class LoginIn(BaseModel):
    # Sin largo mínimo ni patrón a propósito: cualquier error de datos es "usuario o contraseña
    # incorrectos", así no se le explica a un atacante qué formato tiene que adivinar.
    usuario: str = Field(max_length=40)
    password: str = Field(max_length=LARGO_MAXIMO)

    @field_validator("usuario", mode="before")
    @classmethod
    def _usuario_en_minusculas(cls, v):
        v = _limpiar(v)
        return v.lower() if isinstance(v, str) else v


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    usuario: str = Field(pattern=PATRON_USUARIO)
    password: str = Field(min_length=LARGO_MINIMO, max_length=LARGO_MAXIMO)
    rol: Rol

    @field_validator("nombre", mode="before")
    @classmethod
    def _nombre_sin_espacios_de_mas(cls, v):
        return _limpiar(v)

    @field_validator("usuario", mode="before")
    @classmethod
    def _usuario_en_minusculas(cls, v):
        v = _limpiar(v)
        return v.lower() if isinstance(v, str) else v


class UsuarioPatch(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    rol: Rol | None = None
    activo: bool | None = None

    @field_validator("nombre", mode="before")
    @classmethod
    def _nombre_sin_espacios_de_mas(cls, v):
        return _limpiar(v)


class PasswordNuevaIn(BaseModel):
    password_nueva: str = Field(min_length=LARGO_MINIMO, max_length=LARGO_MAXIMO)


class CambiarPasswordIn(PasswordNuevaIn):
    password_actual: str = Field(max_length=LARGO_MAXIMO)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    usuario: str
    rol: Rol
    activo: bool
    creado_en: dt.datetime
