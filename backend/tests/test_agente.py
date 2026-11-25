"""Agente de ayuda: herramientas según el rol, datos mínimos hacia Gemini y el endpoint del chat."""

import pytest
from conftest import DUENO, PASSWORD_DUENO, PASSWORD_EMPLEADO, presupuesto_valido

from presupuestos_backend import agente, llm, webhook
from presupuestos_backend.database import SessionLocal
from presupuestos_backend.models import Usuario

TELEFONO = "11 5555 0000"
NOTA_PRIVADA = "El portero se llama Rodolfo y tiene un perro"

HERRAMIENTAS_DUENO = {
    "como_se_hace",
    "abrir_pantalla",
    "buscar_clientes",
    "ver_cliente",
    "ver_trabajos",
    "ver_presupuestos",
    "ver_cobros_pendientes",
}
HERRAMIENTAS_EMPLEADO = {
    "como_se_hace",
    "abrir_pantalla",
    "buscar_clientes",
    "ver_cliente",
    "ver_trabajos",
}


@pytest.fixture
def datos(autenticado):
    """Un cliente con teléfono y notas, su obra y un trabajo agendado (con presupuesto)."""
    cliente = autenticado.post(
        "/api/clientes",
        json={
            "nombre": "Consorcio Sol",
            "tipo": "consorcio",
            "telefono": TELEFONO,
            "notas": NOTA_PRIVADA,
        },
    ).json()
    obra = autenticado.post(
        f"/api/clientes/{cliente['id']}/obras",
        json={"direccion": "Corrientes 1200", "referencia": "Hall", "notas": NOTA_PRIVADA},
    ).json()
    p = autenticado.post(
        "/api/presupuestos", json=presupuesto_valido(cliente_id=cliente["id"], obra_id=obra["id"])
    ).json()
    assert (
        autenticado.put(
            f"/api/presupuestos/{p['id']}/estado", json={"estado": "aprobado"}
        ).status_code
        == 200
    )
    trabajo = autenticado.post(f"/api/presupuestos/{p['id']}/trabajo").json()
    assert (
        autenticado.post(
            f"/api/trabajos/{trabajo['id']}/agendar", json={"dias": ["2026-12-10", "2026-12-11"]}
        ).status_code
        == 200
    )
    return {"cliente": cliente, "obra": obra, "trabajo": trabajo}


def _herramientas(usuario_nombre):
    db = SessionLocal()
    usuario = db.query(Usuario).filter_by(usuario=usuario_nombre).one()
    acciones: list[dict] = []
    return db, usuario, agente.construir_herramientas(db, usuario, acciones), acciones


@pytest.fixture
def del_dueno(datos):
    db, usuario, herramientas, acciones = _herramientas(DUENO)
    yield usuario, herramientas, acciones
    db.close()


@pytest.fixture
def de_la_empleada(datos, autenticado):
    autenticado.post(
        "/api/usuarios",
        json={"nombre": "Ana", "usuario": "ana", "password": PASSWORD_EMPLEADO, "rol": "empleado"},
    )
    db, usuario, herramientas, acciones = _herramientas("ana")
    yield usuario, herramientas, acciones
    db.close()


class TestHerramientasPorRol:
    def test_el_dueno_tiene_todas(self, del_dueno):
        assert set(del_dueno[1]) == HERRAMIENTAS_DUENO

    def test_la_empleada_no_tiene_presupuestos_ni_cobros(self, de_la_empleada):
        assert set(de_la_empleada[1]) == HERRAMIENTAS_EMPLEADO

    def test_la_guia_de_la_empleada_no_incluye_plata(self, de_la_empleada):
        usuario, herramientas, _ = de_la_empleada
        temas = agente.temas_disponibles(usuario)
        assert "cobros" not in temas and "presupuesto" not in temas and "agendar" not in temas
        assert "iniciar_y_terminar" in temas and "calendario" in temas
        assert "No tengo una guía" in herramientas["como_se_hace"]("cobros")

    def test_la_empleada_no_puede_abrir_pantallas_de_plata(self, de_la_empleada):
        _, herramientas, acciones = de_la_empleada
        assert "no tiene acceso" in herramientas["abrir_pantalla"]("cobros")
        assert "no tiene acceso" in herramientas["abrir_pantalla"]("presupuesto", 1)
        assert "no tiene acceso" in herramientas["abrir_pantalla"]("usuarios")
        assert acciones == []

    def test_abrir_pantalla_arma_el_boton(self, del_dueno, datos):
        _, herramientas, acciones = del_dueno
        herramientas["abrir_pantalla"]("trabajo", datos["trabajo"]["id"])
        herramientas["abrir_pantalla"]("nuevo_presupuesto")
        assert [a["ruta"] for a in acciones] == [
            f"/trabajos/{datos['trabajo']['id']}",
            "/presupuestos/nuevo",
        ]

    def test_una_pantalla_inexistente_no_rompe(self, del_dueno):
        assert "No conozco" in del_dueno[1]["abrir_pantalla"]("la-luna")


