"""Las migraciones deben funcionar tanto en una base nueva como en una creada por la versión
anterior de la app (que usaba create_all, sin Alembic)."""

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from presupuestos_backend import models  # noqa: F401  (registra las tablas)
from presupuestos_backend.database import Base
from presupuestos_backend.migraciones import aplicar_migraciones

# Esquema exacto que creaba create_all antes de usar Alembic (importes en FLOAT).
ESQUEMA_LEGADO = [
    """CREATE TABLE presupuestos (
        id INTEGER NOT NULL, cliente_obra VARCHAR(200) NOT NULL, direccion VARCHAR(300) NOT NULL,
        fecha_emision DATE NOT NULL, vigencia_dias INTEGER NOT NULL, plazo_obra VARCHAR(200) NOT NULL,
        forma_pago VARCHAR(300) NOT NULL, materiales_a_cargo VARCHAR(100) NOT NULL,
        observaciones TEXT NOT NULL, total FLOAT NOT NULL, creado_en DATETIME NOT NULL,
        PRIMARY KEY (id))""",
    """CREATE TABLE items_presupuesto (
        id INTEGER NOT NULL, presupuesto_id INTEGER NOT NULL, orden INTEGER NOT NULL,
        descripcion VARCHAR(500) NOT NULL, unidad VARCHAR(50) NOT NULL, cantidad FLOAT NOT NULL,
        importe FLOAT NOT NULL, PRIMARY KEY (id), FOREIGN KEY(presupuesto_id) REFERENCES presupuestos (id))""",
]


@pytest.fixture
def motor(tmp_path):
    motor = create_engine(f"sqlite:///{tmp_path}/migracion.db")
    yield motor
    motor.dispose()


def _tipo(motor, tabla: str, columna: str) -> str:
    columnas = {c["name"]: str(c["type"]) for c in inspect(motor).get_columns(tabla)}
    return columnas[columna]


def _migrar(motor) -> None:
    with motor.begin() as conexion:
        aplicar_migraciones(conexion)


def test_base_nueva_queda_con_importes_numericos(motor):
    _migrar(motor)
    assert _tipo(motor, "presupuestos", "total").startswith("NUMERIC")
    assert _tipo(motor, "items_presupuesto", "importe").startswith("NUMERIC")


def test_base_de_la_version_anterior_se_migra_sin_perder_datos(motor):
    with motor.begin() as conexion:
        for sentencia in ESQUEMA_LEGADO:
            conexion.execute(text(sentencia))
        conexion.execute(
            text(
                "INSERT INTO presupuestos VALUES (1, 'Cliente viejo', '', '2026-01-01', 15, '', "
                "'50%', 'Cliente', 'obs', 1000.5, '2026-01-01 10:00:00')"
            )
        )
        conexion.execute(
            text("INSERT INTO items_presupuesto VALUES (1, 1, 0, 'Pintura', 'gl', 1, 1000.5)")
        )

    _migrar(motor)

    assert _tipo(motor, "presupuestos", "total").startswith("NUMERIC")
    with motor.connect() as conexion:
        fila = conexion.execute(text("SELECT cliente_obra, total FROM presupuestos")).one()
        item = conexion.execute(text("SELECT descripcion, importe FROM items_presupuesto")).one()
    assert fila[0] == "Cliente viejo"
    assert float(fila[1]) == 1000.5
    assert (item[0], float(item[1])) == ("Pintura", 1000.5)


def test_migrar_dos_veces_no_falla(motor):
    _migrar(motor)
    _migrar(motor)


def test_las_migraciones_coinciden_con_los_modelos(motor):
    """Si alguien cambia models.py y olvida crear la migración, este test lo detecta."""
    _migrar(motor)
    with motor.connect() as conexion:
        contexto = MigrationContext.configure(conexion, opts={"compare_type": True})
        diferencias = compare_metadata(contexto, Base.metadata)
    assert diferencias == [], f"Faltan migraciones: {diferencias}"


def test_se_puede_volver_atras(motor):
    from alembic import command
    from alembic.config import Config

    from presupuestos_backend.migraciones import CARPETA_MIGRACIONES

    _migrar(motor)
    config = Config()
    config.set_main_option("script_location", str(CARPETA_MIGRACIONES))
    with motor.begin() as conexion:
        config.attributes["connection"] = conexion
        command.downgrade(config, "0001")
    assert sa.inspect(motor).has_table("presupuestos")
    assert _tipo(motor, "presupuestos", "total") == "FLOAT"


