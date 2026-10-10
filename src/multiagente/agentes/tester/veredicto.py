"""Veredicto del tester (N14, RF-21, RF-24): dictamen por caso, veredicto único y retroalimentación.

Todo lo verificable se decide en código (cal-pg). Cada caso del plan (N16) se asocia a sus
pruebas por nombre (`test_rf_01_esc_02_…`) y no se cumple si:
- no tiene prueba (CAL-FS-001);
- alguna de sus pruebas falla, da error o no se ejecutó (CAL-FS-002);
- sus pruebas no verifican nada, porque no tienen `assert` ni `pytest.raises` (CAL-FS-001).

El modelo solo juzga los casos cuyas pruebas pasaron: si la prueba verifica de verdad el
«entonces» del escenario o lo debilita (CAL-FS-001). El veredicto único sigue la regla de
cal-sv, también en código: se rechaza con algún hallazgo de severidad alta, con algún caso
incumplido o con más hallazgos de severidad media que el umbral configurado.
"""

import ast
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict

from multiagente.agentes.tester.analisis import hallazgo
from multiagente.agentes.tester.contexto import mensaje_contexto
from multiagente.agentes.tester.reglas import ReglaCalidad
from multiagente.agentes.tester.reporte import reporte_validacion
from multiagente.core.conformidad import (
    ARCHIVO_PRUEBA,
    RUTA_CONFTEST,
    es_prueba_de,
    funciones_de_prueba,
    nombre_de_prueba,
)
from multiagente.llm.cliente import ErrorRespuestaModelo
from multiagente.llm.invocador import ErrorValidacionSalida, InvocadorNodo
from multiagente.orquestador.estado import (
    CasoPrueba,
    Contexto,
    EjecucionPruebas,
    Hallazgo,
    PruebaEjecutada,
    ResultadoPrueba,
    Severidad,
    Validacion,
    Veredicto,
    VeredictoCaso,
    VersionCodigo,
)
from multiagente.orquestador.servicios import Dictamen

ORDEN_SEVERIDAD = {Severidad.ALTA: 0, Severidad.MEDIA: 1, Severidad.BAJA: 2}
FALLIDAS = (ResultadoPrueba.FALLO, ResultadoPrueba.ERROR)
LONGITUD_DETALLE = 300
"""Caracteres del mensaje de una prueba fallida que se citan como evidencia."""


_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PruebaFuente:
    """Función de prueba de la versión, con su código y si verifica algo."""

    archivo: str
    nombre: str
    codigo: str
    verifica: bool

    @property
    def identificador(self) -> str:
        """Archivo y nombre, p. ej. `tests/test_avaluo.py::test_rf_01_esc_01`."""
        return f"{self.archivo}::{self.nombre}"