class TestDatosMinimos:
    """Lo que las herramientas le devuelven a Gemini nunca incluye teléfono, notas ni precios (empleada)."""

    def _todo(self, herramientas, datos):
        return str(
            [
                herramientas["buscar_clientes"](""),
                herramientas["ver_cliente"](datos["cliente"]["id"]),
                herramientas["ver_trabajos"](),
            ]
        )

    @pytest.mark.parametrize("quien", ["del_dueno", "de_la_empleada"])
    def test_no_salen_telefono_ni_notas(self, quien, request, datos):
        _, herramientas, _ = request.getfixturevalue(quien)
        texto = self._todo(herramientas, datos)
        assert TELEFONO not in texto and NOTA_PRIVADA not in texto and "Rodolfo" not in texto
        assert "Consorcio Sol" in texto and "Corrientes 1200" in texto

    def test_los_trabajos_salen_sin_precios(self, de_la_empleada):
        trabajo = de_la_empleada[1]["ver_trabajos"]()[0]
        assert set(trabajo) == {"id", "cliente", "direccion", "estado", "dias", "tareas"}
        assert trabajo["dias"] == ["2026-12-10", "2026-12-11"]

    def test_el_dueno_ve_los_importes_de_presupuestos_y_cobros(self, del_dueno):
        _, herramientas, _ = del_dueno
        assert herramientas["ver_presupuestos"]()[0]["total"] > 0
        assert herramientas["ver_cobros_pendientes"]()["total_pendiente"] > 0

    def test_las_fechas_mal_escritas_devuelven_un_error_claro(self, del_dueno):
        assert "AAAA-MM-DD" in del_dueno[1]["ver_trabajos"](desde="ayer")["error"]

    def test_ver_trabajos_filtra_por_rango_y_estado(self, del_dueno):
        herramientas = del_dueno[1]
        assert len(herramientas["ver_trabajos"](desde="2026-12-01", hasta="2026-12-31")) == 1
        assert herramientas["ver_trabajos"](desde="2027-01-01") == []
        assert herramientas["ver_trabajos"](estado="agendado")[0]["estado"] == "agendado"
        assert herramientas["ver_trabajos"](estado="cobrado") == []


class TestPromptDeSistema:
    def test_dice_quien_habla_y_que_rol_tiene(self, del_dueno, de_la_empleada):
        texto_dueno = agente.instrucciones_de(del_dueno[0], del_dueno[1])
        texto_empleada = agente.instrucciones_de(de_la_empleada[0], de_la_empleada[1])
        assert "el dueño" in texto_dueno and "un empleado" in texto_empleada
        assert "Ana" in texto_empleada
        assert "no ve precios" in texto_empleada and "no ve precios" not in texto_dueno


