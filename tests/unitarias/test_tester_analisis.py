"""Tester, N11 y N12 sin Docker: reglas de la base, correspondencia de Ruff y conformidad."""

import pytest

from multiagente.agentes.tester.analisis import analizar_version
from multiagente.agentes.tester.ejecucion import ejecutar_version
from multiagente.agentes.tester.reglas import (
    EVALUADAS,
    cargar_reglas_calidad,
    regla_de_ruff,
)
from multiagente.core.esquemas.comunes import Enunciado, Impacto, Prioridad
from multiagente.core.esquemas.especificacion_diseno import (
    EspecificacionDiseno,
    InterfazPublica,
    Modulo,
    TipoInterfaz,
)
from multiagente.core.esquemas.requerimiento import (
    DatoEntrada,
    DatoSalida,
    Descripcion,
    EscenarioAceptacion,
    RequerimientoFormal,
    TipoSolicitud,
)
from multiagente.orquestador.estado import (
    Requerimientos,
    ResultadoPrueba,
    Severidad,
    VersionCodigo,
)
from multiagente.sandbox.ejecutor import (
    PruebaReportada,
    ResultadoEjecucion,
    ResultadoImportacion,
    ResultadoPruebas,
)

REGLAS = cargar_reglas_calidad()

RF1 = RequerimientoFormal(
    id_requerimiento="RF-01",
    version="0.1",
    proyecto="Catastro",
    tipo_solicitud=TipoSolicitud.NUEVO,
    impacto=Impacto.ALTO,
    modulo="avaluo",
    autor="Agente elicitador",
    area_funcional="Liquidación",
    titulo=Enunciado(
        como="liquidador catastral", quiero="calcular el avalúo", para="liquidar el impuesto"
    ),
    descripcion=Descripcion(
        precondicion="El predio existe",
        regla_negocio="El avalúo es el área por el valor del metro cuadrado.",
        datos_entrada=[DatoEntrada(nombre="area_terreno", tipo="Decimal", obligatorio=True)],
        datos_salida=[DatoSalida(nombre="avaluo", tipo="Decimal")],
    ),
    criterios_aceptacion=[
        EscenarioAceptacion(id="ESC-01", dado_que="un predio", cuando="calcula", entonces="ok"),
        EscenarioAceptacion(id="ESC-02", dado_que="valor 0", cuando="calcula", entonces="no"),
    ],
    prioridad=Prioridad.ALTA,
)
REQUERIMIENTOS = Requerimientos(requerimientos=(RF1,))
ESPECIFICACION = EspecificacionDiseno(
    id_especificacion="ED-01",
    version="0.1",
    arquitectura_base="ARQ-01",
    requerimientos_cubiertos=["RF-01"],
    modulos=[
        Modulo(
            nombre="dominio.predio",
            ruta="src/dominio/predio.py",
            responsabilidad="Entidad de predio",
            capa="dominio",
            interfaces_publicas=[
                InterfazPublica(
                    nombre="Predio",
                    tipo=TipoInterfaz.CLASE,
                    firma="Predio(numero_predial: str, area_terreno: Decimal)",
                    descripcion="Predio",
                )
            ],
            requerimientos=["RF-01"],
        ),
        Modulo(
            nombre="aplicacion.avaluo",
            ruta="src/aplicacion/avaluo.py",
            responsabilidad="Cálculo del avalúo",
            capa="aplicacion",
            interfaces_publicas=[
                InterfazPublica(
                    nombre="calcular_avaluo",
                    tipo=TipoInterfaz.FUNCION,
                    firma="calcular_avaluo(predio: Predio, valor_m2: Decimal) -> Decimal",
                    descripcion="Calcula el avalúo",
                    excepciones=["ValueError"],
                )
            ],
            dependencias_permitidas=["dominio.predio"],
            requerimientos=["RF-01"],
        ),
    ],
    modelo_datos=[],
    dependencias_externas=[],
    reglas_de_dependencia=["El dominio no importa de ninguna capa"],
)

PREDIO = '''"""Entidad de predio."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Predio:
    """Predio con sus atributos físicos.

    Attributes:
        numero_predial: Número predial.
        area_terreno: Área del terreno en metros cuadrados.
    """

    numero_predial: str
    area_terreno: Decimal
'''

