"""Conformidad del código generado con su especificación de diseño, leyendo el árbol sintáctico.

Lo usan el desarrollador (N10), para verificar su salida antes de entregarla, y el tester (N12),
para dictaminar la conformidad arquitectónica (RF-22). Así ambos aplican la misma noción de firma
compatible (ADR-0011 y ADR-0012). No ejecuta nada del código.

El informe reúne problemas tipados con un mensaje accionable, sin prefijo de criterio: cada
agente los presenta a su manera. N10 los agrupa por requerimiento (RF-15, RF-17, RF-18) y N12 los
convierte en hallazgos referidos a una regla de calidad.
"""

import ast
import builtins
import copy
import re
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from multiagente.core.esquemas.especificacion_diseno import (
    EspecificacionDiseno,
    InterfazPublica,
    Modulo,
    TipoInterfaz,
    firma_como_funcion,
)
from multiagente.core.esquemas.requerimiento import RequerimientoFormal
from multiagente.sandbox.ejecutor import es_ruta_segura

RUTA_USO = "USO.md"
"""Documento de uso del módulo, en Markdown."""

RUTA_CONFTEST = "tests/conftest.py"
"""Fixtures compartidas de las pruebas; es opcional."""

ARCHIVO_PRUEBA = re.compile(r"^tests/test_[a-z0-9_]+\.py$")
PRUEBA_DE_ESCENARIO = re.compile(r"^test_rf_(\d+)_esc_(\d+)(?:_|$)")

VERSION_PYTHON = (3, 11)
"""Versión mínima del catálogo tecnológico (arq-004) y del RNF-07."""

ESTANDAR = frozenset(sys.stdlib_module_names) | {"__future__"}
"""Módulos de la biblioteca estándar, que no se declaran como dependencia."""

Funcion = ast.FunctionDef | ast.AsyncFunctionDef


class TipoProblema(StrEnum):
    """Clase de incumplimiento de la estructura que declara la especificación."""

    RUTA_INSEGURA = "ruta_insegura"
    MODULO_FALTANTE = "modulo_faltante"
    NO_PREVISTO = "no_previsto"
    SIN_PRUEBAS = "sin_pruebas"
    SIN_USO = "sin_uso"
    SINTAXIS = "sintaxis"
    INTERFAZ = "interfaz"
    EXCEPCION = "excepcion"
    IMPORTACION_RELATIVA = "importacion_relativa"
    IMPORTACION_NO_PERMITIDA = "importacion_no_permitida"
    IMPORTACION_NO_DECLARADA = "importacion_no_declarada"
    IMPORTACION_EXTERNA = "importacion_externa"
    IMPORTACION_PRIVADA = "importacion_privada"
    SIN_DOCSTRING = "sin_docstring"
    ESCENARIO_SIN_PRUEBA = "escenario_sin_prueba"
    PRUEBA_SIN_ESCENARIO = "prueba_sin_escenario"
    PRUEBA_SIMULADA = "prueba_simulada"


@dataclass(frozen=True)
class Problema:
    """Incumplimiento encontrado, con su ubicación y un mensaje que dice cómo corregirlo.

    Attributes:
        tipo: Clase de incumplimiento.
        ruta: Archivo afectado; vacía si el problema es de la versión completa.
        mensaje: Descripción accionable, sin prefijo de criterio.
        linea: Línea del archivo, si aplica.
        modulo: Módulo declarado afectado, si aplica.
    """

    tipo: TipoProblema
    ruta: str
    mensaje: str
    linea: int | None = None
    modulo: str | None = None

    @property
    def ubicacion(self) -> str:
        """Archivo y línea, p. ej. `src/dominio/predio.py:12`."""
        return f"{self.ruta}:{self.linea}" if self.linea else self.ruta


@dataclass(frozen=True)
class ResumenModulo:
    """Conformidad de un módulo declarado (RF-22): existencia, interfaces y dependencias."""

    nombre: str
    ruta: str
    existe: bool
    interfaces_conformes: tuple[str, ...]
    interfaces_divergentes: tuple[str, ...]
    dependencias_no_autorizadas: tuple[str, ...]


@dataclass(frozen=True)
class ArchivoPrueba:
    """Archivo de pruebas con sus funciones y los módulos declarados que importa."""

    ruta: str
    funciones: tuple[str, ...]
    modulos_importados: frozenset[str]


