"""Esquemas del Anexo A: backlog de historias de usuario y requerimiento funcional formal.

La estructura sigue `docs/anexos.md`. Las reglas de redacción (QUIERO en infinitivo, ausencia de
marcadores pendientes, escenario de error) son atributos de calidad que verifica el RF-07; el
esquema solo exige la estructura.
"""

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from multiagente.core.esquemas.comunes import (
    Enunciado,
    IdEscenario,
    IdHistoria,
    IdRequerimiento,
    Impacto,
    ModeloEstricto,
    Prioridad,
    TextoObligatorio,
    Version,
    repetidos,
)


class TipoSolicitud(StrEnum):
    """Tipo de solicitud de la ficha del requerimiento (Anexo A)."""

    NUEVO = "nuevo"
    ADICIONAL = "adicional"
    AJUSTE = "ajuste"
    CORRECCION = "correccion"


class HistoriaUsuario(ModeloEstricto):
    """Fila del backlog de historias de usuario (Anexo A, Tabla 27)."""

    id: IdHistoria
    enunciado: Enunciado
    epica: TextoObligatorio | None = None
    prioridad: Prioridad | None = None
    supuestos: list[TextoObligatorio] = Field(default_factory=list)
    preguntas_abiertas: list[TextoObligatorio] = Field(default_factory=list)


class BacklogHistorias(ModeloEstricto):
    """Backlog de historias de usuario que entrega el agente elicitador."""

    historias: list[HistoriaUsuario] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_unicos(self) -> Self:
        if duplicados := repetidos(historia.id for historia in self.historias):
            raise ValueError(f"Historias con identificador repetido: {duplicados}")
        return self


class DatoEntrada(ModeloEstricto):
    """Dato que recibe la funcionalidad, con su restricción de dominio si la tiene."""

    nombre: TextoObligatorio
    tipo: TextoObligatorio
    obligatorio: bool
    restriccion: TextoObligatorio | None = None


class DatoSalida(ModeloEstricto):
    """Resultado que produce la funcionalidad."""

    nombre: TextoObligatorio
    tipo: TextoObligatorio
    formato: TextoObligatorio | None = None


class Descripcion(ModeloEstricto):
    """Descripción del requerimiento: precondición, regla de negocio y datos."""

    precondicion: TextoObligatorio
    regla_negocio: TextoObligatorio
    datos_entrada: list[DatoEntrada]
    datos_salida: list[DatoSalida]

    @model_validator(mode="after")
    def _nombres_unicos(self) -> Self:
        for campo, datos in (
            ("datos_entrada", self.datos_entrada),
            ("datos_salida", self.datos_salida),
        ):
            if duplicados := repetidos(dato.nombre for dato in datos):
                raise ValueError(f"Nombres repetidos en {campo}: {duplicados}")
        return self


class EscenarioAceptacion(ModeloEstricto):
    """Criterio de aceptación en formato Gherkin: dado que, cuando, entonces."""

    id: IdEscenario
    nombre: TextoObligatorio | None = None
    dado_que: TextoObligatorio
    cuando: TextoObligatorio
    entonces: TextoObligatorio


class RequerimientoFormal(ModeloEstricto):
    """Ficha de detalle del requerimiento funcional (Anexo A, Tabla 28)."""

    id_requerimiento: IdRequerimiento
    version: Version
    proyecto: TextoObligatorio
    tipo_solicitud: TipoSolicitud
    impacto: Impacto
    modulo: TextoObligatorio
    riesgo: TextoObligatorio | None = None
    autor: TextoObligatorio
    area_funcional: TextoObligatorio
    funcional_responsable: TextoObligatorio | None = None
    titulo: Enunciado
    descripcion: Descripcion
    criterios_aceptacion: list[EscenarioAceptacion] = Field(min_length=1)
    prioridad: Prioridad
    requerimientos_relacionados: list[IdRequerimiento] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistencia(self) -> Self:
        if duplicados := repetidos(escenario.id for escenario in self.criterios_aceptacion):
            raise ValueError(f"Escenarios con identificador repetido: {duplicados}")
        if duplicados := repetidos(self.requerimientos_relacionados):
            raise ValueError(f"Requerimientos relacionados repetidos: {duplicados}")
        if self.id_requerimiento in self.requerimientos_relacionados:
            raise ValueError("Un requerimiento no puede declararse relacionado consigo mismo")
        return self
