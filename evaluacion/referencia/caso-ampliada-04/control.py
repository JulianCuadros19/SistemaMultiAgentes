"""Implementación de control del caso 04, para validar las pruebas de referencia (ADR-0019).

No participa en la comparación: sirve para comprobar que las pruebas pasan con una implementación
que sigue la ficha y fallan con cada mutante de `mutantes.json`. Expone directamente la interfaz de
referencia, así que hace también de adaptador.
"""

from dataclasses import dataclass, field
from datetime import date

MESES_MINIMOS = 6


@dataclass
class _Contrato:
    inmueble: str
    arrendatario: str | None
    canon: int
    inicio: date
    fin: date
    estado: str = "borrador"
    cambios: list[str] = field(default_factory=list)


def _meses(inicio: date, fin: date) -> int:
    return (fin.year - inicio.year) * 12 + fin.month - inicio.month + (fin.day >= inicio.day - 1)


class Contratos:
    """Contratos en memoria, con las reglas de la ficha."""

    def __init__(self) -> None:
        self._contratos: dict[str, _Contrato] = {}

    def crear(
        self,
        codigo: str,
        inmueble: str,
        arrendatario: str | None,
        canon: int,
        inicio: date,
        fin: date,
        usuario: str,
    ) -> None:
        """Registra un contrato en borrador."""
        self._contratos[codigo] = _Contrato(inmueble, arrendatario, canon, inicio, fin, cambios=[usuario])

    def _exigir(self, contrato: _Contrato, estado: str) -> None:
        if contrato.estado != estado:
            raise ValueError(f"Transición no permitida desde el estado {contrato.estado}")

    def activar(self, codigo: str, usuario: str) -> str:
        """Pasa el contrato a vigente y devuelve su estado."""
        contrato = self._contratos[codigo]
        self._exigir(contrato, "borrador")
        if not contrato.arrendatario:
            raise ValueError("El contrato no tiene arrendatario")
        if contrato.canon <= 0:
            raise ValueError("El canon debe ser mayor que cero")
        if contrato.fin <= contrato.inicio or _meses(contrato.inicio, contrato.fin) < MESES_MINIMOS:
            raise ValueError("La duración mínima es de seis meses")
        for otro in self._contratos.values():
            if (
                otro is not contrato
                and otro.inmueble == contrato.inmueble
                and otro.estado == "vigente"
                and otro.inicio <= contrato.fin
                and contrato.inicio <= otro.fin
            ):
                raise ValueError("El inmueble ya tiene un contrato vigente en ese periodo")
        contrato.estado = "vigente"
        contrato.cambios.append(usuario)
        return contrato.estado

    def terminar(self, codigo: str, motivo: str, fecha: date, usuario: str) -> str:
        """Pasa el contrato a terminado y devuelve su estado."""
        contrato = self._contratos[codigo]
        self._exigir(contrato, "vigente")
        if not motivo:
            raise ValueError("Se exige un motivo")
        if not contrato.inicio <= fecha <= contrato.fin:
            raise ValueError("La fecha de terminación debe estar dentro del periodo")
        contrato.estado = "terminado"
        contrato.cambios.append(usuario)
        return contrato.estado

    def anular(self, codigo: str, usuario: str) -> str:
        """Pasa el contrato a anulado y devuelve su estado."""
        contrato = self._contratos[codigo]
        self._exigir(contrato, "borrador")
        contrato.estado = "anulado"
        contrato.cambios.append(usuario)
        return contrato.estado

    def usuarios_de_los_cambios(self, codigo: str) -> list[str]:
        """El usuario de cada cambio de estado registrado, en orden."""
        return list(self._contratos[codigo].cambios)
