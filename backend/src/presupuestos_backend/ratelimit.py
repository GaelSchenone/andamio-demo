"""Límite de intentos fallidos en memoria (para frenar adivinar la clave de acceso).

Guarda, por cada clave (por ejemplo una IP), cuándo fueron los últimos fallos. Si hay
`maximo` fallos dentro de la ventana, queda bloqueada hasta que el más viejo venza.
Es de un solo proceso: alcanza para un servicio con un solo worker, como este.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable


class LimiteIntentos:
    def __init__(
        self, maximo: int, ventana_s: float, reloj: Callable[[], float] = time.monotonic
    ) -> None:
        self._maximo = maximo
        self._ventana_s = ventana_s
        self._reloj = reloj
        self._fallos: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _depurar(self, clave: str, ahora: float) -> deque[float]:
        fallos = self._fallos.get(clave)
        if fallos is None:
            return deque()
        while fallos and ahora - fallos[0] >= self._ventana_s:
            fallos.popleft()
        if not fallos:
            del self._fallos[clave]
            return deque()
        return fallos

    def segundos_de_espera(self, clave: str) -> int:
        """0 si puede intentar; si no, cuántos segundos faltan para el próximo intento."""
        with self._lock:
            ahora = self._reloj()
            fallos = self._depurar(clave, ahora)
            if len(fallos) < self._maximo:
                return 0
            return max(1, math.ceil(self._ventana_s - (ahora - fallos[0])))

    def registrar_fallo(self, clave: str) -> None:
        with self._lock:
            ahora = self._reloj()
            self._depurar(clave, ahora)
            self._fallos.setdefault(clave, deque()).append(ahora)

    def reiniciar(self, clave: str) -> None:
        with self._lock:
            self._fallos.pop(clave, None)

    def reiniciar_todo(self) -> None:
        with self._lock:
            self._fallos.clear()
