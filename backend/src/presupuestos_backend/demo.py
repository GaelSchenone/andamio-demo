"""Datos de ejemplo para la versión de demostración (todo inventado).

Con `DEMO=1`, al arrancar con la base vacía se crean dos usuarios y clientes, presupuestos, trabajos
y cobros ficticios. Pasa por las mismas funciones que usa la app: valen las reglas de negocio.
Las fechas son relativas a hoy: el calendario y el Inicio siempre tienen contenido.
"""

import datetime as dt
import logging
import os

from sqlalchemy.orm import Session

from presupuestos_backend import crud, crud_clientes, crud_cobros, crud_trabajos, crud_usuarios
from presupuestos_backend.database import SessionLocal
from presupuestos_backend.permisos import ROL_DUENO, ROL_EMPLEADO
from presupuestos_backend.schemas import ItemIn, PresupuestoIn
from presupuestos_backend.schemas_clientes import ClienteIn, ObraIn

log = logging.getLogger(__name__)

# Credenciales públicas a propósito (están en el README): es una demo, no hay nada que proteger.
PASSWORD_DEMO = "demo-obras-2026"

# (nombre, tipo, teléfono ficticio, [(dirección, referencia)])
CLIENTES = [
    (
        "Familia Ejemplo Rivas",
        "casa",
        "11 0000 0001",
        [("Calle Ficticia 123", "Casa con rejas verdes")],
    ),
    (
        "Consorcio Edificio Demo",
        "consorcio",
        "11 0000 0002",
        [("Av. Imaginaria 4500", "Portería"), ("Av. Imaginaria 4520", "Cochera")],
    ),
    ("Marta Prueba", "casa", "11 0000 0003", [("Pasaje Inventado 88", "")]),
    ("Familia Muestra Gómez", "casa", "11 0000 0004", [("Calle de Ejemplo 2050", "Timbre 2")]),
    (
        "Consorcio Torre Ejemplo",
        "consorcio",
        "11 0000 0005",
        [("Av. Demostración 900", "Hall principal")],
    ),
    ("Lucía Demostración", "casa", "11 0000 0006", [("Calle Simulada 311", "")]),
]

# (cliente, obra, ítems [(descripción, unidad, cantidad, importe)], estado, plan del trabajo)
# plan: None = sin trabajo · ("agendar", desde, hasta) · ("terminar", desde, hasta, cobros)
# con desfases en días respecto de hoy. cobros: "todo", "sena" o "nada".
PRESUPUESTOS = [
    (
        0,
        0,
        [
            ("Pintura de living y comedor", "m2", 45, 270000),
            ("Reparación de grietas", "gl", 1, 60000),
        ],
        "aprobado",
        ("terminar", -12, -10, "todo"),
    ),
    (
        1,
        0,
        [
            ("Pintura de fachada", "m2", 120, 960000),
            ("Impermeabilización de cornisas", "ml", 30, 150000),
        ],
        "aprobado",
        ("terminar", -6, -4, "sena"),
    ),
    (
        2,
        0,
        [("Reemplazo de tomacorrientes en cocina", "u", 6, 72000)],
        "aprobado",
        ("agendar", 0, 0),
    ),
    (
        3,
        0,
        [("Pintura de dormitorios", "m2", 60, 360000), ("Colocación de zócalos", "ml", 24, 96000)],
        "aprobado",
        ("agendar", 2, 4),
    ),
    (4, 0, [("Pintura de hall y escaleras", "m2", 200, 1400000)], "aprobado", ("agendar", 8, 12)),
    (5, 0, [("Arreglo de filtraciones en baño", "gl", 1, 180000)], "aprobado", ("sin_agendar",)),
    (1, 1, [("Pintura de cochera", "m2", 80, 400000)], "enviado", None),
    (2, 0, [("Colocación de cielorraso de durlock", "m2", 18, 270000)], "borrador", None),
    (0, 0, [("Pintura de exteriores", "m2", 90, 630000)], "rechazado", None),
]


def _fecha(hoy: dt.date, desfase: int) -> dt.date:
    return hoy + dt.timedelta(days=desfase)


def _cobrar(db: Session, trabajo, dueno, fecha: dt.date, que: str) -> None:
    total = crud_cobros.total_a_cobrar(trabajo)
    mitad = float(total) / 2
    if que in ("sena", "todo"):
        crud_cobros.registrar(db, trabajo, "sena", mitad, fecha, "", dueno)
    if que == "todo":
        crud_cobros.registrar(
            db, trabajo, "saldo", float(crud_cobros.pendiente(trabajo)), fecha, "", dueno
        )


def cargar_datos_demo(db: Session) -> None:
    """Crea usuarios y datos de ejemplo. Solo se llama con la base sin usuarios."""
    # Hora de Argentina (UTC-3, sin horario de verano): el "hoy" que ve quien usa la app.
    hoy = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()
    dueno = crud_usuarios.crear(db, "Dueño Demo", "demo", PASSWORD_DEMO, ROL_DUENO)
    crud_usuarios.crear(db, "Empleada Demo", "empleada", PASSWORD_DEMO, ROL_EMPLEADO)

    clientes = []
    for nombre, tipo, telefono, obras in CLIENTES:
        cliente = crud_clientes.crear_cliente(
            db, ClienteIn(nombre=nombre, tipo=tipo, telefono=telefono)
        )
        clientes.append(
            (
                cliente,
                [
                    crud_clientes.crear_obra(db, cliente, ObraIn(direccion=d, referencia=r))
                    for d, r in obras
                ],
            )
        )

    for n, (c, o, items, estado, plan) in enumerate(PRESUPUESTOS):
        cliente, obras = clientes[c]
        obra = obras[o]
        presupuesto = crud.crear_presupuesto(
            db,
            PresupuestoIn(
                cliente_obra=cliente.nombre,
                direccion=obra.direccion,
                fecha_emision=_fecha(hoy, -20 + n),
                plazo_obra="3 días hábiles",
                cliente_id=cliente.id,
                obra_id=obra.id,
                items=[
                    ItemIn(descripcion=d, unidad=u, cantidad=q, importe=i) for d, u, q, i in items
                ],
            ),
        )
        crud.cambiar_estado(db, presupuesto, estado)
        if plan is None:
            continue
        trabajo = crud_trabajos.crear_desde_presupuesto(db, presupuesto)
        if plan[0] == "sin_agendar":
            continue
        crud_trabajos.agendar(db, trabajo, _fecha(hoy, plan[1]), _fecha(hoy, plan[2]))
        if plan[0] == "terminar":
            crud_trabajos.terminar(db, trabajo)
            _cobrar(db, trabajo, dueno, _fecha(hoy, plan[2]), plan[3])
    log.info("Datos de demostración cargados.")


def cargar_si_corresponde() -> bool:
    """Con `DEMO=1` y sin ningún usuario, siembra la base. Nunca toca una base con datos."""
    if os.environ.get("DEMO") != "1":
        return False
    with SessionLocal() as db:
        if crud_usuarios.hay_usuarios(db):
            return False
        cargar_datos_demo(db)
        return True
