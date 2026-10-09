"""Verificación estructural de una versión del módulo antes del entorno aislado (N10).

Comprueba, sin ejecutar el código, los criterios de aceptación del desarrollador que pueden
verificarse leyendo el árbol sintáctico (arquitectura, §11):

- RF-15: un archivo Python sintácticamente válido para Python 3.11 por cada módulo declarado,
  sin módulos no previstos, que expone las interfaces públicas de la especificación con firmas
  compatibles y define o importa las excepciones declaradas.
- RF-17: cada módulo importa solo la biblioteca estándar, las dependencias externas declaradas y
  los módulos de sus `dependencias_permitidas`, siempre con importaciones absolutas.
- RF-18: toda función, clase y método público documentado, y al menos una prueba por cada
  escenario de cada requerimiento cubierto, nombrada `test_rf_01_esc_01_…`.

El estilo (RF-16), la ejecución y la conformidad completa los dictamina el tester (N11 a N14).
Los problemas se redactan para que el modelo los corrija en su reintento.
"""

import ast
import builtins
import copy
import re
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from multiagente.core.esquemas.especificacion_diseno import (
    EspecificacionDiseno,
    InterfazPublica,
    Modulo,
    TipoInterfaz,
    firma_como_funcion,
)
from multiagente.orquestador.estado import Requerimientos
from multiagente.sandbox.ejecutor import es_ruta_segura

ARCHIVOS = "RF-15 · archivos"
SINTAXIS = "RF-15 · sintaxis"
INTERFACES = "RF-15 · interfaces"
DEPENDENCIAS = "RF-17 · dependencias"
DOCUMENTACION = "RF-18 · documentación"
PRUEBAS = "RF-18 · pruebas"

RUTA_USO = "USO.md"
"""Documento de uso del módulo, en Markdown."""

RUTA_CONFTEST = "tests/conftest.py"
"""Fixtures compartidas de las pruebas; es opcional."""

ARCHIVO_PRUEBA = re.compile(r"^tests/test_[a-z0-9_]+\.py$")
PRUEBA_DE_ESCENARIO = re.compile(r"^test_rf_(\d+)_esc_(\d+)(?:_|$)")

VERSION_PYTHON = (3, 11)
"""Versión mínima del catálogo tecnológico (arq-004) y del RNF-07."""

Funcion = ast.FunctionDef | ast.AsyncFunctionDef


def nombre_de_prueba(id_requerimiento: str, id_escenario: str) -> str:
    """Prefijo que debe llevar la prueba de un escenario, p. ej. `test_rf_01_esc_02`.

    Args:
        id_requerimiento: Identificador del requerimiento, p. ej. `RF-01`.
        id_escenario: Identificador del escenario, p. ej. `ESC-02`.

    Returns:
        El prefijo del nombre de la función de prueba.
    """
    partes = (id_requerimiento, id_escenario)
    return "test_" + "_".join(parte.lower().replace("-", "_") for parte in partes)


def importacion_de_paquete(paquete: str) -> str:
    """Nombre con que se importa un paquete del catálogo, p. ej. `psycopg[binary]` → `psycopg`.

    Args:
        paquete: Paquete declarado en las dependencias externas.

    Returns:
        El nombre del módulo raíz que importa el código.
    """
    return paquete.split("[", 1)[0].strip().lower().replace("-", "_")


# Firmas --------------------------------------------------------------------------------------


