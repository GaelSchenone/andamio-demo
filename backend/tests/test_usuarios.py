import logging

import pytest
from conftest import DUENO, PASSWORD_DUENO, PASSWORD_EMPLEADO

from presupuestos_backend import usuarios_cli
from presupuestos_backend.bootstrap import crear_dueno_inicial
from presupuestos_backend.database import SessionLocal
from presupuestos_backend.models import Usuario


def _nuevo(**cambios):
    datos = {
        "nombre": "Pedro Gómez",
        "usuario": "pedro",
        "password": "clave-de-pedro-123",
        "rol": "empleado",
    }
    datos.update(cambios)
    return datos


class TestAltaYListado:
    def test_el_duenio_crea_un_usuario_que_despues_puede_entrar(self, autenticado, iniciar_sesion):
        r = autenticado.post("/api/usuarios", json=_nuevo())
        assert r.status_code == 201
        cuerpo = r.json()
        assert (cuerpo["usuario"], cuerpo["rol"], cuerpo["activo"]) == ("pedro", "empleado", True)
        assert "password" not in str(cuerpo).lower()
        assert iniciar_sesion("pedro", "clave-de-pedro-123").status_code == 200

    def test_el_usuario_se_guarda_en_minusculas(self, autenticado):
        r = autenticado.post("/api/usuarios", json=_nuevo(usuario="  Pedro.G  "))
        assert r.json()["usuario"] == "pedro.g"

    def test_la_contrasena_nunca_se_guarda_en_texto(self, autenticado):
        autenticado.post("/api/usuarios", json=_nuevo())
        with SessionLocal() as db:
            guardado = db.query(Usuario).filter_by(usuario="pedro").one().password_hash
        assert "clave-de-pedro-123" not in guardado
        assert guardado.startswith("$argon2")

    def test_usuario_repetido_da_409_aunque_cambien_las_mayusculas(self, autenticado):
        autenticado.post("/api/usuarios", json=_nuevo())
        r = autenticado.post("/api/usuarios", json=_nuevo(usuario="PEDRO"))
        assert r.status_code == 409
        assert "Ya existe" in r.json()["detail"]

    @pytest.mark.parametrize(
        ("campo", "valor", "texto"),
        [
            ("usuario", "ana lópez", "Usuario"),
            ("usuario", "ab", "Usuario"),
            ("password", "corta", "Contraseña"),
            ("password", "x" * 129, "Contraseña"),
            ("rol", "jefe", "Rol"),
            ("nombre", "   ", "Nombre"),
        ],
    )
    def test_datos_invalidos_dan_422_con_mensaje_legible(self, autenticado, campo, valor, texto):
        r = autenticado.post("/api/usuarios", json=_nuevo(**{campo: valor}))
        assert r.status_code == 422
        assert texto in r.json()["detail"]

    def test_listar_incluye_al_duenio(self, autenticado, empleado):
        autenticado.post("/api/auth/login", json={"usuario": DUENO, "password": PASSWORD_DUENO})
        usuarios = autenticado.get("/api/usuarios").json()
        assert {u["usuario"] for u in usuarios} == {DUENO, "ana"}


