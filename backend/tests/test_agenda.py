"""Calendario: agendar, no superponer, reprogramar con historial, iniciar y terminar."""

import pytest
from conftest import DUENO, PASSWORD_DUENO, PASSWORD_EMPLEADO, presupuesto_valido
from sqlalchemy.exc import IntegrityError

from presupuestos_backend.database import SessionLocal
from presupuestos_backend.models import Trabajo

INICIO, FIN = "2026-12-10", "2026-12-12"  # el trabajo "de referencia": 10, 11 y 12 de diciembre


def _trabajo(client, nombre="Consorcio Sol", direccion="Corrientes 1200"):
    """Un trabajo recién creado ("por agendar"), con su cliente, obra y presupuesto aprobado."""
    cliente = client.post("/api/clientes", json={"nombre": nombre, "tipo": "consorcio"}).json()
    obra = client.post(f"/api/clientes/{cliente['id']}/obras", json={"direccion": direccion}).json()
    datos = presupuesto_valido(cliente_id=cliente["id"], obra_id=obra["id"])
    p = client.post("/api/presupuestos", json=datos).json()
    aprobado = client.put(f"/api/presupuestos/{p['id']}/estado", json={"estado": "aprobado"})
    assert aprobado.status_code == 200, aprobado.text
    r = client.post(f"/api/presupuestos/{p['id']}/trabajo")
    assert r.status_code == 201, r.text
    return r.json()


def _agendar(client, trabajo_id, inicio=INICIO, fin=FIN):
    return client.post(
        f"/api/trabajos/{trabajo_id}/agendar", json={"fecha_inicio": inicio, "fecha_fin": fin}
    )


def _agendado(client, inicio=INICIO, fin=FIN, **trabajo):
    t = _trabajo(client, **trabajo)
    r = _agendar(client, t["id"], inicio, fin)
    assert r.status_code == 200, r.text
    return r.json()


def _reprogramar(
    client, trabajo_id, inicio, fin, causa="clima", motivo="Llovió todo el fin de semana"
):
    return client.post(
        f"/api/trabajos/{trabajo_id}/reprogramar",
        json={"fecha_inicio": inicio, "fecha_fin": fin, "causa": causa, "motivo": motivo},
    )


def _accion(client, trabajo_id, accion):
    return client.post(f"/api/trabajos/{trabajo_id}/{accion}")


class TestAgendar:
    def test_agendar_pone_las_fechas_y_pasa_a_agendado(self, autenticado):
        t = _trabajo(autenticado)
        assert (t["estado"], t["fecha_inicio"], t["fecha_fin"]) == ("por_agendar", None, None)
        r = _agendar(autenticado, t["id"])
        assert r.status_code == 200
        assert (r.json()["estado"], r.json()["fecha_inicio"], r.json()["fecha_fin"]) == (
            "agendado",
            INICIO,
            FIN,
        )

    def test_un_trabajo_de_un_solo_dia(self, autenticado):
        t = _trabajo(autenticado)
        assert _agendar(autenticado, t["id"], INICIO, INICIO).status_code == 200

    def test_el_fin_no_puede_ser_anterior_al_inicio(self, autenticado):
        t = _trabajo(autenticado)
        r = _agendar(autenticado, t["id"], "2026-12-12", "2026-12-10")
        assert r.status_code == 409
        assert "anterior" in r.json()["detail"]
        assert autenticado.get(f"/api/trabajos/{t['id']}").json()["estado"] == "por_agendar"

    def test_un_trabajo_no_puede_durar_mas_de_un_anio(self, autenticado):
        t = _trabajo(autenticado)
        r = _agendar(autenticado, t["id"], "2026-01-01", "2027-06-01")
        assert r.status_code == 409 and "más de 366 días" in r.json()["detail"]

    @pytest.mark.parametrize(
        "datos", [{}, {"fecha_inicio": INICIO}, {"fecha_inicio": "ayer", "fecha_fin": FIN}]
    )
    def test_fechas_faltantes_o_invalidas_dan_422(self, autenticado, datos):
        t = _trabajo(autenticado)
        r = autenticado.post(f"/api/trabajos/{t['id']}/agendar", json=datos)
        assert r.status_code == 422
        assert "Fecha" in r.json()["detail"] or "días" in r.json()["detail"]

    def test_no_se_agenda_dos_veces(self, autenticado):
        t = _agendado(autenticado)
        r = _agendar(autenticado, t["id"], "2026-12-20", "2026-12-21")
        assert r.status_code == 409 and "reprogramalo" in r.json()["detail"]
        assert autenticado.get(f"/api/trabajos/{t['id']}").json()["fecha_inicio"] == INICIO

    def test_un_trabajo_cancelado_no_se_agenda(self, autenticado):
        t = _trabajo(autenticado)
        _accion(autenticado, t["id"], "cancelar")
        r = _agendar(autenticado, t["id"])
        assert r.status_code == 409 and "cancelado" in r.json()["detail"]

    def test_trabajo_inexistente_da_404(self, autenticado):
        assert _agendar(autenticado, 99999).status_code == 404


