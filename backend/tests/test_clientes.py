import pytest
from conftest import DUENO, PASSWORD_DUENO, PASSWORD_EMPLEADO


def _cliente(**cambios):
    datos = {
        "nombre": "Juan Pérez",
        "tipo": "casa",
        "telefono": "11 5555 0000",
        "notas": "Prefiere que lo llamen de tarde.",
    }
    datos.update(cambios)
    return datos


def _obra(**cambios):
    datos = {
        "direccion": "Av. Siempre Viva 123",
        "referencia": "Depto 3B",
        "notas": "Timbre roto: llamar por teléfono.",
    }
    datos.update(cambios)
    return datos


def _crear_cliente(client, **cambios):
    r = client.post("/api/clientes", json=_cliente(**cambios))
    assert r.status_code == 201, r.text
    return r.json()


def _crear_obra(client, cliente_id, **cambios):
    r = client.post(f"/api/clientes/{cliente_id}/obras", json=_obra(**cambios))
    assert r.status_code == 201, r.text
    return r.json()


class TestClientes:
    def test_crear_y_obtener(self, autenticado):
        creado = _crear_cliente(autenticado)
        assert creado["obras"] == []
        leido = autenticado.get(f"/api/clientes/{creado['id']}").json()
        assert (leido["nombre"], leido["tipo"], leido["telefono"]) == (
            "Juan Pérez",
            "casa",
            "11 5555 0000",
        )

    def test_saca_los_espacios_de_mas(self, autenticado):
        creado = _crear_cliente(autenticado, nombre="  Ana  Gómez ", telefono="  11 1  ")
        assert creado["nombre"] == "Ana  Gómez"  # solo los de los bordes
        assert creado["telefono"] == "11 1"

    def test_telefono_y_notas_son_opcionales(self, autenticado):
        r = autenticado.post("/api/clientes", json={"nombre": "Consorcio Sol", "tipo": "consorcio"})
        assert r.status_code == 201
        assert (r.json()["telefono"], r.json()["notas"]) == ("", "")

    @pytest.mark.parametrize(
        ("campo", "valor", "texto"),
        [
            ("nombre", "   ", "Nombre"),
            ("nombre", "x" * 151, "Nombre"),
            ("tipo", "oficina", "Tipo de cliente"),
            ("telefono", "1" * 41, "Teléfono"),
            ("notas", "x" * 1001, "Notas"),
        ],
    )
    def test_datos_invalidos_dan_422_con_mensaje_legible(self, autenticado, campo, valor, texto):
        r = autenticado.post("/api/clientes", json=_cliente(**{campo: valor}))
        assert r.status_code == 422
        assert texto in r.json()["detail"]

    def test_listar_ordena_por_nombre_sin_distinguir_mayusculas(self, autenticado):
        for nombre in ("zulema", "Ana", "beto", "Carla"):
            _crear_cliente(autenticado, nombre=nombre)
        nombres = [c["nombre"] for c in autenticado.get("/api/clientes").json()]
        assert nombres == ["Ana", "beto", "Carla", "zulema"]

    def test_listar_cuenta_las_obras_de_cada_cliente(self, autenticado):
        con_dos = _crear_cliente(autenticado, nombre="Con dos")
        _crear_cliente(autenticado, nombre="Sin obras")
        _crear_obra(autenticado, con_dos["id"], direccion="Calle 1")
        _crear_obra(autenticado, con_dos["id"], direccion="Calle 2")
        cantidades = {
            c["nombre"]: c["cantidad_obras"] for c in autenticado.get("/api/clientes").json()
        }
        assert cantidades == {"Con dos": 2, "Sin obras": 0}

    def test_actualizar(self, autenticado):
        creado = _crear_cliente(autenticado)
        r = autenticado.put(
            f"/api/clientes/{creado['id']}",
            json=_cliente(nombre="Juan P. Pérez", tipo="consorcio", telefono=""),
        )
        assert r.status_code == 200
        assert (r.json()["nombre"], r.json()["tipo"], r.json()["telefono"]) == (
            "Juan P. Pérez",
            "consorcio",
            "",
        )

    def test_inexistente_da_404_en_castellano(self, autenticado):
        for r in (
            autenticado.get("/api/clientes/9999"),
            autenticado.put("/api/clientes/9999", json=_cliente()),
            autenticado.delete("/api/clientes/9999"),
        ):
            assert r.status_code == 404
            assert "No se encontró" in r.json()["detail"]

    def test_borrar_un_cliente_sin_obras(self, autenticado):
        creado = _crear_cliente(autenticado)
        assert autenticado.delete(f"/api/clientes/{creado['id']}").status_code == 204
        assert autenticado.get(f"/api/clientes/{creado['id']}").status_code == 404

    def test_no_se_puede_borrar_un_cliente_con_obras(self, autenticado):
        creado = _crear_cliente(autenticado)
        obra = _crear_obra(autenticado, creado["id"])
        r = autenticado.delete(f"/api/clientes/{creado['id']}")
        assert r.status_code == 409
        assert "obras" in r.json()["detail"]
        assert autenticado.get(f"/api/clientes/{creado['id']}").status_code == 200  # sigue ahí

        autenticado.delete(f"/api/obras/{obra['id']}")
        assert autenticado.delete(f"/api/clientes/{creado['id']}").status_code == 204


