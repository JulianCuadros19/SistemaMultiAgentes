"""Análisis estático y conformidad arquitectónica de una versión (N12, RF-22, RF-23).

Todo es determinístico y reproducible (cal-pg), sin ejecutar el código:

- **Estilo y seguridad:** Ruff con la configuración del código generado; cada código se reporta
  con la regla que lo verifica.
- **Conformidad:** existencia de los módulos, interfaces, módulos no previstos, dependencias
  internas, externas y nombres privados. Usa el mismo análisis que N10 (`core.conformidad`).
- **Trazabilidad (CAL-AR-005):** cada requerimiento tiene una prueba que lo cita y que importa un
  módulo asignado a él.
- **Dinero (CAL-FS-005):** `float` en nombres monetarios, `float(…)` sobre ellos y `Decimal`
  construido desde un `float`.
- **Secretos (CAL-SG-001):** literales de texto asignados, comparados, pasados como argumento o
  usados como valor por defecto con nombres de secretos en español o inglés. Es el único detector
  de la regla: la configuración del código generado ignora S105, S106 y S107 de Ruff, que solo
  reconoce nombres en inglés y marca cualquier texto, también un mensaje que menciona un token.
  No cuentan los textos en lenguaje natural ni los nombres de variables de entorno, y las pruebas
  no se revisan, porque sus valores son datos de prueba.

Los casos de aceptación, la ejecución y el veredicto son de N14.
"""

import ast
import re
from collections.abc import Iterator

from multiagente.agentes.tester.reglas import (
    EVALUADAS,
    SUGERENCIAS,
    ReglaCalidad,
    regla_de_ruff,
)
from multiagente.core.conformidad import (
    InformeConformidad,
    TipoProblema,
    analizar_conformidad,
    es_prueba_de,
    tipo_normalizado,
)
from multiagente.core.dinero import es_monetario
from multiagente.core.esquemas.especificacion_diseno import EspecificacionDiseno
from multiagente.core.estilo import hallazgos_de_estilo
from multiagente.orquestador.estado import (
    ConformidadModulo,
    Hallazgo,
    Requerimientos,
    VersionCodigo,
)
from multiagente.orquestador.servicios import AnalisisEstatico

REGLA_POR_PROBLEMA: dict[TipoProblema, str] = {
    TipoProblema.MODULO_FALTANTE: "CAL-AR-001",
    TipoProblema.INTERFAZ: "CAL-AR-002",
    TipoProblema.EXCEPCION: "CAL-AR-002",
    TipoProblema.NO_PREVISTO: "CAL-AR-003",
    TipoProblema.RUTA_INSEGURA: "CAL-AR-003",
    TipoProblema.IMPORTACION_EXTERNA: "CAL-AR-004",
    TipoProblema.IMPORTACION_NO_PERMITIDA: "CAL-MT-006",
    TipoProblema.IMPORTACION_NO_DECLARADA: "CAL-MT-006",
    TipoProblema.IMPORTACION_RELATIVA: "CAL-MT-006",
    TipoProblema.IMPORTACION_PRIVADA: "CAL-MT-010",
    TipoProblema.SINTAXIS: "CAL-FS-003",
}
"""Regla de cada problema de conformidad. Los docstrings faltantes los reporta Ruff
(CAL-MT-001) y los escenarios sin prueba, N14 (CAL-FS-001)."""


def hallazgo(
    reglas: dict[str, ReglaCalidad],
    regla: str,
    ubicacion: str,
    descripcion: str,
    origen: str,
    sugerencia: str | None = None,
) -> Hallazgo:
    """Construye un hallazgo con la severidad que declara la regla en la base de conocimiento.

    Args:
        reglas: Reglas de calidad leídas de la base.
        regla: Identificador de la regla, p. ej. `CAL-MT-001`.
        ubicacion: Archivo y línea, módulo o caso afectado.
        descripcion: Qué se encontró.
        origen: Comprobación que lo detectó.
        sugerencia: Cómo corregirlo; si se omite, la sugerencia de la regla.

    Returns:
        El hallazgo, listo para el reporte y la retroalimentación.
    """
    return Hallazgo(
        regla=regla,
        severidad=reglas[regla].severidad,
        ubicacion=ubicacion or "versión completa",
        descripcion=descripcion,
        sugerencia=sugerencia or SUGERENCIAS[regla],
        origen=origen,
    )


