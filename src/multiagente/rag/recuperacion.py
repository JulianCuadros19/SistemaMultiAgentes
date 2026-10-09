"""Recuperación híbrida con aislamiento por agente (RF-29, RF-31 y RF-32).

Cada consulta combina búsqueda semántica (distancia coseno sobre BGE-M3) y búsqueda léxica
(texto completo en español) con fusión por rango recíproco. Ambas consultas SQL llevan el filtro
obligatorio por colección: un `Recuperador` solo existe para un agente y solo consulta las
colecciones que ese agente tiene autorizadas.
"""

from collections.abc import Iterable

from psycopg import Connection
from pydantic import BaseModel, ConfigDict

from multiagente.core.configuracion import ConfiguracionRecuperacion
from multiagente.rag.colecciones import Agente, Coleccion, autorizar
from multiagente.rag.embeddings import Vectorizador
from multiagente.rag.ingesta import literal_vector

K_FUSION = 60
"""Constante de la fusión por rango recíproco (arquitectura, §3.2)."""


class FragmentoRecuperado(BaseModel):
    """Fragmento devuelto por una consulta, con la evidencia de su posición."""

    model_config = ConfigDict(frozen=True)

    id: int
    coleccion: Coleccion
    documento_id: str
    version_documento: str
    titulo: str
    contenido: str
    metadatos: dict[str, str]
    similitud: float
    rango_semantico: int | None
    rango_lexico: int | None
    puntaje: float


class Descarte(BaseModel):
    """Fragmento descartado por irrelevante, con el motivo (RF-32)."""

    model_config = ConfigDict(frozen=True)

    fragmento: FragmentoRecuperado
    motivo: str


class ResultadoRecuperacion(BaseModel):
    """Contexto recuperado para una consulta y contexto descartado."""

    model_config = ConfigDict(frozen=True)

    agente: Agente
    consulta: str
    colecciones: tuple[Coleccion, ...]
    fragmentos: tuple[FragmentoRecuperado, ...]
    descartados: tuple[Descarte, ...]

    @property
    def sin_contexto(self) -> bool:
        """Indica que la base no tiene contexto relevante para la consulta."""
        return not self.fragmentos


def fusionar(
    rangos_semanticos: dict[int, int], rangos_lexicos: dict[int, int], k: int = K_FUSION
) -> dict[int, float]:
    """Fusiona dos listas ordenadas por rango recíproco: suma de 1 / (k + rango).

    Args:
        rangos_semanticos: Rango (desde 1) de cada fragmento en la búsqueda semántica.
        rangos_lexicos: Rango (desde 1) de cada fragmento en la búsqueda léxica.
        k: Constante de suavizado.

    Returns:
        Puntaje fusionado de cada fragmento que aparece en alguna de las dos listas.
    """
    puntajes: dict[int, float] = {}
    for rangos in (rangos_semanticos, rangos_lexicos):
        for fragmento, rango in rangos.items():
            puntajes[fragmento] = puntajes.get(fragmento, 0.0) + 1 / (k + rango)
    return puntajes


_SEMANTICA = """
SELECT id FROM kb_fragmentos
WHERE coleccion = ANY(%(colecciones)s::coleccion_conocimiento[])
ORDER BY embedding <=> %(vector)s::vector
LIMIT %(limite)s
"""

_LEXICA = """
SELECT f.id FROM kb_fragmentos AS f, websearch_to_tsquery('spanish', %(consulta)s) AS q
WHERE f.coleccion = ANY(%(colecciones)s::coleccion_conocimiento[]) AND f.lexico @@ q
ORDER BY ts_rank_cd(f.lexico, q) DESC, f.id
LIMIT %(limite)s
"""

_DETALLE = """
SELECT f.id, f.coleccion::text, f.documento_id, d.version, f.titulo, f.contenido, f.metadatos,
       1 - (f.embedding <=> %(vector)s::vector) AS similitud
FROM kb_fragmentos AS f JOIN kb_documentos AS d ON d.id = f.documento_id
WHERE f.id = ANY(%(ids)s) AND f.coleccion = ANY(%(colecciones)s::coleccion_conocimiento[])
"""