AVALUO = '''"""Cálculo del avalúo."""

from decimal import Decimal

from dominio.predio import Predio


def calcular_avaluo(predio: Predio, valor_m2: Decimal) -> Decimal:
    """Calcula el avalúo del terreno.

    Args:
        predio: Predio a avaluar.
        valor_m2: Valor del metro cuadrado.

    Returns:
        El avalúo del terreno.

    Raises:
        ValueError: Si el valor no es positivo.
    """
    if valor_m2 <= 0:
        raise ValueError("El valor por metro cuadrado debe ser positivo")
    return predio.area_terreno * valor_m2
'''

PRUEBAS = """from decimal import Decimal

import pytest

from aplicacion.avaluo import calcular_avaluo
from dominio.predio import Predio


def test_rf_01_esc_01_calcula():
    assert calcular_avaluo(Predio("1", Decimal(2)), Decimal(3)) == Decimal(6)


def test_rf_01_esc_02_rechaza_valor_cero():
    with pytest.raises(ValueError):
        calcular_avaluo(Predio("1", Decimal(2)), Decimal(0))
"""


def archivos_validos() -> dict[str, str]:
    return {
        "src/dominio/predio.py": PREDIO,
        "src/aplicacion/avaluo.py": AVALUO,
        "tests/test_avaluo.py": PRUEBAS,
        "USO.md": "# Uso\n",
    }


def analizar(archivos):
    version = VersionCodigo(numero=1, archivos=archivos)
    return analizar_version(version, ESPECIFICACION, REQUERIMIENTOS, REGLAS)


# Reglas -----------------------------------------------------------------------------------------


def test_reglas_y_severidades_salen_de_la_base_de_conocimiento():
    assert len(REGLAS) == 34
    assert REGLAS["CAL-SG-002"].severidad is Severidad.ALTA
    assert REGLAS["CAL-MT-004"].severidad is Severidad.MEDIA
    assert REGLAS["CAL-MT-009"].severidad is Severidad.BAJA
    assert REGLAS["CAL-MT-010"].severidad is Severidad.MEDIA
    assert REGLAS["CAL-MT-010"].documento == "cal-mt"
    assert EVALUADAS <= set(REGLAS)


@pytest.mark.parametrize(
    ("codigo", "regla"),
    [
        ("S307", "CAL-SG-002"),
        ("S602", "CAL-SG-004"),
        ("S110", "CAL-SG-006"),
        ("BLE001", "CAL-SG-006"),
        ("D103", "CAL-MT-001"),
        ("ANN201", "CAL-MT-002"),
        ("C901", "CAL-MT-003"),
        ("F401", "CAL-MT-004"),
        ("N802", "CAL-MT-007"),
        ("B006", "CAL-FB-002"),
        ("B010", "CAL-MT-009"),
        ("E501", "CAL-MT-009"),
        ("I001", "CAL-MT-009"),
    ],
)
def test_cada_codigo_de_ruff_va_a_su_regla(codigo, regla):
    assert regla_de_ruff(codigo) == regla


# N12 --------------------------------------------------------------------------------------------


def test_version_conforme_sin_hallazgos():
    analisis = analizar(archivos_validos())
    assert analisis.hallazgos == ()
    assert [(c.modulo, c.existe, c.interfaces_divergentes) for c in analisis.conformidad] == [
        ("dominio.predio", True, ()),
        ("aplicacion.avaluo", True, ()),
    ]
    assert set(analisis.no_evaluadas) == set(REGLAS) - EVALUADAS
    assert "CAL-SG-005" in analisis.no_evaluadas


def reemplazar(ruta, viejo, nuevo):
    def aplicar(archivos):
        assert viejo in archivos[ruta]
        archivos[ruta] = archivos[ruta].replace(viejo, nuevo)

    return aplicar


def agregar(ruta, contenido):
    def aplicar(archivos):
        archivos[ruta] = contenido

    return aplicar


def quitar(ruta):
    def aplicar(archivos):
        del archivos[ruta]

    return aplicar


AVALUO_PY = "src/aplicacion/avaluo.py"


