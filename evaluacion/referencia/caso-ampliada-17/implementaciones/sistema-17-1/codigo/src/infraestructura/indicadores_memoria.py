"""Almacenamiento de tiempos por trámite y promedios decimales por tipo."""

from decimal import Decimal

from eventos.aviso import RegistroIndicadores


class RegistroIndicadoresMemoria(RegistroIndicadores):
    """Conserva un cálculo vigente por trámite en cada instancia."""

    def __init__(self) -> None:
        """Inicializa un registro vacío."""
        self._calculos: dict[str, tuple[str, int]] = {}

    def registrar_dias(self, numero_tramite: str, tipo_tramite: str, dias_habiles: int) -> None:
        """Guarda o reemplaza el cálculo de un trámite.

        Args:
            numero_tramite: Identificador no vacío.
            tipo_tramite: Tipo no vacío para agrupar el promedio.
            dias_habiles: Entero no negativo de días calculados.

        Raises:
            ValueError: Los identificadores o los días son inválidos.
        """
        for valor in (numero_tramite, tipo_tramite):
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError("El número y el tipo de trámite deben ser textos no vacíos.")
        if type(dias_habiles) is not int or dias_habiles < 0:
            raise ValueError("Los días hábiles deben ser un entero no negativo.")
        self._calculos[numero_tramite] = (tipo_tramite, dias_habiles)

    def consultar_dias_calculados(self, numero_tramite: str) -> int | None:
        """Consulta el tiempo vigente de un trámite.

        Args:
            numero_tramite: Identificador buscado.

        Returns:
            Días calculados o None si no hay cálculo.
        """
        calculo = self._calculos.get(numero_tramite)
        return None if calculo is None else calculo[1]

    def promedio_por_tipo(self, tipo_tramite: str) -> Decimal:
        """Calcula el promedio de los trámites registrados del tipo.

        Args:
            tipo_tramite: Tipo buscado.

        Returns:
            Promedio Decimal sin formato fijo, o Decimal(0) si no hay datos.
        """
        dias = [dias for tipo, dias in self._calculos.values() if tipo == tipo_tramite]
        if not dias:
            return Decimal(0)
        return Decimal(sum(dias)) / Decimal(len(dias))
