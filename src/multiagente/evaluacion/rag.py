"""Métricas RAGs del paso 15, sobre las sesiones guardadas (Tabla 14 de la tesis, ADR-0019).

Por sesión y por agente que consultó una base de conocimiento se arma una muestra:
- **la consulta:** lo que el agente debía resolver;
- **los fragmentos recuperados,** de cada colección, que el estado guarda en `Contexto.fragmentos`;
- **las demás entradas** del agente;
- **el artefacto** que produjo con ellos.

Por agente:
- **Elicitador** (`elicitacion` y `dominio_negocio`):
  - consulta: la necesidad;
  - entradas: la conversación;
  - artefacto: los requerimientos.
- **Arquitecto** (`arquitecturas_referencia`):
  - consulta y entradas: los requerimientos aprobados;
  - artefacto: el registro de decisión y la especificación.
- **Tester** (`criterios_calidad`):
  - consulta: el plan de pruebas;
  - entradas: el plan y el código validado;
  - artefacto: el reporte de validación.

El elicitador produce un solo artefacto con sus dos colecciones: se juzga una vez, con los
fragmentos de ambas marcados por colección.

**El juez.** Es externo al sistema, con su prompt en `evaluacion/juez_rag.md`. Hace tres cosas:
- descompone el artefacto en afirmaciones y dice cuáles se sustentan en el contexto;
- propone tres preguntas que el artefacto responde;
- marca cada fragmento como necesario o no.

**Las métricas,** calculadas con ese juicio:
- **fidelidad:** las afirmaciones sustentadas entre el total. Se calcula por agente;
- **relevancia de la respuesta:** la similitud media entre la consulta y las preguntas propuestas,
  con BGE-M3, como en RAGs. Se calcula por agente;
- **relevancia del contexto:** los fragmentos necesarios entre los recuperados. Se calcula por
  colección.
"""

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import mean

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ConfigDict

from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION
from multiagente.interfaces.documentos import especificacion_md, requerimientos_md
from multiagente.llm.invocador import ErrorValidacionSalida, InvocadorNodo
from multiagente.orquestador.estado import EstadoGrafo, FragmentoContexto
from multiagente.rag.embeddings import Vectorizador

RUTA_PROMPT = RAIZ_EVALUACION / "juez_rag.md"
"""Prompt del juez de las métricas RAGs."""

NODO_JUEZ = "juez_rag"
AGENTE_DE_COLECCION = {
    "elicitacion": "elicitador",
    "dominio_negocio": "elicitador",
    "arquitecturas_referencia": "arquitecto",
    "criterios_calidad": "tester",
}
"""Agente que consulta cada colección."""

AGENTES = ("elicitador", "arquitecto", "tester")
LIMITE_TEXTO = 40_000
"""Caracteres que se envían al juez de cada entrada y del artefacto, para acotar el costo."""

PREGUNTAS = 3


@dataclass(frozen=True)
class FragmentoRecuperado:
    """Un fragmento recuperado, con la colección de la que salió.

    Attributes:
        coleccion: Colección de la base de conocimiento.
        fragmento: El fragmento, con su fuente y su contenido.
    """

    coleccion: str
    fragmento: FragmentoContexto


@dataclass(frozen=True)
class MuestraRag:
    """Lo que recibió y produjo un agente con sus colecciones, en una sesión.

    Attributes:
        sesion: Identificador de la sesión.
        agente: Agente que consultó las colecciones.
        consulta: Lo que el agente debía resolver.
        fragmentos: Fragmentos recuperados, con su colección, en orden.
        entradas: Lo demás que recibió el agente.
        artefacto: Lo que produjo.
    """

    sesion: str
    agente: str
    consulta: str
    fragmentos: tuple[FragmentoRecuperado, ...]
    entradas: str
    artefacto: str

    @property
    def colecciones(self) -> list[str]:
        """Colecciones de la muestra, en el orden en que aparecen sus fragmentos."""
        return list(dict.fromkeys(recuperado.coleccion for recuperado in self.fragmentos))

    @property
    def identificadores(self) -> list[str]:
        """Identificadores con que el juez recibe los fragmentos, F1, F2 y siguientes."""
        return [f"F{numero}" for numero in range(1, len(self.fragmentos) + 1)]


