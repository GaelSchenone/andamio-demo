"""Presupuesto -> trabajo: estados, vínculo con cliente y obra, y que el empleado nunca vea precios."""

import pytest
from conftest import DUENO, PASSWORD_DUENO, PASSWORD_EMPLEADO, presupuesto_valido
from sqlalchemy.exc import IntegrityError

from presupuestos_backend.database import SessionLocal
from presupuestos_backend.models import Trabajo

IMPORTE_SECRETO = 123456.78  # un importe reconocible, para buscarlo en las respuestas del empleado


def _cliente_con_obra(client, nombre="Consorcio Sol", direccion="Corrientes 1200"):
    cliente = client.post("/api/clientes", json={"nombre": nombre, "tipo": "consorcio"}).json()
    obra = client.post(
        f"/api/clientes/{cliente['id']}/obras", json={"direccion": direccion, "referencia": "Hall"}
    ).json()
    return cliente, obra


def _presupuesto(client, cliente=None, obra=None, **cambios):
    datos = presupuesto_valido(**cambios)
    if cliente:
        datos["cliente_id"] = cliente["id"]
    if obra:
        datos["obra_id"] = obra["id"]
    r = client.post("/api/presupuestos", json=datos)
    assert r.status_code == 201, r.text
    return r.json()


def _estado(client, presupuesto_id, estado):
    return client.put(f"/api/presupuestos/{presupuesto_id}/estado", json={"estado": estado})


def _aprobado(client, **cambios):
    """Un presupuesto aprobado y listo para pasar a trabajo."""
    cliente, obra = _cliente_con_obra(client)
    p = _presupuesto(client, cliente, obra, **cambios)
    assert _estado(client, p["id"], "aprobado").status_code == 200
    return p, cliente, obra


def _pasar_a_trabajo(client, presupuesto_id):
    return client.post(f"/api/presupuestos/{presupuesto_id}/trabajo")


class TestVinculoConClienteYObra:
    def test_un_presupuesto_nuevo_arranca_como_borrador(self, autenticado):
        p = _presupuesto(autenticado)
        assert p["estado"] == "borrador"
        assert (p["cliente_id"], p["obra_id"], p["trabajo_id"]) == (None, None, None)

    def test_se_puede_vincular_a_un_cliente_y_una_obra(self, autenticado):
        cliente, obra = _cliente_con_obra(autenticado)
        p = _presupuesto(autenticado, cliente, obra)
        assert (p["cliente_id"], p["obra_id"]) == (cliente["id"], obra["id"])

    def test_se_puede_vincular_solo_el_cliente(self, autenticado):
        cliente, _ = _cliente_con_obra(autenticado)
        assert _presupuesto(autenticado, cliente)["cliente_id"] == cliente["id"]

    def test_una_obra_de_otro_cliente_es_rechazada(self, autenticado):
        cliente, _ = _cliente_con_obra(autenticado)
        _, obra_ajena = _cliente_con_obra(autenticado, nombre="Otro", direccion="Calle 9")
        datos = presupuesto_valido(cliente_id=cliente["id"], obra_id=obra_ajena["id"])
        r = autenticado.post("/api/presupuestos", json=datos)
        assert r.status_code == 422
        assert "no es de ese cliente" in r.json()["detail"]

    def test_una_obra_sin_cliente_es_rechazada(self, autenticado):
        _, obra = _cliente_con_obra(autenticado)
        r = autenticado.post("/api/presupuestos", json=presupuesto_valido(obra_id=obra["id"]))
        assert r.status_code == 422
        assert "cliente" in r.json()["detail"]

    @pytest.mark.parametrize("campo", ["cliente_id", "obra_id"])
    def test_ids_inexistentes_son_rechazados(self, autenticado, campo):
        cliente, _ = _cliente_con_obra(autenticado)
        datos = presupuesto_valido(cliente_id=cliente["id"])
        datos[campo] = 99999
        assert autenticado.post("/api/presupuestos", json=datos).status_code == 422

    def test_al_editar_tambien_se_valida_y_se_puede_desvincular(self, autenticado):
        cliente, obra = _cliente_con_obra(autenticado)
        p = _presupuesto(autenticado, cliente, obra)
        url = f"/api/presupuestos/{p['id']}"
        assert autenticado.put(url, json=presupuesto_valido(obra_id=obra["id"])).status_code == 422
        r = autenticado.put(url, json=presupuesto_valido())
        assert r.status_code == 200
        assert (r.json()["cliente_id"], r.json()["obra_id"]) == (None, None)

    def test_no_se_borra_un_cliente_ni_una_obra_con_presupuestos(self, autenticado):
        cliente, obra = _cliente_con_obra(autenticado)
        p = _presupuesto(autenticado, cliente, obra)

        r = autenticado.delete(f"/api/obras/{obra['id']}")
        assert r.status_code == 409 and "presupuestos" in r.json()["detail"]
        # El cliente además tiene obras: se avisa por eso primero.
        assert autenticado.delete(f"/api/clientes/{cliente['id']}").status_code == 409

        # Sin obras pero con presupuesto vinculado al cliente, tampoco.
        sin_obra = autenticado.post("/api/clientes", json={"nombre": "X", "tipo": "casa"}).json()
        _presupuesto(autenticado, sin_obra)
        r = autenticado.delete(f"/api/clientes/{sin_obra['id']}")
        assert r.status_code == 409 and "presupuestos" in r.json()["detail"]

        autenticado.delete(f"/api/presupuestos/{p['id']}")  # al borrar el presupuesto, ya se puede
        assert autenticado.delete(f"/api/obras/{obra['id']}").status_code == 204