class TestAgendaUnica:
    @pytest.mark.parametrize(
        ("inicio", "fin", "motivo"),
        [
            ("2026-12-10", "2026-12-12", "mismas fechas"),
            ("2026-12-11", "2026-12-11", "adentro"),
            ("2026-12-08", "2026-12-10", "toca el primer día"),
            ("2026-12-12", "2026-12-14", "toca el último día"),
            ("2026-12-01", "2026-12-31", "lo abarca"),
        ],
    )
    def test_fechas_que_se_pisan_son_rechazadas(self, autenticado, inicio, fin, motivo):
        _agendado(autenticado, nombre="Primero", direccion="Calle Uno 1")
        segundo = _trabajo(autenticado, nombre="Segundo", direccion="Calle Dos 2")
        r = _agendar(autenticado, segundo["id"], inicio, fin)
        assert r.status_code == 409, motivo
        # El mensaje dice con qué trabajo se pisa, para que se pueda resolver.
        assert "Primero" in r.json()["detail"] and "Calle Uno 1" in r.json()["detail"]
        assert "10/12/2026" in r.json()["detail"] and "12/12/2026" in r.json()["detail"]
        assert autenticado.get(f"/api/trabajos/{segundo['id']}").json()["estado"] == "por_agendar"

    @pytest.mark.parametrize(
        ("inicio", "fin"),
        [
            ("2026-12-13", "2026-12-15"),  # arranca el día siguiente a que termina el otro
            ("2026-12-08", "2026-12-09"),  # termina el día anterior a que arranca el otro
            ("2026-12-01", "2026-12-05"),
        ],
    )
    def test_dias_seguidos_sin_compartir_ninguno_estan_permitidos(self, autenticado, inicio, fin):
        _agendado(autenticado, nombre="Primero")
        segundo = _trabajo(autenticado, nombre="Segundo")
        assert _agendar(autenticado, segundo["id"], inicio, fin).status_code == 200

    def test_un_trabajo_cancelado_no_ocupa_la_agenda(self, autenticado):
        primero = _agendado(autenticado)
        _accion(autenticado, primero["id"], "cancelar")
        segundo = _trabajo(autenticado)
        assert _agendar(autenticado, segundo["id"]).status_code == 200

    def test_un_trabajo_por_agendar_no_ocupa_la_agenda(self, autenticado):
        _trabajo(autenticado)  # sin fechas
        otro = _trabajo(autenticado)
        assert _agendar(autenticado, otro["id"]).status_code == 200

    def test_un_trabajo_terminado_sigue_ocupando_sus_dias(self, autenticado):
        primero = _agendado(autenticado)
        _accion(autenticado, primero["id"], "terminar")
        segundo = _trabajo(autenticado)
        assert _agendar(autenticado, segundo["id"]).status_code == 409


