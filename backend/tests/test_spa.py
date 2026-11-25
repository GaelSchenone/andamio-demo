"""El frontend tiene URLs propias: recargar `/clientes/12` tiene que devolver la app, no un 404."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from presupuestos_backend.spa import AplicacionDeUnaPagina

MARCA = "<title>Andamio de prueba</title>"
SECRETO = "contenido-fuera-de-dist"


@pytest.fixture
def cliente(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(f"<!doctype html>{MARCA}", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('hola')", encoding="utf-8")
    (tmp_path / "secreto.txt").write_text(SECRETO, encoding="utf-8")

    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"ok": True}

    app.mount("/", AplicacionDeUnaPagina(directory=dist, html=True), name="frontend")
    return TestClient(app)


class TestRutasDelNavegador:
    @pytest.mark.parametrize(
        "ruta",
        [
            "/",
            "/clientes",
            "/clientes/12",
            "/trabajos/7",
            "/presupuestos/nuevo",
            "/ajustes/usuarios",
        ],
    )
    def test_devuelven_la_app(self, cliente, ruta):
        r = cliente.get(ruta)
        assert r.status_code == 200
        assert MARCA in r.text
        assert r.headers["content-type"].startswith("text/html")

    def test_con_barra_final_tambien(self, cliente):
        assert MARCA in cliente.get("/clientes/12/").text


class TestLoQueNoDebeResolverseComoApp:
    def test_una_ruta_de_api_inexistente_sigue_siendo_404_y_no_html(self, cliente):
        r = cliente.get("/api/no-existe")
        assert r.status_code == 404
        assert MARCA not in r.text

    def test_la_api_real_sigue_andando(self, cliente):
        assert cliente.get("/api/health").json() == {"ok": True}

    def test_un_archivo_que_falta_es_404_y_no_la_app(self, cliente):
        for ruta in ("/assets/falta.js", "/favicon.ico", "/robots.txt"):
            r = cliente.get(ruta)
            assert r.status_code == 404, ruta
            assert MARCA not in r.text

    def test_los_archivos_que_existen_se_sirven_con_su_tipo(self, cliente):
        r = cliente.get("/assets/app.js")
        assert r.status_code == 200
        assert "javascript" in r.headers["content-type"]
        assert MARCA not in r.text


class TestSeguridad:
    @pytest.mark.parametrize(
        "ruta",
        [
            "/../secreto.txt",
            "/%2e%2e/secreto.txt",
            "/..%2fsecreto.txt",
            "/assets/../../secreto.txt",
            "/clientes/../../secreto.txt",
        ],
    )
    def test_no_se_puede_salir_de_la_carpeta_del_frontend(self, cliente, ruta):
        r = cliente.get(ruta)
        assert SECRETO not in r.text
