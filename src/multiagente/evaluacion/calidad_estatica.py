"""Calidad estática de las implementaciones del objetivo 4 (paso 15, ADR-0019).

Aplica, por igual a los tres enfoques, las reglas de calidad cuya verificación es estática y no
exige especificación ni requerimientos. Las métricas se fijaron en el ADR-0019 antes de calcularlas.
Es una medición exploratoria con detectores aproximados.

Solo lee el código: no lo ejecuta, así que no necesita el entorno aislado, y no llama a ningún
modelo.
"""

import ast
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from multiagente.agentes.tester.analisis import _secretos_embebidos, _usos_de_float_monetario

CARPETA_DE_PRUEBAS = "tests"
PREFIJO_DE_PRUEBA = "test"
RECURSOS = frozenset({"open", "connect", "urlopen", "socket"})
"""Llamadas que abren un recurso externo (CAL-FB-003), con o sin prefijo."""
FECHA_ACTUAL = frozenset({"now", "utcnow", "today"})
"""Atributos que dependen de la fecha actual (CAL-FB-004)."""
GENERADORES = frozenset({"uuid1", "uuid4", "urandom"})
"""Funciones que devuelven un valor distinto en cada llamada (CAL-FB-004)."""
RELOJ = frozenset({"time", "sleep"})
"""Funciones del módulo `time` que dependen del reloj (CAL-FB-004)."""
RECHAZOS_HTTP = range(400, 500)
"""Códigos con los que una prueba espera un rechazo (CAL-FS-004)."""
COMPLEJIDAD = re.compile(r"\((\d+) > 0\)")
"""Valor que Ruff informa en el mensaje de C901 con umbral 0."""


@dataclass(frozen=True)
class Metricas:
    """Métricas de calidad estática de una implementación.

    Attributes:
        usos_float_monetario: Usos de `float` en valores monetarios, en el código (CAL-FS-005).
        credenciales: Credenciales escritas en el código (CAL-SG-001).
        complejidad_media: Complejidad ciclomática media por función, en el código (CAL-MT-003).
        complejidad_maxima: Complejidad ciclomática máxima, en el código (CAL-MT-003).
        nombres_privados: Nombres privados importados de otro módulo, en el código (CAL-MT-010).
        sentencias_global: Sentencias `global`, en el código (CAL-FB-001).
        recursos_sin_with: Aperturas de recursos fuera de la expresión de un `with` (CAL-FB-003).
        no_deterministas: Usos no deterministas en las pruebas (CAL-FB-004).
        pruebas_de_rechazo: Funciones de prueba que esperan un rechazo (CAL-FS-004).
        funciones_de_prueba: Funciones de prueba.
        modulos: Módulos de código, sin `__init__.py`.
        lineas_codigo: Líneas no vacías de código.
        lineas_pruebas: Líneas no vacías de pruebas.
    """

    usos_float_monetario: int
    credenciales: int
    complejidad_media: float
    complejidad_maxima: int
    nombres_privados: int
    sentencias_global: int
    recursos_sin_with: int
    no_deterministas: int
    pruebas_de_rechazo: int
    funciones_de_prueba: int
    modulos: int
    lineas_codigo: int
    lineas_pruebas: int

    @property
    def proporcion_de_rechazo(self) -> float:
        """Proporción de las funciones de prueba que esperan un rechazo, de 0 a 1."""
        if not self.funciones_de_prueba:
            return 0.0
        return self.pruebas_de_rechazo / self.funciones_de_prueba


def leer_archivos(carpeta: Path) -> dict[str, str]:
    """Lee los archivos Python de una implementación.

    Args:
        carpeta: Carpeta del código de la implementación.

    Returns:
        El contenido de cada archivo por su ruta relativa.
    """
    return {
        ruta.relative_to(carpeta).as_posix(): ruta.read_text(encoding="utf-8")
        for ruta in sorted(carpeta.rglob("*.py"))
    }


def es_de_pruebas(ruta: str) -> bool:
    """Indica si un archivo está dentro de la carpeta de pruebas.

    Args:
        ruta: Ruta relativa del archivo.

    Returns:
        Verdadero si alguna carpeta de la ruta es `tests`.
    """
    return CARPETA_DE_PRUEBAS in ruta.split("/")[:-1]