@dataclass(frozen=True)
class InformeConformidad:
    """Resultado del análisis de una versión del módulo contra su especificación.

    Attributes:
        problemas: Incumplimientos encontrados, en orden de archivo.
        modulos: Conformidad de cada módulo declarado.
        pruebas: Archivos de prueba analizados.
        arboles: Árbol sintáctico de cada archivo Python que se pudo analizar.
    """

    problemas: tuple[Problema, ...]
    modulos: tuple[ResumenModulo, ...]
    pruebas: tuple[ArchivoPrueba, ...]
    arboles: dict[str, ast.Module] = field(default_factory=dict, compare=False, repr=False)

    def de_tipo(self, *tipos: TipoProblema) -> list[Problema]:
        """Problemas de los tipos indicados.

        Args:
            *tipos: Tipos de problema buscados.

        Returns:
            Los problemas de esos tipos, en orden.
        """
        return [problema for problema in self.problemas if problema.tipo in tipos]


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


def es_prueba_de(funcion: str, prefijo: str) -> bool:
    """Indica si una función de prueba lleva el prefijo de un escenario o de un requerimiento.

    Args:
        funcion: Nombre de la función de prueba.
        prefijo: Prefijo buscado, p. ej. `test_rf_01_esc_02` o `test_rf_01`.

    Returns:
        True si el nombre es el prefijo o lo continúa tras un guion bajo.
    """
    return funcion == prefijo or funcion.startswith(f"{prefijo}_")


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


def tipo_normalizado(anotacion: ast.expr | None) -> str | None:
    """Anotación en su forma común, para comparar firmas.

    Args:
        anotacion: Nodo de la anotación, o None si no la hay.

    Returns:
        La anotación normalizada como texto, o None.
    """
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
        _Parametro("pos", a.arg, tipo_normalizado(a.annotation), d is not None)
        for a, d in zip(posicionales, defectos, strict=True)
    ][1 if omitir_primero else 0 :]
    if argumentos.vararg is not None:
        vararg = argumentos.vararg
        parametros.append(_Parametro("var", vararg.arg, tipo_normalizado(vararg.annotation), False))
    parametros += [
        _Parametro("solo_nombre", a.arg, tipo_normalizado(a.annotation), d is not None)
        for a, d in zip(argumentos.kwonlyargs, argumentos.kw_defaults, strict=True)
    ]
    if argumentos.kwarg is not None:
        kwarg = argumentos.kwarg
        parametros.append(_Parametro("kw", kwarg.arg, tipo_normalizado(kwarg.annotation), False))
    return parametros


def _compatibles(declarados: list[_Parametro], implementados: list[_Parametro]) -> bool:
    """Una llamada con la firma declarada funciona con la implementada (CAL-AR-002).

    Los parámetros declarados deben estar en el mismo orden, con el mismo nombre, clase y tipo,
    y conservar su valor por defecto. Al final se admiten parámetros adicionales solo si tienen
    valor por defecto, como un campo privado opcional de una dataclass.
    """
    comunes, adicionales = implementados[: len(declarados)], implementados[len(declarados) :]
    if len(comunes) != len(declarados):
        return False
    iguales = all(
        (d.clase, d.nombre, d.tipo) == (i.clase, i.nombre, i.tipo)
        and (i.con_defecto or not d.con_defecto)
        for d, i in zip(declarados, comunes, strict=True)
    )
    return iguales and all(
        parametro.con_defecto and parametro.clase in ("pos", "solo_nombre")
        for parametro in adicionales
    )


def _campos_de_clase(clase: ast.ClassDef) -> list[_Parametro]:
    """Campos anotados de una dataclass o un BaseModel, en orden; omite los ClassVar."""
    campos = []
    for sentencia in clase.body:
        if not (isinstance(sentencia, ast.AnnAssign) and isinstance(sentencia.target, ast.Name)):
            continue
        tipo = tipo_normalizado(sentencia.annotation) or ""
        if tipo.startswith("ClassVar"):
            continue
        campos.append(_Parametro("pos", sentencia.target.id, tipo, sentencia.value is not None))
    return campos


def _firma(parametros: list[_Parametro]) -> str:
    return f"({', '.join(str(parametro) for parametro in parametros)})"