def test_los_presupuestos_existentes_quedan_como_borrador_y_sin_vinculo(motor):
    """Una base con presupuestos cargados antes de existir estados y vínculos no pierde nada."""
    with motor.begin() as conexion:
        aplicar_migraciones(conexion, revision="0004")
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO presupuestos (id, cliente_obra, direccion, fecha_emision, "
                "vigencia_dias, plazo_obra, forma_pago, materiales_a_cargo, observaciones, "
                "total, creado_en) VALUES (1, 'Presupuesto viejo', '', '2026-01-01', 15, '', "
                "'50%', 'Cliente', 'obs', 1000.50, '2026-01-01 10:00:00')"
            )
        )
        conexion.execute(
            text("INSERT INTO items_presupuesto VALUES (1, 1, 0, 'Pintura', 'gl', 1, 1000.50)")
        )

    _migrar(motor)

    with motor.connect() as conexion:
        fila = conexion.execute(
            text("SELECT cliente_obra, estado, cliente_id, obra_id, total FROM presupuestos")
        ).one()
        items = conexion.execute(text("SELECT count(*) FROM items_presupuesto")).scalar()
    assert tuple(fila[:4]) == ("Presupuesto viejo", "borrador", None, None)
    assert float(fila[4]) == 1000.5
    assert items == 1


def test_los_trabajos_existentes_quedan_por_agendar_y_sin_fechas(motor):
    """Un trabajo creado antes del calendario conserva su estado y queda sin fechas."""
    with motor.begin() as conexion:
        aplicar_migraciones(conexion, revision="0005")
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO clientes VALUES (1, 'Consorcio Sol', 'consorcio', '', '', "
                "'2026-01-01 10:00:00')"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO obras VALUES (1, 1, 'Corrientes 1200', '', '', '2026-01-01 10:00:00')"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO presupuestos (id, cliente_obra, direccion, fecha_emision, "
                "vigencia_dias, plazo_obra, forma_pago, materiales_a_cargo, observaciones, total, "
                "creado_en, estado, cliente_id, obra_id) VALUES (1, 'Consorcio Sol', '', "
                "'2026-01-01', 15, '', '50%', 'Cliente', 'obs', 1000, '2026-01-01 10:00:00', "
                "'aprobado', 1, 1)"
            )
        )
        conexion.execute(
            text("INSERT INTO trabajos VALUES (1, 1, 'por_agendar', '2026-01-02 09:00:00')")
        )

    _migrar(motor)

    with motor.connect() as conexion:
        fila = conexion.execute(
            text("SELECT estado, fecha_inicio, fecha_fin, iniciado_en, terminado_en FROM trabajos")
        ).one()
    assert tuple(fila) == ("por_agendar", None, None, None, None)


def _cargar_trabajo(conexion, estado):
    """Un cliente, una obra, un presupuesto aprobado y un trabajo en el estado indicado."""
    conexion.execute(
        text(
            "INSERT INTO clientes VALUES (1, 'Consorcio Sol', 'consorcio', '', '', '2026-01-01 10:00')"
        )
    )
    conexion.execute(
        text("INSERT INTO obras VALUES (1, 1, 'Corrientes 1200', '', '', '2026-01-01 10:00')")
    )
    conexion.execute(
        text(
            "INSERT INTO presupuestos (id, cliente_obra, direccion, fecha_emision, vigencia_dias, "
            "plazo_obra, forma_pago, materiales_a_cargo, observaciones, total, creado_en, estado, "
            "cliente_id, obra_id) VALUES (1, 'Consorcio Sol', '', '2026-01-01', 15, '', '50%', "
            "'Cliente', 'obs', 1000, '2026-01-01 10:00', 'aprobado', 1, 1)"
        )
    )
    conexion.execute(
        text(
            "INSERT INTO trabajos (id, presupuesto_id, estado, creado_en) "
            f"VALUES (1, 1, '{estado}', '2026-01-02 09:00')"
        )
    )


def test_los_trabajos_existentes_quedan_sin_cobros_al_migrar(motor):
    with motor.begin() as conexion:
        aplicar_migraciones(conexion, revision="0006")
    with motor.begin() as conexion:
        _cargar_trabajo(conexion, "terminado")

    _migrar(motor)

    with motor.connect() as conexion:
        estado = conexion.execute(text("SELECT estado FROM trabajos")).scalar()
        cobros = conexion.execute(text("SELECT count(*) FROM cobros")).scalar()
    assert (estado, cobros) == ("terminado", 0)


def test_al_volver_atras_los_trabajos_cobrados_pasan_a_terminados(motor):
    """Sin la tabla de cobros no se sabe si están pagados: vuelven al estado anterior."""
    from alembic import command
    from alembic.config import Config

    from presupuestos_backend.migraciones import CARPETA_MIGRACIONES

    _migrar(motor)
    with motor.begin() as conexion:
        _cargar_trabajo(conexion, "cobrado")

    config = Config()
    config.set_main_option("script_location", str(CARPETA_MIGRACIONES))
    with motor.begin() as conexion:
        config.attributes["connection"] = conexion
        command.downgrade(config, "0006")

    with motor.connect() as conexion:
        assert conexion.execute(text("SELECT estado FROM trabajos")).scalar() == "terminado"
    assert not sa.inspect(motor).has_table("cobros")