class TestReprogramar:
    def test_cambia_las_fechas_y_deja_constancia(self, autenticado):
        t = _agendado(autenticado)
        r = _reprogramar(autenticado, t["id"], "2026-12-15", "2026-12-17")
        assert r.status_code == 200
        assert (r.json()["fecha_inicio"], r.json()["fecha_fin"]) == ("2026-12-15", "2026-12-17")
        assert r.json()["estado"] == "agendado"

        historial = autenticado.get(f"/api/trabajos/{t['id']}/reprogramaciones").json()
        assert len(historial) == 1
        h = historial[0]
        assert (h["fecha_inicio_anterior"], h["fecha_fin_anterior"]) == (INICIO, FIN)
        assert (h["fecha_inicio_nueva"], h["fecha_fin_nueva"]) == ("2026-12-15", "2026-12-17")
        assert (h["causa"], h["motivo"]) == ("clima", "Llovió todo el fin de semana")
        assert h["usuario_nombre"] == "Dueño de Prueba"

    def test_el_historial_guarda_todos_los_cambios_en_orden(self, autenticado):
        t = _agendado(autenticado)
        _reprogramar(
            autenticado, t["id"], "2026-12-15", "2026-12-17", causa="clima", motivo="Lluvia"
        )
        _reprogramar(
            autenticado,
            t["id"],
            "2026-12-20",
            "2026-12-22",
            causa="cliente",
            motivo="Se fue de viaje",
        )
        historial = autenticado.get(f"/api/trabajos/{t['id']}/reprogramaciones").json()
        assert [h["causa"] for h in historial] == ["clima", "cliente"]
        # El segundo cambio parte de donde terminó el primero: no se pierde la cadena.
        assert historial[1]["fecha_inicio_anterior"] == "2026-12-15"

    def test_se_puede_ampliar_hacia_los_dias_que_ya_ocupaba(self, autenticado):
        t = _agendado(autenticado)
        r = _reprogramar(autenticado, t["id"], INICIO, "2026-12-14", motivo="Faltó un día de obra")
        assert r.status_code == 200  # no se pisa a sí mismo

    def test_no_puede_pisar_a_otro_trabajo(self, autenticado):
        _agendado(autenticado, nombre="Otro", direccion="Calle Otra 5")
        propio = _agendado(autenticado, "2026-12-20", "2026-12-21", nombre="Propio")
        r = _reprogramar(autenticado, propio["id"], "2026-12-12", "2026-12-13")
        assert r.status_code == 409 and "Otro" in r.json()["detail"]
        assert (
            autenticado.get(f"/api/trabajos/{propio['id']}").json()["fecha_inicio"] == "2026-12-20"
        )
        assert autenticado.get(f"/api/trabajos/{propio['id']}/reprogramaciones").json() == []

    def test_con_las_mismas_fechas_no_hay_nada_que_reprogramar(self, autenticado):
        t = _agendado(autenticado)
        r = _reprogramar(autenticado, t["id"], INICIO, FIN)
        assert r.status_code == 409 and "mismas" in r.json()["detail"]
        assert autenticado.get(f"/api/trabajos/{t['id']}/reprogramaciones").json() == []

    @pytest.mark.parametrize("motivo", ["", "   ", "ok", "Lo pidió el cliente"])
    def test_se_puede_reprogramar_por_cualquier_motivo_incluso_sin_explicarlo(
        self, autenticado, motivo
    ):
        t = _agendado(autenticado)
        r = _reprogramar(autenticado, t["id"], "2026-12-15", "2026-12-17", motivo=motivo)
        assert r.status_code == 200
        guardado = autenticado.get(f"/api/trabajos/{t['id']}/reprogramaciones").json()[0]
        assert guardado["motivo"] == motivo.strip()
        assert guardado["causa"] == "clima"  # la causa sí queda siempre

    def test_sin_el_campo_motivo_tambien_se_puede_reprogramar(self, autenticado):
        t = _agendado(autenticado)
        r = autenticado.post(
            f"/api/trabajos/{t['id']}/reprogramar",
            json={"fecha_inicio": "2026-12-15", "fecha_fin": "2026-12-17", "causa": "otra"},
        )
        assert r.status_code == 200

    def test_el_detalle_no_puede_ser_larguisimo(self, autenticado):
        t = _agendado(autenticado)
        r = _reprogramar(autenticado, t["id"], "2026-12-15", "2026-12-17", motivo="x" * 501)
        assert r.status_code == 422 and "Motivo" in r.json()["detail"]

    def test_la_causa_si_es_obligatoria(self, autenticado):
        t = _agendado(autenticado)
        r = autenticado.post(
            f"/api/trabajos/{t['id']}/reprogramar",
            json={"fecha_inicio": "2026-12-15", "fecha_fin": "2026-12-17"},
        )
        assert r.status_code == 422 and "Causa" in r.json()["detail"]

    def test_la_causa_tiene_que_ser_una_de_la_lista(self, autenticado):
        t = _agendado(autenticado)
        r = _reprogramar(autenticado, t["id"], "2026-12-15", "2026-12-17", causa="porque sí")
        assert r.status_code == 422 and "Causa" in r.json()["detail"]

    def test_solo_se_reprograma_un_trabajo_agendado_o_en_curso(self, autenticado):
        sin_agendar = _trabajo(autenticado)
        r = _reprogramar(autenticado, sin_agendar["id"], "2026-12-15", "2026-12-17")
        assert r.status_code == 409 and "agendado o en curso" in r.json()["detail"]

        terminado = _agendado(autenticado, "2026-11-01", "2026-11-02")
        _accion(autenticado, terminado["id"], "terminar")
        assert (
            _reprogramar(autenticado, terminado["id"], "2026-12-15", "2026-12-17").status_code
            == 409
        )

    def test_un_trabajo_en_curso_solo_puede_cambiar_el_fin(self, autenticado):
        t = _agendado(autenticado)
        _accion(autenticado, t["id"], "iniciar")
        r = _reprogramar(autenticado, t["id"], "2026-12-11", "2026-12-14")
        assert (
            r.status_code == 409 and "solo se puede cambiar la fecha de fin" in r.json()["detail"]
        )
        r = _reprogramar(autenticado, t["id"], INICIO, "2026-12-14", motivo="Se alargó la obra")
        assert r.status_code == 200 and r.json()["fecha_fin"] == "2026-12-14"
        assert r.json()["estado"] == "en_curso"


