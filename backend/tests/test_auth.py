import time

import pytest
from conftest import DUENO, PASSWORD_DUENO

from presupuestos_backend import auth


def _firmado(carga: str) -> str:
    return f"{carga}.{auth._firmar(carga)}"


class TestToken:
    def test_token_recien_creado_es_valido(self):
        assert auth.leer_token(auth.crear_token(7, 3)) == (7, 3)

    def test_token_vencido_no_es_valido(self):
        assert auth.leer_token(_firmado(f"7.3.{int(time.time()) - 10}")) is None

    def test_firma_adulterada_no_es_valida(self):
        carga, firma = auth.crear_token(7, 3).rsplit(".", 1)
        assert auth.leer_token(f"{carga}.{'0' * len(firma)}") is None

    def test_cambiar_el_id_invalida_la_firma(self):
        _, version, vencimiento, firma = auth.crear_token(7, 3).split(".")
        assert auth.leer_token(f"1.{version}.{vencimiento}.{firma}") is None

    @pytest.mark.parametrize(
        "basura", [None, "", "sinpunto", "abc.def", ".", "1.", "x.y.z", "1.2.3", "a.b.c.d.e"]
    )
    def test_basura_no_rompe_y_es_invalida(self, basura):
        assert auth.leer_token(basura) is None

    def test_cookie_con_tildes_no_rompe(self):
        # Antes: TypeError (comparar texto no ASCII) -> error 500 en el servidor.
        assert auth.leer_token("1.1.123.ñandú") is None

    def test_partes_no_numericas_aunque_esten_firmadas_son_invalidas(self):
        assert auth.leer_token(_firmado("uno.dos.tres")) is None

    def test_formato_viejo_de_la_clave_compartida_ya_no_vale(self):
        vencimiento = str(int(time.time()) + 1000)
        assert auth.leer_token(f"{vencimiento}.{auth._firmar(vencimiento)}") is None


class TestConfiguracionProduccion:
    def test_desarrollo_acepta_cualquier_cosa(self):
        auth.validar_configuracion(False, auth.SECRET_KEY_POR_DEFECTO)

    def test_produccion_con_secret_key_por_defecto_no_arranca(self):
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            auth.validar_configuracion(True, auth.SECRET_KEY_POR_DEFECTO)

    def test_produccion_con_secret_key_corta_no_arranca(self):
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            auth.validar_configuracion(True, "corta")

    def test_produccion_bien_configurada_arranca(self):
        auth.validar_configuracion(True, "s" * 40)


class TestLogin:
    def test_sin_sesion_la_api_responde_401(self, client):
        assert client.get("/api/presupuestos").status_code == 401
        assert client.get("/api/auth/yo").status_code == 401
        assert client.get("/api/usuarios").status_code == 401

    def test_health_es_publico(self, client):
        assert client.get("/api/health").json() == {"ok": True}

    def test_login_correcto_devuelve_el_usuario_sin_datos_sensibles(self, iniciar_sesion):
        r = iniciar_sesion(DUENO, PASSWORD_DUENO)
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["usuario"] == DUENO
        assert cuerpo["rol"] == "dueno"
        assert "password" not in str(cuerpo).lower()
        assert "hash" not in str(cuerpo).lower()

    def test_el_usuario_no_distingue_mayusculas_ni_espacios(self, iniciar_sesion):
        assert iniciar_sesion(f"  {DUENO.upper()} ", PASSWORD_DUENO).status_code == 200

    def test_la_cookie_es_httponly(self, iniciar_sesion):
        r = iniciar_sesion(DUENO, PASSWORD_DUENO)
        assert "httponly" in r.headers["set-cookie"].lower()

    def test_yo_devuelve_el_usuario_de_la_sesion(self, autenticado):
        assert autenticado.get("/api/auth/yo").json()["usuario"] == DUENO

    @pytest.mark.parametrize(
        ("usuario", "password"),
        [(DUENO, "mal"), ("no-existe", PASSWORD_DUENO), ("no-existe", "mal"), ("", "")],
    )
    def test_datos_incorrectos_dan_el_mismo_401(self, iniciar_sesion, usuario, password):
        r = iniciar_sesion(usuario, password)
        assert r.status_code == 401
        assert r.json()["detail"] == "Usuario o contraseña incorrectos."

    def test_usuario_desactivado_no_entra_y_el_mensaje_no_lo_delata(
        self, autenticado, iniciar_sesion, empleado
    ):
        autenticado.cookies.clear()
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        autenticado.patch(f"/api/usuarios/{empleado['id']}", json={"activo": False})
        r = iniciar_sesion("ana", "clave-de-ana-123")
        assert r.status_code == 401
        assert r.json()["detail"] == "Usuario o contraseña incorrectos."

    def test_logout_cierra_la_sesion(self, autenticado):
        autenticado.post("/api/auth/logout")
        assert autenticado.get("/api/auth/yo").status_code == 401

    def test_cookie_basura_da_401_y_no_500(self, client):
        client.cookies.set(auth.COOKIE_NAME, "abc.def")
        assert client.get("/api/presupuestos").status_code == 401


