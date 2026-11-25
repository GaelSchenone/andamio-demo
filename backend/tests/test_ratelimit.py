from presupuestos_backend.ratelimit import LimiteIntentos


class Reloj:
    def __init__(self) -> None:
        self.ahora = 1000.0

    def __call__(self) -> float:
        return self.ahora


def test_permite_hasta_el_maximo_y_despues_bloquea():
    reloj = Reloj()
    limite = LimiteIntentos(maximo=3, ventana_s=60, reloj=reloj)
    for _ in range(3):
        assert limite.segundos_de_espera("ip") == 0
        limite.registrar_fallo("ip")
    assert limite.segundos_de_espera("ip") == 60


def test_el_bloqueo_vence_con_el_tiempo():
    reloj = Reloj()
    limite = LimiteIntentos(maximo=2, ventana_s=60, reloj=reloj)
    limite.registrar_fallo("ip")
    limite.registrar_fallo("ip")
    assert limite.segundos_de_espera("ip") > 0
    reloj.ahora += 61
    assert limite.segundos_de_espera("ip") == 0


def test_los_fallos_viejos_no_cuentan():
    reloj = Reloj()
    limite = LimiteIntentos(maximo=2, ventana_s=60, reloj=reloj)
    limite.registrar_fallo("ip")
    reloj.ahora += 61
    limite.registrar_fallo("ip")
    assert limite.segundos_de_espera("ip") == 0


def test_cada_origen_tiene_su_cuenta():
    limite = LimiteIntentos(maximo=1, ventana_s=60, reloj=Reloj())
    limite.registrar_fallo("a")
    assert limite.segundos_de_espera("a") > 0
    assert limite.segundos_de_espera("b") == 0


def test_reiniciar_borra_los_fallos():
    limite = LimiteIntentos(maximo=1, ventana_s=60, reloj=Reloj())
    limite.registrar_fallo("a")
    limite.reiniciar("a")
    assert limite.segundos_de_espera("a") == 0
