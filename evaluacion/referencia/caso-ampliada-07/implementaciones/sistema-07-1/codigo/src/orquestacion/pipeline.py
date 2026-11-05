"""Orquestación secuencial con estado intermedio y reanudación explícita."""

from contratos.esquemas import DatosLeidos, DatosNormalizados, ResultadoConciliacion, Resumen
from etapas.conciliacion import conciliar_lotes
from etapas.escritura import EscrituraError, escribir_resultados
from etapas.lectura import ColumnaFaltante, leer_archivos
from etapas.normalizacion import normalizar_datos

__all__ = ["ColumnaFaltante", "EscrituraError", "Orquestador"]


class Orquestador:
    """Coordina las etapas y conserva sus últimas salidas válidas."""

    def __init__(self) -> None:
        """Inicializa un orquestador sin datos y con contadores en cero."""
        self._leidos: DatosLeidos | None = None
        self._normalizados: DatosNormalizados | None = None
        self._resultado: ResultadoConciliacion | None = None
        self._contadores = {
            "lectura": 0,
            "normalizacion": 0,
            "conciliacion": 0,
            "escritura": 0,
        }

    def ejecutar(
        self,
        pagos_banco_a: str,
        pagos_banco_b: str,
        pagos_banco_c: str,
        facturas_emitidas: str,
        destino_csv: str,
    ) -> Resumen:
        """Ejecuta un lote completo.

        Args:
            pagos_banco_a: Ruta de pagos de Banco A.
            pagos_banco_b: Ruta de pagos de Banco B.
            pagos_banco_c: Ruta de pagos de Banco C.
            facturas_emitidas: Ruta de facturas.
            destino_csv: Ruta del CSV de resultados.

        Returns:
            Totales por estado.

        Raises:
            ColumnaFaltante: Si una entrada carece de una columna requerida.
            EscrituraError: Si falla la escritura.
            OSError: Si falla la lectura de archivos.
            ValueError: Si hay datos estructurales o fechas inválidas.
        """
        self.ejecutar_hasta(
            "conciliacion", pagos_banco_a, pagos_banco_b, pagos_banco_c, facturas_emitidas
        )
        return self.reintentar_desde("escritura", destino_csv)

    def ejecutar_hasta(
        self,
        etapa: str,
        pagos_banco_a: str,
        pagos_banco_b: str,
        pagos_banco_c: str,
        facturas_emitidas: str,
    ) -> None:
        """Inicia un lote y conserva las salidas hasta la etapa indicada.

        Args:
            etapa: lectura, normalizacion o conciliacion.
            pagos_banco_a: Ruta de pagos de Banco A.
            pagos_banco_b: Ruta de pagos de Banco B.
            pagos_banco_c: Ruta de pagos de Banco C.
            facturas_emitidas: Ruta de facturas.

        Raises:
            ColumnaFaltante: Si falta una columna requerida.
            OSError: Si no se puede leer un archivo.
            ValueError: Si la etapa o los datos son inválidos.
        """
        if etapa not in ("lectura", "normalizacion", "conciliacion"):
            raise ValueError("Etapa final inválida.")
        self._leidos = None
        self._normalizados = None
        self._resultado = None
        self._contadores["lectura"] += 1
        self._leidos = leer_archivos(
            pagos_banco_a, pagos_banco_b, pagos_banco_c, facturas_emitidas
        )
        if etapa != "lectura":
            self._normalizar()
        if etapa == "conciliacion":
            self._conciliar()

    def reintentar_desde(self, etapa: str, destino_csv: str) -> Resumen:
        """Reanuda desde una etapa sin repetir las anteriores.

        Args:
            etapa: normalizacion, conciliacion o escritura.
            destino_csv: Ruta del CSV de resultados.

        Returns:
            Totales del resultado actualizado.

        Raises:
            EscrituraError: Si no se puede escribir el resultado.
            ValueError: Si la etapa es inválida, falta estado previo o hay fechas inválidas.
        """
        if etapa not in ("normalizacion", "conciliacion", "escritura"):
            raise ValueError("Etapa de reintento inválida.")
        if etapa == "normalizacion":
            self._normalizar()
        if etapa in ("normalizacion", "conciliacion"):
            self._conciliar()
        if self._resultado is None:
            raise ValueError("Se requiere un resultado de conciliación previo.")
        self._contadores["escritura"] += 1
        escribir_resultados(self._resultado, destino_csv)
        return self._resultado.resumen

    def obtener_contadores(self) -> dict[str, int]:
        """Obtiene una copia de los contadores de intentos de ejecución.

        Returns:
            Número de intentos por etapa, incluidos los fallidos.
        """
        return dict(self._contadores)

    def _normalizar(self) -> None:
        if self._leidos is None:
            raise ValueError("Se requiere una lectura previa.")
        self._normalizados = None
        self._resultado = None
        self._contadores["normalizacion"] += 1
        self._normalizados = normalizar_datos(self._leidos)

    def _conciliar(self) -> None:
        if self._normalizados is None:
            raise ValueError("Se requiere una normalización previa.")
        self._resultado = None
        self._contadores["conciliacion"] += 1
        self._resultado = conciliar_lotes(self._normalizados)
