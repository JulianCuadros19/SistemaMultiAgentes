"""Verificación estructural del código generado (N10): RF-15, RF-17 y RF-18, sin ejecutarlo."""

import pytest

from multiagente.agentes.desarrollador.verificacion import (
    SECCIONES_USO,
    importacion_de_paquete,
    nombre_de_prueba,
    verificar_version,
)
from multiagente.core.conformidad import TipoProblema, analizar_conformidad
from multiagente.core.dinero import es_monetario
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
        "USO.md": "# Uso\n\n"
        + "".join(f"## {seccion}\n\nLlame a `calcular_avaluo`.\n\n" for seccion in SECCIONES_USO),
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
            reemplazar("USO.md", "## Ejecución", "## Cómo se usa"),
            "a USO.md le faltan las secciones «## Ejecución»",
        ),
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
                "src/aplicacion/avaluo.py",
                "valor_m2: Optional[Decimal]) -> Decimal",
                "valor_m2: Optional[Decimal], vigencia: int) -> Decimal",
            ),
            "implementa",
        ),
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
        (
            reemplazar(
                "src/aplicacion/avaluo.py",
                "from dominio.predio import Predio",
                "from dominio.predio import Predio, _validar",
            ),
            "importa los nombres privados ['_validar'] de dominio.predio",
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
        # Al final se admiten parámetros y campos con valor por defecto.
        reemplazar(
            "src/aplicacion/avaluo.py",
            "valor_m2: Optional[Decimal]) -> Decimal",
            "valor_m2: Optional[Decimal], redondear: bool = True) -> Decimal",
        ),
        reemplazar(
            "src/dominio/predio.py",
            "    area_terreno: Decimal\n",
            "    area_terreno: Decimal\n    _vigencia: int | None = None\n",
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


# Informe compartido con el tester (core.conformidad) -------------------------------------------


def informe(archivos):
    return analizar_conformidad(archivos, especificacion(), REQUERIMIENTOS.requerimientos)


def test_informe_resume_cada_modulo_y_las_pruebas():
    resultado = informe(archivos_validos())
    assert resultado.problemas == ()
    resumen = {modulo.nombre: modulo for modulo in resultado.modulos}
    assert resumen["dominio.predio"].existe
    assert resumen["aplicacion.avaluo"].interfaces_conformes == ("calcular_avaluo",)
    (pruebas,) = resultado.pruebas
    assert pruebas.ruta == "tests/test_avaluo.py"
    assert pruebas.modulos_importados == {"aplicacion.avaluo", "dominio.predio"}
    assert set(resultado.arboles) == {
        "src/dominio/predio.py",
        "src/aplicacion/avaluo.py",
        "tests/test_avaluo.py",
    }


def test_informe_marca_el_modulo_faltante_y_sus_interfaces_divergentes():
    archivos = archivos_validos()
    quitar("src/aplicacion/avaluo.py")(archivos)
    resumen = {modulo.nombre: modulo for modulo in informe(archivos).modulos}
    assert not resumen["aplicacion.avaluo"].existe
    assert resumen["aplicacion.avaluo"].interfaces_divergentes == ("calcular_avaluo",)


def test_informe_detecta_nombres_privados_importados_de_otro_modulo():
    archivos = archivos_validos()
    reemplazar(
        "src/aplicacion/avaluo.py",
        "from dominio.predio import Predio",
        "from dominio.predio import Predio, _validar",
    )(archivos)
    privados = informe(archivos).de_tipo(TipoProblema.IMPORTACION_PRIVADA)
    assert [problema.ubicacion for problema in privados] == ["src/aplicacion/avaluo.py:6"]
    assert privados[0].modulo == "aplicacion.avaluo"


def test_las_pruebas_pueden_importar_nombres_privados():
    archivos = archivos_validos()
    reemplazar(
        "tests/test_avaluo.py",
        "from dominio.predio import Predio",
        "from dominio.predio import Predio, _validar",
    )(archivos)
    assert informe(archivos).de_tipo(TipoProblema.IMPORTACION_PRIVADA) == []


def test_nombres_monetarios():
    assert es_monetario("avaluo_total") and es_monetario("valorM2") and es_monetario("Tarifa")
    assert not es_monetario("area_terreno") and not es_monetario("vigencia")


ENCABEZADO_SIMULACION = (
    "import pytest\n\nfrom aplicacion.avaluo import calcular_avaluo\n"
    "from dominio.predio import Predio\n\n\n"
)


def simuladas(pruebas: str) -> list[str]:
    archivos = archivos_validos() | {"tests/test_simulacion.py": ENCABEZADO_SIMULACION + pruebas}
    informe = analizar_conformidad(archivos, especificacion(), (RF1,))
    return [problema.mensaje for problema in informe.de_tipo(TipoProblema.PRUEBA_SIMULADA)]


@pytest.mark.parametrize(
    "pruebas, esperado",
    [
        (
            "def test_x():\n    predio = Predio('1', 2)\n    predio.zona = 'A'\n",
            "`test_x` le agrega a `predio` el atributo `zona`, que Predio no tiene",
        ),
        # Un ayudante del archivo que devuelve un objeto del módulo cuenta como su fuente.
        (
            "def _predio():\n    predio = Predio('1', 2)\n    return predio\n\n\n"
            "def test_x():\n    predio = _predio()\n    predio.zona = 'A'\n",
            "`test_x` le agrega a `predio` el atributo `zona`",
        ),
        (
            "def test_x():\n    predio = Predio('1', 2)\n"
            "    object.__setattr__(predio, 'zona', 'A')\n",
            "el atributo `zona` con `object.__setattr__`",
        ),
        (
            "def test_x():\n    with pytest.raises(ValueError):\n"
            "        raise ValueError('valor')\n",
            "`test_x` lanza ella misma una excepción dentro de `pytest.raises`",
        ),
    ],
)
def test_detecta_las_pruebas_que_simulan_el_efecto(pruebas, esperado):
    [mensaje] = simuladas(pruebas)
    assert esperado in mensaje
    assert mensaje.startswith("tests/test_simulacion.py:")


@pytest.mark.parametrize(
    "pruebas",
    [
        # Cambiar un campo que la clase tiene, también con object.__setattr__, para probar que
        # el módulo lo vuelve a validar.
        "def test_x():\n    predio = Predio('1', 2)\n    predio.area_terreno = 3\n"
        "    object.__setattr__(predio, 'numero_predial', '')\n",
        # Un objeto que no es del módulo y el monkeypatch de un nombre privado.
        "class Doble:\n    pass\n\n\ndef test_x(monkeypatch):\n    doble = Doble()\n"
        "    doble.zona = 'A'\n    monkeypatch.setattr('aplicacion.avaluo._TARIFA', 1)\n",
        # La excepción la lanza el módulo; la que lanza la función interna no cuenta.
        "def test_x():\n    with pytest.raises(ValueError):\n        def interna():\n"
        "            raise RuntimeError('ayudante')\n\n"
        "        calcular_avaluo(Predio('1', 2), 0)\n",
        # Un raise fuera del bloque pytest.raises.
        "def test_x():\n    if False:\n        raise AssertionError('nunca')\n"
        "    with pytest.raises(ValueError):\n        calcular_avaluo(Predio('1', 2), 0)\n",
    ],
)
def test_no_marca_lo_que_no_simula(pruebas):
    assert simuladas(pruebas) == []


def test_la_verificacion_pide_corregir_la_prueba_que_simula():
    archivos = archivos_validos() | {
        "tests/test_simulacion.py": ENCABEZADO_SIMULACION
        + "def test_x():\n    predio = Predio('1', 2)\n    predio.zona = 'A'\n"
    }
    problemas = verificar(archivos)
    assert any(p.startswith("RF-18 · pruebas: tests/test_simulacion.py:") for p in problemas)


# Métodos como interfaces ----------------------------------------------------------------------

REGISTRO = '''

class RegistroPredios:
    """Predios registrados, por número predial."""

    def __init__(self) -> None:
        """Crea el registro vacío."""
        self._predios: dict[str, Predio] = {}

    def registrar(self, predio: Predio) -> None:
        """Registra un predio."""
        self._predios[predio.numero_predial] = predio

    def consultar(self, numero_predial: str) -> Predio:
        """Devuelve el predio registrado con ese número."""
        return self._predios[numero_predial]
'''


def especificacion_con_metodos() -> EspecificacionDiseno:
    datos = especificacion().model_dump(mode="json")
    datos["modulos"][0]["interfaces_publicas"] += [
        {
            "nombre": "RegistroPredios",
            "tipo": "clase",
            "firma": "RegistroPredios()",
            "descripcion": "Registro de predios",
        },
        {
            "nombre": "RegistroPredios.registrar",
            "tipo": "funcion",
            "firma": "registrar(self, predio: Predio) -> None",
            "descripcion": "Registra un predio",
        },
        {
            "nombre": "RegistroPredios.consultar",
            "tipo": "funcion",
            "firma": "consultar(self, numero_predial: str) -> Predio",
            "descripcion": "Consulta un predio",
        },
    ]
    return EspecificacionDiseno.model_validate(datos)


def con_registro(cambio=None) -> dict[str, str]:
    archivos = archivos_validos()
    archivos["src/dominio/predio.py"] += REGISTRO
    if cambio:
        cambio(archivos)
    return archivos


def problemas_de_metodos(archivos) -> list[str]:
    return verificar_version(archivos, especificacion_con_metodos(), REQUERIMIENTOS)


def test_los_metodos_declarados_se_buscan_en_su_clase():
    assert problemas_de_metodos(con_registro()) == []


@pytest.mark.parametrize(
    ("cambio", "esperado"),
    [
        (
            reemplazar("src/dominio/predio.py", "    def consultar(", "    def buscar("),
            "no define el método consultar(self, numero_predial: str) -> Predio en la clase "
            "RegistroPredios",
        ),
        (
            reemplazar(
                "src/dominio/predio.py", "def registrar(self, predio", "def registrar(self, p"
            ),
            "implementa (self, p: Predio) y la especificación declara (self, predio: Predio)",
        ),
        (
            reemplazar(
                "src/dominio/predio.py",
                "def registrar(self, predio",
                "def registrar(self: object, predio",
            ),
            "RegistroPredios.registrar implementa (self: object, predio: Predio)",
        ),
        (
            reemplazar(
                "src/dominio/predio.py",
                "def consultar(self, numero_predial: str) -> Predio:",
                "def consultar(self, numero_predial: str) -> Predio | None:",
            ),
            "retorna Predio | None y la especificación declara Predio",
        ),
        (
            reemplazar("src/dominio/predio.py", "class RegistroPredios:", "class Registro:"),
            "no define en su nivel superior la clase RegistroPredios del método registrar",
        ),
    ],
)
def test_detecta_los_metodos_que_no_cumplen(cambio, esperado):
    problemas = problemas_de_metodos(con_registro(cambio))
    assert any(esperado in problema for problema in problemas), problemas


def test_sigue_a_los_objetos_que_devuelve_un_metodo():
    pruebas = (
        "from dominio.predio import Predio, RegistroPredios\n\n\n"
        "def test_x():\n    registro = RegistroPredios()\n"
        "    predio = registro.consultar('1')\n    predio.zona = 'A'\n"
    )
    archivos = con_registro() | {"tests/test_registro.py": pruebas}
    informe = analizar_conformidad(archivos, especificacion_con_metodos(), (RF1,))
    [problema] = informe.de_tipo(TipoProblema.PRUEBA_SIMULADA)
    assert "le agrega a `predio` el atributo `zona`, que Predio no tiene" in problema.mensaje