class Recuperador:
    """Recupera contexto para un agente, solo de sus colecciones autorizadas."""

    def __init__(
        self,
        conexion: Connection,
        vectorizador: Vectorizador,
        agente: Agente,
        configuracion: ConfiguracionRecuperacion | None = None,
    ) -> None:
        """Crea el recuperador del agente.

        Args:
            conexion: Conexión con las tablas de conocimiento en su `search_path`.
            vectorizador: Servicio de embeddings, el mismo con que se ingirió el corpus.
            agente: Agente que consulta.
            configuracion: Fragmentos, candidatos y umbral; si se omite, se lee del entorno.

        Raises:
            ErrorAccesoNoAutorizado: Si el agente no consulta bases de conocimiento, como el
                desarrollador (decisión 1).
        """
        self.autorizadas = autorizar(agente)
        self.conexion = conexion
        self.vectorizador = vectorizador
        self.agente = agente
        self.configuracion = configuracion or ConfiguracionRecuperacion()

    def recuperar(
        self,
        consulta: str,
        colecciones: Iterable[Coleccion] | None = None,
        k: int | None = None,
    ) -> ResultadoRecuperacion:
        """Recupera los fragmentos más relevantes para la consulta.

        Un fragmento se conserva si su similitud semántica alcanza el umbral o si contiene los
        términos de la consulta (coincidencia léxica). Los demás candidatos se descartan con su
        motivo; si no queda ninguno, el resultado declara ausencia de contexto.

        Args:
            consulta: Texto de la consulta.
            colecciones: Colecciones a consultar; si se omite, todas las del agente.
            k: Número máximo de fragmentos; si se omite, el configurado.

        Returns:
            Fragmentos en orden de puntaje fusionado y candidatos descartados.

        Raises:
            ErrorAccesoNoAutorizado: Si se pide una colección que el agente no tiene autorizada.
        """
        seleccionadas = autorizar(self.agente, colecciones)
        nombres = sorted(coleccion.value for coleccion in seleccionadas)
        vector = literal_vector(self.vectorizador.vectorizar([consulta])[0])
        limite = self.configuracion.candidatos
        parametros = {"colecciones": nombres, "vector": vector, "limite": limite}

        semanticos = [fila[0] for fila in self.conexion.execute(_SEMANTICA, parametros).fetchall()]
        lexicos = [
            fila[0]
            for fila in self.conexion.execute(
                _LEXICA, {**parametros, "consulta": consulta}
            ).fetchall()
        ]
        rango_sem = {fragmento: rango for rango, fragmento in enumerate(semanticos, 1)}
        rango_lex = {fragmento: rango for rango, fragmento in enumerate(lexicos, 1)}
        puntajes = fusionar(rango_sem, rango_lex)

        filas = self.conexion.execute(
            _DETALLE, {"vector": vector, "ids": list(puntajes), "colecciones": nombres}
        ).fetchall()
        candidatos = [
            FragmentoRecuperado(
                id=fila[0],
                coleccion=Coleccion(fila[1]),
                documento_id=fila[2],
                version_documento=fila[3],
                titulo=fila[4],
                contenido=fila[5],
                metadatos=fila[6],
                similitud=float(fila[7]),
                rango_semantico=rango_sem.get(fila[0]),
                rango_lexico=rango_lex.get(fila[0]),
                puntaje=puntajes[fila[0]],
            )
            for fila in filas
        ]
        # A igual puntaje, primero la coincidencia léxica: favorece los términos exactos.
        candidatos.sort(key=lambda f: (-f.puntaje, f.rango_lexico or limite + 1, f.id))

        umbral = self.configuracion.umbral_similitud
        relevantes = [f for f in candidatos if f.similitud >= umbral or f.rango_lexico]
        descartados = tuple(
            Descarte(
                fragmento=f,
                motivo=f"similitud {f.similitud:.3f} menor que el umbral {umbral} "
                "y sin coincidencia léxica",
            )
            for f in candidatos
            if f not in relevantes
        )
        return ResultadoRecuperacion(
            agente=self.agente,
            consulta=consulta,
            colecciones=tuple(sorted(seleccionadas)),
            fragmentos=tuple(relevantes[: k or self.configuracion.fragmentos]),
            descartados=descartados,
        )