def lineas_no_vacias(texto: str) -> int:
    """Cuenta las líneas con contenido.

    Args:
        texto: Contenido de un archivo.

    Returns:
        Las líneas que no están vacías.
    """
    return sum(bool(linea.strip()) for linea in texto.splitlines())


def contar_sentencias_global(arbol: ast.Module) -> int:
    """Cuenta las sentencias `global` (CAL-FB-001).

    Args:
        arbol: Árbol sintáctico de un archivo.

    Returns:
        Cuántas sentencias `global` tiene.
    """
    return sum(isinstance(nodo, ast.Global) for nodo in ast.walk(arbol))


def contar_nombres_privados(arbol: ast.Module) -> int:
    """Cuenta los nombres con un guion bajo inicial importados de otro módulo (CAL-MT-010).

    Args:
        arbol: Árbol sintáctico de un archivo.

    Returns:
        Cuántos nombres privados importa; no cuenta los que empiezan por dos guiones bajos.
    """
    return sum(
        nombre.name.startswith("_") and not nombre.name.startswith("__")
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom)
        for nombre in nodo.names
    )


def _nombre_de_llamada(llamada: ast.Call) -> str | None:
    """Devuelve el nombre o el atributo final de lo que se llama."""
    if isinstance(llamada.func, ast.Name):
        return llamada.func.id
    if isinstance(llamada.func, ast.Attribute):
        return llamada.func.attr
    return None


def contar_recursos_sin_with(arbol: ast.Module) -> int:
    """Cuenta las aperturas de recursos fuera de la expresión de un `with` (CAL-FB-003).

    Es aproximado: también cuenta una conexión que se cierra con `try` y `finally`.

    Args:
        arbol: Árbol sintáctico de un archivo.

    Returns:
        Cuántas aperturas no están dentro de la expresión de un `with`.
    """
    gestionadas = {
        id(interno)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.With | ast.AsyncWith)
        for item in nodo.items
        for interno in ast.walk(item.context_expr)
    }
    return sum(
        isinstance(nodo, ast.Call)
        and _nombre_de_llamada(nodo) in RECURSOS
        and id(nodo) not in gestionadas
        for nodo in ast.walk(arbol)
    )


def _importados_de(arbol: ast.Module) -> dict[str, str]:
    """Relaciona cada nombre importado con `from` con el módulo del que viene."""
    return {
        nombre.asname or nombre.name: nodo.module
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom) and nodo.module is not None
        for nombre in nodo.names
    }


def _es_no_determinista(llamada: ast.Call, importados: Mapping[str, str]) -> bool:
    """Indica si una llamada depende de la fecha, del reloj o del azar (CAL-FB-004)."""
    funcion = llamada.func
    if isinstance(funcion, ast.Attribute):
        modulo = funcion.value.id if isinstance(funcion.value, ast.Name) else None
        nombre = funcion.attr
    elif isinstance(funcion, ast.Name):
        modulo = importados.get(funcion.id)
        nombre = funcion.id
    else:
        return False
    if nombre in GENERADORES or modulo == "secrets":
        return True
    if modulo == "random":
        return nombre != "seed"
    if modulo == "time":
        return nombre in RELOJ
    return isinstance(funcion, ast.Attribute) and nombre in FECHA_ACTUAL


def contar_no_deterministas(arbol: ast.Module) -> int:
    """Cuenta los usos no deterministas en un archivo de pruebas (CAL-FB-004).

    Args:
        arbol: Árbol sintáctico de un archivo de pruebas.

    Returns:
        Cuántas llamadas dependen de la fecha actual, del reloj o del azar.
    """
    importados = _importados_de(arbol)
    return sum(
        isinstance(nodo, ast.Call) and _es_no_determinista(nodo, importados)
        for nodo in ast.walk(arbol)
    )


def _espera_un_rechazo(funcion: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Indica si una prueba usa `pytest.raises` o compara con un literal de 400 a 499."""
    for nodo in ast.walk(funcion):
        if isinstance(nodo, ast.Call) and _nombre_de_llamada(nodo) == "raises":
            return True
        if isinstance(nodo, ast.Compare):
            for valor in [nodo.left, *nodo.comparators]:
                if isinstance(valor, ast.Constant) and valor.value in RECHAZOS_HTTP:
                    return True
    return False


def _funciones_de_prueba(arbol: ast.Module) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Recorre las funciones cuyo nombre empieza por `test`."""
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef) and nodo.name.startswith(
            PREFIJO_DE_PRUEBA
        ):
            yield nodo