class TestEdicion:
    def test_cambiar_nombre_y_rol(self, autenticado, empleado):
        autenticado.post("/api/auth/login", json={"usuario": DUENO, "password": PASSWORD_DUENO})
        r = autenticado.patch(
            f"/api/usuarios/{empleado['id']}", json={"nombre": "Ana María", "rol": "dueno"}
        )
        assert r.status_code == 200
        assert (r.json()["nombre"], r.json()["rol"]) == ("Ana María", "dueno")

    def test_usuario_inexistente_da_404(self, autenticado):
        assert autenticado.patch("/api/usuarios/9999", json={"activo": False}).status_code == 404
        assert (
            autenticado.post(
                "/api/usuarios/9999/password", json={"password_nueva": "clave-larga-123"}
            ).status_code
            == 404
        )

    def test_desactivar_bloquea_el_ingreso_y_cierra_las_sesiones_abiertas(
        self, autenticado, iniciar_sesion, empleado, client
    ):
        # Ana inicia sesión y guarda su cookie.
        iniciar_sesion("ana", PASSWORD_EMPLEADO)
        cookie_de_ana = client.cookies.get("obras_demo_sesion")
        assert client.get("/api/auth/yo").status_code == 200

        # El dueño la desactiva.
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        assert (
            client.patch(f"/api/usuarios/{empleado['id']}", json={"activo": False}).status_code
            == 200
        )

        # La cookie que Ana ya tenía dejó de servir, y no puede volver a entrar.
        client.cookies.clear()
        client.cookies.set("obras_demo_sesion", cookie_de_ana)
        assert client.get("/api/auth/yo").status_code == 401
        assert iniciar_sesion("ana", PASSWORD_EMPLEADO).status_code == 401

    def test_reactivar_permite_volver_a_entrar(self, autenticado, iniciar_sesion, empleado):
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        autenticado.patch(f"/api/usuarios/{empleado['id']}", json={"activo": False})
        autenticado.patch(f"/api/usuarios/{empleado['id']}", json={"activo": True})
        assert iniciar_sesion("ana", PASSWORD_EMPLEADO).status_code == 200


class TestUltimoDueno:
    def _id_dueno(self, client):
        return client.get("/api/auth/yo").json()["id"]

    def test_el_unico_duenio_no_puede_desactivarse(self, autenticado):
        r = autenticado.patch(
            f"/api/usuarios/{self._id_dueno(autenticado)}", json={"activo": False}
        )
        assert r.status_code == 409
        assert "al menos un dueño" in r.json()["detail"]

    def test_el_unico_duenio_no_puede_bajarse_a_empleado(self, autenticado):
        r = autenticado.patch(
            f"/api/usuarios/{self._id_dueno(autenticado)}", json={"rol": "empleado"}
        )
        assert r.status_code == 409

    def test_con_otro_duenio_activo_si_se_puede(self, autenticado):
        autenticado.post("/api/usuarios", json=_nuevo(usuario="socio", rol="dueno"))
        r = autenticado.patch(
            f"/api/usuarios/{self._id_dueno(autenticado)}", json={"rol": "empleado"}
        )
        assert r.status_code == 200

    def test_un_duenio_desactivado_no_cuenta_como_activo(self, autenticado):
        socio = autenticado.post("/api/usuarios", json=_nuevo(usuario="socio", rol="dueno")).json()
        autenticado.patch(f"/api/usuarios/{socio['id']}", json={"activo": False})
        r = autenticado.patch(
            f"/api/usuarios/{self._id_dueno(autenticado)}", json={"activo": False}
        )
        assert r.status_code == 409


class TestRestablecerPassword:
    NUEVA = "clave-restablecida-789"

    def test_el_duenio_le_pone_una_nueva_y_se_cierran_sus_sesiones(
        self, autenticado, iniciar_sesion, empleado, client
    ):
        iniciar_sesion("ana", PASSWORD_EMPLEADO)
        cookie_de_ana = client.cookies.get("obras_demo_sesion")

        iniciar_sesion(DUENO, PASSWORD_DUENO)
        r = client.post(
            f"/api/usuarios/{empleado['id']}/password", json={"password_nueva": self.NUEVA}
        )
        assert r.status_code == 200

        client.cookies.clear()
        client.cookies.set("obras_demo_sesion", cookie_de_ana)
        assert client.get("/api/auth/yo").status_code == 401
        assert iniciar_sesion("ana", PASSWORD_EMPLEADO).status_code == 401
        assert iniciar_sesion("ana", self.NUEVA).status_code == 200

    def test_la_nueva_tiene_que_cumplir_el_largo_minimo(
        self, autenticado, empleado, iniciar_sesion
    ):
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        r = autenticado.post(
            f"/api/usuarios/{empleado['id']}/password", json={"password_nueva": "corta"}
        )
        assert r.status_code == 422


