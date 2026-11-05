"""Adaptador de modelo-unico-04-1: un rechazo llega como valor y se convierte en excepción.

La implementación puede rechazar al crear el borrador lo que la ficha exige para activar; en ese
caso, el adaptador entrega ese rechazo al activar.
"""

from datetime import date

from arrendamientos import RepositorioMemoria, ServicioContratos


class Contratos:
    def __init__(self) -> None:
        self._repositorio = RepositorioMemoria()
        self._servicio = ServicioContratos(self._repositorio)
        self._rechazos: dict[str, str] = {}

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
        resultado = self._servicio.crear_borrador(
            codigo,
            inmueble,
            canon,
            inicio,
            fin,
            usuario,
            identificacion_arrendatario=arrendatario,
            documento_arrendatario=arrendatario,
        )
        if not resultado.aceptado:
            self._rechazos[codigo] = resultado.motivo

    def _estado(self, resultado) -> str:
        if not resultado.aceptado:
            raise ValueError(resultado.motivo)
        return resultado.contrato.estado.value.lower()

    def activar(self, codigo: str, usuario: str) -> str:
        if codigo in self._rechazos:
            raise ValueError(self._rechazos[codigo])
        return self._estado(self._servicio.activar(codigo, usuario))

    def terminar(self, codigo: str, motivo: str, fecha: date, usuario: str) -> str:
        return self._estado(self._servicio.terminar(codigo, usuario, motivo, fecha))

    def anular(self, codigo: str, usuario: str) -> str:
        return self._estado(self._servicio.anular(codigo, usuario))

    def usuarios_de_los_cambios(self, codigo: str) -> list[str]:
        return [cambio.usuario for cambio in self._repositorio.obtener(codigo).historial]
