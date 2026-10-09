"""Verificación automática de los atributos de calidad de los requerimientos (RF-07, N6).

Es determinística: aplica las señales que la base de conocimiento declara detectables sin juicio
humano (eli-005), los antipatrones de eli-009, las reglas de redacción de la historia (eli-001)
y de los criterios de aceptación (eli-003, eli-004), y las reglas que el ADR-0005 dejó fuera del
esquema. La consistencia semántica, la corrección y la factibilidad no se verifican aquí: quedan
para el analista en el punto de control N6.

Los textos se comparan sin mayúsculas ni tildes y por palabra completa.
"""

import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum

from multiagente.core.esquemas.comunes import Enunciado, repetidos
from multiagente.core.esquemas.requerimiento import HistoriaUsuario, RequerimientoFormal
from multiagente.orquestador.estado import Requerimientos


class Caracteristica(StrEnum):
    """Característica de calidad que un defecto incumple (eli-005 y RF-07)."""

    NECESARIO = "C1 Necesario"
    NO_AMBIGUO = "C3 No ambiguo"
    COMPLETO = "C4 Completo"
    SINGULAR = "C5 Singular"
    VERIFICABLE = "C7 Verificable"
    CONFORME = "C9 Conforme"
    TRAZABLE = "Trazable"
    CONSISTENTE = "Consistente"


@dataclass(frozen=True)
class DefectoCalidad:
    """Incumplimiento de una característica de calidad en un campo de un artefacto."""

    artefacto: str
    caracteristica: Caracteristica
    campo: str
    detalle: str

    @property
    def requiere_cliente(self) -> bool:
        """Solo el cliente puede resolverlo: corregirlo sin él sería inventar (eli-009)."""
        return self.campo == "preguntas_abiertas" or self.detalle.startswith(
            "marcador de pendiente"
        )

    def __str__(self) -> str:
        """Texto del defecto tal como se registra en el estado y se muestra al analista."""
        return f"{self.artefacto} · {self.caracteristica} · {self.campo}: {self.detalle}"


def normalizar(texto: str) -> str:
    """Quita tildes y mayúsculas para comparar textos.

    Args:
        texto: Texto original.

    Returns:
        Texto en minúsculas y sin marcas diacríticas.
    """
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).casefold()


def identificador(nombre: str) -> str:
    """Convierte el nombre de un dato en identificador: minúsculas, sin tildes y con guion bajo.

    Args:
        nombre: Nombre del dato, p. ej. «Número predial».

    Returns:
        Identificador, p. ej. `numero_predial`.
    """
    return re.sub(r"[^a-z0-9]+", "_", normalizar(nombre)).strip("_")


def _patron(frases: tuple[str, ...]) -> re.Pattern[str]:
    alternativas = "|".join(re.escape(normalizar(frase)) for frase in frases)
    return re.compile(rf"\b(?:{alternativas})\b")


