"""Datos de demostración y asistente simulado (todo ficticio, sin red ni claves)."""

import pytest
from sqlalchemy import func, select

from presupuestos_backend import demo, simulado
from presupuestos_backend.database import SessionLocal
from presupuestos_backend.models import Cliente, Presupuesto, Trabajo


@pytest.fixture
def demo_cargado(client, monkeypatch):
    monkeypatch.setenv("AGENTE_SIMULADO", "1")
    with SessionLocal() as db:
        demo.cargar_datos_demo(db)


def _chat(cliente, texto):
    r = cliente.post("/api/agente/chat", json={"mensajes": [{"rol": "usuario", "texto": texto}]})
    assert r.status_code == 200, r.text
    return r.json()


def test_la_carga_deja_datos_coherentes(demo_cargado):
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Cliente)) == len(demo.CLIENTES)
        assert db.scalar(select(func.count()).select_from(Presupuesto)) == len(demo.PRESUPUESTOS)
        trabajos = db.scalars(select(Trabajo)).all()
        assert {t.estado for t in trabajos} >= {"por_agendar", "agendado", "terminado", "cobrado"}
        # Lo cobrado de un trabajo "cobrado" es exactamente su total (seña + saldo, sin redondeos).
        cobrado = next(t for t in trabajos if t.estado == "cobrado")
        assert sum(c.monto for c in cobrado.cobros) == cobrado.presupuesto.total


def test_no_siembra_si_ya_hay_usuarios_ni_sin_demo(client, monkeypatch):
    monkeypatch.delenv("DEMO", raising=False)
    assert demo.cargar_si_corresponde() is False
    monkeypatch.setenv("DEMO", "1")
    assert demo.cargar_si_corresponde() is False  # el dueño de prueba ya existe


def test_los_usuarios_demo_pueden_entrar(demo_cargado, iniciar_sesion):
    assert iniciar_sesion("demo", demo.PASSWORD_DEMO).status_code == 200
    assert iniciar_sesion("empleada", demo.PASSWORD_DEMO).status_code == 200


def test_el_estado_avisa_que_es_simulado(demo_cargado, iniciar_sesion, client):
    iniciar_sesion("demo", demo.PASSWORD_DEMO)
    assert client.get("/api/agente/estado").json() == {"disponible": True, "simulado": True}
    assert client.get("/api/asistente/estado").json()["simulado"] is True


def test_el_duenio_ve_los_cobros_pendientes_con_boton(demo_cargado, iniciar_sesion, client):
    iniciar_sesion("demo", demo.PASSWORD_DEMO)
    r = _chat(client, "¿Cuánto falta cobrar?")
    assert "Falta cobrar $" in r["respuesta"]
    assert {"ruta": "/cobros", "etiqueta": "Ir a Cobros"} in r["acciones"]


def test_la_empleada_nunca_recibe_importes(demo_cargado, iniciar_sesion, client):
    iniciar_sesion("empleada", demo.PASSWORD_DEMO)
    for pregunta in ("cuánto falta cobrar", "mostrame los presupuestos", "trabajos de la semana"):
        r = _chat(client, pregunta)
        assert "$" not in r["respuesta"]
        assert all(a["ruta"] not in ("/cobros", "/presupuestos") for a in r["acciones"])
    assert "no tenés acceso" in _chat(client, "cuánto falta cobrar")["respuesta"]


def test_responde_por_clientes_guia_y_lo_que_no_entiende(demo_cargado, iniciar_sesion, client):
    iniciar_sesion("demo", demo.PASSWORD_DEMO)
    cliente = _chat(client, "¿dónde queda la obra de Marta Prueba?")
    assert "Pasaje Inventado 88" in cliente["respuesta"]
    assert cliente["acciones"][0]["ruta"].startswith("/clientes/")
    assert "Agendar" in _chat(client, "¿cómo agendo un trabajo?")["respuesta"]
    assert "simulación" in _chat(client, "blablabla")["respuesta"]


def test_completar_con_ia_simulado_arma_un_borrador(demo_cargado, iniciar_sesion, client):
    iniciar_sesion("demo", demo.PASSWORD_DEMO)
    r = client.post(
        "/api/asistente/presupuesto",
        json={"mensaje": "pintar living 30 m2 45 lucas, cambiar 3 enchufes cocina"},
    )
    assert r.status_code == 200, r.text
    primero, segundo = r.json()["items"]
    assert primero["descripcion"] == "Pintura de living"
    assert (primero["cantidad"], primero["unidad"], primero["importe"]) == (30, "m2", 45000)
    assert segundo["descripcion"] == "Reemplazo de 3 enchufes cocina"
    assert (segundo["cantidad"], segundo["unidad"], segundo["importe"]) == (1, "gl", None)


def test_desactivado_por_defecto(monkeypatch):
    monkeypatch.delenv("AGENTE_SIMULADO", raising=False)
    assert simulado.disponible() is False