def _funcion_declarada(
    ruta: str, interfaz: InterfazPublica, definiciones: dict[str, ast.stmt]
) -> Funcion | str:
    """Definición de la función o del método que declara la interfaz, o por qué falta."""
    clase, _, metodo = interfaz.nombre.rpartition(".")
    if not clase:
        definicion = definiciones.get(interfaz.nombre)
        if isinstance(definicion, ast.FunctionDef | ast.AsyncFunctionDef):
            return definicion
        return f"{ruta} no define la función {interfaz.firma} en su nivel superior"
    contenedora = definiciones.get(clase)
    if not isinstance(contenedora, ast.ClassDef):
        return f"{ruta} no define en su nivel superior la clase {clase} del método {metodo}"
    for sentencia in contenedora.body:
        if isinstance(sentencia, ast.FunctionDef | ast.AsyncFunctionDef) and (
            sentencia.name == metodo
        ):
            return sentencia
    return f"{ruta} no define el método {interfaz.firma} en la clase {clase}"


def _divergencias_de_interfaz(
    ruta: str, interfaz: InterfazPublica, definiciones: dict[str, ast.stmt]
) -> list[str]:
    ubicacion = f"{ruta}: {interfaz.nombre}"
    try:
        declarada = firma_como_funcion(interfaz)
    except SyntaxError:
        return []  # N9 ya rechaza las firmas inválidas; aquí no hay contra qué comparar.
    esperados = _parametros(declarada)
    if interfaz.tipo is TipoInterfaz.FUNCION:
        definicion = _funcion_declarada(ruta, interfaz, definiciones)
        if isinstance(definicion, str):
            return [definicion]
        implementados = _parametros(definicion)
        divergencias = []
        if not _compatibles(esperados, implementados):
            divergencias.append(
                f"{ubicacion} implementa {_firma(implementados)} y la especificación declara "
                f"{_firma(esperados)}: mismos nombres, orden y tipos"
            )
        if tipo_normalizado(definicion.returns) != tipo_normalizado(declarada.returns):
            divergencias.append(
                f"{ubicacion} retorna {tipo_normalizado(definicion.returns)} y la "
                f"especificación declara {tipo_normalizado(declarada.returns)}"
            )
        return divergencias
    definicion = definiciones.get(interfaz.nombre)
    if not isinstance(definicion, ast.ClassDef):
        return [f"{ruta} no define la clase {interfaz.nombre} en su nivel superior"]
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
        f"el constructor de {ubicacion} recibe {_firma(implementados)} y la especificación "
        f"declara {interfaz.firma}: defínelo con `__init__` o con campos anotados en el mismo "
        "orden"
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


@dataclass(frozen=True)
class _Importacion:
    linea: int
    modulo: str | None
    """Módulo importado; None si la importación es relativa."""
    privados: tuple[str, ...] = ()
    """Nombres con prefijo `_` que se importan del módulo."""


def _importaciones(arbol: ast.Module, declarados: frozenset[str]) -> Iterator[_Importacion]:
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield _Importacion(nodo.lineno, alias.name)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:
                yield _Importacion(nodo.lineno, None)
                continue
            modulo = nodo.module or ""
            # `from dominio import predio` importa el módulo declarado `dominio.predio`.
            submodulos = [
                f"{modulo}.{a.name}" for a in nodo.names if f"{modulo}.{a.name}" in declarados
            ]
            yield from (_Importacion(nodo.lineno, submodulo) for submodulo in submodulos)
            if len(submodulos) < len(nodo.names):
                privados = tuple(
                    a.name
                    for a in nodo.names
                    if a.name.startswith("_") and not a.name.startswith("__")
                )
                yield _Importacion(nodo.lineno, modulo, privados)


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


def funciones_de_prueba(arbol: ast.Module) -> Iterator[Funcion]:
    """Recorre las funciones de prueba de un archivo, también las de clases `Test…`.

    Args:
        arbol: Árbol sintáctico del archivo de pruebas.

    Yields:
        Cada función de nivel superior y cada método de una clase `Test…`.
    """
    for sentencia in arbol.body:
        if isinstance(sentencia, ast.FunctionDef | ast.AsyncFunctionDef):
            yield sentencia
        elif isinstance(sentencia, ast.ClassDef) and sentencia.name.startswith("Test"):
            yield from (
                metodo
                for metodo in sentencia.body
                if isinstance(metodo, ast.FunctionDef | ast.AsyncFunctionDef)
            )


# Pruebas que simulan el efecto ---------------------------------------------------------------
#
# Una prueba que pasa sin que el módulo haga su trabajo no verifica nada (CAL-FS-006). Aquí se
# reconocen en el árbol sintáctico los tres patrones que no admiten otra lectura (ADR-0015):
# inyectar en un objeto del módulo un atributo que su clase no tiene, escribirle atributos
# saltándose sus validaciones y lanzar desde la propia prueba la excepción que espera. Lo demás,
# como reconstruir en la prueba el estado que debía producir el módulo, lo juzga N14.