# La palabra suelta «pendiente» no se marca: en el dominio tributario es legítima
# («saldo pendiente de pago»). Se marcan las frases que dejan contenido por definir.
MARCADORES_PENDIENTE = _patron(
    (
        "TBD",
        "por definir",
        "por confirmar",
        "a definir",
        "pendiente de definir",
        "pendiente de confirmar",
        "pendiente por definir",
        "se confirmará",
        "se definirá",
    )
)
CUANTIFICADORES_VAGOS = _patron(
    (
        "rápido",
        "rápida",
        "lento",
        "lenta",
        "eficiente",
        "amigable",
        "robusto",
        "robusta",
        "adecuado",
        "adecuada",
        "adecuadamente",
        "suficiente",
        "óptimo",
        "óptima",
        "razonable",
        "apropiado",
        "apropiada",
        "fácil",
        "simple",
        "moderno",
        "moderna",
        "intuitivo",
        "intuitiva",
        "correctamente",
    )
)
GENERALIZACIONES = _patron(
    ("etc", "etcétera", "entre otros", "entre otras", "y demás", "cualquier", "todos los casos")
)
OPCIONALIDAD = _patron(
    (
        "debería",
        "deberían",
        "podría",
        "podrían",
        "sería deseable",
        "de ser posible",
        "preferiblemente",
    )
)
COMPARATIVOS = re.compile(
    r"\b(?:mejor|peor|mas (?:rapido|rapida|lento|lenta|seguro|segura|facil|eficiente|agil))\b"
    r"(?!(?:\s+\w+){0,2}\s+que\b)"
)
CONECTORES_COMPUESTOS = _patron(("así como", "además de", "también"))
DETALLE_IMPLEMENTACION = re.compile(r"\w+\(\)|\w+_\w+|[<>]=?|[=!]=|\s=\s|[≤≥≠]")
"""Llamadas, identificadores y operadores que un escenario Gherkin no debe contener (eli-004).

Un identificador con guion bajo se admite si es el nombre de un dato declarado en la ficha.
"""
SENALES_ERROR = re.compile(
    r"\b(?:rechaz\w*|error\w*|invalid\w*|incorrect\w*|inexistent\w*|no existe\w*|no permite"
    r"|no se permite|impide|deniega|bloquea|falla\w*|incumpl\w*|falta\w*|incomplet\w*|vaci[oa]s?"
    r"|excede\w*|duplicad\w*|vencid\w*|no autorizad\w*|no corresponde\w*)"
)
ROL_GENERICO = re.compile(
    r"^(?:el |la |un |una |los |las )?(?:usuari[oa]s?|sistema)(?: finale?s?)?$"
)
INFINITIVO = re.compile(r"^\w+(?:ar|er|ir)(?:se|lo|la|los|las|le|les|me|nos)?$")
NO_VERBOS = frozenset(
    {
        "auxiliar",
        "caracter",
        "celular",
        "escolar",
        "familiar",
        "hogar",
        "lugar",
        "militar",
        "mujer",
        "particular",
        "popular",
        "regular",
        "similar",
        "singular",
        "titular",
    }
)
"""Palabras terminadas como infinitivo que en el dominio funcionan como sustantivo o adjetivo."""


def _es_infinitivo(palabra: str) -> bool:
    return palabra not in NO_VERBOS and INFINITIVO.match(palabra) is not None


SENALES_REDACCION: tuple[tuple[re.Pattern[str], Caracteristica, str], ...] = (
    (CUANTIFICADORES_VAGOS, Caracteristica.NO_AMBIGUO, "cuantificador vago"),
    (COMPARATIVOS, Caracteristica.VERIFICABLE, "comparativo sin referencia"),
    (GENERALIZACIONES, Caracteristica.COMPLETO, "generalización sin límite"),
    (OPCIONALIDAD, Caracteristica.NECESARIO, "opcionalidad encubierta"),
)
"""Señales léxicas de eli-005 y eli-009 que se buscan en los textos evaluables."""


def _senales(
    artefacto: str,
    campo: str,
    texto: str,
    patron: re.Pattern[str],
    caracteristica: Caracteristica,
    descripcion: str,
) -> Iterator[DefectoCalidad]:
    for coincidencia in patron.finditer(normalizar(texto)):
        detalle = f"{descripcion} «{coincidencia.group(0)}»"
        yield DefectoCalidad(artefacto, caracteristica, campo, detalle)


def _redaccion(artefacto: str, campo: str, texto: str) -> Iterator[DefectoCalidad]:
    """Señales léxicas de ambigüedad, verificabilidad y necesidad en un texto evaluable."""
    for patron, caracteristica, descripcion in SENALES_REDACCION:
        yield from _senales(artefacto, campo, texto, patron, caracteristica, descripcion)


def _pendientes(artefacto: str, campo: str, texto: str) -> Iterator[DefectoCalidad]:
    yield from _senales(
        artefacto,
        campo,
        texto,
        MARCADORES_PENDIENTE,
        Caracteristica.COMPLETO,
        "marcador de pendiente",
    )


def _textos(valor: object, ruta: str) -> Iterator[tuple[str, str]]:
    """Recorre un volcado de modelo y entrega cada texto con la ruta de su campo."""
    if isinstance(valor, str):
        yield ruta, valor
    elif isinstance(valor, dict):
        for clave, interno in valor.items():
            yield from _textos(interno, f"{ruta}.{clave}" if ruta else clave)
    elif isinstance(valor, list):
        for posicion, interno in enumerate(valor):
            yield from _textos(interno, f"{ruta}[{posicion}]")