class _NormalizadorTipos(ast.NodeTransformer):
    """Lleva anotaciones equivalentes a una forma común para compararlas.

    `typing.Optional[X]` y `Optional[X]` pasan a `X | None`, `Union[A, B]` a `A | B`, las
    referencias adelantadas entre comillas a su expresión y `decimal.Decimal` a `Decimal`.
    """

    def visit_Constant(self, nodo: ast.Constant) -> ast.AST:
        if isinstance(nodo.value, str):
            try:
                return self.visit(ast.parse(nodo.value, mode="eval").body)
            except SyntaxError:
                return nodo
        return nodo

    def visit_Attribute(self, nodo: ast.Attribute) -> ast.AST:
        return ast.Name(id=nodo.attr, ctx=ast.Load())

    def visit_Subscript(self, nodo: ast.Subscript) -> ast.AST:
        nodo = self.generic_visit(nodo)
        nombre = nodo.value.id if isinstance(nodo.value, ast.Name) else None
        if nombre == "Optional":
            return ast.BinOp(left=nodo.slice, op=ast.BitOr(), right=ast.Constant(None))
        if nombre == "Union":
            miembros = nodo.slice.elts if isinstance(nodo.slice, ast.Tuple) else [nodo.slice]
            union = miembros[0]
            for miembro in miembros[1:]:
                union = ast.BinOp(left=union, op=ast.BitOr(), right=miembro)
            return union
        return nodo


def _tipo(anotacion: ast.expr | None) -> str | None:
    if anotacion is None:
        return None
    return ast.unparse(_NormalizadorTipos().visit(copy.deepcopy(anotacion)))


@dataclass(frozen=True)
class _Parametro:
    clase: str
    nombre: str
    tipo: str | None
    con_defecto: bool

    def __str__(self) -> str:
        prefijo = {"var": "*", "kw": "**"}.get(self.clase, "")
        anotacion = f": {self.tipo}" if self.tipo else ""
        return f"{prefijo}{self.nombre}{anotacion}{' = …' if self.con_defecto else ''}"


def _parametros(funcion: Funcion, omitir_primero: bool = False) -> list[_Parametro]:
    argumentos = funcion.args
    posicionales = [*argumentos.posonlyargs, *argumentos.args]
    defectos = [None] * (len(posicionales) - len(argumentos.defaults)) + argumentos.defaults
    parametros = [
        _Parametro("pos", a.arg, _tipo(a.annotation), d is not None)
        for a, d in zip(posicionales, defectos, strict=True)
    ][1 if omitir_primero else 0 :]
    if argumentos.vararg is not None:
        vararg = argumentos.vararg
        parametros.append(_Parametro("var", vararg.arg, _tipo(vararg.annotation), False))
    parametros += [
        _Parametro("solo_nombre", a.arg, _tipo(a.annotation), d is not None)
        for a, d in zip(argumentos.kwonlyargs, argumentos.kw_defaults, strict=True)
    ]
    if argumentos.kwarg is not None:
        kwarg = argumentos.kwarg
        parametros.append(_Parametro("kw", kwarg.arg, _tipo(kwarg.annotation), False))
    return parametros


def _compatibles(declarados: list[_Parametro], implementados: list[_Parametro]) -> bool:
    if len(declarados) != len(implementados):
        return False
    return all(
        (d.clase, d.nombre, d.tipo) == (i.clase, i.nombre, i.tipo)
        and (i.con_defecto or not d.con_defecto)
        for d, i in zip(declarados, implementados, strict=True)
    )


def _campos_de_clase(clase: ast.ClassDef) -> list[_Parametro]:
    """Campos anotados de una dataclass o un BaseModel, en orden; omite los ClassVar."""
    campos = []
    for sentencia in clase.body:
        if not (isinstance(sentencia, ast.AnnAssign) and isinstance(sentencia.target, ast.Name)):
            continue
        tipo = _tipo(sentencia.annotation) or ""
        if tipo.startswith("ClassVar"):
            continue
        campos.append(_Parametro("pos", sentencia.target.id, tipo, sentencia.value is not None))
    return campos


def _firma(parametros: list[_Parametro]) -> str:
    return f"({', '.join(str(parametro) for parametro in parametros)})"