class TestIniciarTerminarCancelar:
    def test_el_ciclo_completo(self, autenticado):
        t = _agendado(autenticado)
        assert _accion(autenticado, t["id"], "iniciar").json()["estado"] == "en_curso"
        assert _accion(autenticado, t["id"], "terminar").json()["estado"] == "terminado"

    def test_se_puede_terminar_un_trabajo_que_nadie_marco_como_iniciado(self, autenticado):
        t = _agendado(autenticado)
        assert _accion(autenticado, t["id"], "terminar").json()["estado"] == "terminado"

    def test_no_se_inicia_un_trabajo_sin_agendar_ni_dos_veces(self, autenticado):
        sin_agendar = _trabajo(autenticado)
        assert _accion(autenticado, sin_agendar["id"], "iniciar").status_code == 409
        t = _agendado(autenticado)
        _accion(autenticado, t["id"], "iniciar")
        r = _accion(autenticado, t["id"], "iniciar")
        assert r.status_code == 409 and "agendado" in r.json()["detail"]

    def test_no_se_termina_un_trabajo_sin_agendar_ni_dos_veces(self, autenticado):
        sin_agendar = _trabajo(autenticado)
        assert _accion(autenticado, sin_agendar["id"], "terminar").status_code == 409
        t = _agendado(autenticado)
        _accion(autenticado, t["id"], "terminar")
        assert _accion(autenticado, t["id"], "terminar").status_code == 409

    def test_se_cancela_un_trabajo_agendado_y_sus_fechas_quedan_libres(self, autenticado):
        t = _agendado(autenticado)
        r = _accion(autenticado, t["id"], "cancelar")
        assert r.status_code == 200 and r.json()["estado"] == "cancelado"
        otro = _trabajo(autenticado)
        assert _agendar(autenticado, otro["id"]).status_code == 200

    def test_un_trabajo_que_ya_empezo_no_se_cancela(self, autenticado):
        t = _agendado(autenticado)
        _accion(autenticado, t["id"], "iniciar")
        r = _accion(autenticado, t["id"], "cancelar")
        assert r.status_code == 409 and "todavía no empezó" in r.json()["detail"]

    def test_acciones_sobre_un_trabajo_inexistente_dan_404(self, autenticado):
        for accion in ("iniciar", "terminar", "cancelar"):
            assert _accion(autenticado, 99999, accion).status_code == 404
        assert autenticado.get("/api/trabajos/99999/reprogramaciones").status_code == 404
        assert _reprogramar(autenticado, 99999, "2026-12-15", "2026-12-17").status_code == 404