def _verifica(funcion: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """La prueba afirma algo: `assert`, `pytest.raises`, `pytest.fail` o un ayudante `assert…`."""
    for nodo in ast.walk(funcion):
        if isinstance(nodo, ast.Assert):
            return True
        if isinstance(nodo, ast.Call):
            llamada = ast.unparse(nodo.func).rsplit(".", 1)[-1].lstrip("_")
            if llamada in ("raises", "warns", "fail") or llamada.startswith(
                ("assert", "verificar", "comprobar")
            ):
                return True
    return False


def pruebas_fuente(archivos: Mapping[str, str]) -> list[PruebaFuente]:
    """Funciones de prueba de la versión con su código fuente.

    Args:
        archivos: Archivos de la versión; solo se leen los `tests/test_*.py` analizables.

    Returns:
        Las funciones de prueba en orden de archivo y de aparición.
    """
    fuentes = []
    for ruta, texto in sorted(archivos.items()):
        if not ARCHIVO_PRUEBA.match(ruta):
            continue
        try:
            arbol = ast.parse(texto)
        except SyntaxError:
            continue
        fuentes.extend(
            PruebaFuente(
                archivo=ruta,
                nombre=funcion.name,
                codigo=ast.get_source_segment(texto, funcion) or "",
                verifica=_verifica(funcion),
            )
            for funcion in funciones_de_prueba(arbol)
        )
    return fuentes


def _detalle(mensaje: str) -> str:
    """Líneas `E …` de pytest, o la última línea, recortadas para la evidencia."""
    lineas = [linea.strip() for linea in mensaje.splitlines() if linea.strip()]
    errores = [linea.removeprefix("E").strip() for linea in lineas if linea.startswith("E ")]
    texto = " ".join(errores) if errores else (lineas[-1] if lineas else "sin detalle")
    return texto[:LONGITUD_DETALLE]


def _funcion_base(nombre: str) -> str:
    """Nombre de la función de una prueba ejecutada, sin clase ni parámetros."""
    return nombre.rsplit("::", 1)[-1].split("[", 1)[0]


def hallazgos_de_ejecucion(
    ejecucion: EjecucionPruebas, reglas: dict[str, ReglaCalidad]
) -> list[Hallazgo]:
    """Hallazgos de la ejecución en el entorno aislado (CAL-FS-002, CAL-FS-003).

    Args:
        ejecucion: Resultado de N11.
        reglas: Reglas de calidad leídas de la base.

    Returns:
        Un hallazgo por módulo que no se importa, por archivo de prueba que no se recolecta, por
        prueba que falla o da error y por tiempo vencido.
    """
    hallazgos = [
        hallazgo(
            reglas,
            "CAL-FS-003",
            modulo,
            f"El módulo {modulo} no se importa: {_detalle(traza)}",
            "ejecucion",
        )
        for modulo, traza in sorted(ejecucion.errores_importacion.items())
    ]
    hallazgos += [
        hallazgo(
            reglas,
            "CAL-FS-002",
            error.split(":", 1)[0],
            f"El archivo de pruebas no se pudo recolectar: {_detalle(error)}",
            "ejecucion",
        )
        for error in ejecucion.errores_recoleccion
    ]
    hallazgos += [
        hallazgo(
            reglas,
            "CAL-FS-002",
            prueba.identificador,
            f"La prueba termina en {prueba.resultado.value}: {_detalle(prueba.mensaje)}",
            "ejecucion",
        )
        for prueba in ejecucion.pruebas
        if prueba.resultado in FALLIDAS
    ]
    if ejecucion.vencido:
        hallazgos.append(
            hallazgo(
                reglas,
                "CAL-FS-002",
                "tests/",
                "La ejecución superó el tiempo límite del entorno aislado",
                "ejecucion",
            )
        )
    return hallazgos


# Juez -------------------------------------------------------------------------------------------


class JuicioCaso(BaseModel):
    """Juicio del modelo sobre un caso cuyas pruebas pasaron."""

    model_config = ConfigDict(extra="forbid")

    id_caso: str
    cumple: bool
    justificacion: str
    sugerencia: str


class SalidaVeredicto(BaseModel):
    """Salida del juez de N14: un juicio por caso enviado."""

    model_config = ConfigDict(extra="forbid")

    juicios: list[JuicioCaso]


@dataclass(frozen=True)
class CasoPorJuzgar:
    """Caso cuyas pruebas pasaron, con el código de esas pruebas."""

    caso: CasoPrueba
    pruebas: tuple[PruebaFuente, ...]


def mensajes_veredicto(
    casos: list[CasoPorJuzgar], contexto: Contexto, archivos: Mapping[str, str]
) -> list[ChatCompletionMessageParam]:
    """Arma los mensajes de datos del juez: los criterios y los casos con sus pruebas.

    Además del código de cada prueba, el juez recibe completos los archivos de prueba
    implicados y `tests/conftest.py`: el «dado que» suele prepararse en fixtures y constantes
    fuera de la función, y sin verlos el juez rechazaba pruebas correctas.

    Args:
        casos: Casos por juzgar.
        contexto: Contexto acumulado; solo se presentan los criterios de calidad.
        archivos: Archivos de la versión, de los que se toman los de prueba.

    Returns:
        Dos mensajes de datos que acompañan al prompt del veredicto.
    """
    datos = [
        {
            "id_caso": por_juzgar.caso.id,
            "requerimiento": por_juzgar.caso.id_requerimiento,
            "escenario": por_juzgar.caso.id_escenario,
            "dado_que": por_juzgar.caso.dado_que,
            "cuando": por_juzgar.caso.cuando,
            "entonces": por_juzgar.caso.entonces,
            "pruebas": [
                {
                    "identificador": prueba.identificador,
                    "resultado": "paso",
                    "codigo": prueba.codigo,
                }
                for prueba in por_juzgar.pruebas
            ],
        }
        for por_juzgar in casos
    ]
    rutas = {prueba.archivo for por_juzgar in casos for prueba in por_juzgar.pruebas}
    rutas |= {RUTA_CONFTEST} & set(archivos)
    archivos_prueba = [{"ruta": ruta, "contenido": archivos[ruta]} for ruta in sorted(rutas)]
    contenido = json.dumps(
        {"casos": datos, "archivos_prueba": archivos_prueba},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return [mensaje_contexto(contexto), {"role": "user", "content": contenido}]


def validar_juicios(salida: SalidaVeredicto, esperados: set[str]) -> dict[str, JuicioCaso]:
    """Comprueba que el juez dictaminó exactamente los casos enviados, con justificación.

    Args:
        salida: Salida del modelo.
        esperados: Identificadores de los casos enviados.

    Returns:
        El juicio de cada caso por su identificador.

    Raises:
        ErrorValidacionSalida: Si falta, sobra o se repite un caso, si falta una justificación
            o si un caso incumplido no trae sugerencia.
    """
    ids = [juicio.id_caso.strip() for juicio in salida.juicios]
    problemas = []
    if faltantes := sorted(esperados - set(ids)):
        problemas.append(f"Faltan los juicios de los casos {faltantes}")
    if ajenos := sorted(set(ids) - esperados):
        problemas.append(f"Los casos {ajenos} no se enviaron; juzga solo los casos recibidos")
    if repetidos := sorted({i for i in ids if ids.count(i) > 1}):
        problemas.append(f"Los casos {repetidos} tienen más de un juicio")
    for juicio in salida.juicios:
        if not juicio.justificacion.strip():
            problemas.append(f"{juicio.id_caso}: falta la justificación")
        if not juicio.cumple and not juicio.sugerencia.strip():
            problemas.append(f"{juicio.id_caso}: un caso incumplido necesita una sugerencia")
    if problemas:
        raise ErrorValidacionSalida(problemas)
    return {juicio.id_caso.strip(): juicio for juicio in salida.juicios}


# Dictamen ---------------------------------------------------------------------------------------


def _escenario(caso: CasoPrueba) -> str:
    return f"dado que {caso.dado_que}, cuando {caso.cuando}, entonces {caso.entonces}"


def dictaminar_version(
    plan: tuple[CasoPrueba, ...],
    validacion: Validacion,
    contexto: Contexto,
    version: VersionCodigo,
    reglas: dict[str, ReglaCalidad],
    umbral_media: int,
    juez: InvocadorNodo | None,
) -> Dictamen:
    """Dictamina cada caso del plan, aplica la regla de veredicto y arma la retroalimentación.

    Args:
        plan: Casos de prueba de aceptación (N16).
        validacion: Validación con la ejecución (N11) y los hallazgos estáticos (N12).
        contexto: Criterios recuperados en N13, que se presentan al juez.
        version: Versión del módulo, de la que se lee el código de las pruebas.
        reglas: Reglas de calidad leídas de la base.
        umbral_media: Hallazgos de severidad media que se toleran.
        juez: Invocador del modelo que juzga los casos cuyas pruebas pasaron. Sin juez, esos
            casos se dan por cumplidos; solo sirve para probar la parte determinística.

    Returns:
        El dictamen por caso, todos los hallazgos, el veredicto, la retroalimentación y el
        reporte.
    """
    ejecucion = validacion.ejecucion or EjecucionPruebas()
    fuentes = pruebas_fuente(version.archivos)
    hallazgos = [*validacion.hallazgos, *hallazgos_de_ejecucion(ejecucion, reglas)]
    veredictos: dict[str, VeredictoCaso] = {}
    por_juzgar: list[CasoPorJuzgar] = []

    for caso in plan:
        prefijo = nombre_de_prueba(caso.id_requerimiento, caso.id_escenario)
        asociadas = tuple(f for f in fuentes if es_prueba_de(f.nombre, prefijo))
        ids = tuple(prueba.identificador for prueba in asociadas)
        if not asociadas:
            veredictos[caso.id] = VeredictoCaso(
                id_caso=caso.id, cumple=False, evidencia=f"No hay una prueba {prefijo}_…"
            )
            hallazgos.append(
                hallazgo(
                    reglas,
                    "CAL-FS-001",
                    caso.id,
                    f"El escenario {caso.id_requerimiento} {caso.id_escenario} no tiene una "
                    f"prueba {prefijo}_…: {_escenario(caso)}",
                    "veredicto",
                )
            )
            continue
        claves = {(prueba.archivo, prueba.nombre) for prueba in asociadas}
        ejecutadas: list[PruebaEjecutada] = [
            e for e in ejecucion.pruebas if (e.archivo, _funcion_base(e.nombre)) in claves
        ]
        fallidas = [e for e in ejecutadas if e.resultado in FALLIDAS]
        if fallidas:
            primera = fallidas[0]
            evidencia = (
                f"{primera.identificador} termina en {primera.resultado.value}: "
                f"{_detalle(primera.mensaje)}"
            )
            veredictos[caso.id] = VeredictoCaso(
                id_caso=caso.id, cumple=False, evidencia=evidencia, pruebas=ids
            )
            continue
        if not any(e.resultado is ResultadoPrueba.PASO for e in ejecutadas):
            veredictos[caso.id] = VeredictoCaso(
                id_caso=caso.id,
                cumple=False,
                evidencia=f"Sus pruebas no se ejecutaron o se omitieron: {list(ids)}",
                pruebas=ids,
            )
            if not ejecucion.errores_recoleccion and not ejecucion.vencido:
                hallazgos.append(
                    hallazgo(
                        reglas,
                        "CAL-FS-002",
                        caso.id,
                        f"Las pruebas {list(ids)} no se ejecutaron o se omitieron",
                        "veredicto",
                    )
                )
            continue
        if not any(prueba.verifica for prueba in asociadas):
            veredictos[caso.id] = VeredictoCaso(
                id_caso=caso.id,
                cumple=False,
                evidencia=f"{list(ids)} pasan, pero no tienen assert ni pytest.raises",
                pruebas=ids,
            )
            hallazgos.append(
                hallazgo(
                    reglas,
                    "CAL-FS-001",
                    ids[0],
                    f"La prueba no verifica nada del escenario: {_escenario(caso)}",
                    "veredicto",
                )
            )
            continue
        por_juzgar.append(CasoPorJuzgar(caso=caso, pruebas=asociadas))

    juicios = None
    sin_juicio = "sin juicio del modelo"
    if por_juzgar and juez is not None:
        esperados = {item.caso.id for item in por_juzgar}
        try:
            juicios = juez.invocar_validado(
                mensajes_veredicto(por_juzgar, contexto, version.archivos),
                SalidaVeredicto,
                lambda salida: validar_juicios(salida, esperados),
            )
        except (ErrorRespuestaModelo, ErrorValidacionSalida) as error:
            # El juez solo agrega un control sobre pruebas que ya pasan: si no responde, los
            # casos no se bloquean y la persona los revisa en la aprobación final (N17).
            _log.warning("N14: el juez no dio un juicio válido: %s", error)
            sin_juicio = (
                f"sin juicio del modelo: el juez no respondió ({error}); revise este caso en la "
                "aprobación final"
            )
    if juicios is not None:
        for item in por_juzgar:
            juicio = juicios[item.caso.id]
            ids = tuple(prueba.identificador for prueba in item.pruebas)
            veredictos[item.caso.id] = VeredictoCaso(
                id_caso=item.caso.id,
                cumple=juicio.cumple,
                evidencia=f"{list(ids)} pasan. {juicio.justificacion.strip()}",
                pruebas=ids,
            )
            if not juicio.cumple:
                hallazgos.append(
                    hallazgo(
                        reglas,
                        "CAL-FS-001",
                        ids[0],
                        f"La prueba pasa, pero no verifica el escenario ({_escenario(item.caso)}): "
                        f"{juicio.justificacion.strip()}",
                        "juez",
                        sugerencia=juicio.sugerencia.strip(),
                    )
                )
    else:
        for item in por_juzgar:
            ids = tuple(prueba.identificador for prueba in item.pruebas)
            veredictos[item.caso.id] = VeredictoCaso(
                id_caso=item.caso.id,
                cumple=True,
                evidencia=f"{list(ids)} pasan ({sin_juicio})",
                pruebas=ids,
            )

    unicos = {(h.regla, h.ubicacion, h.descripcion): h for h in hallazgos}
    ordenados = tuple(
        sorted(
            unicos.values(),
            key=lambda h: (ORDEN_SEVERIDAD[h.severidad], h.regla, h.ubicacion),
        )
    )
    casos = tuple(veredictos[caso.id] for caso in plan)
    altas = sum(h.severidad is Severidad.ALTA for h in ordenados)
    medias = sum(h.severidad is Severidad.MEDIA for h in ordenados)
    incumplidos = sum(not caso.cumple for caso in casos)
    veredicto = (
        Veredicto.RECHAZADO if altas or incumplidos or medias > umbral_media else Veredicto.APROBADO
    )
    retroalimentacion = (
        tuple(h.como_linea() for h in ordenados) if veredicto is Veredicto.RECHAZADO else ()
    )
    reporte = reporte_validacion(
        version.numero,
        veredicto,
        plan,
        casos,
        ordenados,
        validacion.conformidad,
        validacion.no_evaluadas,
        ejecucion,
        umbral_media,
    )
    return Dictamen(
        veredictos=casos,
        hallazgos=ordenados,
        veredicto=veredicto,
        retroalimentacion=retroalimentacion,
        reporte=reporte,
    )
