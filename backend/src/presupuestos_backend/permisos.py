"""Roles y permisos: qué puede hacer cada tipo de usuario.

Es la única fuente de verdad: los endpoints piden un permiso (`requiere_permiso("...")`),
nunca un rol. Si cambia lo que puede hacer un rol, se cambia acá y en ningún otro lado.

Decidido por el autor, a validar con el dueño del negocio (ver docs/decisiones.md): el empleado ve
la agenda, cambia el estado de un trabajo y ve clientes y direcciones, pero NO ve precios,
presupuestos ni cobros, y no gestiona usuarios.
Los permisos de agenda, trabajos, clientes y cobros se aplican a medida que existan esas pantallas.
"""

ROL_DUENO = "dueno"
ROL_EMPLEADO = "empleado"
ROLES = (ROL_DUENO, ROL_EMPLEADO)

PERMISOS_EMPLEADO = frozenset({"agenda:ver", "trabajos:cambiar_estado", "clientes:ver"})
PERMISOS_DUENO = PERMISOS_EMPLEADO | frozenset(
    {
        "usuarios:gestionar",
        "presupuestos:gestionar",
        "clientes:gestionar",
        "trabajos:gestionar",
        "cobros:gestionar",
    }
)

PERMISOS_POR_ROL = {ROL_DUENO: PERMISOS_DUENO, ROL_EMPLEADO: PERMISOS_EMPLEADO}


def tiene_permiso(rol: str, permiso: str) -> bool:
    """Un rol desconocido no tiene ningún permiso."""
    return permiso in PERMISOS_POR_ROL.get(rol, frozenset())
