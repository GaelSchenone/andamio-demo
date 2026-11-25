"""Respuesta a datos rechazados (422): un mensaje que entienda quien usa la app.

FastAPI por defecto devuelve una lista técnica de errores que el frontend no puede mostrar.
Acá se arma un texto en castellano con el campo y el motivo, y se deja registro en el log
de qué campo falló. En el log nunca van los valores: pueden ser datos de clientes.
"""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

NOMBRES_CAMPOS = {
    "cliente_obra": "Cliente / Obra",
    "direccion": "Dirección",
    "fecha_emision": "Fecha de emisión",
    "vigencia_dias": "Vigencia (días)",
    "plazo_obra": "Plazo de obra",
    "forma_pago": "Forma de pago",
    "materiales_a_cargo": "Materiales a cargo de",
    "observaciones": "Observaciones",
    "items": "Trabajos",
    "descripcion": "descripción",
    "unidad": "unidad",
    "cantidad": "cantidad",
    "importe": "importe",
    "mensaje": "Mensaje",
    "nombre": "Nombre",
    "usuario": "Usuario",
    "password": "Contraseña",
    "password_actual": "Contraseña actual",
    "password_nueva": "Contraseña nueva",
    "rol": "Rol",
    "tipo": "Tipo de cliente",
    "telefono": "Teléfono",
    "notas": "Notas",
    "referencia": "Referencia",
    "fecha_inicio": "Fecha de inicio",
    "fecha_fin": "Fecha de fin",
    "causa": "Causa",
    "concepto": "Concepto",
    "monto": "Monto",
    "fecha": "Fecha",
    "nota": "Nota",
    "motivo": "Motivo",
    "desde": "Desde",
    "hasta": "Hasta",
    "mensajes": "Mensajes",
    "texto": "Mensaje",
}
MAXIMO_ERRORES_EN_MENSAJE = 3


def _nombre_campo(loc: tuple) -> str:
    partes = [p for p in loc if p not in ("body", "query")]
    # ("items", 1, "descripcion") -> "Trabajo 2: descripción"
    if len(partes) >= 3 and partes[0] == "items" and isinstance(partes[1], int):
        return f"Trabajo {partes[1] + 1}: {NOMBRES_CAMPOS.get(partes[2], partes[2])}"
    if not partes:
        return "Datos enviados"
    return NOMBRES_CAMPOS.get(partes[0], str(partes[0]))


def _motivo(error: dict) -> str:
    tipo = error["type"]
    ctx = error.get("ctx") or {}
    if tipo == "string_too_long":
        return f"tiene más de {ctx.get('max_length')} caracteres"
    if tipo == "string_too_short":
        return "no puede quedar vacío"
    if tipo == "too_short":
        return "agregá al menos uno"
    if tipo == "too_long":
        return f"no puede tener más de {ctx.get('max_length')}"
    if tipo == "string_pattern_mismatch":
        return "solo puede tener letras sin tildes, números, punto, guion y guion bajo (3 a 40)"
    if tipo == "literal_error":
        return "no es una opción válida"
    if tipo == "missing":
        return "falta completarlo"
    if tipo == "less_than_equal":
        return f"no puede ser mayor a {ctx.get('le')}"
    if tipo == "greater_than_equal":
        return f"no puede ser menor a {ctx.get('ge')}"
    if tipo == "greater_than":
        return f"tiene que ser mayor a {ctx.get('gt')}"
    if tipo.startswith("int_"):
        return "tiene que ser un número entero"
    if tipo.startswith("float_"):
        return "tiene que ser un número"
    if tipo.startswith("date_"):
        return "no es una fecha válida"
    return "no es válido"


def _texto(error: dict) -> str:
    # Una regla que mira varios campos a la vez (por ejemplo "faltan los días del trabajo") ya trae
    # su mensaje completo y no pertenece a un campo en particular.
    if error["type"] == "value_error" and not [
        p for p in error["loc"] if p not in ("body", "query")
    ]:
        return str(error["msg"]).removeprefix("Value error, ").rstrip(".")
    return f"{_nombre_campo(error['loc'])} {_motivo(error)}"


async def datos_rechazados(request: Request, exc: RequestValidationError) -> JSONResponse:
    errores = exc.errors()
    log.warning(
        "Datos rechazados en %s %s: %s",
        request.method,
        request.url.path,
        [(".".join(str(p) for p in e["loc"]), e["type"]) for e in errores],
    )
    partes = [_texto(e) for e in errores]
    if len(partes) > MAXIMO_ERRORES_EN_MENSAJE:
        restantes = len(partes) - MAXIMO_ERRORES_EN_MENSAJE
        partes = [*partes[:MAXIMO_ERRORES_EN_MENSAJE], f"y {restantes} más"]
    return JSONResponse(
        status_code=422,
        content={"detail": "Revisá estos datos: " + "; ".join(partes) + "."},
    )