class TestVistaDeCalendario:
    @pytest.fixture
    def agenda(self, autenticado):
        """Un trabajo a fines de mes, uno a mediados (cargado después) y uno sin agendar."""
        tarde = _agendado(autenticado, "2026-12-20", "2026-12-22", nombre="Tarde")
        temprano = _agendado(autenticado, "2026-12-10", "2026-12-12", nombre="Temprano")
        sin_fecha = _trabajo(autenticado, nombre="Sin fecha")
        return autenticado, tarde, temprano, sin_fecha

    def _ids(self, client, **filtros):
        return [t["id"] for t in client.get("/api/trabajos", params=filtros).json()]

    def test_sin_filtros_trae_todos_los_vigentes_los_mas_nuevos_primero(self, agenda):
        client, tarde, temprano, sin_fecha = agenda
        assert self._ids(client) == [sin_fecha["id"], temprano["id"], tarde["id"]]

    def test_un_rango_trae_solo_los_que_caen_adentro_ordenados_por_fecha(self, agenda):
        client, tarde, temprano, _ = agenda
        assert self._ids(client, desde="2026-12-01", hasta="2026-12-31") == [
            temprano["id"],
            tarde["id"],
        ]
        assert self._ids(client, desde="2026-12-11", hasta="2026-12-15") == [temprano["id"]]
        assert self._ids(client, desde="2026-12-13", hasta="2026-12-19") == []

    def test_cuenta_si_el_trabajo_apenas_toca_el_rango(self, agenda):
        client, tarde, temprano, _ = agenda
        assert self._ids(client, desde="2026-12-12", hasta="2026-12-12") == [temprano["id"]]
        assert self._ids(client, desde="2026-12-22", hasta="2026-12-30") == [tarde["id"]]

    def test_con_un_solo_extremo(self, agenda):
        client, tarde, temprano, _ = agenda
        assert self._ids(client, desde="2026-12-13") == [tarde["id"]]
        assert self._ids(client, hasta="2026-12-15") == [temprano["id"]]

    def test_los_sin_agendar_nunca_aparecen_en_un_rango(self, agenda):
        client, _, _, sin_fecha = agenda
        assert sin_fecha["id"] not in self._ids(client, desde="2000-01-01", hasta="2100-01-01")

    def test_los_cancelados_se_ocultan_salvo_que_se_pidan(self, agenda):
        client, _, temprano, _ = agenda
        _accion(client, temprano["id"], "cancelar")
        assert temprano["id"] not in self._ids(client, desde="2026-12-01", hasta="2026-12-31")
        con_cancelados = self._ids(
            client, desde="2026-12-01", hasta="2026-12-31", incluir_cancelados="true"
        )
        assert temprano["id"] in con_cancelados

    def test_una_fecha_mal_escrita_da_422_legible(self, agenda):
        client = agenda[0]
        r = client.get("/api/trabajos", params={"desde": "no-es-fecha"})
        assert r.status_code == 422 and "Desde" in r.json()["detail"]