def verificar_enunciado(artefacto: str, enunciado: Enunciado, campo: str) -> list[DefectoCalidad]:
    """Verifica la redacción de una historia en sus partes como, quiero y para (eli-001).

    Args:
        artefacto: Identificador de la historia o del requerimiento.
        enunciado: Enunciado a verificar.
        campo: Nombre del campo que contiene el enunciado, para ubicar el defecto.

    Returns:
        Defectos encontrados; vacía si el enunciado cumple.
    """
    defectos: list[DefectoCalidad] = []
    if ROL_GENERICO.match(normalizar(enunciado.como)):
        defectos.append(
            DefectoCalidad(
                artefacto,
                Caracteristica.CONFORME,
                f"{campo}.como",
                f"rol genérico «{enunciado.como}»: debe ser un rol concreto del negocio",
            )
        )
    quiero = normalizar(enunciado.quiero)
    primera = re.match(r"\w+", quiero)
    if primera is None or not _es_infinitivo(primera.group(0)):
        defectos.append(
            DefectoCalidad(
                artefacto,
                Caracteristica.CONFORME,
                f"{campo}.quiero",
                "el QUIERO no inicia con un verbo en infinitivo",
            )
        )
    for coincidencia in re.finditer(r"\b[ye]\s+(\w+)", quiero):
        if _es_infinitivo(coincidencia.group(1)):
            defectos.append(
                DefectoCalidad(
                    artefacto,
                    Caracteristica.SINGULAR,
                    f"{campo}.quiero",
                    f"une dos capacidades con «{coincidencia.group(0)}»",
                )
            )
    defectos.extend(
        _senales(
            artefacto,
            f"{campo}.quiero",
            enunciado.quiero,
            CONECTORES_COMPUESTOS,
            Caracteristica.SINGULAR,
            "enumera capacidades con",
        )
    )
    defectos.extend(_redaccion(artefacto, f"{campo}.quiero", enunciado.quiero))
    return defectos


def verificar_historia(historia: HistoriaUsuario) -> list[DefectoCalidad]:
    """Verifica una historia del backlog: redacción, pendientes y preguntas abiertas.

    Args:
        historia: Historia a verificar.

    Returns:
        Defectos encontrados; vacía si la historia cumple.
    """
    defectos = verificar_enunciado(historia.id, historia.enunciado, "enunciado")
    for campo, texto in _textos(historia.model_dump(mode="json"), ""):
        defectos.extend(_pendientes(historia.id, campo, texto))
    if historia.preguntas_abiertas:
        defectos.append(
            DefectoCalidad(
                historia.id,
                Caracteristica.COMPLETO,
                "preguntas_abiertas",
                f"quedan {len(historia.preguntas_abiertas)} preguntas sin resolver con el cliente",
            )
        )
    return defectos


def verificar_requerimiento(requerimiento: RequerimientoFormal) -> list[DefectoCalidad]:
    """Verifica un requerimiento formal del Anexo A de forma individual.

    Args:
        requerimiento: Requerimiento a verificar.

    Returns:
        Defectos encontrados; vacía si el requerimiento cumple.
    """
    artefacto = requerimiento.id_requerimiento
    defectos = verificar_enunciado(artefacto, requerimiento.titulo, "titulo")
    for campo, texto in _textos(requerimiento.model_dump(mode="json"), ""):
        defectos.extend(_pendientes(artefacto, campo, texto))

    descripcion = requerimiento.descripcion
    evaluables = [
        ("descripcion.precondicion", descripcion.precondicion),
        ("descripcion.regla_negocio", descripcion.regla_negocio),
    ]
    evaluables += [
        (f"descripcion.datos_entrada[{i}].restriccion", dato.restriccion)
        for i, dato in enumerate(descripcion.datos_entrada)
        if dato.restriccion
    ]
    evaluables += [
        (f"descripcion.datos_salida[{i}].formato", dato.formato)
        for i, dato in enumerate(descripcion.datos_salida)
        if dato.formato
    ]
    for escenario in requerimiento.criterios_aceptacion:
        evaluables += [
            (f"{escenario.id}.dado_que", escenario.dado_que),
            (f"{escenario.id}.cuando", escenario.cuando),
            (f"{escenario.id}.entonces", escenario.entonces),
        ]
    for campo, texto in evaluables:
        defectos.extend(_redaccion(artefacto, campo, texto))
    declarados = {
        identificador(dato.nombre)
        for dato in (*descripcion.datos_entrada, *descripcion.datos_salida)
    }
    for escenario in requerimiento.criterios_aceptacion:
        for parte in ("dado_que", "cuando", "entonces"):
            texto = normalizar(getattr(escenario, parte))
            for coincidencia in DETALLE_IMPLEMENTACION.finditer(texto):
                if coincidencia.group(0) in declarados:
                    continue
                defectos.append(
                    DefectoCalidad(
                        artefacto,
                        Caracteristica.CONFORME,
                        f"{escenario.id}.{parte}",
                        f"detalle de implementación «{coincidencia.group(0)}»",
                    )
                )

    for campo, datos in (
        ("descripcion.datos_entrada", descripcion.datos_entrada),
        ("descripcion.datos_salida", descripcion.datos_salida),
    ):
        if not datos:
            defectos.append(
                DefectoCalidad(artefacto, Caracteristica.COMPLETO, campo, "no declara ningún dato")
            )

    escenarios = requerimiento.criterios_aceptacion
    if len(escenarios) < 2:
        defectos.append(
            DefectoCalidad(
                artefacto,
                Caracteristica.VERIFICABLE,
                "criterios_aceptacion",
                "un solo escenario: falta el camino alterno o de error",
            )
        )
    con_error = any(
        SENALES_ERROR.search(normalizar(f"{e.nombre or ''} {e.dado_que} {e.entonces}"))
        for e in escenarios
    )
    if not con_error:
        defectos.append(
            DefectoCalidad(
                artefacto,
                Caracteristica.VERIFICABLE,
                "criterios_aceptacion",
                "ningún escenario cubre un caso de error o una entrada inválida",
            )
        )
    return defectos


