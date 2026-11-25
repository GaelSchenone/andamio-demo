"""Cliente del webhook de Power Automate que ejecuta un agente de Copilot Studio.

Es un POST sincrónico: se manda un mensaje (y el `conversationId` de la charla, si ya hay una) y
vuelve el texto del agente. Copilot Studio guarda el historial asociado a ese id.

La URL lleva una clave firmada: es un secreto. Va solo en la variable de entorno AGENTE_WEBHOOK_URL
y nunca se escribe en un log ni en un mensaje de error (por eso no se registra el texto de las
excepciones de httpx, que pueden incluirla). Cada llamada consume créditos de Copilot Studio.
"""

import json
import logging
import os

import httpx
from pydantic import BaseModel, ValidationError

from presupuestos_backend.llm import INSTRUCCIONES, MENSAJE_NO_DISPONIBLE, LLMError

URL = os.environ.get("AGENTE_WEBHOOK_URL", "")
TIMEOUT_S = 130  # el trigger HTTP corta las llamadas sincrónicas cerca de los 120 s

log = logging.getLogger(__name__)


def disponible() -> bool:
    return bool(URL)


def _falla(motivo: str) -> LLMError:
    log.warning("Webhook del agente: %s", motivo)  # nunca la URL ni el cuerpo
    return LLMError(MENSAJE_NO_DISPONIBLE)


def preguntar(mensaje: str, conversacion_id: str | None = None) -> tuple[str, str | None]:
    """Devuelve (texto del agente, id de la conversación para el próximo mensaje)."""
    cuerpo = {"message": mensaje}
    if conversacion_id:
        cuerpo["conversationId"] = conversacion_id

    respuesta = None
    for intento in (1, 2):
        try:
            respuesta = httpx.post(URL, json=cuerpo, timeout=TIMEOUT_S)
        except httpx.TimeoutException:
            raise _falla("no respondió a tiempo") from None
        except httpx.ConnectError:
            if intento == 1:
                continue  # no llegó a conectar: se puede reintentar sin riesgo de duplicar
            raise _falla("no se pudo conectar") from None
        except httpx.HTTPError as e:
            # Conexión cortada: el pedido pudo ejecutarse; reintentar duplicaría el gasto.
            raise _falla(f"error de red ({type(e).__name__})") from None
        if respuesta.status_code == 503 and intento == 1:
            continue
        break

    if respuesta.status_code != 200:
        raise _falla(f"respondió HTTP {respuesta.status_code}")
    try:
        datos = respuesta.json()
    except ValueError:
        raise _falla("no devolvió JSON") from None
    texto = datos.get("lastResponse") if isinstance(datos, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        raise _falla("la respuesta no trae `lastResponse`")
    nuevo_id = datos.get("conversationId")
    return texto.strip(), nuevo_id if isinstance(nuevo_id, str) and nuevo_id else conversacion_id


def _primer_objeto_json(texto: str) -> dict | None:
    """El primer objeto JSON del texto (el agente a veces lo rodea de explicaciones)."""
    decodificador = json.JSONDecoder()
    for i, caracter in enumerate(texto):
        if caracter == "{":
            try:
                objeto, _ = decodificador.raw_decode(texto[i:])
            except ValueError:
                continue
            if isinstance(objeto, dict):
                return objeto
    return None


def rellenar[Esquema: BaseModel](esquema: type[Esquema], texto: str, contexto: str = "") -> Esquema:
    """Igual que `llm.rellenar`, pero con el agente de Copilot Studio.

    El agente no obliga a respetar un esquema: se le pide solo el JSON, se busca el primer objeto
    en su respuesta y se valida. Si no sirve, se le pide una vez más (en la misma conversación).
    """
    pedido = (
        f"{INSTRUCCIONES}\n"
        f"CONTEXTO:\n{contexto.strip() or '(sin contexto)'}\n\n"
        f"TEXTO:\n{texto.strip()}\n\n"
        "Respondé SOLO con un objeto JSON, sin explicaciones ni Markdown, con este esquema:\n"
        f"{json.dumps(esquema.model_json_schema(), ensure_ascii=False)}"
    )
    conversacion = None
    for _ in (1, 2):
        respuesta, conversacion = preguntar(pedido, conversacion)
        objeto = _primer_objeto_json(respuesta)
        try:
            if objeto is not None:
                return esquema.model_validate(objeto)
        except ValidationError:
            pass
        pedido = "Tu respuesta anterior no era un JSON válido. Respondé solo el objeto JSON."
    raise _falla("no devolvió un JSON válido")