_DEFINICIONES_ANIDADAS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _atributos_implementados(clase: ast.ClassDef) -> set[str]:
    """Atributos que define una clase: sus campos, sus métodos y lo que asigna sobre `self`."""
    nombres: set[str] = set()
    for sentencia in clase.body:
        if isinstance(sentencia, ast.AnnAssign) and isinstance(sentencia.target, ast.Name):
            nombres.add(sentencia.target.id)
        elif isinstance(sentencia, ast.Assign):
            nombres.update(t.id for t in sentencia.targets if isinstance(t, ast.Name))
        elif isinstance(sentencia, ast.FunctionDef | ast.AsyncFunctionDef):
            nombres.add(sentencia.name)
    for nodo in ast.walk(clase):
        if (
            isinstance(nodo, ast.Attribute)
            and isinstance(nodo.ctx, ast.Store)
            and isinstance(nodo.value, ast.Name)
            and nodo.value.id == "self"
        ):
            nombres.add(nodo.attr)
        elif _es_escritura_forzada(nodo) and len(nodo.args) > 1:
            # `object.__setattr__(self, "campo", …)` en el `__post_init__` de una dataclass.
            if isinstance(nombre := nodo.args[1], ast.Constant) and isinstance(nombre.value, str):
                nombres.add(nombre.value)
    return nombres


def _atributos_de_clases(
    especificacion: EspecificacionDiseno, modulos: Mapping[str, ast.Module]
) -> dict[str, frozenset[str]]:
    """Atributos de cada clase declarada, según su firma, su entidad y su implementación."""
    atributos: dict[str, set[str]] = {}
    for modulo in especificacion.modulos:
        for interfaz in modulo.interfaces_publicas:
            if interfaz.tipo is TipoInterfaz.CLASE:
                try:
                    parametros = _parametros(firma_como_funcion(interfaz))
                except SyntaxError:
                    parametros = []
                atributos.setdefault(interfaz.nombre, set()).update(p.nombre for p in parametros)
    for modulo in especificacion.modulos:
        for interfaz in modulo.interfaces_publicas:
            clase, _, metodo = interfaz.nombre.rpartition(".")
            if clase and interfaz.tipo is TipoInterfaz.FUNCION:
                atributos.setdefault(clase, set()).add(metodo)
    for entidad in especificacion.modelo_datos:
        atributos.setdefault(entidad.nombre, set()).update(c.nombre for c in entidad.campos)
    for arbol in modulos.values():
        for clase in (nodo for nodo in ast.walk(arbol) if isinstance(nodo, ast.ClassDef)):
            if clase.name in atributos:
                atributos[clase.name].update(_atributos_implementados(clase))
    return {clase: frozenset(nombres) for clase, nombres in atributos.items()}


def _retornos_de_clases(
    especificacion: EspecificacionDiseno, clases: Mapping[str, frozenset[str]]
) -> dict[str, str]:
    """Clase declarada que devuelve cada interfaz: la clase misma o el retorno de una función.

    Un método `Clase.metodo` cuenta también por su nombre corto, que es lo que se ve en una
    llamada `objeto.metodo(…)`, salvo que otra interfaz con ese nombre devuelva otra clase.
    """
    retornos = {clase: clase for clase in clases}
    cortos: dict[str, set[str]] = {}
    for modulo in especificacion.modulos:
        for interfaz in modulo.interfaces_publicas:
            if interfaz.tipo is TipoInterfaz.FUNCION:
                try:
                    tipo = tipo_normalizado(firma_como_funcion(interfaz).returns)
                except SyntaxError:
                    continue
                corto = interfaz.nombre.rpartition(".")[2]
                cortos.setdefault(corto, set()).add(tipo or "")
                if tipo in clases:
                    retornos[interfaz.nombre] = tipo
    for corto, tipos in cortos.items():
        if len(tipos) > 1:
            # `objeto.consultar(…)` no dice de qué clase es el método: mejor no seguir al objeto
            # que suponerle una clase que no es.
            retornos.pop(corto, None)
        elif (tipo := next(iter(tipos))) in clases:
            retornos.setdefault(corto, tipo)
    return retornos


def _nodos_propios(funcion: Funcion) -> Iterator[ast.AST]:
    """Nodos del cuerpo de una función, sin entrar en las funciones o clases que define."""
    pendientes = list(ast.iter_child_nodes(funcion))
    while pendientes:
        nodo = pendientes.pop()
        yield nodo
        if not isinstance(nodo, _DEFINICIONES_ANIDADAS):
            pendientes.extend(ast.iter_child_nodes(nodo))


