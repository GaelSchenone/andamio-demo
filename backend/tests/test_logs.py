import logging

from presupuestos_backend.logs import SinQueryString, instalar_filtro_de_acceso

FORMATO_DE_UVICORN = '%s - "%s %s HTTP/%s" %d'


def _registro(ruta: str) -> logging.LogRecord:
    return logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        FORMATO_DE_UVICORN,
        ("127.0.0.1:5000", "GET", ruta, "1.1", 200),
        None,
    )


def test_saca_lo_que_se_busco_pero_deja_la_ruta():
    registro = _registro("/api/clientes?buscar=Juan+P%C3%A9rez&otro=11+5555+0000")
    assert SinQueryString().filter(registro) is True
    mensaje = registro.getMessage()
    assert "/api/clientes" in mensaje
    assert "Juan" not in mensaje and "5555" not in mensaje and "buscar" not in mensaje
    assert mensaje.endswith('HTTP/1.1" 200')


def test_una_ruta_sin_busqueda_queda_igual():
    registro = _registro("/api/clientes/7")
    SinQueryString().filter(registro)
    assert "/api/clientes/7" in registro.getMessage()


def test_nunca_descarta_el_registro():
    assert SinQueryString().filter(_registro("/x?y=z")) is True


def test_no_toca_registros_con_otra_forma():
    registro = logging.LogRecord(
        "uvicorn.access", logging.INFO, "", 0, "mensaje %s", ("a?b",), None
    )
    SinQueryString().filter(registro)
    assert registro.getMessage() == "mensaje a?b"


def test_instalar_dos_veces_no_duplica_el_filtro():
    log = logging.getLogger("uvicorn.access")
    instalar_filtro_de_acceso()
    instalar_filtro_de_acceso()
    assert sum(isinstance(f, SinQueryString) for f in log.filters) == 1