class TestEstadosDelPresupuesto:
    def test_se_mueve_libremente_entre_borrador_enviado_y_rechazado(self, autenticado):
        p = _presupuesto(autenticado)
        for estado in ("enviado", "rechazado", "enviado", "borrador", "rechazado"):
            r = _estado(autenticado, p["id"], estado)
            assert r.status_code == 200 and r.json()["estado"] == estado

    def test_el_estado_aparece_en_el_listado(self, autenticado):
        p = _presupuesto(autenticado)
        _estado(autenticado, p["id"], "enviado")
        assert autenticado.get("/api/presupuestos").json()[0]["estado"] == "enviado"

    def test_repetir_el_mismo_estado_no_falla(self, autenticado):
        p = _presupuesto(autenticado)
        assert _estado(autenticado, p["id"], "borrador").status_code == 200

    def test_un_estado_inventado_da_422(self, autenticado):
        p = _presupuesto(autenticado)
        assert _estado(autenticado, p["id"], "casi-aprobado").status_code == 422

    def test_presupuesto_inexistente_da_404(self, autenticado):
        assert _estado(autenticado, 99999, "enviado").status_code == 404

    def test_no_se_puede_aprobar_sin_cliente_y_obra(self, autenticado):
        p = _presupuesto(autenticado)
        r = _estado(autenticado, p["id"], "aprobado")
        assert r.status_code == 409
        assert "cliente y la obra" in r.json()["detail"]
        # Solo el cliente tampoco alcanza: el trabajo necesita un lugar adonde ir.
        cliente, _ = _cliente_con_obra(autenticado)
        con_cliente = _presupuesto(autenticado, cliente)
        assert _estado(autenticado, con_cliente["id"], "aprobado").status_code == 409

    def test_aprobar_con_cliente_y_obra(self, autenticado):
        p, _, _ = _aprobado(autenticado)
        assert autenticado.get(f"/api/presupuestos/{p['id']}").json()["estado"] == "aprobado"

    def test_un_presupuesto_aprobado_no_se_edita_ni_se_borra(self, autenticado):
        p, cliente, obra = _aprobado(autenticado)
        url = f"/api/presupuestos/{p['id']}"
        r = autenticado.put(
            url, json=presupuesto_valido(cliente_id=cliente["id"], obra_id=obra["id"])
        )
        assert r.status_code == 409 and "aprobado" in r.json()["detail"]
        assert autenticado.delete(url).status_code == 409

        # Si se lo pasa a otro estado, vuelve a poder editarse y borrarse.
        _estado(autenticado, p["id"], "enviado")
        assert autenticado.delete(url).status_code == 204

    def test_el_total_no_cambia_si_se_intenta_editar_un_aprobado(self, autenticado):
        p, cliente, obra = _aprobado(autenticado)
        datos = presupuesto_valido(
            cliente_id=cliente["id"],
            obra_id=obra["id"],
            items=[{"descripcion": "Otra cosa", "cantidad": 1, "importe": 999999}],
        )
        autenticado.put(f"/api/presupuestos/{p['id']}", json=datos)
        assert autenticado.get(f"/api/presupuestos/{p['id']}").json()["total"] == 1000.0