def _recortar(texto: str) -> str:
    return texto if len(texto) <= LIMITE_TEXTO else texto[:LIMITE_TEXTO] + "\n[…recortado]"


def _requerimientos(estado: EstadoGrafo) -> str:
    requerimientos = estado["requerimientos"]
    return requerimientos_md(
        requerimientos.historias, requerimientos.requerimientos, requerimientos.referencias
    )


def _conversacion(estado: EstadoGrafo) -> str:
    return "\n".join(
        f"{turno.emisor.value}: {turno.texto}" for turno in estado["conversacion"].turnos
    )


def _plan(estado: EstadoGrafo) -> str:
    return "\n".join(
        f"{caso.id}: dado que {caso.dado_que}, cuando {caso.cuando}, entonces {caso.entonces}"
        for caso in estado["validacion"].plan_pruebas
    )


def _codigo(estado: EstadoGrafo) -> str:
    vigente = estado["codigo"].vigente
    if vigente is None:
        return ""
    return "\n\n".join(
        f"# {ruta}\n{contenido}" for ruta, contenido in sorted(vigente.archivos.items())
    )


def _partes(agente: str, estado: EstadoGrafo) -> tuple[str, str, str] | None:
    """Consulta, entradas y artefacto del agente, o None si el agente no produjo su artefacto."""
    if agente == "elicitador":
        if not estado["requerimientos"].requerimientos:
            return None
        necesidad = estado["conversacion"].necesidad or estado.get("necesidad", "")
        return necesidad, _conversacion(estado), _requerimientos(estado)
    if agente == "arquitecto":
        arquitectura = estado["arquitectura"]
        if arquitectura.especificacion is None:
            return None
        artefacto = (
            (arquitectura.registro_decision or "")
            + "\n\n"
            + especificacion_md(arquitectura.especificacion, arquitectura.recorridos)
        )
        return _requerimientos(estado), _requerimientos(estado), artefacto
    validacion = estado["validacion"]
    if not validacion.reporte:
        return None
    plan = _plan(estado)
    return plan, f"{plan}\n\n{_codigo(estado)}", validacion.reporte


def muestras_de_sesion(sesion: str, estado: EstadoGrafo) -> list[MuestraRag]:
    """Una muestra por agente que consultó una colección y produjo su artefacto.

    Args:
        sesion: Identificador de la sesión.
        estado: Estado final de la sesión.

    Returns:
        Las muestras del elicitador, del arquitecto y del tester, las que haya.
    """
    contexto = estado.get("contexto")
    if contexto is None:
        return []
    muestras = []
    for agente in AGENTES:
        recuperados = tuple(
            FragmentoRecuperado(coleccion, fragmento)
            for coleccion, fragmentos in contexto.fragmentos.items()
            if AGENTE_DE_COLECCION.get(coleccion) == agente
            for fragmento in fragmentos
        )
        if not recuperados or (partes := _partes(agente, estado)) is None:
            continue
        consulta, entradas, artefacto = partes
        muestras.append(MuestraRag(sesion, agente, consulta, recuperados, entradas, artefacto))
    return muestras


class AfirmacionJuzgada(BaseModel):
    """Una afirmación del artefacto y si se sustenta en el contexto."""

    model_config = ConfigDict(extra="forbid")

    texto: str
    sustentada: bool
    fuente: str


class FragmentoJuzgado(BaseModel):
    """Si un fragmento recuperado era necesario para el artefacto."""

    model_config = ConfigDict(extra="forbid")

    id: str
    necesario: bool