def _errores_de_interfaz(
    ruta: str, interfaz: InterfazPublica, definiciones: dict[str, ast.stmt]
) -> list[str]:
    ubicacion = f"{ruta}: {interfaz.nombre}"
    try:
        declarada = firma_como_funcion(interfaz)
    except SyntaxError:
        return []  # N9 ya rechaza las firmas inválidas; aquí no hay contra qué comparar.
    esperados = _parametros(declarada)
    definicion = definiciones.get(interfaz.nombre)
    if interfaz.tipo is TipoInterfaz.FUNCION:
        if not isinstance(definicion, ast.FunctionDef | ast.AsyncFunctionDef):
            return [
                f"{INTERFACES}: {ruta} no define la función {interfaz.firma} en su nivel superior"
            ]
        implementados = _parametros(definicion)
        errores = []
        if not _compatibles(esperados, implementados):
            errores.append(
                f"{INTERFACES}: {ubicacion} implementa {_firma(implementados)} y la especificación "
                f"declara {_firma(esperados)}: mismos nombres, orden y tipos"
            )
        if _tipo(definicion.returns) != _tipo(declarada.returns):
            errores.append(
                f"{INTERFACES}: {ubicacion} retorna {_tipo(definicion.returns)} y la "
                f"especificación declara {_tipo(declarada.returns)}"
            )
        return errores
    if not isinstance(definicion, ast.ClassDef):
        return [f"{INTERFACES}: {ruta} no define la clase {interfaz.nombre} en su nivel superior"]
    constructor = next(
        (
            sentencia
            for sentencia in definicion.body
            if isinstance(sentencia, ast.FunctionDef) and sentencia.name == "__init__"
        ),
        None,
    )
    implementados = (
        _parametros(constructor, omitir_primero=True)
        if constructor is not None
        else _campos_de_clase(definicion)
    )
    if _compatibles(esperados, implementados):
        return []
    return [
        f"{INTERFACES}: el constructor de {ubicacion} recibe {_firma(implementados)} y la "
        f"especificación declara {interfaz.firma}: defínelo con `__init__` o con campos "
        "anotados en el mismo orden"
    ]


# Árbol sintáctico ----------------------------------------------------------------------------


def _definiciones(arbol: ast.Module) -> dict[str, ast.stmt]:
    return {
        sentencia.name: sentencia
        for sentencia in arbol.body
        if isinstance(sentencia, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }


def _nombres_importados(arbol: ast.Module) -> set[str]:
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import | ast.ImportFrom):
            nombres.update(alias.asname or alias.name.split(".")[0] for alias in nodo.names)
    return nombres


def _importaciones(arbol: ast.Module, declarados: set[str]) -> Iterator[tuple[int, str | None]]:
    """Recorre las importaciones con su línea y el módulo importado; None si es relativa."""
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield nodo.lineno, alias.name
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:
                yield nodo.lineno, None
                continue
            modulo = nodo.module or ""
            # `from dominio import predio` importa el módulo declarado `dominio.predio`.
            submodulos = [
                f"{modulo}.{a.name}" for a in nodo.names if f"{modulo}.{a.name}" in declarados
            ]
            yield from ((nodo.lineno, submodulo) for submodulo in submodulos)
            if len(submodulos) < len(nodo.names):
                yield nodo.lineno, modulo


def _es_excepcion_integrada(nombre: str) -> bool:
    objeto = getattr(builtins, nombre, None)
    return isinstance(objeto, type) and issubclass(objeto, BaseException)