@pytest.mark.parametrize(
    ("cambio", "regla", "severidad"),
    [
        (
            reemplazar(AVALUO_PY, "return predio.area_terreno * valor_m2", "return eval('1')"),
            "CAL-SG-002",
            Severidad.ALTA,
        ),
        (
            reemplazar(
                AVALUO_PY,
                "from dominio.predio import Predio\n",
                'from dominio.predio import Predio\n\nCONTRASENA_BD = "admin123"\n',
            ),
            "CAL-SG-001",
            Severidad.ALTA,
        ),
        (
            reemplazar(
                AVALUO_PY,
                "return predio.area_terreno * valor_m2",
                "return Decimal(float(predio.area_terreno) * float(valor_m2))",
            ),
            "CAL-FS-005",
            Severidad.ALTA,
        ),
        (
            reemplazar(
                AVALUO_PY,
                "from dominio.predio import Predio",
                "from dominio.predio import Predio, _x",
            ),
            "CAL-MT-010",
            Severidad.MEDIA,
        ),
        (
            reemplazar(
                "src/dominio/predio.py",
                "from decimal import Decimal\n",
                "from decimal import Decimal\n\nimport aplicacion.avaluo\n",
            ),
            "CAL-MT-006",
            Severidad.ALTA,
        ),
        (quitar(AVALUO_PY), "CAL-AR-001", Severidad.ALTA),
        (agregar("src/dominio/extra.py", '"""Extra."""\n'), "CAL-AR-003", Severidad.MEDIA),
        (
            reemplazar(AVALUO_PY, "valor_m2: Decimal) -> Decimal:", "valor: Decimal) -> Decimal:"),
            "CAL-AR-002",
            Severidad.ALTA,
        ),
        (
            reemplazar(
                AVALUO_PY,
                "from decimal import Decimal\n",
                "import os\nfrom decimal import Decimal\n",
            ),
            "CAL-MT-004",
            Severidad.MEDIA,
        ),
        (
            reemplazar(
                AVALUO_PY,
                "    if valor_m2 <= 0:",
                "    # " + "comentario largo " * 6 + "\n    if valor_m2 <= 0:",
            ),
            "CAL-MT-009",
            Severidad.BAJA,
        ),
        (
            reemplazar(AVALUO_PY, "def calcular_avaluo(", "def calcular_avaluo(:"),
            "CAL-FS-003",
            Severidad.ALTA,
        ),
        (
            reemplazar("tests/test_avaluo.py", "def test_rf_01_esc_0", "def test_escenario_0"),
            "CAL-AR-005",
            Severidad.ALTA,
        ),
    ],
)
def test_cada_defecto_estatico_se_reporta_con_su_regla(cambio, regla, severidad):
    archivos = archivos_validos()
    cambio(archivos)
    hallazgos = analizar(archivos).hallazgos
    encontrados = [h for h in hallazgos if h.regla == regla]
    assert encontrados, [(h.regla, h.descripcion) for h in hallazgos]
    assert all(h.severidad is severidad for h in encontrados)
    assert all(h.sugerencia and h.ubicacion for h in encontrados)


def test_la_dependencia_no_autorizada_queda_en_la_conformidad_del_modulo():
    archivos = archivos_validos()
    reemplazar(
        "src/dominio/predio.py",
        "from decimal import Decimal\n",
        "from decimal import Decimal\n\nimport aplicacion.avaluo\n",
    )(archivos)
    conformidad = {c.modulo: c for c in analizar(archivos).conformidad}
    (dependencia,) = conformidad["dominio.predio"].dependencias_no_autorizadas
    assert "aplicacion.avaluo" in dependencia


# N11 --------------------------------------------------------------------------------------------


