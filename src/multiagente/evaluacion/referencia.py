"""Oráculo común del paso 15: pruebas de aceptación de referencia (ADR-0019).

Cada caso de `evaluacion/referencia/<caso>/` trae:
- una interfaz neutra (`interfaz.md`);
- sus pruebas (`test_referencia.py`), que verifican solo lo que la ficha dice sin ambigüedad;
- una implementación de control (`control.py`) y unos mutantes (`mutantes.json`), con los que se
  comprueba el oráculo antes de medir.

Una implementación evaluada se conecta con un adaptador: un `adaptador_referencia.py` que traduce
la interfaz neutra a la de la implementación. El adaptador no puede calcular por su cuenta, así que
se rechaza si tiene aritmética o llama a funciones que calculan. Las pruebas corren en el entorno
aislado, aparte de las pruebas propias de la implementación.
"""

import ast
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from multiagente.agentes.tester.analisis import hallazgos_de_ruff
from multiagente.agentes.tester.reglas import cargar_reglas_calidad
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION
from multiagente.sandbox.ejecutor import EntornoAislado, ResultadoPruebas

RAIZ_REFERENCIA = RAIZ_EVALUACION / "referencia"
"""Carpeta de los casos de referencia."""

ADAPTADOR = "src/adaptador_referencia.py"
COMUN = "src/referencia_comun.py"
PRUEBAS = "tests/test_referencia.py"
MARCA_AUSENTE = "referencia_comun.Ausente"
"""Así aparece en el reporte de pytest una verificación que falla por un comportamiento ausente."""

FUNCIONES_QUE_CALCULAN = frozenset({"abs", "divmod", "max", "min", "pow", "round", "sum"})
METODOS_QUE_CALCULAN = frozenset({"quantize", "fma", "sqrt", "exp", "ln", "log10", "scaleb"})
MODULOS_QUE_CALCULAN = frozenset({"math", "cmath", "statistics", "operator", "numpy"})

Resultado = Literal["paso", "fallo", "ausente", "error"]


class ErrorReferencia(ValueError):
    """Un caso de referencia, un mutante o un adaptador no se pueden usar."""


@dataclass(frozen=True)
class Mutante:
    """Variante del control con un defecto a propósito, que las pruebas deben detectar.

    Attributes:
        nombre: Identificador del mutante.
        descripcion: Defecto que introduce.
        codigo: Código del control con el defecto aplicado.
    """

    nombre: str
    descripcion: str
    codigo: str


@dataclass(frozen=True)
class CasoReferencia:
    """Un caso de referencia con su oráculo.

    Attributes:
        id: Identificador del caso, como en la ficha: `caso-ampliada-12`.
        carpeta: Carpeta del caso.
        pruebas: Código de las pruebas de referencia.
        comun: Código del módulo común de las pruebas y los adaptadores.
        control: Implementación de control, que expone la interfaz directamente.
        mutantes: Variantes del control con un defecto cada una.
    """

    id: str
    carpeta: Path
    pruebas: str
    comun: str
    control: str
    mutantes: tuple[Mutante, ...]

    @property
    def verificaciones(self) -> tuple[str, ...]:
        """Nombres de las pruebas de referencia, en el orden del archivo."""
        arbol = ast.parse(self.pruebas)
        return tuple(
            nodo.name
            for nodo in arbol.body
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_")
        )


def aplicar_cambios(texto: str, cambios: list[dict[str, str]]) -> str:
    """Aplica a un texto los cambios de un mutante, cada uno sobre un fragmento único.

    Args:
        texto: Código de partida.
        cambios: Pares `buscar` y `reemplazar`.

    Returns:
        El texto con los cambios.

    Raises:
        ErrorReferencia: Si un fragmento no aparece exactamente una vez.
    """
    for cambio in cambios:
        veces = texto.count(cambio["buscar"])
        if veces != 1:
            raise ErrorReferencia(f"El fragmento aparece {veces} veces: {cambio['buscar']!r}")
        texto = texto.replace(cambio["buscar"], cambio["reemplazar"])
    return texto