class TestPaseATrabajo:
    def test_un_presupuesto_aprobado_se_pasa_a_trabajo_por_agendar(self, autenticado):
        p, cliente, obra = _aprobado(autenticado)
        r = _pasar_a_trabajo(autenticado, p["id"])
        assert r.status_code == 201
        t = r.json()
        assert t["estado"] == "por_agendar"
        assert t["presupuesto_id"] == p["id"]
        assert t["presupuesto_numero"] == p["numero"]
        assert t["cliente"]["nombre"] == cliente["nombre"]
        assert t["obra"]["direccion"] == obra["direccion"]
        assert t["tareas"][0]["descripcion"] == "Pintura de living"
        assert autenticado.get(f"/api/presupuestos/{p['id']}").json()["trabajo_id"] == t["id"]

    @pytest.mark.parametrize("estado", ["borrador", "enviado", "rechazado"])
    def test_solo_se_pasa_a_trabajo_un_presupuesto_aprobado(self, autenticado, estado):
        cliente, obra = _cliente_con_obra(autenticado)
        p = _presupuesto(autenticado, cliente, obra)
        _estado(autenticado, p["id"], estado)
        r = _pasar_a_trabajo(autenticado, p["id"])
        assert r.status_code == 409
        assert "aprobado" in r.json()["detail"]

    def test_no_se_pasa_dos_veces(self, autenticado):
        p, _, _ = _aprobado(autenticado)
        assert _pasar_a_trabajo(autenticado, p["id"]).status_code == 201
        r = _pasar_a_trabajo(autenticado, p["id"])
        assert r.status_code == 409 and "ya tiene un trabajo" in r.json()["detail"]
        assert len(autenticado.get("/api/trabajos").json()) == 1

    def test_presupuesto_inexistente_da_404(self, autenticado):
        assert _pasar_a_trabajo(autenticado, 99999).status_code == 404

    def test_el_listado_de_presupuestos_indica_cual_ya_tiene_trabajo(self, autenticado):
        con_trabajo, _, _ = _aprobado(autenticado)
        sin_trabajo, _, _ = _aprobado(autenticado)
        trabajo = _pasar_a_trabajo(autenticado, con_trabajo["id"]).json()

        filas = {p["id"]: p for p in autenticado.get("/api/presupuestos").json()}
        assert filas[con_trabajo["id"]]["trabajo_id"] == trabajo["id"]
        assert filas[sin_trabajo["id"]]["trabajo_id"] is None
        assert filas[sin_trabajo["id"]]["estado"] == "aprobado"

    def test_con_trabajo_vigente_no_se_le_saca_la_aprobacion_ni_se_borra(self, autenticado):
        p, _, _ = _aprobado(autenticado)
        _pasar_a_trabajo(autenticado, p["id"])
        r = _estado(autenticado, p["id"], "rechazado")
        assert r.status_code == 409 and "Cancelá el trabajo" in r.json()["detail"]
        assert autenticado.delete(f"/api/presupuestos/{p['id']}").status_code == 409
        assert autenticado.get(f"/api/presupuestos/{p['id']}").json()["estado"] == "aprobado"

    def test_cancelar_el_trabajo_libera_al_presupuesto(self, autenticado):
        p, _, _ = _aprobado(autenticado)
        t = _pasar_a_trabajo(autenticado, p["id"]).json()

        r = autenticado.post(f"/api/trabajos/{t['id']}/cancelar")
        assert r.status_code == 200 and r.json()["estado"] == "cancelado"
        assert autenticado.get(f"/api/presupuestos/{p['id']}").json()["trabajo_id"] is None
        assert _estado(autenticado, p["id"], "enviado").status_code == 200

    def test_despues_de_cancelar_se_puede_crear_otro_trabajo(self, autenticado):
        p, _, _ = _aprobado(autenticado)
        primero = _pasar_a_trabajo(autenticado, p["id"]).json()
        autenticado.post(f"/api/trabajos/{primero['id']}/cancelar")
        segundo = _pasar_a_trabajo(autenticado, p["id"])
        assert segundo.status_code == 201
        assert segundo.json()["id"] != primero["id"]

    def test_un_trabajo_cancelado_no_se_cancela_otra_vez(self, autenticado):
        p, _, _ = _aprobado(autenticado)
        t = _pasar_a_trabajo(autenticado, p["id"]).json()
        autenticado.post(f"/api/trabajos/{t['id']}/cancelar")
        r = autenticado.post(f"/api/trabajos/{t['id']}/cancelar")
        assert r.status_code == 409 and "todavía no empezó" in r.json()["detail"]

    def test_un_presupuesto_con_trabajos_cancelados_tampoco_se_borra(self, autenticado):
        # Aunque ya no tenga trabajo vigente, el trabajo cancelado sigue referenciándolo.
        p, _, _ = _aprobado(autenticado)
        t = _pasar_a_trabajo(autenticado, p["id"]).json()
        autenticado.post(f"/api/trabajos/{t['id']}/cancelar")
        _estado(autenticado, p["id"], "enviado")
        r = autenticado.delete(f"/api/presupuestos/{p['id']}")
        assert r.status_code == 409 and "trabajos asociados" in r.json()["detail"]

    def test_listar_oculta_los_cancelados_salvo_que_se_pidan(self, autenticado):
        p1, _, _ = _aprobado(autenticado)
        p2, _, _ = _aprobado(autenticado)
        t1 = _pasar_a_trabajo(autenticado, p1["id"]).json()
        t2 = _pasar_a_trabajo(autenticado, p2["id"]).json()
        autenticado.post(f"/api/trabajos/{t1['id']}/cancelar")

        vigentes = [t["id"] for t in autenticado.get("/api/trabajos").json()]
        assert vigentes == [t2["id"]]
        todos = autenticado.get("/api/trabajos", params={"incluir_cancelados": True}).json()
        assert [t["id"] for t in todos] == [t2["id"], t1["id"]]  # el más nuevo primero

    def test_obtener_y_trabajo_inexistente(self, autenticado):
        p, _, _ = _aprobado(autenticado)
        t = _pasar_a_trabajo(autenticado, p["id"]).json()
        assert autenticado.get(f"/api/trabajos/{t['id']}").json()["id"] == t["id"]
        assert autenticado.get("/api/trabajos/99999").status_code == 404
        assert autenticado.post("/api/trabajos/99999/cancelar").status_code == 404


