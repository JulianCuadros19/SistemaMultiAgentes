"""Adaptador de sistema-04-1: registra el borrador en el repositorio en memoria y activa con sus datos.

La aplicación devuelve cada cambio con su fecha y su usuario, pero no los conserva: el registro de
los cambios es un comportamiento ausente.
"""

from datetime import date
from decimal import Decimal

from adaptadores.salida.repositorios_memoria import RepositorioContratosMemoria
from aplicacion.contratos import activar_contrato, cambiar_estado, terminar_contrato
from dominio.contratos import Contrato
from referencia_comun import Ausente


class Contratos:
    def __init__(self) -> None:
        self._repo = RepositorioContratosMemoria()

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
        self._repo.registrar(
            Contrato(codigo, inmueble, inicio, fin, arrendatario, Decimal(canon), "borrador")
        )

    def activar(self, codigo: str, usuario: str) -> str:
        c = self._repo.consultar_por_codigo(codigo)
        cambio = activar_contrato(
            codigo,
            c.inmueble,
            c.fecha_inicio,
            c.fecha_fin,
            c.documento_arrendatario,
            c.canon_mensual,
            usuario,
            self._repo,
        )
        return cambio.contrato.estado

    def terminar(self, codigo: str, motivo: str, fecha: date, usuario: str) -> str:
        return terminar_contrato(codigo, motivo, fecha, usuario, self._repo).contrato.estado

    def anular(self, codigo: str, usuario: str) -> str:
        return cambiar_estado(codigo, "anulado", usuario, self._repo).contrato.estado

    def usuarios_de_los_cambios(self, codigo: str) -> list[str]:
        raise Ausente("La aplicación no conserva el registro de los cambios de estado.")