def _sin_documentar(arbol: ast.Module) -> Iterator[tuple[int, str]]:
    for sentencia in arbol.body:
        if not isinstance(sentencia, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if sentencia.name.startswith("_"):
            continue
        if ast.get_docstring(sentencia) is None:
            yield sentencia.lineno, sentencia.name
        if isinstance(sentencia, ast.ClassDef):
            for metodo in sentencia.body:
                if (
                    isinstance(metodo, ast.FunctionDef | ast.AsyncFunctionDef)
                    and not metodo.name.startswith("_")
                    and ast.get_docstring(metodo) is None
                ):
                    yield metodo.lineno, f"{sentencia.name}.{metodo.name}"


def _funciones_de_prueba(arbol: ast.Module) -> Iterator[str]:
    for sentencia in arbol.body:
        if isinstance(sentencia, ast.FunctionDef | ast.AsyncFunctionDef):
            yield sentencia.name
        elif isinstance(sentencia, ast.ClassDef) and sentencia.name.startswith("Test"):
            yield from (
                metodo.name
                for metodo in sentencia.body
                if isinstance(metodo, ast.FunctionDef | ast.AsyncFunctionDef)
            )


# Verificación --------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Permitidos:
    estandar: frozenset[str]
    externos: frozenset[str]
    declarados: frozenset[str]
    paquetes_propios: frozenset[str]


def _errores_de_importacion(
    ruta: str, arbol: ast.Module, permitidos: _Permitidos, internos: frozenset[str] | None
) -> list[str]:
    """Importaciones fuera de lo permitido; `internos` None admite cualquier módulo declarado."""
    errores = []
    for linea, modulo in _importaciones(arbol, set(permitidos.declarados)):
        if modulo is None:
            errores.append(
                f"{DEPENDENCIAS}: {ruta}:{linea} usa una importación relativa; usa la ruta "
                "absoluta del módulo declarado"
            )
            continue
        raiz = modulo.split(".", 1)[0]
        if modulo in permitidos.declarados:
            if internos is not None and modulo not in internos:
                errores.append(
                    f"{DEPENDENCIAS}: {ruta}:{linea} importa {modulo}, que no está en sus "
                    f"dependencias permitidas {sorted(internos)}"
                )
        elif raiz in permitidos.paquetes_propios:
            errores.append(
                f"{DEPENDENCIAS}: {ruta}:{linea} importa {modulo}, que no es un módulo declarado "
                "en la especificación"
            )
        elif raiz not in permitidos.estandar and raiz not in permitidos.externos:
            errores.append(
                f"{DEPENDENCIAS}: {ruta}:{linea} importa {raiz}, que no es de la biblioteca "
                f"estándar ni una dependencia externa declarada {sorted(permitidos.externos)}"
            )
    return errores


def _errores_de_modulo(modulo: Modulo, arbol: ast.Module, permitidos: _Permitidos) -> list[str]:
    ruta = modulo.ruta
    definiciones = _definiciones(arbol)
    importados = _nombres_importados(arbol)
    errores = []
    for interfaz in modulo.interfaces_publicas:
        errores.extend(_errores_de_interfaz(ruta, interfaz, definiciones))
        for excepcion in interfaz.excepciones:
            nombre = excepcion.strip().rsplit(".", 1)[-1]
            definida = isinstance(definiciones.get(nombre), ast.ClassDef)
            if not (definida or nombre in importados or _es_excepcion_integrada(nombre)):
                errores.append(
                    f"{INTERFACES}: {ruta} no define ni importa la excepción {nombre} que "
                    f"declara {interfaz.nombre}"
                )
    internos = frozenset(modulo.dependencias_permitidas)
    errores.extend(_errores_de_importacion(ruta, arbol, permitidos, internos))
    errores.extend(
        f"{DOCUMENTACION}: {ruta}:{linea} {nombre} es público y no tiene docstring"
        for linea, nombre in _sin_documentar(arbol)
    )
    return errores


def _analizar(ruta: str, contenido: str) -> ast.Module | str:
    try:
        return ast.parse(contenido, filename=ruta, feature_version=VERSION_PYTHON)
    except SyntaxError as error:
        return f"{SINTAXIS}: {ruta}:{error.lineno} no es Python 3.11 válido: {error.msg}"


def verificar_version(
    archivos: Mapping[str, str],
    especificacion: EspecificacionDiseno,
    requerimientos: Requerimientos,
) -> list[str]:
    """Verifica la estructura de una versión del módulo contra su especificación.

    Args:
        archivos: Contenido de cada archivo de la versión por su ruta.
        especificacion: Especificación de diseño aprobada en N9.
        requerimientos: Requerimientos aprobados en N6, con sus escenarios.

    Returns:
        Problemas encontrados, cada uno con el criterio que incumple; vacía si la versión puede
        pasar al tester.
    """
    errores: list[str] = []
    modulos = {modulo.ruta: modulo for modulo in especificacion.modulos}
    pruebas = sorted(ruta for ruta in archivos if ARCHIVO_PRUEBA.match(ruta))

    errores.extend(
        f"{ARCHIVOS}: la ruta {ruta} no es relativa o sale de su carpeta"
        for ruta in sorted(archivos)
        if not es_ruta_segura(ruta)
    )
    errores.extend(
        f"{ARCHIVOS}: falta {ruta}, el archivo del módulo {modulos[ruta].nombre}"
        for ruta in sorted(set(modulos) - set(archivos))
    )
    previstos = set(modulos) | set(pruebas) | {RUTA_USO, RUTA_CONFTEST}
    errores.extend(
        f"{ARCHIVOS}: {ruta} no está previsto en la especificación; los módulos van solo en las "
        "rutas declaradas, las pruebas en tests/test_*.py y la documentación en USO.md"
        for ruta in sorted(set(archivos) - previstos)
    )
    if not pruebas:
        errores.append(f"{ARCHIVOS}: no hay archivos de prueba tests/test_*.py")
    if not archivos.get(RUTA_USO, "").strip():
        errores.append(f"{ARCHIVOS}: falta el documento de uso {RUTA_USO}")

    arboles: dict[str, ast.Module] = {}
    for ruta in sorted(set(archivos) & (set(modulos) | set(pruebas) | {RUTA_CONFTEST})):
        analizado = _analizar(ruta, archivos[ruta])
        if isinstance(analizado, str):
            errores.append(analizado)
        else:
            arboles[ruta] = analizado

    declarados = frozenset(modulo.nombre for modulo in especificacion.modulos)
    externos = frozenset(
        importacion_de_paquete(dependencia.paquete)
        for dependencia in especificacion.dependencias_externas
    )
    permitidos = _Permitidos(
        estandar=frozenset(sys.stdlib_module_names) | {"__future__"},
        externos=externos,
        declarados=declarados,
        paquetes_propios=frozenset(nombre.split(".", 1)[0] for nombre in declarados),
    )
    for ruta, modulo in modulos.items():
        if ruta in arboles:
            errores.extend(_errores_de_modulo(modulo, arboles[ruta], permitidos))

    de_pruebas = _Permitidos(
        estandar=permitidos.estandar,
        externos=externos | {"pytest"},
        declarados=declarados,
        paquetes_propios=permitidos.paquetes_propios,
    )
    funciones: list[str] = []
    for ruta in [*pruebas, RUTA_CONFTEST]:
        if ruta in arboles:
            errores.extend(_errores_de_importacion(ruta, arboles[ruta], de_pruebas, None))
            funciones.extend(_funciones_de_prueba(arboles[ruta]))
    errores.extend(_errores_de_pruebas(funciones, especificacion, requerimientos))
    return errores


def _errores_de_pruebas(
    funciones: list[str], especificacion: EspecificacionDiseno, requerimientos: Requerimientos
) -> list[str]:
    cubiertos = set(especificacion.requerimientos_cubiertos)
    escenarios = {
        nombre_de_prueba(requerimiento.id_requerimiento, escenario.id): (requerimiento, escenario)
        for requerimiento in requerimientos.requerimientos
        if requerimiento.id_requerimiento in cubiertos
        for escenario in requerimiento.criterios_aceptacion
    }
    errores = []
    for prefijo, (requerimiento, escenario) in escenarios.items():
        if not any(f == prefijo or f.startswith(f"{prefijo}_") for f in funciones):
            nombre = f" «{escenario.nombre}»" if escenario.nombre else ""
            errores.append(
                f"{PRUEBAS}: falta una prueba {prefijo}_… para {requerimiento.id_requerimiento} "
                f"{escenario.id}{nombre}"
            )
    for funcion in funciones:
        if (cita := PRUEBA_DE_ESCENARIO.match(funcion)) and not any(
            funcion == prefijo or funcion.startswith(f"{prefijo}_") for prefijo in escenarios
        ):
            errores.append(
                f"{PRUEBAS}: {funcion} cita RF-{cita.group(1)} ESC-{cita.group(2)}, que no es "
                "un escenario de los requerimientos cubiertos"
            )
    return errores
