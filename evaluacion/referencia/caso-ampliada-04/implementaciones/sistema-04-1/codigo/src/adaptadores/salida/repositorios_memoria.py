"""Repositorio de contratos en memoria, con estado independiente por instancia."""

from datetime import date

from dominio.contratos import Contrato, RepositorioContratos


class RepositorioContratosMemoria(RepositorioContratos):
    """Almacena contratos inmutables indexados por su código."""

    def __init__(self) -> None:
        """Inicializa un almacén vacío."""
        self._contratos: dict[str, Contrato] = {}

    def registrar(self, contrato: Contrato) -> None:
        """Registra un contrato, reemplazando el registro del mismo código si existe.

        Args:
            contrato: Datos iniciales del contrato.
        """
        self._contratos[contrato.codigo] = contrato

    def consultar_por_codigo(self, codigo: str) -> Contrato:
        """Devuelve el contrato identificado por su código.

        Args:
            codigo: Código previamente registrado.

        Returns:
            Contrato almacenado e inmutable.

        Raises:
            KeyError: El código no está registrado.
        """
        return self._contratos[codigo]

    def existe_vigencia_en_inmueble(self, inmueble: str, desde: date, hasta: date) -> bool:
        """Comprueba la intersección de periodos cerrados de contratos vigentes.

        Args:
            inmueble: Código del inmueble.
            desde: Inicio del periodo consultado.
            hasta: Fin del periodo consultado.

        Returns:
            Si existe un contrato vigente que intersecta el periodo en ese inmueble.
        """
        return any(
            contrato.estado == "vigente"
            and contrato.inmueble == inmueble
            and contrato.fecha_inicio <= hasta
            and desde <= contrato.fecha_fin
            for contrato in self._contratos.values()
        )

    def actualizar(self, contrato: Contrato) -> None:
        """Reemplaza los datos de un contrato existente.

        Args:
            contrato: Contrato con sus nuevos datos.

        Raises:
            KeyError: El contrato no está registrado.
        """
        if contrato.codigo not in self._contratos:
            raise KeyError(contrato.codigo)
        self._contratos[contrato.codigo] = contrato
