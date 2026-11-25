"""Asistente simulado para la demo: sin red, sin claves, determinista.

Se activa con `AGENTE_SIMULADO=1`. No entiende lenguaje libre: busca palabras clave y contesta con
los datos de la base, a través de las MISMAS herramientas del asistente real
(`agente.construir_herramientas`), así que los permisos son idénticos: quien no ve precios no los
recibe por acá.
"""

import datetime as dt
import os
import re
import unicodedata
from collections.abc import Callable
from decimal import Decimal

from presupuestos_backend.formato import moneda
from presupuestos_backend.llm import LLMError
from presupuestos_backend.schemas import BorradorItem, BorradorPresupuesto

SIN_ACCESO = "Con tu usuario no tenés acceso a eso."
MAS_TIPICOS = "Puedo contarte los trabajos de hoy o de la semana, clientes, presupuestos y cobros."

# Palabra clave -> tema de la guía (`agente_guia.GUIA`). Gana el primero que cuadra.
TEMAS = [
    (r"reprogram|mover|cambiar la fecha|cambiar fecha", "reprogramar"),
    (r"agend", "agendar"),
    (r"aprob", "aprobar"),
    (r"termin|inici", "iniciar_y_terminar"),
    (r"calendario", "calendario"),
    (r"cobr|sena|saldo", "cobros"),
    (r"presupuest", "presupuesto"),
    (r"client|obra|direcc", "clientes"),
    (r"usuario", "usuarios"),
    (r"cuenta|contrasena|clave", "cuenta"),
]
PALABRAS_GENERICAS = {"familia", "consorcio", "edificio", "torre"}


def disponible() -> bool:
    return os.environ.get("AGENTE_SIMULADO") == "1"


def _sin_tildes(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in base if not unicodedata.combining(c))


def _linea_de_trabajo(t: dict) -> str:
    dias = t.get("dias") or []
    cuando = "sin fecha" if not dias else dias[0] if len(dias) == 1 else f"{dias[0]} al {dias[-1]}"
    return f"- {t['cliente']}, {t['direccion']} ({cuando}, {t['estado'].replace('_', ' ')})"


def _trabajos(herramientas: dict[str, Callable], q: str, hoy: dt.date) -> str:
    if "ver_trabajos" not in herramientas:
        return SIN_ACCESO
    ver, ir = herramientas["ver_trabajos"], herramientas["abrir_pantalla"]
    if "por agendar" in q:
        filas, titulo = ver(estado="por_agendar"), "Trabajos por agendar"
        ir("trabajos")
    elif "manana" in q:
        dia = (hoy + dt.timedelta(days=1)).isoformat()
        filas, titulo = ver(desde=dia, hasta=dia), "Trabajos de mañana"
        ir("semana")
    elif "hoy" in q:
        filas, titulo = ver(desde=hoy.isoformat(), hasta=hoy.isoformat()), "Trabajos de hoy"
        ir("semana")
    else:
        lunes = hoy - dt.timedelta(days=hoy.weekday())
        filas = ver(desde=lunes.isoformat(), hasta=(lunes + dt.timedelta(days=6)).isoformat())
        titulo = "Trabajos de esta semana"
        ir("semana")
    if isinstance(filas, dict):
        return filas.get("error", "No pude consultar los trabajos.")
    if not filas:
        return f"{titulo}: no hay ninguno."
    return f"{titulo}:\n" + "\n".join(_linea_de_trabajo(t) for t in filas)


def _clientes(herramientas: dict[str, Callable], q: str) -> str:
    if "buscar_clientes" not in herramientas:
        return SIN_ACCESO
    lista = herramientas["buscar_clientes"]("")
    if isinstance(lista, dict):
        return lista.get("error", "No pude consultar los clientes.")
    for c in lista:
        palabras = [p for p in _sin_tildes(c["nombre"]).split() if len(p) > 3]
        if any(p in q for p in palabras if p not in PALABRAS_GENERICAS):
            datos = herramientas["ver_cliente"](c["id"])
            herramientas["abrir_pantalla"]("cliente", c["id"])
            obras = "\n".join(f"- {o['direccion']}" for o in datos["obras"]) or "- (sin obras)"
            return f"{datos['nombre']} ({datos['tipo']}). Obras:\n{obras}"
    herramientas["abrir_pantalla"]("clientes")
    nombres = ", ".join(c["nombre"] for c in lista[:6])
    return f"Tenés {len(lista)} clientes. Algunos: {nombres}. Preguntame por uno por su nombre."


def _cobros(herramientas: dict[str, Callable]) -> str:
    if "ver_cobros_pendientes" not in herramientas:
        return SIN_ACCESO
    datos = herramientas["ver_cobros_pendientes"]()
    herramientas["abrir_pantalla"]("cobros")
    if not datos["trabajos"]:
        return "No falta cobrar nada."
    filas = "\n".join(
        f"- {t['cliente']}, {t['direccion']}: $ {moneda(Decimal(str(t['falta'])))}"
        for t in datos["trabajos"]
    )
    return f"Falta cobrar $ {moneda(Decimal(str(datos['total_pendiente'])))} en total:\n{filas}"