class SalidaJuezRag(BaseModel):
    """Salida del juez de las métricas RAGs."""

    model_config = ConfigDict(extra="forbid")

    afirmaciones: list[AfirmacionJuzgada]
    preguntas: list[str]
    fragmentos: list[FragmentoJuzgado]


def mensajes_juez(muestra: MuestraRag) -> list[ChatCompletionMessageParam]:
    """Mensaje de datos del juez para una muestra.

    Args:
        muestra: Muestra de la sesión.

    Returns:
        Un mensaje con las colecciones, la consulta, los fragmentos, las entradas y el artefacto.
    """
    datos = {
        "coleccion": ", ".join(muestra.colecciones),
        "consulta": _recortar(muestra.consulta),
        "fragmentos": [
            {
                "id": id_fragmento,
                "coleccion": recuperado.coleccion,
                "fuente": recuperado.fragmento.referencia,
                "contenido": recuperado.fragmento.contenido,
            }
            for id_fragmento, recuperado in zip(
                muestra.identificadores, muestra.fragmentos, strict=True
            )
        ],
        "entradas": _recortar(muestra.entradas),
        "artefacto": _recortar(muestra.artefacto),
    }
    return [{"role": "user", "content": json.dumps(datos, ensure_ascii=False)}]


def validador(muestra: MuestraRag) -> Callable[[SalidaJuezRag], SalidaJuezRag]:
    """Valida la salida del juez contra la muestra: los fragmentos y las preguntas esperados.

    Args:
        muestra: Muestra de la sesión.

    Returns:
        Una función que devuelve la salida si es válida o lanza `ErrorValidacionSalida`.
    """
    esperados = muestra.identificadores

    def validar(salida: SalidaJuezRag) -> SalidaJuezRag:
        problemas = []
        juzgados = [fragmento.id for fragmento in salida.fragmentos]
        if sorted(juzgados) != sorted(esperados):
            problemas.append(
                f"`fragmentos` debe traer cada id una vez: {', '.join(esperados)}; trajo "
                f"{', '.join(juzgados) or 'ninguno'}."
            )
        preguntas = [pregunta for pregunta in salida.preguntas if pregunta.strip()]
        if len(preguntas) != PREGUNTAS:
            problemas.append(f"`preguntas` debe traer exactamente {PREGUNTAS} preguntas.")
        if not salida.afirmaciones:
            problemas.append("`afirmaciones` no puede ir vacía.")
        if problemas:
            raise ErrorValidacionSalida(problemas)
        return salida

    return validar


def coseno(a: Sequence[float], b: Sequence[float]) -> float:
    """Similitud del coseno entre dos vectores.

    Args:
        a: Primer vector.
        b: Segundo vector.

    Returns:
        El coseno, entre -1 y 1; 0 si alguno es nulo.
    """
    norma = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norma if norma else 0.0


class ContextoDeColeccion(BaseModel):
    """Relevancia del contexto recuperado de una colección.

    Attributes:
        fragmentos: Fragmentos recuperados de la colección.
        necesarios: Los que el juez marcó como necesarios.
        relevancia: Los necesarios entre los recuperados.
    """

    fragmentos: int
    necesarios: int
    relevancia: float


class MetricasRag(BaseModel):
    """Las métricas RAGs de una muestra, con el juicio del que salen.

    Attributes:
        sesion: Identificador de la sesión.
        agente: Agente que consultó las colecciones.
        fidelidad: Afirmaciones sustentadas entre el total.
        relevancia_respuesta: Similitud media entre la consulta y las preguntas propuestas.
        contexto: Relevancia del contexto de cada colección.
        afirmaciones: Afirmaciones juzgadas.
        sustentadas: Las que se sustentan en el contexto.
        juicio: Salida del juez, para la revisión humana de la muestra.
    """

    sesion: str
    agente: str
    fidelidad: float
    relevancia_respuesta: float
    contexto: dict[str, ContextoDeColeccion]
    afirmaciones: int
    sustentadas: int
    juicio: SalidaJuezRag