class EntornoFalso:
    def importar(self, archivos, modulos):
        ejecucion = ResultadoEjecucion(
            codigo_salida=0, salida="", errores="", vencido=False, duracion_ms=300
        )
        return ResultadoImportacion(
            errores={"aplicacion.avaluo": "SyntaxError"}, ejecucion=ejecucion
        )

    def probar(self, archivos, tiempo_limite_s):
        ejecucion = ResultadoEjecucion(
            codigo_salida=1, salida="", errores="", vencido=False, duracion_ms=500
        )
        return ResultadoPruebas(
            pruebas=(
                PruebaReportada(
                    archivo="tests/test_avaluo.py",
                    nombre="test_rf_01_esc_01_calcula",
                    resultado="fallo",
                    duracion_ms=3,
                    mensaje="AssertionError",
                ),
            ),
            errores_recoleccion=(),
            codigo_pytest=1,
            salida_pytest="1 failed",
            ejecucion=ejecucion,
        )


def test_n11_reune_la_importacion_y_las_pruebas():
    version = VersionCodigo(numero=1, archivos=archivos_validos())
    ejecucion = ejecutar_version(EntornoFalso(), version, ESPECIFICACION, 120)
    assert ejecucion.errores_importacion == {"aplicacion.avaluo": "SyntaxError"}
    (prueba,) = ejecucion.pruebas
    assert prueba.resultado is ResultadoPrueba.FALLO
    assert prueba.identificador == "tests/test_avaluo.py::test_rf_01_esc_01_calcula"
    assert ejecucion.duracion_ms == 800 and ejecucion.salida == "1 failed"


def test_clave_sola_no_es_un_secreto():
    # En el dominio, «clave» es también la llave de un diccionario o la clave catastral.
    archivos = archivos_validos()
    reemplazar(
        AVALUO_PY,
        "from dominio.predio import Predio\n",
        'from dominio.predio import Predio\n\nCLAVE_CATASTRAL = "numero_predial"\n',
    )(archivos)
    assert [h for h in analizar(archivos).hallazgos if h.regla == "CAL-SG-001"] == []


def secretos(archivos):
    return [h for h in analizar(archivos).hallazgos if h.regla == "CAL-SG-001"]


def con_codigo(codigo, ruta=AVALUO_PY):
    archivos = archivos_validos()
    archivos[ruta] += f"\n\n{codigo}\n"
    return archivos


@pytest.mark.parametrize(
    "codigo",
    [
        'CONTRASENA_BD = "admin123"',
        'DB_PASSWORD = "catastro2026"',
        'TOKEN: str = "abc123"',
        'conectar(password="admin123")',
        'def conectar(token: str = "abc123") -> None:\n    """Conecta."""',
        'def conectar(*, clave_api: str = "abc123") -> None:\n    """Conecta."""',
        'if clave_api == "abc123":\n    pass',
        'if "abc123" != token_notion:\n    pass',
    ],
)
def test_cada_secreto_se_reporta_una_vez(codigo):
    (hallazgo,) = secretos(con_codigo(codigo))
    assert hallazgo.severidad is Severidad.ALTA
    assert hallazgo.ubicacion.startswith(f"{AVALUO_PY}:")
    assert "abc123" not in hallazgo.descripcion and "admin123" not in hallazgo.descripcion


@pytest.mark.parametrize(
    "codigo",
    [
        # El mensaje que pidió el cliente de NotionSync (sesión 9da543db), que se marcó en la v1
        # y, renombrado, en la v2.
        '_MENSAJE_TOKEN = (\n    "Error: No se encontró un token de Notion válido. "\n'
        '    "Por favor, verifica tu archivo .env"\n)',
        '_MENSAJE_CREDENCIALES = "Error: No se encontró un token de Notion válido."',
        'VARIABLE_TOKEN = "NOTION_TOKEN"',
        'def leer(nombre_token: str = "NOTION_TOKEN") -> None:\n    """Lee."""',
        'TOKEN_VACIO = ""',
    ],
)
def test_mensajes_y_variables_de_entorno_no_son_secretos(codigo):
    assert secretos(con_codigo(codigo)) == []


@pytest.mark.parametrize(
    "codigo",
    [
        'CONFIGURACION = dict(token_notion="token-prueba")',
        'assert CONFIGURACION["token_notion"] == "token-entorno"',
    ],
)
def test_los_datos_de_las_pruebas_no_son_secretos(codigo):
    assert secretos(con_codigo(codigo, "tests/test_avaluo.py")) == []
    # El mismo código en un módulo sí se reporta.
    assert len(secretos(con_codigo(codigo))) == 1