def _presupuestos(herramientas: dict[str, Callable]) -> str:
    if "ver_presupuestos" not in herramientas:
        return SIN_ACCESO
    lista = herramientas["ver_presupuestos"]("")
    herramientas["abrir_pantalla"]("presupuestos")
    if not lista:
        return "Todavía no hay presupuestos."
    filas = "\n".join(
        f"- Nº {p['numero']}, {p['cliente']}: {p['estado']}, $ {moneda(Decimal(str(p['total'])))}"
        for p in lista[:5]
    )
    return f"Los últimos presupuestos:\n{filas}"


def responder(nombre: str, herramientas: dict[str, Callable], pregunta: str) -> str:
    """Contesta por palabras clave. Los botones "Ir a…" los agregan las herramientas."""
    q = _sin_tildes(pregunta)
    hoy = dt.date.today()
    if re.search(r"\bcomo\b|explic|ayuda|paso a paso", q):
        for patron, tema in TEMAS:
            if re.search(patron, q):
                guia = herramientas["como_se_hace"](tema)
                return SIN_ACCESO if guia.startswith("No tengo una guía") else guia
    if re.search(r"cobr|deb|plata|pendiente|saldo|sena", q):
        return _cobros(herramientas)
    if re.search(r"presupuest", q):
        return _presupuestos(herramientas)
    if re.search(r"client|direcc|obra|donde|queda|vive", q):
        return _clientes(herramientas, q)
    if re.search(r"hoy|manana|semana|trabajo|agenda|calendario|proxim|por agendar", q):
        return _trabajos(herramientas, q, hoy)
    if re.search(r"^(hola|buen|hey|que tal)", q):
        return f"¡Hola, {nombre.split()[0]}! Soy el asistente de la demo. {MAS_TIPICOS}"
    return (
        f"No entendí la pregunta (esto es una simulación que busca palabras clave). {MAS_TIPICOS}"
    )


# --- Completar un presupuesto con IA, simulado ---------------------------------------------------

VERBOS = {
    "pintar": "Pintura de",
    "cambiar": "Reemplazo de",
    "arreglar": "Reparación de",
    "reparar": "Reparación de",
    "colocar": "Colocación de",
    "instalar": "Instalación de",
}
_NUMERO = r"(\d+(?:[.,]\d+)?)"
_PRECIO_MIL = re.compile(rf"{_NUMERO}\s*(?:lucas?|luka|k|mil)\b", re.I)
_PRECIO_MILLON = re.compile(rf"{_NUMERO}\s*(?:palos?|M)\b")
_PRECIO_PESOS = re.compile(r"\$\s*([\d.]+)")
_MEDIDA = re.compile(rf"{_NUMERO}\s*(m2|m²|mts2|ml|u|unidades?)\b", re.I)


def _numero(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", ".")) if "," in texto else float(texto)


def _item(parte: str) -> BorradorItem:
    importe = None
    for patron, factor in ((_PRECIO_MIL, 1_000), (_PRECIO_MILLON, 1_000_000), (_PRECIO_PESOS, 1)):
        hallado = patron.search(parte)
        if hallado:
            importe = _numero(hallado.group(1)) * factor
            parte = parte.replace(hallado.group(0), " ")
            break
    unidad, cantidad = "gl", 1.0
    medida = _MEDIDA.search(parte)
    if medida:
        cantidad = _numero(medida.group(1))
        unidad = {"m²": "m2", "mts2": "m2", "unidades": "u", "unidad": "u"}.get(
            medida.group(2).lower(), medida.group(2).lower()
        )
        parte = parte.replace(medida.group(0), " ")
    descripcion = re.sub(r"\s+", " ", parte).strip(" .:-")
    primera, _, resto = descripcion.partition(" ")
    if primera.lower() in VERBOS:
        descripcion = f"{VERBOS[primera.lower()]} {resto}".strip()
    return BorradorItem(
        descripcion=descripcion[:1].upper() + descripcion[1:],
        unidad=unidad,
        cantidad=cantidad,
        importe=importe,
    )


def rellenar(
    esquema: type[BorradorPresupuesto], texto: str, contexto: str = ""
) -> BorradorPresupuesto:
    """Como `llm.rellenar`, por reglas: una tarea por coma, punto y coma, línea o " y "."""
    partes = [p for p in re.split(r"[\n;,]|\s+y\s+", texto) if len(p.strip()) >= 3]
    if not partes:
        raise LLMError(
            "No encontré tareas en el texto. Probá con algo como: pintar living 30 m2, 45 lucas."
        )
    return esquema(
        vigencia_dias=None,
        plazo_obra=None,
        forma_pago=None,
        materiales_a_cargo=None,
        observaciones=None,
        items=[_item(p) for p in partes],
    )
