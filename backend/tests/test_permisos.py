"""Qué puede y qué no puede hacer cada rol (decisión del negocio, ver permisos.py)."""

import pytest
from conftest import DUENO, PASSWORD_DUENO, PASSWORD_EMPLEADO, presupuesto_valido

from presupuestos_backend.permisos import (
    PERMISOS_DUENO,
    PERMISOS_EMPLEADO,
    ROL_DUENO,
    ROL_EMPLEADO,
    tiene_permiso,
)


class TestMatriz:
    def test_el_empleado_tiene_exactamente_estos_tres_permisos(self):
        assert {"agenda:ver", "trabajos:cambiar_estado", "clientes:ver"} == PERMISOS_EMPLEADO

    @pytest.mark.parametrize(
        "permiso", ["presupuestos:gestionar", "cobros:gestionar", "usuarios:gestionar"]
    )
    def test_el_empleado_no_ve_precios_ni_gestiona_usuarios(self, permiso):
        assert not tiene_permiso(ROL_EMPLEADO, permiso)

    def test_el_duenio_puede_todo_lo_que_puede_el_empleado_y_mas(self):
        assert PERMISOS_EMPLEADO < PERMISOS_DUENO
        assert all(tiene_permiso(ROL_DUENO, p) for p in PERMISOS_DUENO)

    def test_un_rol_desconocido_no_puede_nada(self):
        assert not tiene_permiso("invitado", "agenda:ver")
        assert not tiene_permiso("", "agenda:ver")


class TestEndpointsComoEmpleado:
    @pytest.fixture
    def sesion_de_ana(self, empleado, iniciar_sesion, client):
        # Primero el dueño crea un presupuesto, para que el empleado intente verlo.
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        creado = client.post("/api/presupuestos", json=presupuesto_valido()).json()
        assert iniciar_sesion("ana", PASSWORD_EMPLEADO).status_code == 200
        return client, creado["id"]

    def test_no_puede_ver_ni_crear_presupuestos(self, sesion_de_ana):
        client, id_presupuesto = sesion_de_ana
        assert client.get("/api/presupuestos").status_code == 403
        assert client.get(f"/api/presupuestos/{id_presupuesto}").status_code == 403
        assert client.post("/api/presupuestos", json=presupuesto_valido()).status_code == 403

    def test_no_puede_modificar_ni_borrar_presupuestos(self, sesion_de_ana):
        client, id_presupuesto = sesion_de_ana
        url = f"/api/presupuestos/{id_presupuesto}"
        assert client.put(url, json=presupuesto_valido()).status_code == 403
        assert client.delete(url).status_code == 403

    def test_no_puede_bajar_el_pdf_con_precios(self, sesion_de_ana):
        client, id_presupuesto = sesion_de_ana
        assert client.get(f"/api/presupuestos/{id_presupuesto}/pdf").status_code == 403

    def test_no_puede_usar_el_asistente_de_ia(self, sesion_de_ana):
        client, _ = sesion_de_ana
        assert client.get("/api/asistente/estado").status_code == 403
        assert (
            client.post("/api/asistente/presupuesto", json={"mensaje": "pintar"}).status_code == 403
        )

    def test_no_puede_gestionar_usuarios(self, sesion_de_ana):
        client, _ = sesion_de_ana
        assert client.get("/api/usuarios").status_code == 403
        nuevo = {"nombre": "X", "usuario": "xxx", "password": "una-clave-larga-1", "rol": "dueno"}
        assert client.post("/api/usuarios", json=nuevo).status_code == 403
        assert client.patch("/api/usuarios/1", json={"rol": "dueno"}).status_code == 403
        assert (
            client.post(
                "/api/usuarios/1/password", json={"password_nueva": "una-clave-larga-1"}
            ).status_code
            == 403
        )

    def test_el_prohibido_es_403_y_no_404_ni_se_filtra_el_contenido(self, sesion_de_ana):
        client, id_presupuesto = sesion_de_ana
        r = client.get(f"/api/presupuestos/{id_presupuesto}")
        assert r.status_code == 403
        assert "Juan" not in r.text and "1000" not in r.text

    def test_si_puede_ver_su_perfil_y_cambiar_su_contrasena(self, sesion_de_ana):
        client, _ = sesion_de_ana
        assert client.get("/api/auth/yo").json()["rol"] == "empleado"
        r = client.post(
            "/api/auth/cambiar-password",
            json={"password_actual": PASSWORD_EMPLEADO, "password_nueva": "otra-clave-de-ana-9"},
        )
        assert r.status_code == 200

    def test_no_puede_subirse_el_rol_a_si_mismo(self, sesion_de_ana):
        client, _ = sesion_de_ana
        mi_id = client.get("/api/auth/yo").json()["id"]
        assert client.patch(f"/api/usuarios/{mi_id}", json={"rol": "dueno"}).status_code == 403
        assert client.get("/api/auth/yo").json()["rol"] == "empleado"


class TestElRolSeLeeSiempreDeLaBase:
    def test_bajarle_el_rol_a_alguien_con_sesion_abierta_le_quita_permisos_al_instante(
        self, autenticado, iniciar_sesion, client
    ):
        autenticado.post(
            "/api/usuarios",
            json={
                "nombre": "Socio",
                "usuario": "socio",
                "password": "clave-del-socio-1",
                "rol": "dueno",
            },
        )
        socio_id = next(
            u["id"] for u in client.get("/api/usuarios").json() if u["usuario"] == "socio"
        )

        iniciar_sesion("socio", "clave-del-socio-1")
        assert client.get("/api/presupuestos").status_code == 200

        iniciar_sesion(DUENO, PASSWORD_DUENO)
        client.patch(f"/api/usuarios/{socio_id}", json={"rol": "empleado"})

        iniciar_sesion("socio", "clave-del-socio-1")
        assert client.get("/api/presupuestos").status_code == 403