def _llamado(expresion: ast.expr | None) -> str:
    """Nombre de lo que llama una expresión `f(…)` o `m.f(…)`; vacío si no es una llamada."""
    if isinstance(expresion, ast.Call):
        if isinstance(expresion.func, ast.Name):
            return expresion.func.id
        if isinstance(expresion.func, ast.Attribute):
            return expresion.func.attr
    return ""


def _objetos_del_modulo(funcion: Funcion, retornos: Mapping[str, str]) -> dict[str, str]:
    """Variables de la función que guardan un objeto de una clase declarada, con su clase."""
    variables = {}
    for nodo in _nodos_propios(funcion):
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1:
            objetivo, valor = nodo.targets[0], nodo.value
        elif isinstance(nodo, ast.AnnAssign):
            objetivo, valor = nodo.target, nodo.value
        else:
            continue
        if isinstance(objetivo, ast.Name) and (clase := retornos.get(_llamado(valor))):
            variables[objetivo.id] = clase
    return variables


def _es_escritura_forzada(nodo: ast.AST) -> bool:
    """Indica si el nodo es `setattr(…)` u `object.__setattr__(…)`."""
    if not isinstance(nodo, ast.Call):
        return False
    funcion = nodo.func
    return (isinstance(funcion, ast.Name) and funcion.id == "setattr") or (
        isinstance(funcion, ast.Attribute)
        and funcion.attr == "__setattr__"
        and isinstance(funcion.value, ast.Name)
        and funcion.value.id == "object"
    )


def _espera_excepcion(bloque: ast.With | ast.AsyncWith) -> bool:
    """Indica si el bloque es `with pytest.raises(…)`."""
    return any(_llamado(item.context_expr) == "raises" for item in bloque.items)


