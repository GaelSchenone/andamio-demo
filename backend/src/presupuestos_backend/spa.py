"""Sirve el frontend compilado y soporta las rutas del navegador (deep links).

La app tiene URLs propias (`/clientes/12`, `/trabajos`...). Si alguien recarga la página o abre un
enlace, el servidor recibe esa ruta y no hay ningún archivo con ese nombre: `StaticFiles` daría 404.
Esta variante responde con `index.html` y deja que el frontend resuelva la ruta.

Lo que NO se resuelve así, a propósito:
- `/api/...`: una ruta de API inexistente tiene que seguir siendo un 404 (no una página HTML).
- Rutas con extensión (`/assets/falta.js`): un archivo que falta es un 404, no `index.html`.
"""

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class AplicacionDeUnaPagina(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or not self._es_ruta_del_navegador(path):
                raise
            return await super().get_response("index.html", scope)

    @staticmethod
    def _es_ruta_del_navegador(path: str) -> bool:
        if path == "api" or path.startswith("api/"):
            return False
        ultimo_tramo = path.rsplit("/", 1)[-1]
        return "." not in ultimo_tramo