def verificar_conjunto(requerimientos: Requerimientos) -> list[DefectoCalidad]:
    """Verifica el conjunto que produjo N5: cada artefacto, la trazabilidad y las referencias.

    Las historias cuyo enunciado ya es el título de un requerimiento se verifican solo por sus
    campos propios, para no repetir los defectos de redacción del título.

    Args:
        requerimientos: Partición con las historias, los requerimientos y sus referencias.

    Returns:
        Defectos encontrados, en orden de artefacto; vacía si el conjunto cumple.
    """
    defectos: list[DefectoCalidad] = []
    if not requerimientos.historias or not requerimientos.requerimientos:
        defectos.append(
            DefectoCalidad(
                "conjunto",
                Caracteristica.COMPLETO,
                "historias" if not requerimientos.historias else "requerimientos",
                "no hay ningún artefacto",
            )
        )
    for campo, identificadores in (
        ("historias", [historia.id for historia in requerimientos.historias]),
        (
            "requerimientos",
            [requerimiento.id_requerimiento for requerimiento in requerimientos.requerimientos],
        ),
    ):
        if duplicados := repetidos(identificadores):
            defectos.append(
                DefectoCalidad(
                    "conjunto",
                    Caracteristica.CONSISTENTE,
                    campo,
                    f"identificadores repetidos {duplicados}",
                )
            )

    titulos = {
        requerimiento.titulo.model_dump_json() for requerimiento in requerimientos.requerimientos
    }
    for historia in requerimientos.historias:
        propios = verificar_historia(historia)
        if historia.enunciado.model_dump_json() in titulos:
            propios = [d for d in propios if not d.campo.startswith("enunciado")]
        else:
            defectos.append(
                DefectoCalidad(
                    historia.id,
                    Caracteristica.TRAZABLE,
                    "enunciado",
                    "ningún requerimiento formal desarrolla esta historia",
                )
            )
        defectos.extend(propios)

    enunciados = {historia.enunciado.model_dump_json() for historia in requerimientos.historias}
    for requerimiento in requerimientos.requerimientos:
        artefacto = requerimiento.id_requerimiento
        if requerimiento.titulo.model_dump_json() not in enunciados:
            defectos.append(
                DefectoCalidad(
                    artefacto,
                    Caracteristica.TRAZABLE,
                    "titulo",
                    "el título no reproduce ninguna historia del backlog",
                )
            )
        if not requerimientos.referencias.get(artefacto):
            defectos.append(
                DefectoCalidad(
                    artefacto,
                    Caracteristica.TRAZABLE,
                    "referencias",
                    "no referencia ningún fragmento del contexto recuperado (RF-04)",
                )
            )
        defectos.extend(verificar_requerimiento(requerimiento))
    return defectos