def _problemas_de_simulacion(
    ruta: str,
    arbol: ast.Module,
    atributos: Mapping[str, frozenset[str]],
    retornos: Mapping[str, str],
) -> Iterator[Problema]:
    """Problemas de un archivo de pruebas que pasan sin que el módulo haga su trabajo."""
    funciones = [
        nodo for nodo in ast.walk(arbol) if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    # Un ayudante del archivo que devuelve un objeto del módulo cuenta como su fuente.
    retornos = dict(retornos)
    for _ in range(2):
        for funcion in funciones:
            variables = _objetos_del_modulo(funcion, retornos)
            for nodo in _nodos_propios(funcion):
                if isinstance(nodo, ast.Return) and nodo.value is not None:
                    valor = nodo.value
                    nombre = valor.id if isinstance(valor, ast.Name) else None
                    clase = variables.get(nombre or "") or retornos.get(_llamado(valor))
                    if clase:
                        retornos[funcion.name] = clase
    for funcion in funciones:
        variables = _objetos_del_modulo(funcion, retornos)
        for nodo in _nodos_propios(funcion):
            if isinstance(nodo, ast.Assign | ast.AugAssign | ast.AnnAssign):
                objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
                for objetivo in objetivos:
                    if not (
                        isinstance(objetivo, ast.Attribute)
                        and isinstance(objetivo.value, ast.Name)
                        and (clase := variables.get(objetivo.value.id))
                        and objetivo.attr not in atributos.get(clase, frozenset())
                    ):
                        continue
                    yield Problema(
                        TipoProblema.PRUEBA_SIMULADA,
                        ruta,
                        f"{ruta}:{nodo.lineno}: `{funcion.name}` le agrega a "
                        f"`{objetivo.value.id}` el atributo `{objetivo.attr}`, que {clase} no "
                        "tiene. Prepara cada situación con las interfaces públicas del módulo, "
                        "sin inyectar datos en sus objetos",
                        nodo.lineno,
                    )
            elif (
                _es_escritura_forzada(nodo)
                and len(nodo.args) > 1
                and isinstance(objeto := nodo.args[0], ast.Name)
                and (clase := variables.get(objeto.id))
                and isinstance(nombre := nodo.args[1], ast.Constant)
                and isinstance(nombre.value, str)
                and nombre.value not in atributos.get(clase, frozenset())
            ):
                # Cambiar con `object.__setattr__` un campo que la clase sí tiene, para probar que
                # el módulo vuelve a validarlo, no simula su efecto.
                yield Problema(
                    TipoProblema.PRUEBA_SIMULADA,
                    ruta,
                    f"{ruta}:{nodo.lineno}: `{funcion.name}` le agrega a `{objeto.id}` el "
                    f"atributo `{nombre.value}` con `{ast.unparse(nodo.func)}`, que {clase} no "
                    "tiene. Prepara cada situación con las interfaces públicas del módulo, sin "
                    "inyectar datos en sus objetos",
                    nodo.lineno,
                )
            elif isinstance(nodo, ast.With | ast.AsyncWith) and _espera_excepcion(nodo):
                for interno in (n for s in nodo.body for n in [s, *_nodos_de(s)]):
                    if isinstance(interno, ast.Raise):
                        yield Problema(
                            TipoProblema.PRUEBA_SIMULADA,
                            ruta,
                            f"{ruta}:{interno.lineno}: `{funcion.name}` lanza ella misma una "
                            "excepción dentro de `pytest.raises`, así que pasa aunque el módulo "
                            "no la lance. Dentro del bloque llama solo a la interfaz del módulo",
                            interno.lineno,
                        )


def _nodos_de(sentencia: ast.stmt) -> Iterator[ast.AST]:
    """Nodos de una sentencia, sin entrar en las funciones o clases que define."""
    if isinstance(sentencia, _DEFINICIONES_ANIDADAS):
        return
    pendientes = list(ast.iter_child_nodes(sentencia))
    while pendientes:
        nodo = pendientes.pop()
        yield nodo
        if not isinstance(nodo, _DEFINICIONES_ANIDADAS):
            pendientes.extend(ast.iter_child_nodes(nodo))


# Análisis ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Permitidos:
    externos: frozenset[str]
    declarados: frozenset[str]
    paquetes_propios: frozenset[str]


def _problemas_de_importacion(
    ruta: str,
    arbol: ast.Module,
    permitidos: _Permitidos,
    internos: frozenset[str] | None,
    modulo: str | None = None,
) -> list[Problema]:
    """Importaciones fuera de lo permitido; `internos` None admite cualquier módulo declarado.

    Los nombres privados importados de otro módulo solo se reportan en los módulos, no en las
    pruebas (CAL-MT-010).
    """
    problemas = []
    for importacion in _importaciones(arbol, permitidos.declarados):
        linea, destino = importacion.linea, importacion.modulo
        ubicacion = f"{ruta}:{linea}"
        if destino is None:
            problemas.append(
                Problema(
                    TipoProblema.IMPORTACION_RELATIVA,
                    ruta,
                    f"{ubicacion} usa una importación relativa; usa la ruta absoluta del "
                    "módulo declarado",
                    linea,
                    modulo,
                )
            )
            continue
        raiz = destino.split(".", 1)[0]
        if destino in permitidos.declarados:
            if internos is not None and destino not in internos:
                problemas.append(
                    Problema(
                        TipoProblema.IMPORTACION_NO_PERMITIDA,
                        ruta,
                        f"{ubicacion} importa {destino}, que no está en sus dependencias "
                        f"permitidas {sorted(internos)}",
                        linea,
                        modulo,
                    )
                )
            if internos is not None and importacion.privados:
                problemas.append(
                    Problema(
                        TipoProblema.IMPORTACION_PRIVADA,
                        ruta,
                        f"{ubicacion} importa los nombres privados {list(importacion.privados)} "
                        f"de {destino}; hazlos públicos o deja la lógica en su módulo",
                        linea,
                        modulo,
                    )
                )
        elif raiz in permitidos.paquetes_propios:
            problemas.append(
                Problema(
                    TipoProblema.IMPORTACION_NO_DECLARADA,
                    ruta,
                    f"{ubicacion} importa {destino}, que no es un módulo declarado en la "
                    "especificación",
                    linea,
                    modulo,
                )
            )
        elif raiz not in ESTANDAR and raiz not in permitidos.externos:
            problemas.append(
                Problema(
                    TipoProblema.IMPORTACION_EXTERNA,
                    ruta,
                    f"{ubicacion} importa {raiz}, que no es de la biblioteca estándar ni una "
                    f"dependencia externa declarada {sorted(permitidos.externos)}",
                    linea,
                    modulo,
                )
            )
    return problemas


def _analizar_modulo(
    modulo: Modulo, arbol: ast.Module, permitidos: _Permitidos
) -> tuple[list[Problema], ResumenModulo]:
    ruta = modulo.ruta
    definiciones = _definiciones(arbol)
    importados = _nombres_importados(arbol)
    problemas: list[Problema] = []
    conformes, divergentes = [], []
    for interfaz in modulo.interfaces_publicas:
        divergencias = _divergencias_de_interfaz(ruta, interfaz, definiciones)
        problemas.extend(
            Problema(TipoProblema.INTERFAZ, ruta, mensaje, modulo=modulo.nombre)
            for mensaje in divergencias
        )
        (divergentes if divergencias else conformes).append(interfaz.nombre)
        for excepcion in interfaz.excepciones:
            nombre = excepcion.strip().rsplit(".", 1)[-1]
            definida = isinstance(definiciones.get(nombre), ast.ClassDef)
            if not (definida or nombre in importados or _es_excepcion_integrada(nombre)):
                problemas.append(
                    Problema(
                        TipoProblema.EXCEPCION,
                        ruta,
                        f"{ruta} no define ni importa la excepción {nombre} que declara "
                        f"{interfaz.nombre}",
                        modulo=modulo.nombre,
                    )
                )
    internos = frozenset(modulo.dependencias_permitidas)
    importacion = _problemas_de_importacion(ruta, arbol, permitidos, internos, modulo.nombre)
    problemas.extend(importacion)
    problemas.extend(
        Problema(
            TipoProblema.SIN_DOCSTRING,
            ruta,
            f"{ruta}:{linea} {nombre} es público y no tiene docstring",
            linea,
            modulo.nombre,
        )
        for linea, nombre in _sin_documentar(arbol)
    )
    no_autorizadas = tuple(
        problema.mensaje
        for problema in importacion
        if problema.tipo is not TipoProblema.IMPORTACION_PRIVADA
    )
    resumen = ResumenModulo(
        nombre=modulo.nombre,
        ruta=ruta,
        existe=True,
        interfaces_conformes=tuple(conformes),
        interfaces_divergentes=tuple(divergentes),
        dependencias_no_autorizadas=no_autorizadas,
    )
    return problemas, resumen


def _problemas_de_escenarios(
    funciones: list[str],
    especificacion: EspecificacionDiseno,
    requerimientos: tuple[RequerimientoFormal, ...],
) -> list[Problema]:
    cubiertos = set(especificacion.requerimientos_cubiertos)
    escenarios = {
        nombre_de_prueba(requerimiento.id_requerimiento, escenario.id): (requerimiento, escenario)
        for requerimiento in requerimientos
        if requerimiento.id_requerimiento in cubiertos
        for escenario in requerimiento.criterios_aceptacion
    }
    problemas = []
    for prefijo, (requerimiento, escenario) in escenarios.items():
        if not any(es_prueba_de(funcion, prefijo) for funcion in funciones):
            nombre = f" «{escenario.nombre}»" if escenario.nombre else ""
            problemas.append(
                Problema(
                    TipoProblema.ESCENARIO_SIN_PRUEBA,
                    "",
                    f"falta una prueba {prefijo}_… para {requerimiento.id_requerimiento} "
                    f"{escenario.id}{nombre}",
                )
            )
    for funcion in funciones:
        if (cita := PRUEBA_DE_ESCENARIO.match(funcion)) and not any(
            es_prueba_de(funcion, prefijo) for prefijo in escenarios
        ):
            problemas.append(
                Problema(
                    TipoProblema.PRUEBA_SIN_ESCENARIO,
                    "",
                    f"{funcion} cita RF-{cita.group(1)} ESC-{cita.group(2)}, que no es un "
                    "escenario de los requerimientos cubiertos",
                )
            )
    return problemas


def _contexto_de_linea(contenido: str, linea: int | None) -> str:
    """La línea con el error y la anterior, con su sangría a la vista, para corregirla."""
    lineas = contenido.splitlines()
    if not linea or not 1 <= linea <= len(lineas):
        return ""
    muestra = [
        f"{numero}: {lineas[numero - 1]!r}" for numero in range(max(1, linea - 1), linea + 1)
    ]
    return f" (líneas {'; '.join(muestra)})"


def analizar_conformidad(
    archivos: Mapping[str, str],
    especificacion: EspecificacionDiseno,
    requerimientos: tuple[RequerimientoFormal, ...],
) -> InformeConformidad:
    """Analiza una versión del módulo contra su especificación, sin ejecutarla.

    Args:
        archivos: Contenido de cada archivo de la versión por su ruta.
        especificacion: Especificación de diseño aprobada en N9.
        requerimientos: Requerimientos aprobados en N6, con sus escenarios.

    Returns:
        Los problemas encontrados, la conformidad de cada módulo y las pruebas analizadas.
    """
    problemas: list[Problema] = []
    modulos = {modulo.ruta: modulo for modulo in especificacion.modulos}
    pruebas = sorted(ruta for ruta in archivos if ARCHIVO_PRUEBA.match(ruta))

    problemas.extend(
        Problema(
            TipoProblema.RUTA_INSEGURA, ruta, f"la ruta {ruta} no es relativa o sale de su carpeta"
        )
        for ruta in sorted(archivos)
        if not es_ruta_segura(ruta)
    )
    problemas.extend(
        Problema(
            TipoProblema.MODULO_FALTANTE,
            ruta,
            f"falta {ruta}, el archivo del módulo {modulos[ruta].nombre}",
            modulo=modulos[ruta].nombre,
        )
        for ruta in sorted(set(modulos) - set(archivos))
    )
    previstos = set(modulos) | set(pruebas) | {RUTA_USO, RUTA_CONFTEST}
    problemas.extend(
        Problema(
            TipoProblema.NO_PREVISTO,
            ruta,
            f"{ruta} no está previsto en la especificación; los módulos van solo en las rutas "
            "declaradas, las pruebas en tests/test_*.py y la documentación en USO.md",
        )
        for ruta in sorted(set(archivos) - previstos)
    )
    if not pruebas:
        problemas.append(
            Problema(TipoProblema.SIN_PRUEBAS, "", "no hay archivos de prueba tests/test_*.py")
        )
    if not archivos.get(RUTA_USO, "").strip():
        problemas.append(
            Problema(TipoProblema.SIN_USO, RUTA_USO, f"falta el documento de uso {RUTA_USO}")
        )

    arboles: dict[str, ast.Module] = {}
    for ruta in sorted(set(archivos) & (set(modulos) | set(pruebas) | {RUTA_CONFTEST})):
        try:
            arboles[ruta] = ast.parse(archivos[ruta], filename=ruta, feature_version=VERSION_PYTHON)
        except SyntaxError as error:
            problemas.append(
                Problema(
                    TipoProblema.SINTAXIS,
                    ruta,
                    f"{ruta}:{error.lineno} no es Python 3.11 válido: {error.msg}"
                    + _contexto_de_linea(archivos[ruta], error.lineno),
                    error.lineno,
                    modulos[ruta].nombre if ruta in modulos else None,
                )
            )

    declarados = frozenset(modulo.nombre for modulo in especificacion.modulos)
    externos = frozenset(
        importacion_de_paquete(dependencia.paquete)
        for dependencia in especificacion.dependencias_externas
    )
    permitidos = _Permitidos(
        externos=externos,
        declarados=declarados,
        paquetes_propios=frozenset(nombre.split(".", 1)[0] for nombre in declarados),
    )
    resumenes = []
    for ruta, modulo in modulos.items():
        if ruta in arboles:
            encontrados, resumen = _analizar_modulo(modulo, arboles[ruta], permitidos)
            problemas.extend(encontrados)
            resumenes.append(resumen)
        else:
            resumenes.append(
                ResumenModulo(
                    nombre=modulo.nombre,
                    ruta=ruta,
                    existe=ruta in archivos,
                    interfaces_conformes=(),
                    interfaces_divergentes=tuple(i.nombre for i in modulo.interfaces_publicas),
                    dependencias_no_autorizadas=(),
                )
            )

    de_pruebas = _Permitidos(
        externos=externos | {"pytest"},
        declarados=declarados,
        paquetes_propios=permitidos.paquetes_propios,
    )
    atributos = _atributos_de_clases(
        especificacion, {ruta: arbol for ruta, arbol in arboles.items() if ruta in modulos}
    )
    retornos = _retornos_de_clases(especificacion, atributos)
    archivos_prueba = []
    for ruta in [*pruebas, RUTA_CONFTEST]:
        if ruta not in arboles:
            continue
        problemas.extend(_problemas_de_importacion(ruta, arboles[ruta], de_pruebas, None))
        problemas.extend(_problemas_de_simulacion(ruta, arboles[ruta], atributos, retornos))
        importados = frozenset(
            importacion.modulo
            for importacion in _importaciones(arboles[ruta], declarados)
            if importacion.modulo in declarados
        )
        archivos_prueba.append(
            ArchivoPrueba(
                ruta=ruta,
                funciones=tuple(f.name for f in funciones_de_prueba(arboles[ruta])),
                modulos_importados=importados,
            )
        )
    funciones = [funcion for archivo in archivos_prueba for funcion in archivo.funciones]
    problemas.extend(_problemas_de_escenarios(funciones, especificacion, requerimientos))
    return InformeConformidad(
        problemas=tuple(problemas),
        modulos=tuple(resumenes),
        pruebas=tuple(archivos_prueba),
        arboles=arboles,
    )