def calcular_metricas(
    muestra: MuestraRag, juicio: SalidaJuezRag, vectorizador: Vectorizador
) -> MetricasRag:
    """Calcula las métricas a partir del juicio validado.

    Args:
        muestra: Muestra de la sesión.
        juicio: Salida del juez, ya validada.
        vectorizador: BGE-M3, para la relevancia de la respuesta.

    Returns:
        Las métricas de la muestra.
    """
    necesario = {fragmento.id: fragmento.necesario for fragmento in juicio.fragmentos}
    contexto = {}
    for coleccion in muestra.colecciones:
        suyos = [
            id_fragmento
            for id_fragmento, recuperado in zip(
                muestra.identificadores, muestra.fragmentos, strict=True
            )
            if recuperado.coleccion == coleccion
        ]
        necesarios = sum(1 for id_fragmento in suyos if necesario.get(id_fragmento))
        contexto[coleccion] = ContextoDeColeccion(
            fragmentos=len(suyos), necesarios=necesarios, relevancia=necesarios / len(suyos)
        )
    sustentadas = sum(1 for afirmacion in juicio.afirmaciones if afirmacion.sustentada)
    preguntas = [pregunta for pregunta in juicio.preguntas if pregunta.strip()]
    consulta, *vectores = vectorizador.vectorizar([muestra.consulta, *preguntas])
    return MetricasRag(
        sesion=muestra.sesion,
        agente=muestra.agente,
        fidelidad=sustentadas / len(juicio.afirmaciones),
        relevancia_respuesta=mean(coseno(consulta, vector) for vector in vectores),
        contexto=contexto,
        afirmaciones=len(juicio.afirmaciones),
        sustentadas=sustentadas,
        juicio=juicio,
    )


def evaluar_muestra(
    muestra: MuestraRag, juez: InvocadorNodo, vectorizador: Vectorizador
) -> MetricasRag:
    """Juzga una muestra, con un reintento si el juicio no se ajusta a ella, y calcula sus métricas.

    Args:
        muestra: Muestra de la sesión.
        juez: Invocador del juez, con el prompt de `evaluacion/juez_rag.md`.
        vectorizador: BGE-M3.

    Returns:
        Las métricas de la muestra.

    Raises:
        ErrorRespuestaModelo: Si el juez no da un juicio utilizable en ningún intento.
    """
    juicio = juez.invocar_validado(mensajes_juez(muestra), SalidaJuezRag, validador(muestra))
    return calcular_metricas(muestra, juicio, vectorizador)


def _estadisticas(valores: Sequence[float]) -> dict[str, float]:
    return {"media": mean(valores), "minimo": min(valores), "maximo": max(valores)}


def resumen_por_coleccion(metricas: Sequence[MetricasRag]) -> dict[str, dict[str, object]]:
    """Las tres métricas por colección: media, mínimo y máximo.

    La fidelidad y la relevancia de la respuesta son las del agente que consulta la colección:
    `elicitacion` y `dominio_negocio` comparten las del elicitador.

    Args:
        metricas: Métricas de las muestras.

    Returns:
        Por colección: su agente, el número de muestras y las estadísticas de cada métrica.
    """
    resumen: dict[str, dict[str, object]] = {}
    for coleccion, agente in AGENTE_DE_COLECCION.items():
        suyas = [m for m in metricas if coleccion in m.contexto]
        if not suyas:
            continue
        resumen[coleccion] = {
            "agente": agente,
            "muestras": len(suyas),
            "fidelidad": _estadisticas([m.fidelidad for m in suyas]),
            "relevancia_respuesta": _estadisticas([m.relevancia_respuesta for m in suyas]),
            "relevancia_contexto": _estadisticas([m.contexto[coleccion].relevancia for m in suyas]),
        }
    return resumen