class TestGarantiaDeLaBase:
    """El índice único parcial protege aunque dos pedidos lleguen a la vez."""

    def _insertar(self, presupuesto_id, estado):
        with SessionLocal() as db:
            db.add(Trabajo(presupuesto_id=presupuesto_id, estado=estado))
            db.commit()

    def test_dos_trabajos_vigentes_para_el_mismo_presupuesto_son_imposibles(self, autenticado):
        p, _, _ = _aprobado(autenticado)
        self._insertar(p["id"], "por_agendar")
        with pytest.raises(IntegrityError):
            self._insertar(p["id"], "agendado")

    def test_los_cancelados_no_cuentan(self, autenticado):
        p, _, _ = _aprobado(autenticado)
        self._insertar(p["id"], "cancelado")
        self._insertar(p["id"], "cancelado")
        self._insertar(p["id"], "por_agendar")  # uno vigente, junto a los cancelados: permitido


class TestElEmpleadoNoVePrecios:
    @pytest.fixture
    def sesion_de_ana(self, empleado, iniciar_sesion, client):
        """El dueño aprueba un presupuesto y lo pasa a trabajo; después entra Ana, la empleada."""
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        p, _, _ = _aprobado(
            client,
            items=[
                {
                    "descripcion": "Pintura de hall",
                    "unidad": "m2",
                    "cantidad": 40,
                    "importe": IMPORTE_SECRETO,
                }
            ],
            forma_pago="50% de anticipo",
        )
        trabajo = _pasar_a_trabajo(client, p["id"]).json()
        assert iniciar_sesion("ana", PASSWORD_EMPLEADO).status_code == 200
        return client, p, trabajo

    def test_ve_el_trabajo_con_cliente_obra_y_tareas(self, sesion_de_ana):
        client, _, trabajo = sesion_de_ana
        lista = client.get("/api/trabajos")
        assert lista.status_code == 200
        t = lista.json()[0]
        assert t["cliente"]["nombre"] == "Consorcio Sol"
        assert t["obra"]["direccion"] == "Corrientes 1200"
        assert t["tareas"] == [{"descripcion": "Pintura de hall", "unidad": "m2", "cantidad": 40.0}]
        assert client.get(f"/api/trabajos/{trabajo['id']}").status_code == 200

    def test_ninguna_respuesta_de_trabajos_trae_importes(self, sesion_de_ana):
        client, _, trabajo = sesion_de_ana
        for r in (client.get("/api/trabajos"), client.get(f"/api/trabajos/{trabajo['id']}")):
            texto = r.text.lower()
            assert "123456" not in texto, "se filtró un importe"
            for palabra in ("importe", "total", "forma_pago", "50% de anticipo"):
                assert palabra not in texto, f"'{palabra}' no debería estar en un trabajo"

    def test_el_dueno_tampoco_recibe_precios_en_trabajos(self, sesion_de_ana, iniciar_sesion):
        client, _, trabajo = sesion_de_ana
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        assert "123456" not in client.get(f"/api/trabajos/{trabajo['id']}").text

    def test_sigue_sin_poder_ver_presupuestos(self, sesion_de_ana):
        client, p, _ = sesion_de_ana
        assert client.get("/api/presupuestos").status_code == 403
        assert client.get(f"/api/presupuestos/{p['id']}").status_code == 403

    def test_no_puede_cambiar_estados_ni_crear_ni_cancelar_trabajos(self, sesion_de_ana):
        client, p, trabajo = sesion_de_ana
        assert _estado(client, p["id"], "rechazado").status_code == 403
        assert _pasar_a_trabajo(client, p["id"]).status_code == 403
        assert client.post(f"/api/trabajos/{trabajo['id']}/cancelar").status_code == 403
        assert client.get(f"/api/trabajos/{trabajo['id']}").json()["estado"] == "por_agendar"

    def test_sin_sesion_todo_da_401(self, client):
        assert client.get("/api/trabajos").status_code == 401
        assert client.get("/api/trabajos/1").status_code == 401
        assert client.post("/api/trabajos/1/cancelar").status_code == 401
        assert client.post("/api/presupuestos/1/trabajo").status_code == 401
        assert (
            client.put("/api/presupuestos/1/estado", json={"estado": "enviado"}).status_code == 401
        )
