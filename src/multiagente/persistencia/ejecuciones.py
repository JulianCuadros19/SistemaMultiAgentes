"""Traza por nodo del grafo en PostgreSQL: `ejecuciones` y `llamadas_modelo` (RF-34, ADR-0016).

La comparten todos los procesos que operan sesiones, como la consola y la web. Cada ejecución de
un nodo se guarda con sus llamadas al modelo en una sola transacción, de modo que una consulta
nunca ve un nodo a medias.
"""

from collections import defaultdict
from decimal import Decimal

from psycopg_pool import ConnectionPool

from multiagente.llm.costos import ConsumoTokens
from multiagente.llm.traza import RegistroLlamada
from multiagente.orquestador.traza import EjecucionNodo

COLUMNAS_LLAMADA = (
    "fecha, nodo, prompt, huella_prompt, despliegue, modelo, region_procesamiento, esfuerzo, "
    "max_tokens_salida, motivo_fin, tokens_entrada, tokens_entrada_cacheada, "
    "tokens_entrada_escrita_cache, tokens_salida, tokens_razonamiento, costo_usd, latencia_ms, "
    "error"
)
"""Columnas de `llamadas_modelo` con los campos de `RegistroLlamada`, en el orden en que se leen."""


def _valores(llamada: RegistroLlamada) -> tuple[object, ...]:
    consumo = llamada.consumo
    return (
        llamada.fecha,
        llamada.nodo,
        llamada.prompt,
        llamada.huella_prompt,
        llamada.despliegue,
        llamada.modelo,
        llamada.region_procesamiento,
        llamada.esfuerzo,
        llamada.max_tokens_salida,
        llamada.motivo_fin,
        consumo.entrada,
        consumo.entrada_cacheada,
        consumo.entrada_escrita_cache,
        consumo.salida,
        consumo.razonamiento,
        llamada.costo_usd,
        llamada.latencia_ms,
        llamada.error,
    )


def _llamada(fila: tuple) -> RegistroLlamada:
    (
        fecha,
        nodo,
        prompt,
        huella,
        despliegue,
        modelo,
        region,
        esfuerzo,
        max_tokens,
        motivo_fin,
        entrada,
        cacheada,
        escrita,
        salida,
        razonamiento,
        costo,
        latencia,
        error,
    ) = fila
    return RegistroLlamada(
        fecha=fecha,
        nodo=nodo,
        prompt=prompt,
        huella_prompt=huella,
        despliegue=despliegue,
        modelo=modelo,
        region_procesamiento=region,
        esfuerzo=esfuerzo,
        max_tokens_salida=max_tokens,
        motivo_fin=motivo_fin,
        consumo=ConsumoTokens(
            entrada=entrada,
            entrada_cacheada=cacheada,
            entrada_escrita_cache=escrita,
            salida=salida,
            razonamiento=razonamiento,
        ),
        costo_usd=Decimal(costo),
        latencia_ms=latencia,
        error=error,
    )


class TrazaEjecuciones:
    """Guarda y consulta la traza de los nodos en PostgreSQL (`TrazaDeNodos`)."""

    def __init__(self, pool: ConnectionPool) -> None:
        """Prepara la traza sobre un pool de conexiones en modo autocommit.

        Args:
            pool: Pool de conexiones a la base, con las tablas de la migración 0002.
        """
        self.pool = pool

    def registrar_nodo(self, ejecucion: EjecucionNodo) -> None:
        """Guarda la ejecución de un nodo con sus llamadas, en una sola transacción.

        Args:
            ejecucion: Ejecución del nodo.
        """
        marcadores = ", ".join(["%s"] * len(COLUMNAS_LLAMADA.split(", ")))
        with self.pool.connection() as conexion, conexion.transaction():
            fila = conexion.execute(
                "INSERT INTO ejecuciones (sesion, nodo, inicio, duracion_ms, costo_usd, error) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (
                    ejecucion.sesion,
                    ejecucion.nodo,
                    ejecucion.inicio,
                    ejecucion.duracion_ms,
                    ejecucion.costo_usd,
                    ejecucion.error,
                ),
            ).fetchone()
            for orden, llamada in enumerate(ejecucion.llamadas):
                conexion.execute(
                    f"INSERT INTO llamadas_modelo (ejecucion, orden, {COLUMNAS_LLAMADA}) "
                    f"VALUES (%s, %s, {marcadores})",
                    (fila[0], orden, *_valores(llamada)),
                )

    def consultar(self, sesion: str) -> list[EjecucionNodo]:
        """Devuelve las ejecuciones de una sesión con sus llamadas, en el orden en que ocurrieron.

        Args:
            sesion: Identificador de la sesión.

        Returns:
            Las ejecuciones de esa sesión; vacía si no tiene.
        """
        with self.pool.connection() as conexion:
            ejecuciones = conexion.execute(
                "SELECT id, sesion, nodo, inicio, duracion_ms, error FROM ejecuciones "
                "WHERE sesion = %s ORDER BY inicio, id",
                (sesion,),
            ).fetchall()
            llamadas = conexion.execute(
                f"SELECT ejecucion, {COLUMNAS_LLAMADA} FROM llamadas_modelo "
                "WHERE ejecucion = ANY(%s) ORDER BY ejecucion, orden",
                ([fila[0] for fila in ejecuciones],),
            ).fetchall()
        por_ejecucion: defaultdict[int, list[RegistroLlamada]] = defaultdict(list)
        for ejecucion, *datos in llamadas:
            por_ejecucion[ejecucion].append(_llamada(tuple(datos)))
        return [
            EjecucionNodo(
                sesion=id_sesion,
                nodo=nodo,
                inicio=inicio,
                duracion_ms=duracion_ms,
                llamadas=tuple(por_ejecucion[identificador]),
                error=error,
            )
            for identificador, id_sesion, nodo, inicio, duracion_ms, error in ejecuciones
        ]
