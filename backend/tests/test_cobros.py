"""Cobros: seña y saldo (50 y 50), nunca de más, anulaciones y paso a "cobrado"."""

import datetime as dt

import pytest
from conftest import DUENO, PASSWORD_DUENO, PASSWORD_EMPLEADO, presupuesto_valido
from sqlalchemy.exc import IntegrityError

from presupuestos_backend.database import SessionLocal
from presupuestos_backend.models import Cobro, ahora_utc

HOY = ahora_utc().date().isoformat()
AYER = (ahora_utc().date() - dt.timedelta(days=1)).isoformat()
MANANA = (ahora_utc().date() + dt.timedelta(days=1)).isoformat()


def _trabajo(client, importe=1000, nombre="Consorcio Sol", direccion="Corrientes 1200"):
    """Un trabajo "por agendar" cuyo presupuesto total es `importe`."""
    cliente = client.post("/api/clientes", json={"nombre": nombre, "tipo": "consorcio"}).json()
    obra = client.post(f"/api/clientes/{cliente['id']}/obras", json={"direccion": direccion}).json()
    items = [{"descripcion": "Pintura", "cantidad": 1, "importe": importe}]
    datos = presupuesto_valido(cliente_id=cliente["id"], obra_id=obra["id"], items=items)
    p = client.post("/api/presupuestos", json=datos).json()
    client.put(f"/api/presupuestos/{p['id']}/estado", json={"estado": "aprobado"})
    r = client.post(f"/api/presupuestos/{p['id']}/trabajo")
    assert r.status_code == 201, r.text
    return r.json()


def _agendado(client, inicio="2026-12-10", fin="2026-12-12", **trabajo):
    t = _trabajo(client, **trabajo)
    r = client.post(
        f"/api/trabajos/{t['id']}/agendar", json={"fecha_inicio": inicio, "fecha_fin": fin}
    )
    assert r.status_code == 200, r.text
    return r.json()


def _accion(client, trabajo_id, accion):
    return client.post(f"/api/trabajos/{trabajo_id}/{accion}")


def _cobrar(client, trabajo_id, monto, concepto="sena", fecha=HOY, nota=""):
    return client.post(
        f"/api/trabajos/{trabajo_id}/cobros",
        json={"concepto": concepto, "monto": monto, "fecha": fecha, "nota": nota},
    )


def _resumen(client, trabajo_id):
    return client.get(f"/api/trabajos/{trabajo_id}/cobros").json()


def _estado(client, trabajo_id):
    return client.get(f"/api/trabajos/{trabajo_id}").json()["estado"]


class TestResumenYSugerencias:
    def test_un_trabajo_sin_cobros(self, autenticado):
        t = _trabajo(autenticado, importe=1000)
        r = _resumen(autenticado, t["id"])
        assert (r["total"], r["cobrado"], r["pendiente"]) == (1000.0, 0.0, 1000.0)
        assert (r["sugerido_sena"], r["sugerido_saldo"]) == (500.0, 1000.0)
        assert r["cobros"] == []

    def test_la_sena_sugerida_es_la_mitad_redondeada_al_centavo(self, autenticado):
        # 1000,01 / 2 = 500,005 -> 500,01 (redondeo "como a mano").
        t = _trabajo(autenticado, importe=1000.01)
        assert _resumen(autenticado, t["id"])["sugerido_sena"] == 500.01

    def test_despues_de_cobrar_la_sena_ya_no_se_sugiere_otra(self, autenticado):
        t = _trabajo(autenticado, importe=1000)
        _cobrar(autenticado, t["id"], 500, "sena")
        r = _resumen(autenticado, t["id"])
        assert (r["cobrado"], r["pendiente"]) == (500.0, 500.0)
        assert (r["sugerido_sena"], r["sugerido_saldo"]) == (0.0, 500.0)

    def test_una_sena_chica_deja_sugerida_la_diferencia_hasta_la_mitad(self, autenticado):
        t = _trabajo(autenticado, importe=1000)
        _cobrar(autenticado, t["id"], 200, "sena")
        assert _resumen(autenticado, t["id"])["sugerido_sena"] == 300.0

    def test_trabajo_inexistente_da_404(self, autenticado):
        assert autenticado.get("/api/trabajos/99999/cobros").status_code == 404
        assert _cobrar(autenticado, 99999, 100).status_code == 404