def hallazgos_de_ruff(archivos: dict[str, str], reglas: dict[str, ReglaCalidad]) -> list[Hallazgo]:
    """Hallazgos de estilo y seguridad de Ruff, cada uno con su regla.

    Los errores de sintaxis no se reportan aquí: los cubre la conformidad (CAL-FS-003).

    Args:
        archivos: Archivos de la versión.
        reglas: Reglas de calidad leídas de la base.

    Returns:
        Un hallazgo por infracción.
    """
    return [
        hallazgo(
            reglas,
            regla_de_ruff(infraccion.codigo),
            f"{infraccion.archivo}:{infraccion.linea}",
            f"{infraccion.codigo}: {infraccion.mensaje}",
            f"ruff:{infraccion.codigo}",
        )
        for infraccion in hallazgos_de_estilo(archivos)
        if infraccion.codigo != "sintaxis"
    ]


def hallazgos_de_conformidad(
    informe: InformeConformidad, reglas: dict[str, ReglaCalidad]
) -> list[Hallazgo]:
    """Hallazgos de conformidad arquitectónica del informe compartido con N10.

    Args:
        informe: Análisis de la versión contra la especificación.
        reglas: Reglas de calidad leídas de la base.

    Returns:
        Un hallazgo por problema con regla asignada.
    """
    return [
        hallazgo(
            reglas,
            REGLA_POR_PROBLEMA[problema.tipo],
            problema.ubicacion,
            problema.mensaje,
            "conformidad",
        )
        for problema in informe.problemas
        if problema.tipo in REGLA_POR_PROBLEMA
    ]


def hallazgos_de_trazabilidad(
    informe: InformeConformidad,
    especificacion: EspecificacionDiseno,
    reglas: dict[str, ReglaCalidad],
) -> list[Hallazgo]:
    """Requerimientos sin una prueba que los cite e importe un módulo asignado (CAL-AR-005).

    Args:
        informe: Análisis de la versión, con las pruebas y los módulos que importan.
        especificacion: Especificación aprobada, con los requerimientos de cada módulo.
        reglas: Reglas de calidad leídas de la base.

    Returns:
        Un hallazgo por requerimiento sin trazabilidad a una prueba.
    """
    hallazgos = []
    for requerimiento in especificacion.requerimientos_cubiertos:
        asignados = {m.nombre for m in especificacion.modulos if requerimiento in m.requerimientos}
        prefijo = "test_" + requerimiento.lower().replace("-", "_")
        trazado = any(
            archivo.modulos_importados & asignados
            and any(es_prueba_de(funcion, prefijo) for funcion in archivo.funciones)
            for archivo in informe.pruebas
        )
        if not trazado:
            hallazgos.append(
                hallazgo(
                    reglas,
                    "CAL-AR-005",
                    requerimiento,
                    f"Ninguna prueba {prefijo}_… importa un módulo asignado a {requerimiento} "
                    f"({sorted(asignados)})",
                    "conformidad",
                )
            )
    return hallazgos


SECRETO = re.compile(
    r"contrase[nñ]a|password|passwd|pwd|secret|token|credencial|api_?key"
    r"|clave_?(?:acceso|secreta|privada|api)",
    re.IGNORECASE,
)
"""Nombres que delatan un secreto. «clave» sola no cuenta: en el dominio es también la llave de
un diccionario o la clave catastral."""

VARIABLE_DE_ENTORNO = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+")
"""Nombre de una variable de entorno, como `NOTION_TOKEN`: dice dónde vive el secreto."""


def es_valor_secreto(valor: str) -> bool:
    """Indica si un literal asignado a un nombre de secreto puede ser el secreto mismo.

    No lo es un texto vacío, un texto en lenguaje natural (con espacios), como un mensaje de
    error que menciona el token, ni el nombre de una variable de entorno.

    Args:
        valor: Contenido del literal de texto.

    Returns:
        True si el valor tiene forma de credencial.
    """
    valor = valor.strip()
    return bool(valor) and not re.search(r"\s", valor) and not VARIABLE_DE_ENTORNO.fullmatch(valor)