class TestBusqueda:
    @pytest.fixture
    def datos(self, autenticado):
        juan = _crear_cliente(autenticado, nombre="Juan Pérez", telefono="11 4444 1234")
        _crear_obra(autenticado, juan["id"], direccion="Av. Libertador 500", referencia="Piso 2")
        consorcio = _crear_cliente(
            autenticado, nombre="Consorcio Los Álamos", tipo="consorcio", telefono=""
        )
        _crear_obra(autenticado, consorcio["id"], direccion="Corrientes 1200", referencia="Hall")
        _crear_obra(autenticado, consorcio["id"], direccion="Corrientes 1200", referencia="Fondo")
        return autenticado

    def _buscar(self, client, texto):
        return [c["nombre"] for c in client.get("/api/clientes", params={"buscar": texto}).json()]

    def test_por_nombre_sin_distinguir_mayusculas(self, datos):
        assert self._buscar(datos, "juan") == ["Juan Pérez"]
        assert self._buscar(datos, "CONSORCIO") == ["Consorcio Los Álamos"]

    def test_por_telefono(self, datos):
        assert self._buscar(datos, "4444") == ["Juan Pérez"]

    def test_por_direccion_de_una_obra(self, datos):
        assert self._buscar(datos, "libertador") == ["Juan Pérez"]

    def test_por_referencia_de_una_obra(self, datos):
        assert self._buscar(datos, "hall") == ["Consorcio Los Álamos"]

    def test_la_cantidad_de_obras_no_se_achica_por_la_busqueda(self, datos):
        # Se encuentra por una sola obra ("Hall"), pero el consorcio tiene dos.
        encontrados = datos.get("/api/clientes", params={"buscar": "hall"}).json()
        assert encontrados[0]["cantidad_obras"] == 2

    def test_un_cliente_con_varias_obras_que_coinciden_aparece_una_sola_vez(self, datos):
        assert self._buscar(datos, "corrientes") == ["Consorcio Los Álamos"]

    def test_sin_resultados(self, datos):
        assert self._buscar(datos, "no-existe-nadie") == []

    def test_vacio_o_solo_espacios_lista_todo(self, datos):
        assert len(self._buscar(datos, "   ")) == 2

    @pytest.mark.parametrize("comodin", ["%", "_", "\\"])
    def test_los_comodines_se_buscan_como_texto_y_no_listan_todo(self, datos, comodin):
        assert self._buscar(datos, comodin) == []


