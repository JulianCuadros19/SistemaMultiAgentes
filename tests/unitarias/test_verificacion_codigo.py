"""Verificación estructural del código generado (N10): RF-15, RF-17 y RF-18, sin ejecutarlo."""

import pytest

from multiagente.agentes.desarrollador.verificacion import (
    importacion_de_paquete,
    nombre_de_prueba,
    verificar_version,
)
from multiagente.core.esquemas.comunes import Enunciado, Impacto, Prioridad
from multiagente.core.esquemas.especificacion_diseno import (
    DependenciaExterna,
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
from multiagente.orquestador.estado import Requerimientos

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
        EscenarioAceptacion(
            id="ESC-01", nombre="Cálculo", dado_que="un predio", cuando="calcula", entonces="ok"
        ),
        EscenarioAceptacion(
            id="ESC-02",
            nombre="Valor inválido",
            dado_que="valor 0",
            cuando="calcula",
            entonces="no",
        ),
    ],
    prioridad=Prioridad.ALTA,
)
REQUERIMIENTOS = Requerimientos(requerimientos=(RF1,))
FIRMA_AVALUO = "calcular_avaluo(predio: Predio, valor_m2: Decimal | None) -> Decimal"


def especificacion(externas: tuple[str, ...] = ()) -> EspecificacionDiseno:
    return EspecificacionDiseno(
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
                        excepciones=["NumeroPredialInvalido"],
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
                        firma=FIRMA_AVALUO,
                        descripcion="Calcula el avalúo",
                        excepciones=["ValueError"],
                    )
                ],
                dependencias_permitidas=["dominio.predio"],
                requerimientos=["RF-01"],
            ),
        ],
        modelo_datos=[],
        dependencias_externas=[DependenciaExterna(paquete=p, proposito="x") for p in externas],
        reglas_de_dependencia=["El dominio no importa de ninguna capa"],
    )


CLASE_PREDIO = '''@dataclass(frozen=True)
class Predio:
    """Predio con sus atributos físicos."""

    numero_predial: str
    area_terreno: Decimal

    def __post_init__(self) -> None:
        if len(self.numero_predial) != 30:
            raise NumeroPredialInvalido(self.numero_predial)
'''

PREDIO = (
    '''"""Entidad de predio."""

from dataclasses import dataclass
from decimal import Decimal


class NumeroPredialInvalido(ValueError):
    """El número predial no tiene 30 dígitos."""


'''
    + CLASE_PREDIO
)

AVALUO = '''"""Cálculo del avalúo."""

from decimal import Decimal
from typing import Optional

from dominio.predio import Predio


def calcular_avaluo(predio: Predio, valor_m2: Optional[Decimal]) -> Decimal:
    """Calcula el avalúo del terreno."""
    if not valor_m2:
        raise ValueError("El valor por metro cuadrado debe ser positivo")
    return predio.area_terreno * valor_m2
'''

PRUEBAS = """from decimal import Decimal

import pytest

from aplicacion.avaluo import calcular_avaluo
from dominio.predio import Predio


def test_rf_01_esc_01_calcula_el_avaluo():
    assert calcular_avaluo(Predio("1" * 30, Decimal(2)), Decimal(3)) == Decimal(6)


def test_rf_01_esc_02_rechaza_valor_invalido():
    with pytest.raises(ValueError):
        calcular_avaluo(Predio("1" * 30, Decimal(2)), Decimal(0))
"""


def archivos_validos() -> dict[str, str]:
    return {
        "src/dominio/predio.py": PREDIO,
        "src/aplicacion/avaluo.py": AVALUO,
        "tests/test_avaluo.py": PRUEBAS,
        "USO.md": "# Uso\n\nLlame a `calcular_avaluo`.\n",
    }


def verificar(archivos, externas=()):
    return verificar_version(archivos, especificacion(externas), REQUERIMIENTOS)


def test_version_valida_sin_problemas():
    assert verificar(archivos_validos()) == []


def test_nombres_de_prueba_y_paquetes():
    assert nombre_de_prueba("RF-021", "ESC-03") == "test_rf_021_esc_03"
    assert importacion_de_paquete("psycopg[binary]") == "psycopg"
    assert importacion_de_paquete("SQLAlchemy") == "sqlalchemy"


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


CON_INIT = '''
class Predio:
    """Predio."""

    def __init__(self, numero_predial: str, area_terreno: "Decimal") -> None:
        self.numero_predial = numero_predial
'''