def contar_pruebas(arbol: ast.Module) -> tuple[int, int]:
    """Cuenta las funciones de prueba y las que esperan un rechazo (CAL-FS-004).

    Es aproximado: no ve un rechazo que se exprese con otro valor de retorno.

    Args:
        arbol: Árbol sintáctico de un archivo de pruebas.

    Returns:
        El total de funciones de prueba y cuántas esperan un rechazo.
    """
    funciones = list(_funciones_de_prueba(arbol))
    return len(funciones), sum(_espera_un_rechazo(funcion) for funcion in funciones)


def complejidades(codigo: Mapping[str, str]) -> list[int]:
    """Calcula la complejidad ciclomática de cada función con Ruff C901 y umbral 0 (CAL-MT-003).

    Args:
        codigo: Contenido de cada archivo de código por su ruta relativa.

    Returns:
        La complejidad de cada función.

    Raises:
        RuntimeError: Si Ruff no pudo analizar el código.
    """
    with tempfile.TemporaryDirectory(prefix="calidad-estatica-") as carpeta:
        raiz = Path(carpeta)
        for ruta, contenido in codigo.items():
            destino = raiz / ruta
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(contenido, encoding="utf-8")
        proceso = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--isolated",
                "--select",
                "C901",
                "--config",
                "lint.mccabe.max-complexity = 0",
                "--output-format=json",
                "--no-cache",
                "--exit-zero",
                ".",
            ],
            cwd=raiz,
            capture_output=True,
            text=True,
            check=False,
        )
    if proceso.returncode != 0:
        raise RuntimeError(f"Ruff no pudo analizar el código: {proceso.stderr.strip()}")
    return [
        int(coincidencia.group(1))
        for infraccion in json.loads(proceso.stdout)
        if infraccion["code"] == "C901"
        and (coincidencia := COMPLEJIDAD.search(infraccion["message"]))
    ]


def medir(archivos: Mapping[str, str]) -> Metricas:
    """Calcula las métricas de una implementación.

    Args:
        archivos: Contenido de cada archivo Python por su ruta relativa.

    Returns:
        Las métricas de la implementación.
    """
    codigo = {ruta: texto for ruta, texto in archivos.items() if not es_de_pruebas(ruta)}
    pruebas = {ruta: texto for ruta, texto in archivos.items() if es_de_pruebas(ruta)}
    arboles_codigo = [ast.parse(texto) for texto in codigo.values()]
    arboles_pruebas = [ast.parse(texto) for texto in pruebas.values()]
    conteos = [contar_pruebas(arbol) for arbol in arboles_pruebas]
    valores = complejidades(codigo)
    return Metricas(
        usos_float_monetario=sum(
            sum(1 for _ in _usos_de_float_monetario(arbol)) for arbol in arboles_codigo
        ),
        credenciales=sum(sum(1 for _ in _secretos_embebidos(arbol)) for arbol in arboles_codigo),
        complejidad_media=sum(valores) / len(valores) if valores else 0.0,
        complejidad_maxima=max(valores, default=0),
        nombres_privados=sum(contar_nombres_privados(arbol) for arbol in arboles_codigo),
        sentencias_global=sum(contar_sentencias_global(arbol) for arbol in arboles_codigo),
        recursos_sin_with=sum(contar_recursos_sin_with(arbol) for arbol in arboles_codigo),
        no_deterministas=sum(contar_no_deterministas(arbol) for arbol in arboles_pruebas),
        pruebas_de_rechazo=sum(rechazo for _, rechazo in conteos),
        funciones_de_prueba=sum(total for total, _ in conteos),
        modulos=sum(not ruta.endswith("__init__.py") for ruta in codigo),
        lineas_codigo=sum(lineas_no_vacias(texto) for texto in codigo.values()),
        lineas_pruebas=sum(lineas_no_vacias(texto) for texto in pruebas.values()),
    )
