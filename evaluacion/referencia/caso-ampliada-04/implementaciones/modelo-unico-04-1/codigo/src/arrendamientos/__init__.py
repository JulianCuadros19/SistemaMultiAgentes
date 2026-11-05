"""Ciclo de vida de contratos con almacenamiento intercambiable."""

from calendar import monthrange
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from enum import Enum
from typing import Protocol


class Estado(str, Enum):
    """Estados posibles de un contrato."""

    BORRADOR = "BORRADOR"
    VIGENTE = "VIGENTE"
    TERMINADO = "TERMINADO"
    ANULADO = "ANULADO"


@dataclass(frozen=True)
class Cambio:
    """Registro inmutable de una gestión exitosa."""

    estado: Estado
    fecha: datetime
    usuario: str


@dataclass(frozen=True)
class Contrato:
    """Contrato y su historial; el canon se expresa en pesos enteros."""

    codigo: str
    inmueble: str
    canon: int
    inicio: date
    fin: date
    identificacion_arrendatario: str | None = None
    documento_arrendatario: str | None = None
    estado: Estado = Estado.BORRADOR
    fecha_terminacion: date | None = None
    motivo_terminacion: str | None = None
    historial: tuple[Cambio, ...] = ()


@dataclass(frozen=True)
class Resultado:
    """Contrato actualizado en caso de éxito, o motivo del rechazo."""

    contrato: Contrato | None = None
    motivo: str | None = None

    @property
    def aceptado(self) -> bool:
        """Indicar si la gestión produjo un contrato actualizado."""
        return self.contrato is not None


class Repositorio(Protocol):
    """Puerto de almacenamiento independiente de las reglas de negocio."""

    def obtener(self, codigo: str) -> Contrato | None:
        """Obtener un contrato por código, o None si no existe."""
        ...

    def vigentes(self, inmueble: str) -> tuple[Contrato, ...]:
        """Obtener todos los contratos vigentes del inmueble indicado."""
        ...

    def guardar(self, contrato: Contrato) -> None:
        """Insertar o reemplazar el contrato completo, incluido su historial."""
        ...


class RepositorioMemoria:
    """Adaptador volátil para pruebas y uso sin base de datos."""

    def __init__(self) -> None:
        """Crear un almacenamiento vacío."""
        self._contratos: dict[str, Contrato] = {}

    def obtener(self, codigo: str) -> Contrato | None:
        """Obtener el contrato inmutable asociado al código."""
        return self._contratos.get(codigo)

    def vigentes(self, inmueble: str) -> tuple[Contrato, ...]:
        """Listar únicamente los vigentes del inmueble solicitado."""
        return tuple(
            contrato
            for contrato in self._contratos.values()
            if contrato.inmueble == inmueble and contrato.estado == Estado.VIGENTE
        )

    def guardar(self, contrato: Contrato) -> None:
        """Insertar o reemplazar un contrato inmutable."""
        self._contratos[contrato.codigo] = contrato


class _Rechazo(Exception):
    """Señalar internamente un rechazo de negocio o de entrada."""


def _exigir(condicion: bool, motivo: str) -> None:
    if not condicion:
        raise _Rechazo(motivo)


def _texto(valor: object, etiqueta: str) -> None:
    _exigir(isinstance(valor, str) and bool(valor.strip()), f"{etiqueta} es obligatorio")


def _opcional(valor: object, etiqueta: str) -> None:
    _exigir(valor is None or isinstance(valor, str), f"{etiqueta} debe ser texto o None")


def _fecha(valor: object, etiqueta: str) -> None:
    _exigir(type(valor) is date, f"{etiqueta} debe ser una fecha de calendario")


