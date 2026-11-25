"""Asistente IA: arma un borrador de presupuesto a partir del pedido del cliente."""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException

from presupuestos_backend import llm, simulado, webhook
from presupuestos_backend.auth import requiere_permiso
from presupuestos_backend.models import (
    FORMA_PAGO_DEFAULT,
    MATERIALES_DEFAULT,
    OBSERVACIONES_DEFAULT,
    VIGENCIA_DEFAULT,
)
from presupuestos_backend.schemas import AsistenteIn, BorradorPresupuesto

router = APIRouter(
    prefix="/api/asistente",
    tags=["asistente"],
    dependencies=[Depends(requiere_permiso("presupuestos:gestionar"))],
)


def _contexto() -> str:
    return f"""\
Obras Demo es una empresa argentina de arreglos y mantenimiento del hogar (pintura,
electricidad, plomería, albañilería, durlock, etc.). Hoy es {dt.date.today().isoformat()}.

El TEXTO son notas rápidas y coloquiales que escribió alguien del equipo (a veces pega
el mensaje del cliente): sin mayúsculas, con abreviaturas, errores de tipeo y lunfardo.
Tu trabajo principal es pasarlo en limpio: el resultado es un presupuesto formal que va
a leer el cliente, así que todo texto que devuelvas tiene que sonar profesional.

Cómo redactar:
- descripcion de cada ítem: frase nominal, concisa y técnica, con mayúscula inicial y
  sin punto final, como en un presupuesto de obra. Empezá por la tarea: "Pintura de...",
  "Reemplazo de...", "Provisión y colocación de...", "Reparación de...".
  Ej: "pintar el living q esta todo descascarado" -> "Pintura de living, con reparación
  de superficies descascaradas".
  Ej: "cambiar 3 enchufes cocina" -> "Reemplazo de tomacorrientes en cocina".
- Profesionalizá la forma, no el alcance: no agregues tareas, materiales, calidades ni
  detalles (cantidad de manos, marcas, garantías) que el TEXTO no diga.
- No devuelvas el nombre del cliente ni la dirección: los elige el equipo de la lista de clientes.
  Ignorá los que aparezcan en el TEXTO.
- plazo_obra y forma_pago: expresiones formales ("3 días hábiles", "50% de anticipo y
  50% al finalizar"). Nada de "un par de días" o "la mitad antes".
- Plata coloquial: "45 lucas" o "45k" = 45000; "1 palo" o "1M" = 1000000.

Reglas de los datos:
- Separá cada tarea en un ítem distinto. Si hay medidas, usalas como cantidad con su
  unidad (m2, ml, u); si no, usá unidad "gl" y cantidad 1.
- importe: completalo SOLO si el texto dice un precio para ese trabajo. Nunca lo estimes:
  los precios los pone Obras Demo a mano.
- Si no se menciona, dejá en null: vigencia_dias (por defecto {VIGENCIA_DEFAULT}),
  forma_pago (por defecto "{FORMA_PAGO_DEFAULT}") y materiales_a_cargo (por defecto
  "{MATERIALES_DEFAULT}").
- observaciones: solo aclaraciones propias de este trabajo (ej: "Incluye retiro de
  escombros"). No repitas condiciones generales: se agregan solas.
"""


@router.get("/estado")
def estado() -> dict:
    return {
        "disponible": simulado.disponible() or llm.disponible() or webhook.disponible(),
        "simulado": simulado.disponible(),
    }


@router.post("/presupuesto", response_model=BorradorPresupuesto)
def borrador_presupuesto(datos: AsistenteIn):
    try:
        motor = simulado if simulado.disponible() else webhook if webhook.disponible() else llm
        borrador = motor.rellenar(BorradorPresupuesto, datos.mensaje, _contexto())
    except llm.LLMError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    extra = (borrador.observaciones or "").strip()
    borrador.observaciones = f"{extra}\n{OBSERVACIONES_DEFAULT}" if extra else None
    return borrador