class TestObras:
    def test_crear_aparece_en_el_cliente(self, autenticado):
        cliente = _crear_cliente(autenticado)
        obra = _crear_obra(autenticado, cliente["id"])
        assert obra["cliente_id"] == cliente["id"]
        leido = autenticado.get(f"/api/clientes/{cliente['id']}").json()
        assert [o["direccion"] for o in leido["obras"]] == ["Av. Siempre Viva 123"]

    def test_referencia_y_notas_son_opcionales(self, autenticado):
        cliente = _crear_cliente(autenticado)
        r = autenticado.post(f"/api/clientes/{cliente['id']}/obras", json={"direccion": "Calle 1"})
        assert r.status_code == 201
        assert (r.json()["referencia"], r.json()["notas"]) == ("", "")

    def test_las_obras_salen_en_el_orden_en_que_se_cargaron(self, autenticado):
        cliente = _crear_cliente(autenticado)
        for direccion in ("Calle C", "Calle A", "Calle B"):
            _crear_obra(autenticado, cliente["id"], direccion=direccion)
        leido = autenticado.get(f"/api/clientes/{cliente['id']}").json()
        assert [o["direccion"] for o in leido["obras"]] == ["Calle C", "Calle A", "Calle B"]

    @pytest.mark.parametrize(
        ("campo", "valor", "texto"),
        [
            ("direccion", "  ", "Dirección"),
            ("direccion", "x" * 301, "Dirección"),
            ("referencia", "x" * 101, "Referencia"),
            ("notas", "x" * 1001, "Notas"),
        ],
    )
    def test_datos_invalidos_dan_422_con_mensaje_legible(self, autenticado, campo, valor, texto):
        cliente = _crear_cliente(autenticado)
        r = autenticado.post(f"/api/clientes/{cliente['id']}/obras", json=_obra(**{campo: valor}))
        assert r.status_code == 422
        assert texto in r.json()["detail"]

    def test_para_un_cliente_inexistente_da_404(self, autenticado):
        r = autenticado.post("/api/clientes/9999/obras", json=_obra())
        assert r.status_code == 404
        assert "cliente" in r.json()["detail"]

    def test_actualizar_y_no_cambia_de_cliente(self, autenticado):
        cliente = _crear_cliente(autenticado)
        obra = _crear_obra(autenticado, cliente["id"])
        r = autenticado.put(f"/api/obras/{obra['id']}", json=_obra(direccion="Otra calle 99"))
        assert r.status_code == 200
        assert r.json()["direccion"] == "Otra calle 99"
        assert r.json()["cliente_id"] == cliente["id"]

    def test_borrar(self, autenticado):
        cliente = _crear_cliente(autenticado)
        obra = _crear_obra(autenticado, cliente["id"])
        assert autenticado.delete(f"/api/obras/{obra['id']}").status_code == 204
        assert autenticado.get(f"/api/clientes/{cliente['id']}").json()["obras"] == []

    def test_obra_inexistente_da_404(self, autenticado):
        assert autenticado.put("/api/obras/9999", json=_obra()).status_code == 404
        assert autenticado.delete("/api/obras/9999").status_code == 404


class TestPermisos:
    @pytest.fixture
    def sesion_de_ana(self, empleado, iniciar_sesion, client):
        """El dueño carga un cliente con una obra; después entra Ana, la empleada."""
        iniciar_sesion(DUENO, PASSWORD_DUENO)
        cliente = _crear_cliente(client)
        obra = _crear_obra(client, cliente["id"])
        assert iniciar_sesion("ana", PASSWORD_EMPLEADO).status_code == 200
        return client, cliente, obra

    def test_el_empleado_ve_clientes_telefonos_y_direcciones(self, sesion_de_ana):
        client, cliente, _ = sesion_de_ana
        lista = client.get("/api/clientes")
        assert lista.status_code == 200
        assert lista.json()[0]["telefono"] == "11 5555 0000"
        detalle = client.get(f"/api/clientes/{cliente['id']}").json()
        assert detalle["obras"][0]["direccion"] == "Av. Siempre Viva 123"

    def test_el_empleado_puede_buscar(self, sesion_de_ana):
        client, _, _ = sesion_de_ana
        assert len(client.get("/api/clientes", params={"buscar": "siempre viva"}).json()) == 1

    def test_el_empleado_no_puede_crear_editar_ni_borrar_clientes(self, sesion_de_ana):
        client, cliente, _ = sesion_de_ana
        url = f"/api/clientes/{cliente['id']}"
        assert client.post("/api/clientes", json=_cliente()).status_code == 403
        assert client.put(url, json=_cliente(nombre="Cambiado")).status_code == 403
        assert client.delete(url).status_code == 403
        assert client.get(url).json()["nombre"] == "Juan Pérez"  # no se tocó nada

    def test_el_empleado_no_puede_crear_editar_ni_borrar_obras(self, sesion_de_ana):
        client, cliente, obra = sesion_de_ana
        assert client.post(f"/api/clientes/{cliente['id']}/obras", json=_obra()).status_code == 403
        assert client.put(f"/api/obras/{obra['id']}", json=_obra(direccion="X")).status_code == 403
        assert client.delete(f"/api/obras/{obra['id']}").status_code == 403
        assert len(client.get(f"/api/clientes/{cliente['id']}").json()["obras"]) == 1

    def test_sin_sesion_todo_da_401(self, client):
        assert client.get("/api/clientes").status_code == 401
        assert client.get("/api/clientes/1").status_code == 401
        assert client.post("/api/clientes", json=_cliente()).status_code == 401
        assert client.post("/api/clientes/1/obras", json=_obra()).status_code == 401
        assert client.put("/api/obras/1", json=_obra()).status_code == 401
        assert client.delete("/api/obras/1").status_code == 401