class TestEndpointDeChat:
    @pytest.fixture
    def gemini_falso(self, monkeypatch):
        """Reemplaza a Gemini: guarda lo que recibe y, si se le pide, llama herramientas."""
        visto = {}

        def falso(instrucciones, mensajes, herramientas, max_llamadas=6):
            visto.update(instrucciones=instrucciones, mensajes=mensajes, herramientas=herramientas)
            for h in herramientas:
                if h.__name__ == "abrir_pantalla":
                    h("clientes")
            return "Listo, ahí tenés el botón."

        monkeypatch.setattr(llm, "conversar", falso)
        monkeypatch.setattr(llm, "disponible", lambda: True)
        return visto

    def _chat(self, client, texto="Hola", **extra):
        return client.post(
            "/api/agente/chat", json={"mensajes": [{"rol": "usuario", "texto": texto}], **extra}
        )

    def test_sin_sesion_da_401(self, client):
        assert self._chat(client).status_code == 401
        assert client.get("/api/agente/estado").status_code == 401

    def test_responde_y_devuelve_los_botones(self, autenticado, gemini_falso):
        r = self._chat(autenticado, "¿cómo agendo un trabajo?")
        assert r.status_code == 200, r.text
        assert r.json() == {
            "respuesta": "Listo, ahí tenés el botón.",
            "acciones": [{"ruta": "/clientes", "etiqueta": "Ir a Clientes"}],
            "conversacion_id": None,
        }
        assert gemini_falso["mensajes"] == [("usuario", "¿cómo agendo un trabajo?")]

    def test_a_gemini_solo_le_llegan_las_herramientas_del_rol(
        self, autenticado, empleado, iniciar_sesion, gemini_falso
    ):
        iniciar_sesion(DUENO, PASSWORD_DUENO)  # el fixture `empleado` deja la sesión cerrada
        self._chat(autenticado)
        assert {h.__name__ for h in gemini_falso["herramientas"]} == HERRAMIENTAS_DUENO
        iniciar_sesion("ana", PASSWORD_EMPLEADO)
        self._chat(autenticado)
        assert {h.__name__ for h in gemini_falso["herramientas"]} == HERRAMIENTAS_EMPLEADO

    def test_estado_dice_si_hay_gemini(self, autenticado, monkeypatch):
        monkeypatch.setattr(llm, "disponible", lambda: False)
        assert autenticado.get("/api/agente/estado").json() == {"disponible": False, "simulado": False}

    def test_sin_gemini_da_503_con_un_mensaje(self, autenticado):
        r = self._chat(autenticado)  # en los tests no hay GEMINI_API_KEY
        assert r.status_code == 503 and "no está configurado" in r.json()["detail"]

    @pytest.mark.parametrize(
        "cuerpo",
        [
            {"mensajes": []},
            {"mensajes": [{"rol": "usuario", "texto": ""}]},
            {"mensajes": [{"rol": "usuario", "texto": "x" * 1501}]},
            {"mensajes": [{"rol": "robot", "texto": "hola"}]},
            {"mensajes": [{"rol": "usuario", "texto": "hola"}, {"rol": "agente", "texto": "chau"}]},
        ],
    )
    def test_pedidos_invalidos_dan_422(self, autenticado, gemini_falso, cuerpo):
        assert autenticado.post("/api/agente/chat", json=cuerpo).status_code == 422

    def test_solo_se_mandan_los_ultimos_mensajes(self, autenticado, gemini_falso):
        historial = []
        for i in range(15):
            historial += [
                {"rol": "usuario", "texto": f"pregunta {i}"},
                {"rol": "agente", "texto": f"respuesta {i}"},
            ]
        historial.append({"rol": "usuario", "texto": "la última"})
        assert autenticado.post("/api/agente/chat", json={"mensajes": historial}).status_code == 200
        assert len(gemini_falso["mensajes"]) == 20 and gemini_falso["mensajes"][-1] == (
            "usuario",
            "la última",
        )

    def test_limite_de_mensajes_seguidos(self, autenticado, gemini_falso):
        for _ in range(20):
            assert self._chat(autenticado).status_code == 200
        r = self._chat(autenticado)
        assert r.status_code == 429 and "Esperá" in r.json()["detail"]

    def test_el_contenido_de_la_conversacion_no_se_registra_en_el_log(
        self, autenticado, gemini_falso, caplog
    ):
        caplog.set_level("INFO")
        self._chat(autenticado, "mensaje-secreto-con-datos-de-un-cliente")
        assert "mensaje-secreto" not in caplog.text and "Agente: usuario" in caplog.text


class TestTiempoMaximo:
    def test_si_gemini_tarda_de_mas_la_persona_recibe_un_aviso(self, monkeypatch):
        import time

        monkeypatch.setattr(llm, "GEMINI_API_KEY", "clave-falsa")
        monkeypatch.setattr(llm, "TIEMPO_CHAT_S", 0.2)
        monkeypatch.setattr(llm, "_con_modelos", lambda cliente, hacer: time.sleep(2))
        inicio = time.monotonic()
        with pytest.raises(llm.LLMError, match="no está disponible"):
            llm.conversar("instrucciones", [("usuario", "hola")], [])
        assert time.monotonic() - inicio < 1.5


URL_SECRETA = "https://prod-00.example.logic.azure.com/workflows/abc?sig=CLAVE-SECRETA-123"