class TestGarantiaDeLaBase:
    def _modificar(self, trabajo_id, **cambios):
        with SessionLocal() as db:
            trabajo = db.get(Trabajo, trabajo_id)
            for campo, valor in cambios.items():
                setattr(trabajo, campo, valor)
            db.commit()

    def test_la_base_rechaza_un_fin_anterior_al_inicio(self, autenticado):
        import datetime as dt

        t = _trabajo(autenticado)
        with pytest.raises(IntegrityError):
            self._modificar(
                t["id"], fecha_inicio=dt.date(2026, 12, 12), fecha_fin=dt.date(2026, 12, 10)
            )

    def test_la_base_rechaza_una_sola_fecha(self, autenticado):
        import datetime as dt

        t = _trabajo(autenticado)
        with pytest.raises(IntegrityError):
            self._modificar(t["id"], fecha_inicio=dt.date(2026, 12, 12), fecha_fin=None)

    def test_la_base_acepta_las_dos_fechas_o_ninguna(self, autenticado):
        import datetime as dt

        t = _trabajo(autenticado)
        self._modificar(
            t["id"], fecha_inicio=dt.date(2026, 12, 10), fecha_fin=dt.date(2026, 12, 10)
        )
        self._modificar(t["id"], fecha_inicio=None, fecha_fin=None)


class TestPermisos:
    @pytest.fixture
    def sesion_de_ana(self, empleado, iniciar_sesion, client):
        """El dueño agenda un trabajo; después entra Ana, la empleada."""
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        agendado = _agendado(client)
        otro = _trabajo(client, nombre="Sin agendar", direccion="Calle Sin Fecha 3")
        assert iniciar_sesion("ana", PASSWORD_EMPLEADO).status_code == 200
        return client, agendado, otro

    def test_el_empleado_ve_el_calendario_con_las_fechas(self, sesion_de_ana):
        client, agendado, _ = sesion_de_ana
        r = client.get("/api/trabajos", params={"desde": "2026-12-01", "hasta": "2026-12-31"})
        assert r.status_code == 200
        assert [(t["fecha_inicio"], t["fecha_fin"]) for t in r.json()] == [(INICIO, FIN)]

    def test_el_empleado_inicia_y_termina_trabajos_desde_la_obra(self, sesion_de_ana):
        client, agendado, _ = sesion_de_ana
        assert _accion(client, agendado["id"], "iniciar").json()["estado"] == "en_curso"
        assert _accion(client, agendado["id"], "terminar").json()["estado"] == "terminado"

    def test_el_empleado_no_puede_agendar_reprogramar_ni_cancelar(self, sesion_de_ana):
        client, agendado, sin_agendar = sesion_de_ana
        assert _agendar(client, sin_agendar["id"], "2026-12-20", "2026-12-21").status_code == 403
        r = _reprogramar(client, agendado["id"], "2026-12-15", "2026-12-17")
        assert r.status_code == 403
        assert _accion(client, agendado["id"], "cancelar").status_code == 403
        assert _accion(client, sin_agendar["id"], "cancelar").status_code == 403
        # Nada cambió.
        assert client.get(f"/api/trabajos/{agendado['id']}").json()["fecha_inicio"] == INICIO
        assert client.get(f"/api/trabajos/{sin_agendar['id']}").json()["estado"] == "por_agendar"

    def test_el_empleado_no_ve_el_historial_de_cambios(self, sesion_de_ana):
        client, agendado, _ = sesion_de_ana
        assert client.get(f"/api/trabajos/{agendado['id']}/reprogramaciones").status_code == 403

    def test_el_calendario_tampoco_trae_precios(self, sesion_de_ana):
        client, _, _ = sesion_de_ana
        texto = client.get("/api/trabajos", params={"desde": "2026-12-01"}).text.lower()
        for palabra in ("importe", "total", "forma_pago", "1000"):
            assert palabra not in texto

    def test_sin_sesion_todo_da_401(self, client):
        assert client.get("/api/trabajos", params={"desde": "2026-12-01"}).status_code == 401
        for accion in ("agendar", "reprogramar", "iniciar", "terminar", "cancelar"):
            assert client.post(f"/api/trabajos/1/{accion}", json={}).status_code == 401
        assert client.get("/api/trabajos/1/reprogramaciones").status_code == 401


def _agendar_dias(client, trabajo_id, dias):
    return client.post(f"/api/trabajos/{trabajo_id}/agendar", json={"dias": dias})