def _minimo_seis_meses(inicio: date) -> date | None:
    indice = inicio.year * 12 + inicio.month - 1 + 6
    anio, mes_cero = divmod(indice, 12)
    if anio > date.max.year:
        return None
    mes = mes_cero + 1
    dia = min(inicio.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def _validar_activacion(contrato: Contrato) -> None:
    _texto(contrato.identificacion_arrendatario, "La identificación del arrendatario")
    _texto(contrato.documento_arrendatario, "El documento del arrendatario")
    _exigir(contrato.canon > 0, "El canon debe ser mayor que cero")
    _exigir(contrato.fin > contrato.inicio, "La fecha de fin debe ser posterior a la de inicio")
    minimo = _minimo_seis_meses(contrato.inicio)
    _exigir(
        minimo is not None and contrato.fin >= minimo,
        "La duración debe ser de al menos seis meses",
    )


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class ServicioContratos:
    """Aplicar las reglas y devolver rechazos sin alterar el contrato guardado."""

    def __init__(
        self,
        repositorio: Repositorio,
        reloj: Callable[[], datetime] = _ahora,
    ) -> None:
        """Inyectar el almacenamiento y el reloj de auditoría."""
        self._repositorio = repositorio
        self._reloj = reloj

    def crear_borrador(
        self,
        codigo: str,
        inmueble: str,
        canon: int,
        inicio: date,
        fin: date,
        usuario: str,
        identificacion_arrendatario: str | None = None,
        documento_arrendatario: str | None = None,
    ) -> Resultado:
        """Crear un borrador; las condiciones de vigencia se verifican al activar."""
        return self._ejecutar(
            lambda: self._crear(
                codigo, inmueble, canon, inicio, fin, usuario,
                identificacion_arrendatario, documento_arrendatario,
            )
        )

    def activar(
        self,
        codigo: str,
        usuario: str,
        identificacion_arrendatario: str | None = None,
        documento_arrendatario: str | None = None,
    ) -> Resultado:
        """Activar un borrador, pudiendo completar sus datos de arrendatario."""
        return self._ejecutar(
            lambda: self._activar(
                codigo, usuario, identificacion_arrendatario, documento_arrendatario,
            )
        )

    def terminar(
        self,
        codigo: str,
        usuario: str,
        motivo: str,
        fecha_terminacion: date,
    ) -> Resultado:
        """Terminar un vigente con motivo y fecha dentro de su periodo."""
        return self._ejecutar(
            lambda: self._terminar(codigo, usuario, motivo, fecha_terminacion)
        )

    def anular(self, codigo: str, usuario: str) -> Resultado:
        """Anular exclusivamente un borrador."""
        return self._ejecutar(lambda: self._anular(codigo, usuario))

    def _ejecutar(self, operacion: Callable[[], Contrato]) -> Resultado:
        try:
            return Resultado(contrato=operacion())
        except _Rechazo as error:
            return Resultado(motivo=str(error))

    def _cargar(self, codigo: str, estado: Estado) -> Contrato:
        _texto(codigo, "El código del contrato")
        contrato = self._repositorio.obtener(codigo)
        if contrato is None:
            raise _Rechazo(f"No existe el contrato: {codigo}")
        _exigir(
            contrato.estado == estado,
            f"La gestión no corresponde al estado actual: {contrato.estado.value}",
        )
        return contrato

    def _guardar(self, contrato: Contrato, estado: Estado, usuario: str) -> Contrato:
        cambio = Cambio(estado=estado, fecha=self._reloj(), usuario=usuario)
        actualizado = replace(
            contrato, estado=estado, historial=(*contrato.historial, cambio),
        )
        self._repositorio.guardar(actualizado)
        return actualizado

    def _crear(
        self,
        codigo: str,
        inmueble: str,
        canon: int,
        inicio: date,
        fin: date,
        usuario: str,
        identificacion: str | None,
        documento: str | None,
    ) -> Contrato:
        _texto(codigo, "El código del contrato")
        _texto(inmueble, "El código del inmueble")
        _texto(usuario, "El usuario")
        _exigir(type(canon) is int, "El canon debe ser un número entero de pesos")
        _fecha(inicio, "La fecha de inicio")
        _fecha(fin, "La fecha de fin")
        _opcional(identificacion, "La identificación del arrendatario")
        _opcional(documento, "El documento del arrendatario")
        _exigir(
            self._repositorio.obtener(codigo) is None,
            f"Ya existe un contrato con el código: {codigo}",
        )
        contrato = Contrato(
            codigo=codigo, inmueble=inmueble, canon=canon, inicio=inicio, fin=fin,
            identificacion_arrendatario=identificacion, documento_arrendatario=documento,
        )
        return self._guardar(contrato, Estado.BORRADOR, usuario)

    def _activar(
        self,
        codigo: str,
        usuario: str,
        identificacion: str | None,
        documento: str | None,
    ) -> Contrato:
        contrato = self._cargar(codigo, Estado.BORRADOR)
        _texto(usuario, "El usuario")
        _opcional(identificacion, "La identificación del arrendatario")
        _opcional(documento, "El documento del arrendatario")
        candidato = replace(
            contrato,
            identificacion_arrendatario=(
                contrato.identificacion_arrendatario if identificacion is None else identificacion
            ),
            documento_arrendatario=(
                contrato.documento_arrendatario if documento is None else documento
            ),
        )
        _validar_activacion(candidato)
        for otro in self._repositorio.vigentes(candidato.inmueble):
            solapa = candidato.inicio < otro.fin and otro.inicio < candidato.fin
            _exigir(
                otro.codigo == candidato.codigo or not solapa,
                "El inmueble ya tiene un contrato vigente en ese periodo",
            )
        return self._guardar(candidato, Estado.VIGENTE, usuario)

    def _terminar(
        self,
        codigo: str,
        usuario: str,
        motivo: str,
        fecha_terminacion: date,
    ) -> Contrato:
        contrato = self._cargar(codigo, Estado.VIGENTE)
        _texto(usuario, "El usuario")
        _texto(motivo, "El motivo de terminación")
        _fecha(fecha_terminacion, "La fecha de terminación")
        _exigir(
            contrato.inicio <= fecha_terminacion <= contrato.fin,
            "La fecha de terminación debe estar dentro del periodo del contrato",
        )
        terminado = replace(
            contrato, motivo_terminacion=motivo, fecha_terminacion=fecha_terminacion,
        )
        return self._guardar(terminado, Estado.TERMINADO, usuario)

    def _anular(self, codigo: str, usuario: str) -> Contrato:
        contrato = self._cargar(codigo, Estado.BORRADOR)
        _texto(usuario, "El usuario")
        return self._guardar(contrato, Estado.ANULADO, usuario)