class _Respuesta:
    def __init__(self, codigo=200, cuerpo=None, texto_crudo=None):
        self.status_code = codigo
        self._cuerpo = cuerpo
        self._texto = texto_crudo

    def json(self):
        if self._texto is not None:
            raise ValueError("no es JSON")
        return self._cuerpo


@pytest.fixture
def webhook_configurado(monkeypatch):
    monkeypatch.setattr(webhook, "URL", URL_SECRETA)


class TestClienteDelWebhook:
    @pytest.fixture(autouse=True)
    def _url(self, webhook_configurado):
        pass

    def _post(self, monkeypatch, *respuestas):
        llamadas = []
        pendientes = list(respuestas)

        def falso(url, json, timeout):
            llamadas.append({"url": url, "json": json, "timeout": timeout})
            r = pendientes.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

        monkeypatch.setattr(webhook.httpx, "post", falso)
        return llamadas

    def test_manda_el_mensaje_y_devuelve_el_texto_y_el_id(self, monkeypatch):
        llamadas = self._post(
            monkeypatch, _Respuesta(cuerpo={"lastResponse": " Hola! ", "conversationId": "c-1"})
        )
        assert webhook.preguntar("hola") == ("Hola!", "c-1")
        assert llamadas[0]["json"] == {"message": "hola"}

    def test_reenvia_el_id_de_la_conversacion(self, monkeypatch):
        llamadas = self._post(monkeypatch, _Respuesta(cuerpo={"lastResponse": "ok"}))
        assert webhook.preguntar("hola", "c-1") == ("ok", "c-1")
        assert llamadas[0]["json"] == {"message": "hola", "conversationId": "c-1"}

    def test_un_503_se_reintenta_una_vez(self, monkeypatch):
        llamadas = self._post(
            monkeypatch, _Respuesta(503), _Respuesta(cuerpo={"lastResponse": "ok"})
        )
        assert webhook.preguntar("hola")[0] == "ok" and len(llamadas) == 2

    def test_una_conexion_rechazada_se_reintenta_una_vez(self, monkeypatch):
        llamadas = self._post(
            monkeypatch, webhook.httpx.ConnectError("x"), _Respuesta(cuerpo={"lastResponse": "ok"})
        )
        assert webhook.preguntar("hola")[0] == "ok" and len(llamadas) == 2

    @pytest.mark.parametrize(
        "respuestas",
        [
            [_Respuesta(503), _Respuesta(503)],
            [_Respuesta(500)],
            [_Respuesta(401)],
            [_Respuesta(texto_crudo="<html>")],
            [_Respuesta(cuerpo=["no", "es", "objeto"])],
            [_Respuesta(cuerpo={"conversationId": "c-1"})],
            [_Respuesta(cuerpo={"lastResponse": "   "})],
            [webhook.httpx.ReadTimeout("x")],
            [webhook.httpx.ReadError("x")],  # conexión cortada: no se reintenta
        ],
    )
    def test_los_fallos_dan_un_error_generico_sin_la_url(self, monkeypatch, respuestas, caplog):
        self._post(monkeypatch, *respuestas)
        with pytest.raises(llm.LLMError) as e:
            webhook.preguntar("hola")
        assert "CLAVE-SECRETA" not in str(e.value) and "CLAVE-SECRETA" not in caplog.text

    def test_si_se_corta_la_conexion_no_se_reintenta(self, monkeypatch):
        llamadas = self._post(
            monkeypatch, webhook.httpx.ReadError("x"), _Respuesta(cuerpo={"lastResponse": "ok"})
        )
        with pytest.raises(llm.LLMError):
            webhook.preguntar("hola")
        assert len(llamadas) == 1  # el pedido pudo ejecutarse: reintentar duplicaría el gasto


