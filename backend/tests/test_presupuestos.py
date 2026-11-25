from decimal import Decimal

from conftest import presupuesto_valido

from presupuestos_backend.crud import a_dinero
from presupuestos_backend.formato import moneda


class TestDinero:
    def test_a_dinero_redondea_como_a_mano(self):
        assert a_dinero(10.005) == Decimal("10.01")
        assert a_dinero(10.004) == Decimal("10.00")
        assert a_dinero(0.1) == Decimal("0.10")

    def test_formato_de_pesos_argentinos(self):
        assert moneda(Decimal("1234.5")) == "1.234,50"
        assert moneda(0) == "0,00"
        assert moneda(1234567.891) == "1.234.567,89"


class TestApi:
    def test_crear_calcula_el_total(self, autenticado):
        datos = presupuesto_valido(
            items=[
                {"descripcion": "Pintura", "cantidad": 1, "importe": 1500.50},
                {"descripcion": "Arreglo de humedad", "cantidad": 2, "importe": 499.50},
            ]
        )
        r = autenticado.post("/api/presupuestos", json=datos)
        assert r.status_code == 201
        cuerpo = r.json()
        assert cuerpo["total"] == 2000.0
        assert [i["importe"] for i in cuerpo["items"]] == [1500.5, 499.5]

    def test_la_suma_es_exacta_sin_errores_de_coma_flotante(self, autenticado):
        datos = presupuesto_valido(
            items=[
                {"descripcion": "a", "cantidad": 1, "importe": 0.1},
                {"descripcion": "b", "cantidad": 1, "importe": 0.2},
            ]
        )
        # Con Float: 0.1 + 0.2 = 0.30000000000000004
        assert autenticado.post("/api/presupuestos", json=datos).json()["total"] == 0.3

    def test_importe_con_medio_centavo_redondea_hacia_arriba(self, autenticado):
        datos = presupuesto_valido(items=[{"descripcion": "a", "cantidad": 1, "importe": 10.005}])
        r = autenticado.post("/api/presupuestos", json=datos).json()
        assert r["items"][0]["importe"] == 10.01
        assert r["total"] == 10.01

    def test_obtener_y_listar_y_buscar(self, autenticado):
        autenticado.post("/api/presupuestos", json=presupuesto_valido(cliente_obra="Ana - Casa"))
        autenticado.post("/api/presupuestos", json=presupuesto_valido(cliente_obra="Consorcio Sol"))

        todos = autenticado.get("/api/presupuestos").json()
        assert [p["cliente_obra"] for p in todos] == [
            "Consorcio Sol",
            "Ana - Casa",
        ]  # más nuevo primero

        buscados = autenticado.get("/api/presupuestos", params={"buscar": "consorcio"}).json()
        assert [p["cliente_obra"] for p in buscados] == ["Consorcio Sol"]

        uno = autenticado.get(f"/api/presupuestos/{todos[1]['id']}").json()
        assert uno["cliente_obra"] == "Ana - Casa"
        assert len(uno["numero"]) == 4

    def test_actualizar_reemplaza_los_items(self, autenticado):
        creado = autenticado.post("/api/presupuestos", json=presupuesto_valido()).json()
        nuevos = presupuesto_valido(
            cliente_obra="Otro cliente",
            items=[{"descripcion": "Solo esto", "cantidad": 1, "importe": 250}],
        )
        r = autenticado.put(f"/api/presupuestos/{creado['id']}", json=nuevos)
        assert r.status_code == 200
        assert r.json()["cliente_obra"] == "Otro cliente"
        assert [i["descripcion"] for i in r.json()["items"]] == ["Solo esto"]
        assert r.json()["total"] == 250.0

    def test_eliminar_y_despues_404(self, autenticado):
        creado = autenticado.post("/api/presupuestos", json=presupuesto_valido()).json()
        assert autenticado.delete(f"/api/presupuestos/{creado['id']}").status_code == 204
        assert autenticado.get(f"/api/presupuestos/{creado['id']}").status_code == 404

    def test_inexistente_da_404_en_castellano(self, autenticado):
        r = autenticado.get("/api/presupuestos/999999")
        assert r.status_code == 404
        assert "No se encontró" in r.json()["detail"]

    def test_sin_items_da_422_con_mensaje_legible(self, autenticado):
        r = autenticado.post("/api/presupuestos", json=presupuesto_valido(items=[]))
        assert r.status_code == 422
        assert "Trabajos" in r.json()["detail"]

    def test_importe_gigante_da_422_y_no_rompe_la_base(self, autenticado):
        datos = presupuesto_valido(items=[{"descripcion": "a", "cantidad": 1, "importe": 1e15}])
        r = autenticado.post("/api/presupuestos", json=datos)
        assert r.status_code == 422
        assert "importe" in r.json()["detail"]

    def test_demasiados_items_da_422(self, autenticado):
        items = [{"descripcion": "x", "cantidad": 1, "importe": 1}] * 201
        r = autenticado.post("/api/presupuestos", json=presupuesto_valido(items=items))
        assert r.status_code == 422

    def test_importe_negativo_da_422(self, autenticado):
        datos = presupuesto_valido(items=[{"descripcion": "a", "cantidad": 1, "importe": -1}])
        assert autenticado.post("/api/presupuestos", json=datos).status_code == 422