def casos_de_referencia(raiz: Path = RAIZ_REFERENCIA) -> list[str]:
    """Identificadores de los casos de referencia, en orden.

    Args:
        raiz: Carpeta de los casos.

    Returns:
        Un identificador por carpeta que trae pruebas de referencia.
    """
    return sorted(
        carpeta.name for carpeta in raiz.iterdir() if (carpeta / "test_referencia.py").is_file()
    )


def cargar_caso_referencia(id_caso: str, raiz: Path = RAIZ_REFERENCIA) -> CasoReferencia:
    """Lee un caso de referencia con su control y sus mutantes.

    Args:
        id_caso: Identificador del caso.
        raiz: Carpeta de los casos.

    Returns:
        El caso, con cada mutante ya aplicado sobre el control.

    Raises:
        ErrorReferencia: Si falta un archivo o un mutante no se puede aplicar.
    """
    carpeta = raiz / id_caso
    try:
        pruebas = (carpeta / "test_referencia.py").read_text(encoding="utf-8")
        control = (carpeta / "control.py").read_text(encoding="utf-8")
        comun = (raiz / "referencia_comun.py").read_text(encoding="utf-8")
        definiciones = json.loads((carpeta / "mutantes.json").read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ErrorReferencia(f"Al caso {id_caso} le falta un archivo: {error.filename}") from error
    mutantes = tuple(
        Mutante(d["nombre"], d["descripcion"], aplicar_cambios(control, d["cambios"]))
        for d in definiciones
    )
    return CasoReferencia(id_caso, carpeta, pruebas, comun, control, mutantes)


def problemas_del_adaptador(codigo: str) -> list[str]:
    """Lo que un adaptador no puede hacer: calcular por su cuenta lo que se evalúa.

    Se admiten conversiones de tipo, comparaciones (para detectar un error que la implementación
    devuelve como valor) y manejo de excepciones. Se rechazan:
    - las operaciones aritméticas, también las de asignación (`+=`);
    - las funciones y los métodos que calculan, como `sum`, `round` o `quantize`;
    - los módulos de cálculo, como `math`.

    Args:
        codigo: Código del adaptador.

    Returns:
        Un problema por construcción prohibida, con su línea; vacío si el adaptador se admite.
    """
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as error:
        return [f"El adaptador no compila: {error}"]
    problemas = []
    for nodo in ast.walk(arbol):
        linea = getattr(nodo, "lineno", 0)
        if isinstance(nodo, ast.BinOp | ast.AugAssign):
            problemas.append(f"línea {linea}: operación aritmética")
        elif isinstance(nodo, ast.Call):
            funcion = nodo.func
            if isinstance(funcion, ast.Name) and funcion.id in FUNCIONES_QUE_CALCULAN:
                problemas.append(f"línea {linea}: llama a {funcion.id}()")
            elif isinstance(funcion, ast.Attribute) and funcion.attr in METODOS_QUE_CALCULAN:
                problemas.append(f"línea {linea}: llama a .{funcion.attr}()")
        elif isinstance(nodo, ast.Import | ast.ImportFrom):
            nombres = (
                [alias.name for alias in nodo.names]
                if isinstance(nodo, ast.Import)
                else [nodo.module or ""]
            )
            for nombre in nombres:
                if nombre.split(".")[0] in MODULOS_QUE_CALCULAN:
                    problemas.append(f"línea {linea}: importa {nombre}")
    return problemas


def archivos_para_referencia(
    caso: CasoReferencia, adaptador: str, implementacion: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Arma los archivos de una ejecución de referencia.

    La implementación entra sin sus pruebas, que se evalúan aparte; el adaptador, el módulo común
    y las pruebas de referencia ocupan rutas propias.

    Args:
        caso: Caso de referencia.
        adaptador: Código del adaptador de la implementación.
        implementacion: Archivos de la implementación por su ruta; sin ellos, el adaptador es la
            implementación misma, como el control y sus mutantes.

    Returns:
        Los archivos por ruta, listos para el entorno aislado.
    """
    archivos = {
        ruta: contenido
        for ruta, contenido in (implementacion or {}).items()
        if not ruta.startswith("tests/") and ruta not in (ADAPTADOR, COMUN)
    }
    archivos[ADAPTADOR] = adaptador
    archivos[COMUN] = caso.comun
    archivos[PRUEBAS] = caso.pruebas
    return archivos


class ResultadoVerificacion(BaseModel):
    """Resultado de una verificación de referencia.

    Attributes:
        nombre: Nombre de la prueba de referencia.
        resultado: `paso`; `fallo`; `ausente` si la implementación no ofrece el comportamiento; o
            `error` si no llegó a ejecutarse o falló al prepararse.
        detalle: El final del reporte de pytest, si no pasó.
    """

    model_config = ConfigDict(frozen=True)

    nombre: str
    resultado: Resultado
    detalle: str = ""


class ResultadoReferencia(BaseModel):
    """Resultado de las pruebas de referencia sobre una implementación.

    Attributes:
        caso: Identificador del caso.
        verificaciones: Una por prueba de referencia, en orden.
        errores_recoleccion: Errores de pytest al recolectar, como un adaptador que no importa.
    """

    model_config = ConfigDict(frozen=True)

    caso: str
    verificaciones: tuple[ResultadoVerificacion, ...]
    errores_recoleccion: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        """Número de verificaciones del caso."""
        return len(self.verificaciones)

    def cuenta(self, resultado: Resultado) -> int:
        """Número de verificaciones con ese resultado.

        Args:
            resultado: Resultado que se cuenta.

        Returns:
            Cuántas verificaciones lo tienen.
        """
        return sum(1 for verificacion in self.verificaciones if verificacion.resultado == resultado)

    @property
    def tasa_errores(self) -> float:
        """Verificaciones que no pasan entre el total: la tasa de errores de referencia."""
        return (self.total - self.cuenta("paso")) / self.total if self.total else 1.0


def clasificar(caso: CasoReferencia, corrida: ResultadoPruebas) -> ResultadoReferencia:
    """Convierte la corrida de pytest en una verificación por prueba de referencia.

    Una prueba que no aparece en la corrida, porque el archivo no se recolectó, cuenta como error.

    Args:
        caso: Caso de referencia.
        corrida: Resultado del entorno aislado.

    Returns:
        El resultado de cada verificación del caso.
    """
    por_nombre = {prueba.nombre: prueba for prueba in corrida.pruebas}
    motivo = " | ".join(corrida.errores_recoleccion)[-2000:] or "no se ejecutó"
    verificaciones = []
    for nombre in caso.verificaciones:
        prueba = por_nombre.get(nombre)
        if prueba is None:
            verificaciones.append(
                ResultadoVerificacion(nombre=nombre, resultado="error", detalle=motivo)
            )
        elif prueba.resultado == "paso":
            verificaciones.append(ResultadoVerificacion(nombre=nombre, resultado="paso"))
        elif MARCA_AUSENTE in prueba.mensaje:
            verificaciones.append(
                ResultadoVerificacion(
                    nombre=nombre, resultado="ausente", detalle=prueba.mensaje[-800:]
                )
            )
        else:
            resultado: Resultado = "fallo" if prueba.resultado == "fallo" else "error"
            verificaciones.append(
                ResultadoVerificacion(
                    nombre=nombre, resultado=resultado, detalle=prueba.mensaje[-800:]
                )
            )
    return ResultadoReferencia(
        caso=caso.id,
        verificaciones=tuple(verificaciones),
        errores_recoleccion=corrida.errores_recoleccion,
    )


def evaluar_referencia(
    entorno: EntornoAislado,
    caso: CasoReferencia,
    adaptador: str,
    implementacion: Mapping[str, str] | None = None,
) -> ResultadoReferencia:
    """Corre las pruebas de referencia de un caso sobre una implementación.

    Args:
        entorno: Entorno aislado donde se ejecutan.
        caso: Caso de referencia.
        adaptador: Código del adaptador de la implementación.
        implementacion: Archivos de la implementación; sin ellos, el adaptador es la implementación.

    Returns:
        El resultado de cada verificación.

    Raises:
        ErrorReferencia: Si el adaptador calcula por su cuenta. El control y sus mutantes no se
            revisan: son implementaciones.
    """
    if implementacion is not None and (problemas := problemas_del_adaptador(adaptador)):
        raise ErrorReferencia("El adaptador no se admite: " + "; ".join(problemas))
    corrida = entorno.probar(archivos_para_referencia(caso, adaptador, implementacion))
    return clasificar(caso, corrida)


class ValidacionOraculo(BaseModel):
    """Comprobación del oráculo de un caso antes de medir.

    Attributes:
        caso: Identificador del caso.
        control: Resultado de las pruebas sobre la implementación de control.
        mutantes: Resultado sobre cada mutante, por su nombre.
    """

    model_config = ConfigDict(frozen=True)

    caso: str
    control: ResultadoReferencia
    mutantes: dict[str, ResultadoReferencia]

    @property
    def mutantes_no_detectados(self) -> list[str]:
        """Mutantes con los que todas las pruebas pasan."""
        return [nombre for nombre, r in self.mutantes.items() if r.cuenta("paso") == r.total]

    @property
    def valido(self) -> bool:
        """Indica si el control pasa todo y cada mutante falla al menos una verificación."""
        control_pasa = self.control.total > 0 and self.control.cuenta("paso") == self.control.total
        return control_pasa and not self.mutantes_no_detectados


def validar_oraculo(entorno: EntornoAislado, caso: CasoReferencia) -> ValidacionOraculo:
    """Corre las pruebas de referencia sobre el control y sobre cada mutante.

    Args:
        entorno: Entorno aislado donde se ejecutan.
        caso: Caso de referencia.

    Returns:
        El resultado sobre el control y sobre cada mutante.
    """
    return ValidacionOraculo(
        caso=caso.id,
        control=evaluar_referencia(entorno, caso, caso.control),
        mutantes={m.nombre: evaluar_referencia(entorno, caso, m.codigo) for m in caso.mutantes},
    )


class PruebasPropias(BaseModel):
    """Las pruebas que trae la implementación, corridas en el entorno aislado.

    Attributes:
        total: Pruebas ejecutadas.
        pasan: Las que pasaron.
        errores_recoleccion: Archivos de prueba que no se pudieron recolectar.
    """

    model_config = ConfigDict(frozen=True)

    total: int
    pasan: int
    errores_recoleccion: int


def pruebas_propias(entorno: EntornoAislado, implementacion: Mapping[str, str]) -> PruebasPropias:
    """Corre las pruebas de la propia implementación, sin las de referencia.

    Args:
        entorno: Entorno aislado donde se ejecutan.
        implementacion: Archivos de la implementación, con sus pruebas en `tests/`.

    Returns:
        Cuántas hay y cuántas pasan.
    """
    corrida = entorno.probar(dict(implementacion))
    return PruebasPropias(
        total=len(corrida.pruebas),
        pasan=sum(1 for prueba in corrida.pruebas if prueba.resultado == "paso"),
        errores_recoleccion=len(corrida.errores_recoleccion),
    )


def hallazgos_estaticos(implementacion: Mapping[str, str]) -> dict[str, int]:
    """Hallazgos de Ruff por severidad, con la configuración del código generado.

    Es el mismo análisis que aplica N12 a las versiones del sistema (CAL-MT-009 y las reglas de
    seguridad de Ruff), y no depende de una especificación de diseño, así que vale igual para los
    tres enfoques.

    Args:
        implementacion: Archivos de la implementación.

    Returns:
        Cuántos hallazgos hay de cada severidad.
    """
    hallazgos = hallazgos_de_ruff(dict(implementacion), cargar_reglas_calidad())
    return dict(Counter(hallazgo.severidad.value for hallazgo in hallazgos))


def leer_implementacion(carpeta: Path) -> dict[str, str]:
    """Lee los archivos de texto de una implementación, con su ruta relativa.

    Args:
        carpeta: Raíz de la implementación, con `src/` y `tests/`.

    Returns:
        El contenido de cada archivo `.py`, `.md`, `.toml`, `.txt`, `.json` o `.csv`.
    """
    extensiones = {".py", ".md", ".toml", ".txt", ".json", ".csv", ".cfg", ".ini"}
    return {
        archivo.relative_to(carpeta).as_posix(): archivo.read_text(encoding="utf-8")
        for archivo in sorted(carpeta.rglob("*"))
        if archivo.is_file()
        and archivo.suffix in extensiones
        and "__pycache__" not in archivo.parts
    }