@pytest.mark.parametrize(
    "cambio, esperado",
    [
        (quitar("src/aplicacion/avaluo.py"), "falta src/aplicacion/avaluo.py"),
        (agregar("src/aplicacion/extra.py", '"""x"""\n'), "extra.py no está previsto"),
        (agregar("src/dominio/__init__.py", ""), "__init__.py no está previsto"),
        (agregar("../fuera.py", ""), "no es relativa"),
        (quitar("tests/test_avaluo.py"), "no hay archivos de prueba"),
        (quitar("USO.md"), "falta el documento de uso"),
        (
            reemplazar(
                "src/aplicacion/avaluo.py", "from typing", "type Monto = Decimal\nfrom typing"
            ),
            "no es Python 3.11 válido",
        ),
        (
            reemplazar("src/aplicacion/avaluo.py", "def calcular_avaluo", "def calcular"),
            "no define la función",
        ),
        (
            reemplazar("src/aplicacion/avaluo.py", "valor_m2: Optional", "valor: Optional"),
            "implementa",
        ),
        (
            reemplazar(
                "src/aplicacion/avaluo.py", "valor_m2: Optional[Decimal]", "valor_m2: float"
            ),
            "implementa",
        ),
        (reemplazar("src/aplicacion/avaluo.py", "]) -> Decimal", "]) -> float"), "retorna float"),
        (
            reemplazar(
                "src/dominio/predio.py",
                "    numero_predial: str\n    area_terreno: Decimal\n",
                "    area_terreno: Decimal\n    numero_predial: str\n",
            ),
            "el constructor de src/dominio/predio.py: Predio",
        ),
        (
            reemplazar(
                "src/dominio/predio.py", "class Predio:", "def Predio():\n    pass\n\n\nclass Otro:"
            ),
            "no define la clase Predio",
        ),
        (
            reemplazar(
                "src/dominio/predio.py",
                "class NumeroPredialInvalido(ValueError):",
                "class Invalido(ValueError):",
            ),
            "no define ni importa la excepción NumeroPredialInvalido",
        ),
        (
            reemplazar(
                "src/dominio/predio.py", "from decimal", "import aplicacion.avaluo\nfrom decimal"
            ),
            "no está en sus dependencias permitidas",
        ),
        (
            reemplazar("src/aplicacion/avaluo.py", "from decimal", "import pydantic\nfrom decimal"),
            "importa pydantic, que no es de la biblioteca estándar",
        ),
        (
            reemplazar(
                "src/aplicacion/avaluo.py", "from dominio.predio import", "from .predio import"
            ),
            "importación relativa",
        ),
        (
            reemplazar(
                "src/aplicacion/avaluo.py",
                "from decimal",
                "from dominio.otro import X\nfrom decimal",
            ),
            "dominio.otro, que no es un módulo declarado",
        ),
        (
            reemplazar(
                "src/aplicacion/avaluo.py", '    """Calcula el avalúo del terreno."""\n', ""
            ),
            "calcular_avaluo es público y no tiene docstring",
        ),
        (
            reemplazar("tests/test_avaluo.py", "test_rf_01_esc_02_rechaza", "test_rechaza"),
            "falta una prueba test_rf_01_esc_02_… para RF-01 ESC-02 «Valor inválido»",
        ),
        (
            agregar("tests/test_extra.py", "def test_rf_01_esc_09_inventado():\n    pass\n"),
            "cita RF-01 ESC-09",
        ),
        (
            agregar("tests/test_extra.py", "import pandas\n"),
            "tests/test_extra.py:1 importa pandas",
        ),
    ],
)
def test_detecta_cada_falla_inyectada(cambio, esperado):
    archivos = archivos_validos()
    cambio(archivos)
    problemas = verificar(archivos)
    assert any(esperado in problema for problema in problemas), problemas


@pytest.mark.parametrize(
    "cambio",
    [
        # Constructor explícito, con referencia adelantada entre comillas.
        reemplazar(
            "src/dominio/predio.py",
            CLASE_PREDIO,
            CON_INIT,
        ),
        # `Decimal | None` equivale a `Optional[Decimal]` y `decimal.Decimal` a `Decimal`.
        reemplazar(
            "src/aplicacion/avaluo.py",
            "valor_m2: Optional[Decimal]) -> Decimal",
            "valor_m2: Decimal | None) -> decimal.Decimal",
        ),
        # `from dominio import predio` importa el módulo declarado `dominio.predio`.
        reemplazar(
            "src/aplicacion/avaluo.py",
            "from dominio.predio import Predio",
            "from dominio import predio\nfrom dominio.predio import Predio",
        ),
        # Las pruebas pueden tener fixtures compartidas y pruebas adicionales.
        agregar("tests/conftest.py", "import pytest\n"),
        agregar("tests/test_extra.py", "def test_otro_caso():\n    pass\n"),
    ],
)
def test_admite_variantes_equivalentes(cambio):
    archivos = archivos_validos()
    cambio(archivos)
    assert verificar(archivos) == []


def test_dependencia_externa_declarada_se_admite():
    archivos = archivos_validos()
    reemplazar("src/aplicacion/avaluo.py", "from decimal", "import pydantic\nfrom decimal")(
        archivos
    )
    assert verificar(archivos, externas=("pydantic",)) == []
