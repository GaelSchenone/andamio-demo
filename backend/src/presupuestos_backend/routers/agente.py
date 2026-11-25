"""Agente de ayuda: chat con Gemini que consulta datos (solo lectura) según el rol."""

import logging
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from presupuestos_backend import agente, llm, simulado, webhook
from presupuestos_backend.auth import usuario_actual
from presupuestos_backend.database import get_db
from presupuestos_backend.models import Usuario
from presupuestos_backend.ratelimit import LimiteIntentos

log = logging.getLogger(__name__)

MAX_MENSAJES = 20  # los más viejos se descartan: el chat no necesita acordarse de todo
MAX_LARGO = 1500

# Cada mensaje cuenta como un uso; con 20 en 5 minutos, quien usa el chat normalmente no lo nota.
limite = LimiteIntentos(maximo=20, ventana_s=300)

router = APIRouter(prefix="/api/agente", tags=["agente"])


class MensajeIn(BaseModel):
    rol: Literal["usuario", "agente"]
    texto: str = Field(min_length=1, max_length=MAX_LARGO)

    @field_validator("texto", mode="before")
    @classmethod
    def _sin_espacios_de_mas(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor


class ChatIn(BaseModel):
    mensajes: list[MensajeIn] = Field(min_length=1, max_length=60)
    # Con el webhook, Copilot Studio guarda la charla: se reenvía el id de la respuesta anterior.
    conversacion_id: str | None = Field(default=None, max_length=200)


class AccionOut(BaseModel):
    ruta: str
    etiqueta: str


class ChatOut(BaseModel):
    respuesta: str
    acciones: list[AccionOut]
    conversacion_id: str | None = None


@router.get("/estado")
def estado(_: Usuario = Depends(usuario_actual)) -> dict:
    return {
        "disponible": simulado.disponible() or llm.disponible() or webhook.disponible(),
        "simulado": simulado.disponible(),
    }


@router.post("/chat", response_model=ChatOut)
def chat(datos: ChatIn, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    if datos.mensajes[-1].rol != "usuario":
        raise HTTPException(status_code=422, detail="El último mensaje tiene que ser tuyo.")
    espera = limite.segundos_de_espera(str(usuario.id))
    if espera:
        raise HTTPException(
            status_code=429,
            detail=f"Escribiste muchos mensajes seguidos. Esperá {espera} segundos.",
        )
    limite.registrar_fallo(str(usuario.id))  # cuenta un uso (el límite es el mismo mecanismo)

    mensajes = [(m.rol, m.texto) for m in datos.mensajes][-MAX_MENSAJES:]
    inicio = time.monotonic()
    try:
        resultado = agente.responder(db, usuario, mensajes, datos.conversacion_id)
    except llm.LLMError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    # Nunca se registra lo que se dijo: solo cuánto se usó (puede haber datos de clientes).
    log.info(
        "Agente: usuario %s, %d mensajes, %d botones, %.1f s",
        usuario.id,
        len(mensajes),
        len(resultado.acciones),
        time.monotonic() - inicio,
    )
    return ChatOut(
        respuesta=resultado.respuesta,
        acciones=resultado.acciones,
        conversacion_id=resultado.conversacion_id,
    )