class TestDiasSueltos:
    """Un trabajo puede hacerse en días que no son seguidos (13 y 14, y después 26 y 27)."""

    DIAS = ["2026-12-13", "2026-12-14", "2026-12-26", "2026-12-27"]

    def test_se_agenda_en_dias_sueltos_y_el_tramo_va_del_primero_al_ultimo(self, autenticado):
        t = _trabajo(autenticado)
        r = _agendar_dias(autenticado, t["id"], self.DIAS)
        assert r.status_code == 200, r.text
        assert r.json()["fecha_inicio"] == "2026-12-13"
        assert r.json()["fecha_fin"] == "2026-12-27"
        assert r.json()["dias"] == self.DIAS
        assert r.json()["estado"] == "agendado"

    def test_un_trabajo_de_corrido_lista_todos_sus_dias(self, autenticado):
        t = _agendado(autenticado)
        assert t["dias"] == ["2026-12-10", "2026-12-11", "2026-12-12"]

    def test_por_agendar_no_tiene_dias(self, autenticado):
        assert _trabajo(autenticado)["dias"] == []

    def test_otro_trabajo_puede_usar_los_dias_del_hueco(self, autenticado):
        _agendado_en_dias(autenticado, self.DIAS)
        r = _agendar(
            autenticado, _trabajo(autenticado, nombre="Otro")["id"], "2026-12-16", "2026-12-18"
        )
        assert r.status_code == 200, r.text

    def test_no_se_pueden_pisar_los_dias_trabajados(self, autenticado):
        _agendado_en_dias(autenticado, self.DIAS)
        r = _agendar(
            autenticado, _trabajo(autenticado, nombre="Otro")["id"], "2026-12-14", "2026-12-16"
        )
        assert r.status_code == 409 and "se superponen" in r.json()["detail"]

    def test_un_trabajo_de_corrido_no_puede_tapar_el_dia_de_otro_en_el_medio(self, autenticado):
        _agendado(autenticado, "2026-12-15", "2026-12-15")
        r = _agendar_dias(autenticado, _trabajo(autenticado, nombre="Otro")["id"], self.DIAS)
        assert r.status_code == 200, r.text  # el 15 queda en el hueco

    def test_los_dias_no_pueden_pisar_un_trabajo_existente(self, autenticado):
        _agendado(autenticado, "2026-12-14", "2026-12-14")
        r = _agendar_dias(autenticado, _trabajo(autenticado, nombre="Otro")["id"], self.DIAS)
        assert r.status_code == 409 and "se superponen" in r.json()["detail"]

    def test_se_puede_reprogramar_a_otros_dias_sueltos(self, autenticado):
        t = _agendado_en_dias(autenticado, self.DIAS)
        r = autenticado.post(
            f"/api/trabajos/{t['id']}/reprogramar",
            json={"dias": ["2026-12-20", "2026-12-22"], "causa": "clima"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["dias"] == ["2026-12-20", "2026-12-22"]

    def test_reprogramar_a_los_mismos_dias_se_rechaza(self, autenticado):
        t = _agendado_en_dias(autenticado, self.DIAS)
        r = autenticado.post(
            f"/api/trabajos/{t['id']}/reprogramar", json={"dias": self.DIAS, "causa": "clima"}
        )
        assert r.status_code == 409 and "mismas" in r.json()["detail"]

    def test_sin_dias_ni_fechas_da_422(self, autenticado):
        t = _trabajo(autenticado)
        assert _agendar_dias(autenticado, t["id"], []).status_code == 422

    def test_el_empleado_ve_los_dias_sin_precios(self, empleado, iniciar_sesion, client):
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        _agendado_en_dias(client, self.DIAS)
        iniciar_sesion("ana", PASSWORD_EMPLEADO)
        trabajos = client.get("/api/trabajos").json()
        assert trabajos[0]["dias"] == self.DIAS
        assert "total" not in trabajos[0] and "importe" not in str(trabajos[0])


def _agendado_en_dias(client, dias, **trabajo):
    t = _trabajo(client, **trabajo)
    r = _agendar_dias(client, t["id"], dias)
    assert r.status_code == 200, r.text
    return r.json()