class TestLimiteDeIntentos:
    def test_despues_de_5_fallos_se_bloquea_aunque_la_clave_sea_correcta(self, iniciar_sesion):
        for _ in range(auth.MAX_FALLOS_LOGIN):
            assert iniciar_sesion(DUENO, "mal").status_code == 401
        r = iniciar_sesion(DUENO, PASSWORD_DUENO)
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        assert "intentos" in r.json()["detail"]

    def test_un_login_correcto_reinicia_la_cuenta(self, iniciar_sesion):
        for _ in range(auth.MAX_FALLOS_LOGIN - 1):
            iniciar_sesion(DUENO, "mal")
        assert iniciar_sesion(DUENO, PASSWORD_DUENO).status_code == 200
        for _ in range(auth.MAX_FALLOS_LOGIN - 1):
            assert iniciar_sesion(DUENO, "mal").status_code == 401


class TestCambiarPassword:
    NUEVA = "otra-clave-nueva-456"

    def _cambiar(self, client, actual=PASSWORD_DUENO, nueva=NUEVA):
        return client.post(
            "/api/auth/cambiar-password",
            json={"password_actual": actual, "password_nueva": nueva},
        )

    def test_con_la_actual_correcta_cambia_y_la_vieja_deja_de_servir(
        self, autenticado, iniciar_sesion
    ):
        assert self._cambiar(autenticado).status_code == 200
        assert iniciar_sesion(DUENO, PASSWORD_DUENO).status_code == 401
        assert iniciar_sesion(DUENO, self.NUEVA).status_code == 200

    def test_la_sesion_actual_sigue_abierta_pero_las_otras_se_cierran(self, autenticado):
        cookie_anterior = autenticado.cookies.get(auth.COOKIE_NAME)
        assert self._cambiar(autenticado).status_code == 200
        assert autenticado.get("/api/auth/yo").status_code == 200  # la cookie se renovó

        autenticado.cookies.clear()
        autenticado.cookies.set(auth.COOKIE_NAME, cookie_anterior)
        assert autenticado.get("/api/auth/yo").status_code == 401  # la sesión vieja ya no vale

    def test_con_la_actual_incorrecta_falla(self, autenticado):
        r = self._cambiar(autenticado, actual="no-es-esta")
        assert r.status_code == 400
        assert "actual" in r.json()["detail"]

    def test_la_nueva_no_puede_ser_igual_a_la_actual(self, autenticado):
        r = self._cambiar(autenticado, nueva=PASSWORD_DUENO)
        assert r.status_code == 400
        assert "distinta" in r.json()["detail"]

    def test_la_nueva_demasiado_corta_da_422_legible(self, autenticado):
        r = self._cambiar(autenticado, nueva="corta")
        assert r.status_code == 422
        assert "Contraseña nueva" in r.json()["detail"]

    def test_adivinar_la_actual_se_bloquea(self, autenticado):
        for _ in range(auth.MAX_FALLOS_LOGIN):
            assert self._cambiar(autenticado, actual="mal").status_code == 400
        assert self._cambiar(autenticado, actual=PASSWORD_DUENO).status_code == 429

    def test_sin_sesion_da_401(self, client):
        assert self._cambiar(client).status_code == 401
