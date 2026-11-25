"""Logs sin datos de clientes.

El log de acceso de uvicorn escribe la URL completa de cada pedido. Los buscadores mandan lo que
la persona escribe en la URL (`?buscar=...`): un nombre, un teléfono, una dirección. Eso son datos
personales (Ley 25.326) y no deben quedar en los logs del servidor. Este filtro deja solo la ruta.
"""

import logging

_LOG_DE_ACCESO = "uvicorn.access"
_POSICION_DE_LA_RUTA = 2  # args de uvicorn: (cliente, método, ruta, versión HTTP, estado)
_CANTIDAD_DE_ARGS = 5


class SinQueryString(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) == _CANTIDAD_DE_ARGS:
            args = list(record.args)
            args[_POSICION_DE_LA_RUTA] = str(args[_POSICION_DE_LA_RUTA]).split("?", 1)[0]
            record.args = tuple(args)
        return True


def instalar_filtro_de_acceso() -> None:
    """Se puede llamar más de una vez: no agrega el filtro dos veces."""
    log = logging.getLogger(_LOG_DE_ACCESO)
    if not any(isinstance(f, SinQueryString) for f in log.filters):
        log.addFilter(SinQueryString())
