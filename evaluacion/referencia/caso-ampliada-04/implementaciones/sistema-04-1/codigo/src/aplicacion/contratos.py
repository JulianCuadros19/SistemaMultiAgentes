"""Casos de uso para activar, terminar y cambiar el estado de contratos."""

from calendar import monthrange
from dataclasses import replace
from datetime import date
from decimal import Decimal

from dominio.contratos import (
    CambioEstado,
    CanonInvalido,
    Contrato,
    CruceDeVigencias,
    DocumentoArrendatarioObligatorio,
    EstadoNoModificable,
    FechaTerminacionFueraDePeriodo,
    FechasInvalidas,
    MotivoObligatorio,
    RepositorioContratos,
    TransicionNoPermitida,
)


def _texto_presente(valor: str | None) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _validar_identificacion(codigo: str, usuario: str) -> None:
    if not _texto_presente(codigo) or not _texto_presente(usuario):
        error = TransicionNoPermitida()
        error.args = ("El código del contrato y el usuario son obligatorios",)
        raise error


def _validar_transicion(contrato: Contrato, nuevo_estado: str) -> None:
    if contrato.estado in ("terminado", "anulado"):
        error_final = EstadoNoModificable()
        error_final.args = (f"El estado actual del contrato es {contrato.estado}",)
        raise error_final
    permitidas = (("borrador", "vigente"), ("vigente", "terminado"), ("borrador", "anulado"))
    if (contrato.estado, nuevo_estado) not in permitidas:
        error = TransicionNoPermitida()
        error.args = (
            f"Transición no permitida; el estado actual del contrato es {contrato.estado}",
        )
        raise error


def _validar_fechas(fecha_inicio: date, fecha_fin: date) -> None:
    if not isinstance(fecha_inicio, date) or not isinstance(fecha_fin, date):
        raise FechasInvalidas()
    if fecha_fin <= fecha_inicio:
        error = FechasInvalidas()
        error.args = ("La fecha de fin del contrato debe ser posterior a la fecha de inicio",)
        raise error
    indice_mes = fecha_inicio.month - 1 + 6
    anio = fecha_inicio.year + indice_mes // 12
    mes = indice_mes % 12 + 1
    if anio > date.max.year:
        raise FechasInvalidas()
    dia = min(fecha_inicio.day, monthrange(anio, mes)[1])
    if fecha_fin < date(anio, mes, dia):
        error = FechasInvalidas()
        error.args = ("La duración mínima del contrato debe ser de seis meses",)
        raise error


def _validar_canon(canon_mensual: Decimal) -> None:
    if not isinstance(canon_mensual, Decimal) or not canon_mensual.is_finite():
        raise CanonInvalido()
    if canon_mensual <= 0 or canon_mensual != canon_mensual.to_integral_value():
        raise CanonInvalido()


def _guardar_cambio(
    contrato: Contrato, usuario: str, repo: RepositorioContratos
) -> CambioEstado:
    repo.actualizar(contrato)
    return CambioEstado(date.today(), usuario, contrato)


def activar_contrato(
    codigo: str,
    inmueble: str,
    fecha_inicio: date,
    fecha_fin: date,
    documento_arrendatario: str | None,
    canon_mensual: Decimal,
    usuario: str,
    repo: RepositorioContratos,
) -> CambioEstado:
    """Activa un borrador después de validar los datos y el cruce de vigencias.

    Args:
        codigo: Código del contrato previamente registrado.
        inmueble: Código obligatorio del inmueble.
        fecha_inicio: Inicio del periodo propuesto.
        fecha_fin: Fin del periodo, al menos seis meses después del inicio.
        documento_arrendatario: Documento obligatorio para activar.
        canon_mensual: Entero positivo en pesos representado como Decimal.
        usuario: Usuario responsable del cambio.
        repo: Repositorio de contratos.

    Returns:
        Contrato vigente, fecha del cambio y usuario responsable.

    Raises:
        DocumentoArrendatarioObligatorio: Falta el documento.
        CanonInvalido: El canon no es un entero positivo en pesos.
        FechasInvalidas: El periodo no cumple las restricciones.
        CruceDeVigencias: Existe una vigencia que intersecta el periodo.
        TransicionNoPermitida: La transición o los identificadores no son válidos.
        EstadoNoModificable: El estado actual es terminado o anulado.
    """
    _validar_identificacion(codigo, usuario)
    contrato = repo.consultar_por_codigo(codigo)
    _validar_transicion(contrato, "vigente")
    if not _texto_presente(inmueble):
        error = TransicionNoPermitida()
        error.args = ("El inmueble es obligatorio",)
        raise error
    if not _texto_presente(documento_arrendatario):
        raise DocumentoArrendatarioObligatorio()
    _validar_fechas(fecha_inicio, fecha_fin)
    _validar_canon(canon_mensual)
    if repo.existe_vigencia_en_inmueble(inmueble, fecha_inicio, fecha_fin):
        raise CruceDeVigencias()
    actualizado = replace(
        contrato,
        inmueble=inmueble,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        documento_arrendatario=documento_arrendatario,
        canon_mensual=canon_mensual,
        estado="vigente",
    )
    return _guardar_cambio(actualizado, usuario, repo)


def terminar_contrato(
    codigo: str,
    motivo: str | None,
    fecha_terminacion: date,
    usuario: str,
    repo: RepositorioContratos,
) -> CambioEstado:
    """Termina un contrato vigente con motivo y fecha dentro del periodo.

    Args:
        codigo: Código del contrato registrado.
        motivo: Motivo obligatorio de terminación.
        fecha_terminacion: Fecha dentro del periodo contractual, incluidos sus extremos.
        usuario: Usuario responsable del cambio.
        repo: Repositorio de contratos.

    Returns:
        Contrato terminado, fecha del cambio y usuario responsable.

    Raises:
        MotivoObligatorio: Falta el motivo.
        FechaTerminacionFueraDePeriodo: La fecha no pertenece al periodo.
        TransicionNoPermitida: La transición o los identificadores no son válidos.
        EstadoNoModificable: El contrato está terminado o anulado.
    """
    _validar_identificacion(codigo, usuario)
    contrato = repo.consultar_por_codigo(codigo)
    _validar_transicion(contrato, "terminado")
    if not _texto_presente(motivo):
        raise MotivoObligatorio()
    if not isinstance(fecha_terminacion, date):
        raise FechaTerminacionFueraDePeriodo()
    if not contrato.fecha_inicio <= fecha_terminacion <= contrato.fecha_fin:
        raise FechaTerminacionFueraDePeriodo()
    return _guardar_cambio(replace(contrato, estado="terminado"), usuario, repo)


def cambiar_estado(
    codigo: str, nuevo_estado: str, usuario: str, repo: RepositorioContratos
) -> CambioEstado:
    """Aplica exclusivamente las transiciones de estado declaradas.

    Args:
        codigo: Código del contrato registrado.
        nuevo_estado: Estado de destino solicitado.
        usuario: Usuario responsable del cambio.
        repo: Repositorio de contratos.

    Returns:
        Contrato con su nuevo estado, fecha del cambio y usuario responsable.

    Raises:
        TransicionNoPermitida: La transición o los identificadores no son válidos.
        EstadoNoModificable: El contrato está terminado o anulado.
    """
    _validar_identificacion(codigo, usuario)
    contrato = repo.consultar_por_codigo(codigo)
    _validar_transicion(contrato, nuevo_estado)
    return _guardar_cambio(replace(contrato, estado=nuevo_estado), usuario, repo)