class TestDuenoInicial:
    def _vaciar(self):
        with SessionLocal() as db:
            db.query(Usuario).delete()
            db.commit()

    def test_no_hace_nada_si_ya_hay_usuarios(self, monkeypatch):
        monkeypatch.setenv("DUENO_USUARIO", "otro")
        assert crear_dueno_inicial() is False
        with SessionLocal() as db:
            assert db.query(Usuario).filter_by(usuario="otro").count() == 0

    def test_con_la_base_vacia_crea_al_duenio(self, monkeypatch):
        self._vaciar()
        monkeypatch.setenv("DUENO_USUARIO", "Nuevo.Dueno")
        monkeypatch.setenv("DUENO_PASSWORD", "una-clave-larga-123")
        monkeypatch.setenv("DUENO_NOMBRE", "Dora")
        assert crear_dueno_inicial() is True
        with SessionLocal() as db:
            u = db.query(Usuario).one()
        assert (u.usuario, u.nombre, u.rol, u.activo) == ("nuevo.dueno", "Dora", "dueno", True)

    def test_sin_nombre_usa_el_usuario(self, monkeypatch):
        self._vaciar()
        monkeypatch.setenv("DUENO_NOMBRE", "")
        crear_dueno_inicial()
        with SessionLocal() as db:
            assert db.query(Usuario).one().nombre == DUENO

    def test_sin_variables_no_crea_nada_y_avisa(self, monkeypatch, caplog):
        self._vaciar()
        monkeypatch.setenv("DUENO_USUARIO", "")
        monkeypatch.setenv("DUENO_PASSWORD", "")
        with caplog.at_level(logging.WARNING):
            assert crear_dueno_inicial() is False
        assert "nadie va a poder entrar" in caplog.text

    def test_con_datos_invalidos_corta_el_arranque_sin_mostrar_la_contrasena(self, monkeypatch):
        self._vaciar()
        monkeypatch.setenv("DUENO_PASSWORD", "corta")
        with pytest.raises(RuntimeError) as error:
            crear_dueno_inicial()
        assert "password" in str(error.value)
        assert "corta" not in str(error.value)


class TestLineaDeComandos:
    def _teclear(self, monkeypatch, *respuestas):
        pendientes = list(respuestas)
        monkeypatch.setattr(usuarios_cli.getpass, "getpass", lambda _: pendientes.pop(0))

    def test_crear_un_usuario(self, monkeypatch, iniciar_sesion):
        self._teclear(monkeypatch, "clave-desde-la-terminal", "clave-desde-la-terminal")
        usuarios_cli.main(["crear", "--usuario", "Marta", "--nombre", "Marta", "--rol", "empleado"])
        assert iniciar_sesion("marta", "clave-desde-la-terminal").json()["rol"] == "empleado"

    def test_contrasenas_distintas_no_crean_nada(self, monkeypatch):
        self._teclear(monkeypatch, "una-clave-larga-123", "otra-clave-larga-123")
        with pytest.raises(SystemExit, match="no coinciden"):
            usuarios_cli.main(["crear", "--usuario", "marta"])
        with SessionLocal() as db:
            assert db.query(Usuario).filter_by(usuario="marta").count() == 0

    def test_usuario_repetido(self, monkeypatch):
        self._teclear(monkeypatch, "una-clave-larga-123", "una-clave-larga-123")
        with pytest.raises(SystemExit, match="Ya existe"):
            usuarios_cli.main(["crear", "--usuario", DUENO])

    def test_cambiar_la_contrasena_de_alguien(self, monkeypatch, iniciar_sesion):
        self._teclear(monkeypatch, "clave-recuperada-456", "clave-recuperada-456")
        usuarios_cli.main(["password", "--usuario", DUENO])
        assert iniciar_sesion(DUENO, PASSWORD_DUENO).status_code == 401
        assert iniciar_sesion(DUENO, "clave-recuperada-456").status_code == 200

    def test_cambiar_la_contrasena_de_alguien_que_no_existe(self):
        with pytest.raises(SystemExit, match="No existe"):
            usuarios_cli.main(["password", "--usuario", "fantasma"])
