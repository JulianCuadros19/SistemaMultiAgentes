"""Adaptador de un-prompt-04-1: usa el servicio con el repositorio en memoria."""

from datetime import date

from arrendamientos.dominio import Contrato, Estado
from arrendamientos.repositorio import RepositorioEnMemoria
from arrendamientos.servicio import ServicioContratos


class Contratos:
    def __init__(self) -> None:
        self._servicio = ServicioContratos(RepositorioEnMemoria())

    def crear(
        self,
        codigo: str,
        inmueble: str,
        arrendatario,
        canon: int,
        inicio: date,
        fin: date,
        usuario: str,
    ) -> None:
        self._servicio.registrar(Contrato(codigo, inmueble, arrendatario, canon, inicio, fin))

    def activar(self, codigo: str, usuario: str) -> str:
        return self._servicio.cambiar_estado(codigo, Estado.VIGENTE, usuario).estado.value

    def terminar(self, codigo: str, motivo: str, fecha: date, usuario: str) -> str:
        contrato = self._servicio.cambiar_estado(
            codigo, Estado.TERMINADO, usuario, motivo=motivo, fecha_terminacion=fecha
        )
        return contrato.estado.value

    def anular(self, codigo: str, usuario: str) -> str:
        return self._servicio.cambiar_estado(codigo, Estado.ANULADO, usuario).estado.value

    def usuarios_de_los_cambios(self, codigo: str) -> list[str]:
        return [cambio.usuario for cambio in self._servicio.obtener(codigo).historial]