def _texto(nodo: ast.expr | None) -> str | None:
    """Contenido del nodo si es un literal de texto; None en otro caso."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    return None


def _literales_con_nombre(arbol: ast.Module) -> Iterator[tuple[int, str, str]]:
    """Recorre cada literal de texto con el nombre que lo recibe o con el que se compara.

    Cubre asignaciones, asignaciones anotadas, argumentos por nombre, valores por defecto de
    parámetros y comparaciones de igualdad, en cualquier orden.

    Yields:
        La línea, el nombre y el valor del literal.
    """
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign) and (valor := _texto(nodo.value)) is not None:
            for destino in nodo.targets:
                yield nodo.lineno, ast.unparse(destino), valor
        elif isinstance(nodo, ast.AnnAssign) and (valor := _texto(nodo.value)) is not None:
            yield nodo.lineno, ast.unparse(nodo.target), valor
        elif isinstance(nodo, ast.keyword) and nodo.arg is not None:
            if (valor := _texto(nodo.value)) is not None:
                yield nodo.lineno, nodo.arg, valor
        elif isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            argumentos = nodo.args
            posicionales = [*argumentos.posonlyargs, *argumentos.args]
            con_defecto = posicionales[len(posicionales) - len(argumentos.defaults) :]
            pares = [
                *zip(con_defecto, argumentos.defaults, strict=True),
                *zip(argumentos.kwonlyargs, argumentos.kw_defaults, strict=True),
            ]
            for argumento, defecto in pares:
                if (valor := _texto(defecto)) is not None:
                    yield argumento.lineno, argumento.arg, valor
        elif isinstance(nodo, ast.Compare):
            operandos = [nodo.left, *nodo.comparators]
            for operador, izquierda, derecha in zip(
                nodo.ops, operandos[:-1], operandos[1:], strict=True
            ):
                if not isinstance(operador, ast.Eq | ast.NotEq):
                    continue
                for nombre, literal in ((izquierda, derecha), (derecha, izquierda)):
                    if _texto(nombre) is None and (valor := _texto(literal)) is not None:
                        yield nodo.lineno, ast.unparse(nombre), valor


def _secretos_embebidos(arbol: ast.Module) -> Iterator[tuple[int, str]]:
    """Recorre los literales con forma de credencial que recibe un nombre de secreto."""
    for linea, nombre, valor in _literales_con_nombre(arbol):
        if SECRETO.search(nombre) and es_valor_secreto(valor):
            yield linea, f"{nombre} recibe un secreto literal"


def hallazgos_de_secretos(
    informe: InformeConformidad, reglas: dict[str, ReglaCalidad]
) -> list[Hallazgo]:
    """Secretos escritos en el código con nombres en español o inglés (CAL-SG-001).

    Es el único detector de la regla (Ruff ignora S105, S106 y S107). Las pruebas no se revisan:
    sus valores, como el token de una configuración de prueba, son datos inventados, y marcarlos
    empuja al desarrollador a retorcer las pruebas para esquivar la regla.

    La evidencia no reproduce el valor detectado, como pide la regla.

    Args:
        informe: Análisis de la versión, con el árbol de cada archivo.
        reglas: Reglas de calidad leídas de la base.

    Returns:
        Un hallazgo por secreto detectado.
    """
    return [
        hallazgo(
            reglas, "CAL-SG-001", f"{ruta}:{linea}", f"Credencial embebida: {detalle}", "secretos"
        )
        for ruta, arbol in sorted(informe.arboles.items())
        if not ruta.startswith("tests/")
        for linea, detalle in _secretos_embebidos(arbol)
    ]


def _usos_de_float_monetario(arbol: ast.Module) -> Iterator[tuple[int, str]]:
    """Recorre los usos de `float` en dinero: anotaciones, conversiones, literales y Decimal."""
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
            argumentos = nodo.args
            for argumento in [*argumentos.posonlyargs, *argumentos.args, *argumentos.kwonlyargs]:
                if tipo_normalizado(argumento.annotation) == "float" and es_monetario(
                    argumento.arg
                ):
                    yield nodo.lineno, f"el parámetro {argumento.arg} de {nodo.name} usa float"
            if tipo_normalizado(nodo.returns) == "float" and es_monetario(nodo.name):
                yield nodo.lineno, f"{nodo.name} retorna float"
        elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            if tipo_normalizado(nodo.annotation) == "float" and es_monetario(nodo.target.id):
                yield nodo.lineno, f"{nodo.target.id} se declara float"
        elif isinstance(nodo, ast.Assign):
            literal = isinstance(nodo.value, ast.Constant) and isinstance(nodo.value.value, float)
            for destino in nodo.targets:
                if literal and isinstance(destino, ast.Name) and es_monetario(destino.id):
                    yield nodo.lineno, f"{destino.id} recibe el literal float {nodo.value.value}"
        elif isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name):
            nombres = [ast.unparse(argumento) for argumento in nodo.args]
            if nodo.func.id == "float" and any(es_monetario(nombre) for nombre in nombres):
                yield nodo.lineno, f"convierte a float {', '.join(nombres)}"
            if nodo.func.id == "Decimal" and any(
                isinstance(a, ast.Constant) and isinstance(a.value, float) for a in nodo.args
            ):
                yield nodo.lineno, f"construye Decimal desde un float: {ast.unparse(nodo)}"


def hallazgos_de_dinero(
    informe: InformeConformidad,
    especificacion: EspecificacionDiseno,
    reglas: dict[str, ReglaCalidad],
) -> list[Hallazgo]:
    """Usos de punto flotante en valores monetarios o avalúos en los módulos (CAL-FS-005).

    Args:
        informe: Análisis de la versión, con el árbol de cada archivo.
        especificacion: Especificación aprobada; solo se revisan sus módulos.
        reglas: Reglas de calidad leídas de la base.

    Returns:
        Un hallazgo por uso detectado.
    """
    hallazgos = []
    for modulo in especificacion.modulos:
        if (arbol := informe.arboles.get(modulo.ruta)) is None:
            continue
        for linea, detalle in _usos_de_float_monetario(arbol):
            hallazgos.append(
                hallazgo(
                    reglas,
                    "CAL-FS-005",
                    f"{modulo.ruta}:{linea}",
                    f"Cálculo monetario con punto flotante: {detalle}",
                    "dinero",
                )
            )
    return hallazgos


def analizar_version(
    version: VersionCodigo,
    especificacion: EspecificacionDiseno,
    requerimientos: Requerimientos,
    reglas: dict[str, ReglaCalidad],
) -> AnalisisEstatico:
    """Aplica el análisis estático y la conformidad arquitectónica a una versión.

    Args:
        version: Versión del módulo.
        especificacion: Especificación aprobada en N9.
        requerimientos: Requerimientos aprobados en N6.
        reglas: Reglas de calidad leídas de la base.

    Returns:
        Los hallazgos por regla, la conformidad de cada módulo y las reglas no evaluadas.
    """
    informe = analizar_conformidad(version.archivos, especificacion, requerimientos.requerimientos)
    hallazgos = [
        *hallazgos_de_ruff(version.archivos, reglas),
        *hallazgos_de_conformidad(informe, reglas),
        *hallazgos_de_trazabilidad(informe, especificacion, reglas),
        *hallazgos_de_dinero(informe, especificacion, reglas),
        *hallazgos_de_secretos(informe, reglas),
    ]
    conformidad = tuple(
        ConformidadModulo(
            modulo=resumen.nombre,
            ruta=resumen.ruta,
            existe=resumen.existe,
            interfaces_conformes=resumen.interfaces_conformes,
            interfaces_divergentes=resumen.interfaces_divergentes,
            dependencias_no_autorizadas=resumen.dependencias_no_autorizadas,
        )
        for resumen in informe.modulos
    )
    return AnalisisEstatico(
        hallazgos=tuple(hallazgos),
        conformidad=conformidad,
        no_evaluadas=tuple(sorted(set(reglas) - EVALUADAS)),
    )