class TestRegistrarCobros:
    def test_registrar_la_sena(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        r = _cobrar(autenticado, t["id"], 500, "sena", nota="Efectivo")
        assert r.status_code == 201
        resumen = r.json()
        assert (resumen["cobrado"], resumen["pendiente"]) == (500.0, 500.0)
        cobro = resumen["cobros"][0]
        assert (cobro["concepto"], cobro["monto"], cobro["fecha"], cobro["nota"]) == (
            "sena",
            500.0,
            HOY,
            "Efectivo",
        )
        assert cobro["usuario_nombre"] == "Dueño de Prueba"
        assert cobro["anulado"] is False

    def test_se_puede_cobrar_una_sena_antes_de_agendar(self, autenticado):
        t = _trabajo(autenticado, importe=1000)
        assert _cobrar(autenticado, t["id"], 500).status_code == 201

    def test_se_acepta_un_monto_distinto_a_la_mitad(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        assert _cobrar(autenticado, t["id"], 300, "sena").status_code == 201

    def test_los_centavos_suman_exacto(self, autenticado):
        t = _agendado(autenticado, importe=0.3)
        _cobrar(autenticado, t["id"], 0.1)
        r = _cobrar(autenticado, t["id"], 0.2)
        # Con float, 0.1 + 0.2 = 0.30000000000000004 y esto daría "supera lo que falta".
        assert r.status_code == 201
        assert r.json()["pendiente"] == 0.0

    def test_el_monto_se_redondea_al_centavo(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        r = _cobrar(autenticado, t["id"], 10.005)
        assert r.json()["cobros"][0]["monto"] == 10.01

    def test_no_se_cobra_mas_de_lo_que_falta(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        _cobrar(autenticado, t["id"], 600)
        r = _cobrar(autenticado, t["id"], 400.01, "saldo")
        assert r.status_code == 409
        assert "supera lo que falta cobrar" in r.json()["detail"]
        assert "400,00" in r.json()["detail"]  # le dice cuánto falta, en formato argentino
        assert _resumen(autenticado, t["id"])["cobrado"] == 600.0  # no se guardó nada

    def test_se_puede_cobrar_exactamente_lo_que_falta(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        _cobrar(autenticado, t["id"], 600)
        assert _cobrar(autenticado, t["id"], 400, "saldo").status_code == 201

    def test_un_monto_menor_al_centavo_no_vale(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        r = _cobrar(autenticado, t["id"], 0.004)
        assert r.status_code == 409 and "mayor a cero" in r.json()["detail"]

    @pytest.mark.parametrize("monto", [0, -50, 1e12])
    def test_montos_invalidos_dan_422_legible(self, autenticado, monto):
        t = _agendado(autenticado, importe=1000)
        r = _cobrar(autenticado, t["id"], monto)
        assert r.status_code == 422 and "Monto" in r.json()["detail"]

    def test_el_concepto_tiene_que_ser_sena_o_saldo(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        r = _cobrar(autenticado, t["id"], 100, concepto="propina")
        assert r.status_code == 422 and "Concepto" in r.json()["detail"]

    def test_la_fecha_no_puede_ser_futura_pero_puede_ser_anterior(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        r = _cobrar(autenticado, t["id"], 100, fecha=MANANA)
        assert r.status_code == 409 and "futura" in r.json()["detail"]
        assert _cobrar(autenticado, t["id"], 100, fecha=AYER).status_code == 201
        assert _cobrar(autenticado, t["id"], 100, fecha=HOY).status_code == 201

    def test_una_fecha_mal_escrita_da_422(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        r = _cobrar(autenticado, t["id"], 100, fecha="ayer")
        assert r.status_code == 422 and "Fecha" in r.json()["detail"]

    def test_la_nota_es_opcional_y_se_limpia(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        r = autenticado.post(
            f"/api/trabajos/{t['id']}/cobros",
            json={"concepto": "sena", "monto": 100, "fecha": HOY, "nota": "  Transferencia  "},
        )
        assert r.json()["cobros"][0]["nota"] == "Transferencia"
        sin_nota = autenticado.post(
            f"/api/trabajos/{t['id']}/cobros",
            json={"concepto": "sena", "monto": 100, "fecha": HOY},
        )
        assert sin_nota.status_code == 201

    def test_no_se_cobra_un_trabajo_cancelado(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        _accion(autenticado, t["id"], "cancelar")
        r = _cobrar(autenticado, t["id"], 100)
        assert r.status_code == 409 and "cancelado" in r.json()["detail"]


class TestPasoACobrado:
    def test_el_flujo_normal_50_y_50(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        _accion(autenticado, t["id"], "iniciar")
        _cobrar(autenticado, t["id"], 500, "sena")
        assert _estado(autenticado, t["id"]) == "en_curso"

        _accion(autenticado, t["id"], "terminar")
        assert _estado(autenticado, t["id"]) == "terminado"  # falta el saldo

        r = _cobrar(autenticado, t["id"], 500, "saldo")
        assert r.json()["estado_trabajo"] == "cobrado"
        assert _estado(autenticado, t["id"]) == "cobrado"

    def test_pagado_todo_pero_sin_terminar_no_es_cobrado(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        _cobrar(autenticado, t["id"], 1000)
        assert _estado(autenticado, t["id"]) == "agendado"

    def test_si_ya_estaba_todo_pagado_al_terminar_pasa_directo_a_cobrado(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        _cobrar(autenticado, t["id"], 1000)
        assert _accion(autenticado, t["id"], "terminar").json()["estado"] == "cobrado"

    def test_un_trabajo_de_total_cero_queda_cobrado_al_terminar(self, autenticado):
        t = _agendado(autenticado, importe=0)
        assert _accion(autenticado, t["id"], "terminar").json()["estado"] == "cobrado"
        r = _cobrar(autenticado, t["id"], 1)
        assert r.status_code == 409 and "supera" in r.json()["detail"]

    def test_un_trabajo_cobrado_ya_no_se_reprograma_ni_se_cancela(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        _cobrar(autenticado, t["id"], 1000)
        _accion(autenticado, t["id"], "terminar")
        assert _accion(autenticado, t["id"], "cancelar").status_code == 409
        r = autenticado.post(
            f"/api/trabajos/{t['id']}/reprogramar",
            json={"fecha_inicio": "2026-12-20", "fecha_fin": "2026-12-21", "causa": "otra"},
        )
        assert r.status_code == 409


class TestAnularCobros:
    def _con_un_cobro(self, client, importe=1000, monto=500):
        t = _agendado(client, importe=importe)
        cobro = _cobrar(client, t["id"], monto).json()["cobros"][0]
        return t, cobro

    def test_un_cobro_anulado_deja_de_contar_pero_queda_registrado(self, autenticado):
        t, cobro = self._con_un_cobro(autenticado)
        r = autenticado.post(f"/api/cobros/{cobro['id']}/anular")
        assert r.status_code == 200
        resumen = r.json()
        assert (resumen["cobrado"], resumen["pendiente"]) == (0.0, 1000.0)
        assert len(resumen["cobros"]) == 1  # sigue en el historial
        assert resumen["cobros"][0]["anulado"] is True
        assert resumen["cobros"][0]["anulado_en"] is not None

    def test_un_cobro_anulado_libera_lugar_para_volver_a_cobrar(self, autenticado):
        t, cobro = self._con_un_cobro(autenticado, monto=1000)
        autenticado.post(f"/api/cobros/{cobro['id']}/anular")
        assert _cobrar(autenticado, t["id"], 1000).status_code == 201

    def test_no_se_anula_dos_veces(self, autenticado):
        _, cobro = self._con_un_cobro(autenticado)
        autenticado.post(f"/api/cobros/{cobro['id']}/anular")
        r = autenticado.post(f"/api/cobros/{cobro['id']}/anular")
        assert r.status_code == 409 and "ya estaba anulado" in r.json()["detail"]

    def test_cobro_inexistente_da_404(self, autenticado):
        assert autenticado.post("/api/cobros/99999/anular").status_code == 404

    def test_anular_un_cobro_de_un_trabajo_cobrado_lo_vuelve_a_terminado(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        cobro = _cobrar(autenticado, t["id"], 1000).json()["cobros"][0]
        _accion(autenticado, t["id"], "terminar")
        assert _estado(autenticado, t["id"]) == "cobrado"

        autenticado.post(f"/api/cobros/{cobro['id']}/anular")
        assert _estado(autenticado, t["id"]) == "terminado"

    def test_con_cobros_vigentes_no_se_cancela_el_trabajo(self, autenticado):
        t, cobro = self._con_un_cobro(autenticado)
        r = _accion(autenticado, t["id"], "cancelar")
        assert r.status_code == 409 and "cobros registrados" in r.json()["detail"]
        assert _estado(autenticado, t["id"]) == "agendado"

        autenticado.post(f"/api/cobros/{cobro['id']}/anular")
        assert _accion(autenticado, t["id"], "cancelar").status_code == 200

    def test_el_registro_dice_quien_anulo_y_cuando(self, autenticado):
        _, cobro = self._con_un_cobro(autenticado)
        autenticado.post(f"/api/cobros/{cobro['id']}/anular")
        with SessionLocal() as db:
            guardado = db.get(Cobro, cobro["id"])
            assert guardado.anulado_en is not None
            assert guardado.anulado_por_id is not None


class TestPendientes:
    def test_lista_lo_que_falta_cobrar_con_el_total(self, autenticado):
        a = _agendado(autenticado, "2026-12-10", "2026-12-11", importe=1000, nombre="Ana")
        _agendado(autenticado, "2026-12-20", "2026-12-21", importe=2000, nombre="Beto")
        _cobrar(autenticado, a["id"], 500)
        r = autenticado.get("/api/cobros/pendientes").json()
        assert r["total_pendiente"] == 2500.0  # 500 de Ana + 2000 de Beto
        por_cliente = {t["cliente"]: t for t in r["trabajos"]}
        assert por_cliente["Ana"]["pendiente"] == 500.0
        assert por_cliente["Ana"]["cobrado"] == 500.0
        assert por_cliente["Beto"]["total"] == 2000.0

    def test_primero_los_terminados_que_ya_se_deben(self, autenticado):
        _agendado(autenticado, "2026-12-01", "2026-12-02", nombre="Futuro")
        terminado = _agendado(autenticado, "2026-12-10", "2026-12-11", nombre="Terminado")
        _accion(autenticado, terminado["id"], "terminar")
        clientes = [
            t["cliente"] for t in autenticado.get("/api/cobros/pendientes").json()["trabajos"]
        ]
        assert clientes == ["Terminado", "Futuro"]

    def test_no_aparecen_los_cobrados_ni_los_cancelados(self, autenticado):
        cobrado = _agendado(autenticado, "2026-12-01", "2026-12-02", nombre="Cobrado")
        _cobrar(autenticado, cobrado["id"], 1000)
        _accion(autenticado, cobrado["id"], "terminar")
        cancelado = _agendado(autenticado, "2026-12-10", "2026-12-11", nombre="Cancelado")
        _accion(autenticado, cancelado["id"], "cancelar")
        r = autenticado.get("/api/cobros/pendientes").json()
        assert r["trabajos"] == [] and r["total_pendiente"] == 0.0

    def test_sin_trabajos(self, autenticado):
        assert autenticado.get("/api/cobros/pendientes").json() == {
            "total_pendiente": 0.0,
            "trabajos": [],
        }


class TestPermisos:
    @pytest.fixture
    def sesion_de_ana(self, empleado, iniciar_sesion, client):
        """El dueño carga un trabajo con un cobro; después entra Ana, la empleada."""
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        t = _agendado(client, importe=1000)
        cobro = _cobrar(client, t["id"], 500).json()["cobros"][0]
        assert iniciar_sesion("ana", PASSWORD_EMPLEADO).status_code == 200
        return client, t, cobro

    def test_el_empleado_no_puede_ver_ni_registrar_ni_anular_cobros(self, sesion_de_ana):
        client, t, cobro = sesion_de_ana
        assert client.get(f"/api/trabajos/{t['id']}/cobros").status_code == 403
        assert _cobrar(client, t["id"], 100).status_code == 403
        assert client.post(f"/api/cobros/{cobro['id']}/anular").status_code == 403
        assert client.get("/api/cobros/pendientes").status_code == 403

    def test_nada_cambio_por_los_intentos_del_empleado(self, sesion_de_ana, iniciar_sesion):
        client, t, cobro = sesion_de_ana
        _cobrar(client, t["id"], 100)
        client.post(f"/api/cobros/{cobro['id']}/anular")
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        resumen = _resumen(client, t["id"])
        assert resumen["cobrado"] == 500.0 and len(resumen["cobros"]) == 1

    def test_el_empleado_sigue_sin_ver_plata_en_los_trabajos(self, sesion_de_ana):
        client, t, _ = sesion_de_ana
        for r in (client.get("/api/trabajos"), client.get(f"/api/trabajos/{t['id']}")):
            texto = r.text.lower()
            for palabra in ("cobro", "pendiente", "monto", "sena", "saldo", "500", "1000"):
                assert palabra not in texto, f"'{palabra}' no debería verlo el empleado"

    def test_el_empleado_si_puede_terminar_y_eso_no_le_muestra_plata(self, sesion_de_ana):
        client, t, _ = sesion_de_ana
        r = _accion(client, t["id"], "terminar")
        assert r.status_code == 200 and r.json()["estado"] == "terminado"
        assert "cobro" not in r.text.lower()

    def test_sin_sesion_todo_da_401(self, client):
        assert client.get("/api/trabajos/1/cobros").status_code == 401
        assert client.post("/api/trabajos/1/cobros", json={}).status_code == 401
        assert client.post("/api/cobros/1/anular").status_code == 401
        assert client.get("/api/cobros/pendientes").status_code == 401


class TestGarantiaDeLaBase:
    def test_la_base_rechaza_un_monto_cero_o_negativo(self, autenticado):
        t = _agendado(autenticado, importe=1000)
        for monto in (0, -10):
            with pytest.raises(IntegrityError), SessionLocal() as db:
                db.add(
                    Cobro(
                        trabajo_id=t["id"],
                        concepto="sena",
                        monto=monto,
                        fecha=dt.date.today(),
                        usuario_id=1,
                    )
                )
                db.commit()