class TestPdf:
    def _crear(self, autenticado):
        return autenticado.post("/api/presupuestos", json=presupuesto_valido()).json()["id"]

    def test_devuelve_un_pdf(self, autenticado):
        r = autenticado.get(f"/api/presupuestos/{self._crear(autenticado)}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")

    def test_con_datos_de_contacto_configurados(self, autenticado, monkeypatch):
        monkeypatch.setenv("NEGOCIO_RESPONSABLE", "Persona de Prueba")
        monkeypatch.setenv("NEGOCIO_TELEFONO", "11 0000 0000")
        monkeypatch.setenv("NEGOCIO_INSTAGRAM", "@prueba")
        r = autenticado.get(f"/api/presupuestos/{self._crear(autenticado)}/pdf")
        assert r.status_code == 200 and r.content.startswith(b"%PDF")

    def test_nombre_con_caracteres_especiales_no_rompe_el_pdf(self, autenticado, monkeypatch):
        # "&" y "<" son especiales para ReportLab si no se escapan.
        monkeypatch.setenv("NEGOCIO_NOMBRE", "Pérez & Hijos <Hogar>")
        r = autenticado.get(f"/api/presupuestos/{self._crear(autenticado)}/pdf")
        assert r.status_code == 200 and r.content.startswith(b"%PDF")

    def test_nombre_de_archivo_con_tildes_y_caracteres_fuera_de_latin1(self, autenticado):
        # "Ł" no existe en latin-1: antes provocaba un error 500 al armar el header.
        datos = presupuesto_valido(cliente_obra="Łukasz Ñandú - Casa")
        creado = autenticado.post("/api/presupuestos", json=datos).json()
        r = autenticado.get(f"/api/presupuestos/{creado['id']}/pdf")
        assert r.status_code == 200
        cabecera = r.headers["content-disposition"]
        assert cabecera.startswith('inline; filename="Presupuesto_')
        assert "filename*=UTF-8''" in cabecera
        assert "%C5%81ukasz" in cabecera  # la "Ł" va codificada en UTF-8

    def test_nombre_de_archivo_sin_ningun_caracter_ascii_sigue_funcionando(self, autenticado):
        creado = autenticado.post(
            "/api/presupuestos", json=presupuesto_valido(cliente_obra="漢字")
        ).json()
        r = autenticado.get(f"/api/presupuestos/{creado['id']}/pdf")
        assert r.status_code == 200
        cabecera = r.headers["content-disposition"]
        assert f'filename="Presupuesto_{creado["id"]:04d}_.pdf"' in cabecera  # parte ASCII
        assert "%E6%BC%A2" in cabecera  # nombre real en UTF-8

    def test_el_codigo_no_trae_datos_personales_escritos_a_mano(self):
        """Los datos de contacto deben salir solo de la configuración, nunca del código."""
        from pathlib import Path

        import presupuestos_backend

        codigo = "\n".join(
            p.read_text(encoding="utf-8")
            for p in Path(presupuestos_backend.__file__).parent.rglob("*.py")
        )
        for dato in ("3345", "none.hogar", "Leonardo"):
            assert dato not in codigo, f"'{dato}' quedó escrito en el código"