class TestAgenteConWebhook:
    @pytest.fixture
    def agente_falso(self, monkeypatch, webhook_configurado):
        visto = {}

        def falso(mensaje, conversacion_id=None):
            visto.update(mensaje=mensaje, conversacion_id=conversacion_id)
            return visto.get("respuesta", "Te explico."), "conv-9"

        monkeypatch.setattr(webhook, "preguntar", falso)
        monkeypatch.setattr(llm, "conversar", lambda *a, **k: pytest.fail("no debe usar Gemini"))
        return visto

    def _chat(self, client, texto, conversacion_id=None):
        cuerpo = {
            "mensajes": [{"rol": "usuario", "texto": texto}],
            "conversacion_id": conversacion_id,
        }
        return client.post("/api/agente/chat", json=cuerpo)

    def test_estado_alcanza_con_el_webhook(self, autenticado, webhook_configurado, monkeypatch):
        monkeypatch.setattr(llm, "disponible", lambda: False)
        assert autenticado.get("/api/agente/estado").json() == {"disponible": True, "simulado": False}

    def test_usa_el_webhook_y_devuelve_el_id_de_la_conversacion(
        self, autenticado, datos, agente_falso
    ):
        r = self._chat(autenticado, "¿qué hay esta semana?", "conv-1")
        assert r.status_code == 200, r.text
        assert r.json() == {"respuesta": "Te explico.", "acciones": [], "conversacion_id": "conv-9"}
        assert agente_falso["conversacion_id"] == "conv-1"
        assert "¿qué hay esta semana?" in agente_falso["mensaje"]

    def test_el_mensaje_lleva_la_guia_y_los_datos_sin_telefonos_ni_notas(
        self, autenticado, datos, agente_falso
    ):
        self._chat(autenticado, "¿dónde queda el cliente Consorcio Sol?")
        mensaje = agente_falso["mensaje"]
        assert "GUÍA DE USO DE LA APP" in mensaje and "Cómo hacer un presupuesto" in mensaje
        assert (
            "Consorcio Sol" in mensaje and "Corrientes 1200" in mensaje and "2026-12-10" in mensaje
        )
        assert TELEFONO not in mensaje and NOTA_PRIVADA not in mensaje and "Rodolfo" not in mensaje
        assert "[[IR:" in mensaje  # le explica cómo pedir un botón

    def test_el_mensaje_trae_las_fechas_de_referencia_ya_resueltas(
        self, autenticado, datos, agente_falso
    ):
        import datetime as dt

        self._chat(autenticado, "¿qué hay esta semana?")
        hoy = dt.date.today()
        lunes = hoy - dt.timedelta(days=hoy.weekday())
        assert "FECHAS DE REFERENCIA" in agente_falso["mensaje"]
        assert (
            f"de lunes {lunes.isoformat()} a domingo {(lunes + dt.timedelta(days=6)).isoformat()}"
            in agente_falso["mensaje"]
        )

    def test_los_cobros_solo_van_si_se_pregunta_por_plata(self, autenticado, datos, agente_falso):
        self._chat(autenticado, "¿qué hay hoy?")
        assert "COBROS PENDIENTES" not in agente_falso["mensaje"]
        self._chat(autenticado, "¿cuánto me deben?")
        assert "COBROS PENDIENTES" in agente_falso["mensaje"] and "falta" in agente_falso["mensaje"]

    def test_la_empleada_nunca_recibe_plata_ni_guia_de_plata(
        self, autenticado, datos, empleado, iniciar_sesion, agente_falso
    ):
        iniciar_sesion("ana", PASSWORD_EMPLEADO)
        self._chat(autenticado, "¿cuánto me deben en presupuestos y cobros?")
        mensaje = agente_falso["mensaje"]
        assert "COBROS PENDIENTES" not in mensaje and "PRESUPUESTOS recientes" not in mensaje
        assert "Cobros (solo dueño)" not in mensaje and "Cómo hacer un presupuesto" not in mensaje
        assert "total" not in mensaje.split("DATOS ACTUALES")[1]

    def test_las_etiquetas_se_vuelven_botones_y_se_quitan_del_texto(
        self, autenticado, datos, agente_falso
    ):
        agente_falso["respuesta"] = "Mirá la semana.\n[[IR:semana]]\n[[IR:trabajo:7]]"
        r = self._chat(autenticado, "¿qué hay?").json()
        assert r["respuesta"] == "Mirá la semana."
        assert [a["ruta"] for a in r["acciones"]] == ["/trabajos?vista=semana", "/trabajos/7"]

    def test_la_empleada_no_obtiene_botones_de_pantallas_prohibidas(
        self, autenticado, datos, empleado, iniciar_sesion, agente_falso
    ):
        iniciar_sesion("ana", PASSWORD_EMPLEADO)
        agente_falso["respuesta"] = (
            "Andá a cobros [[IR:cobros]] o a usuarios [[IR:usuarios]] [[IR:inventada]]"
        )
        r = self._chat(autenticado, "hola").json()
        assert r["acciones"] == [] and "[[" not in r["respuesta"]

    def test_si_el_webhook_falla_la_persona_recibe_un_aviso(
        self, autenticado, webhook_configurado, monkeypatch
    ):
        def falla(mensaje, conversacion_id=None):
            raise llm.LLMError(llm.MENSAJE_NO_DISPONIBLE)

        monkeypatch.setattr(webhook, "preguntar", falla)
        r = self._chat(autenticado, "hola")
        assert r.status_code == 503 and "no está disponible" in r.json()["detail"]


JSON_VALIDO = (
    '{"vigencia_dias": null, "plazo_obra": "3 días hábiles", "forma_pago": null,'
    ' "materiales_a_cargo": "Obras Demo", "observaciones": null,'
    ' "items": [{"descripcion": "Pintura de living", "unidad": "m2", "cantidad": 40, "importe": null}]}'
)


class TestCompletarConWebhook:
    """El "Completar con IA" de presupuestos con el agente de Copilot Studio."""

    @pytest.fixture
    def respuestas(self, monkeypatch, webhook_configurado):
        """Cola de respuestas del agente; guarda los pedidos que recibió."""
        visto = {"pedidos": [], "textos": []}

        def falso(mensaje, conversacion_id=None):
            visto["pedidos"].append((mensaje, conversacion_id))
            return visto["textos"].pop(0), "conv-1"

        monkeypatch.setattr(webhook, "preguntar", falso)
        monkeypatch.setattr(llm, "rellenar", lambda *a, **k: pytest.fail("no debe usar Gemini"))
        return visto

    def _completar(self, client, texto="pintar el living 40 m2"):
        return client.post("/api/asistente/presupuesto", json={"mensaje": texto})

    def test_estado_alcanza_con_el_webhook(self, autenticado, webhook_configurado, monkeypatch):
        monkeypatch.setattr(llm, "disponible", lambda: False)
        assert autenticado.get("/api/asistente/estado").json() == {"disponible": True, "simulado": False}

    def test_devuelve_el_borrador_y_agrega_las_observaciones_estandar(
        self, autenticado, respuestas
    ):
        respuestas["textos"] = [f"Acá va:\n```json\n{JSON_VALIDO}\n```\nCualquier cosa avisame."]
        r = self._completar(autenticado)
        assert r.status_code == 200, r.text
        borrador = r.json()
        assert borrador["plazo_obra"] == "3 días hábiles"
        assert borrador["items"][0]["descripcion"] == "Pintura de living"
        assert borrador["items"][0]["importe"] is None  # nunca se inventa un precio

    def test_el_borrador_no_trae_cliente_ni_direccion(self, autenticado, respuestas):
        respuestas["textos"] = [
            JSON_VALIDO.replace(
                '{"vigencia_dias"',
                '{"cliente_obra": "Marta", "direccion": "Maipú 1", "vigencia_dias"',
            )
        ]
        borrador = self._completar(autenticado, "marta gomez, maipu 1234. pintar el living").json()
        assert "cliente_obra" not in borrador and "direccion" not in borrador

    def test_le_pide_el_esquema_sin_cliente_y_le_manda_el_texto(self, autenticado, respuestas):
        respuestas["textos"] = [JSON_VALIDO]
        self._completar(autenticado, "pintar el living 40 m2")
        pedido = respuestas["pedidos"][0][0]
        assert "pintar el living 40 m2" in pedido and "JSON" in pedido
        assert "No devuelvas el nombre del cliente ni la dirección" in pedido
        assert '"cliente_obra"' not in pedido and '"direccion"' not in pedido

    def test_si_la_primera_respuesta_no_sirve_pide_otra_vez_en_la_misma_conversacion(
        self, autenticado, respuestas
    ):
        respuestas["textos"] = ["Claro, te cuento que...", JSON_VALIDO]
        assert self._completar(autenticado).status_code == 200
        assert len(respuestas["pedidos"]) == 2
        assert respuestas["pedidos"][1][1] == "conv-1" and "JSON" in respuestas["pedidos"][1][0]

    def test_si_tampoco_sirve_la_segunda_da_503(self, autenticado, respuestas):
        respuestas["textos"] = ["no sé", '{"items": "esto no es una lista"}']
        r = self._completar(autenticado)
        assert r.status_code == 503 and "no está disponible" in r.json()["detail"]

    def test_la_empleada_no_puede_usarlo(self, autenticado, empleado, iniciar_sesion, respuestas):
        iniciar_sesion("ana", PASSWORD_EMPLEADO)
        assert self._completar(autenticado).status_code == 403
        assert respuestas["pedidos"] == []
