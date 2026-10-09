"""Esquema del Anexo B: especificación de diseño que produce el agente arquitecto.

El esquema aplica la primera de las tres validaciones del Anexo B: conformidad con la
estructura y ausencia de dependencias circulares entre módulos. La cobertura de los
requerimientos aprobados y la pertenencia al catálogo tecnológico necesitan datos externos a
la especificación y se verifican en el nodo N9.
"""

import ast
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from multiagente.core.esquemas.comunes import (
    IdArquitectura,
    IdEspecificacion,
    IdRequerimiento,
    ModeloEstricto,
    TextoObligatorio,
    Version,
    repetidos,
)

NombreModulo = Annotated[str, StringConstraints(pattern=r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$")]
"""Nombre importable del módulo en notación de puntos, p. ej. `dominio.predio`."""

RutaModulo = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_/.-]*\.py$")]
"""Ruta relativa del archivo Python del módulo, p. ej. `src/dominio/predio.py`."""


class TipoInterfaz(StrEnum):
    """Tipo de interfaz pública que declara un módulo."""

    CLASE = "clase"
    FUNCION = "funcion"


class InterfazPublica(ModeloEstricto):
    """Interfaz pública de un módulo con su firma completa."""

    nombre: TextoObligatorio
    tipo: TipoInterfaz
    firma: TextoObligatorio
    descripcion: TextoObligatorio
    excepciones: list[TextoObligatorio] = Field(default_factory=list)


class Modulo(ModeloEstricto):
    """Módulo de la especificación, con sus interfaces, dependencias y requerimientos."""

    nombre: NombreModulo
    ruta: RutaModulo
    responsabilidad: TextoObligatorio
    capa: TextoObligatorio
    interfaces_publicas: list[InterfazPublica] = Field(min_length=1)
    dependencias_permitidas: list[NombreModulo] = Field(default_factory=list)
    requerimientos: list[IdRequerimiento] = Field(min_length=1)

    @model_validator(mode="after")
    def _interfaces_unicas(self) -> Self:
        if duplicados := repetidos(interfaz.nombre for interfaz in self.interfaces_publicas):
            raise ValueError(f"Interfaces repetidas en {self.nombre}: {duplicados}")
        return self


class Campo(ModeloEstricto):
    """Campo de una entidad del modelo de datos."""

    nombre: TextoObligatorio
    tipo: TextoObligatorio
    obligatorio: bool
    restriccion: TextoObligatorio | None = None


class Entidad(ModeloEstricto):
    """Entidad del modelo de datos con sus campos."""

    nombre: TextoObligatorio
    campos: list[Campo] = Field(min_length=1)

    @model_validator(mode="after")
    def _campos_unicos(self) -> Self:
        if duplicados := repetidos(campo.nombre for campo in self.campos):
            raise ValueError(f"Campos repetidos en la entidad {self.nombre}: {duplicados}")
        return self


class DependenciaExterna(ModeloEstricto):
    """Librería externa que emplea el módulo, con su propósito."""

    paquete: TextoObligatorio
    proposito: TextoObligatorio


class EspecificacionDiseno(ModeloEstricto):
    """Especificación de diseño (Anexo B, Tabla 29).

    `modelo_datos`, `dependencias_externas` y `reglas_de_dependencia` son obligatorios pero
    pueden ir vacíos; `dependencias_permitidas` de cada módulo vale lista vacía si se omite.
    """

    id_especificacion: IdEspecificacion
    version: Version
    arquitectura_base: IdArquitectura
    requerimientos_cubiertos: list[IdRequerimiento] = Field(min_length=1)
    modulos: list[Modulo] = Field(min_length=1)
    modelo_datos: list[Entidad]
    dependencias_externas: list[DependenciaExterna]
    reglas_de_dependencia: list[TextoObligatorio]

    @model_validator(mode="after")
    def _estructura_consistente(self) -> Self:
        if duplicados := repetidos(self.requerimientos_cubiertos):
            raise ValueError(f"Requerimientos cubiertos repetidos: {duplicados}")
        if duplicados := repetidos(modulo.nombre for modulo in self.modulos):
            raise ValueError(f"Módulos con nombre repetido: {duplicados}")
        if duplicados := repetidos(modulo.ruta for modulo in self.modulos):
            raise ValueError(f"Módulos con ruta repetida: {duplicados}")
        if duplicados := repetidos(entidad.nombre for entidad in self.modelo_datos):
            raise ValueError(f"Entidades repetidas en el modelo de datos: {duplicados}")
        if duplicados := repetidos(
            dependencia.paquete for dependencia in self.dependencias_externas
        ):
            raise ValueError(f"Dependencias externas repetidas: {duplicados}")

        declarados = {modulo.nombre for modulo in self.modulos}
        cubiertos = set(self.requerimientos_cubiertos)
        for modulo in self.modulos:
            if desconocidos := sorted(set(modulo.dependencias_permitidas) - declarados):
                raise ValueError(
                    f"El módulo {modulo.nombre} depende de módulos no declarados: {desconocidos}"
                )
            if ajenos := sorted(set(modulo.requerimientos) - cubiertos):
                raise ValueError(
                    f"El módulo {modulo.nombre} tiene requerimientos que la especificación no "
                    f"declara como cubiertos: {ajenos}"
                )

        if ciclo := buscar_ciclo({m.nombre: m.dependencias_permitidas for m in self.modulos}):
            raise ValueError(f"Dependencias circulares entre módulos: {' -> '.join(ciclo)}")
        return self


def firma_como_funcion(interfaz: InterfazPublica) -> ast.FunctionDef:
    """Interpreta la firma de una interfaz como una definición de función, aunque sea de clase.

    La firma de una clase es la de su constructor sin `self`, p. ej.
    `Predio(numero_predial: str, area_terreno: Decimal)`. Se admiten los prefijos `def` y
    `class` y los dos puntos finales, que el modelo a veces agrega.

    Args:
        interfaz: Interfaz pública declarada en la especificación.

    Returns:
        La definición de función equivalente, con sus parámetros y su retorno.

    Raises:
        SyntaxError: Si la firma no es una firma de Python válida.
    """
    firma = interfaz.firma.strip().removeprefix("def ").removeprefix("class ").rstrip(":").strip()
    arbol = ast.parse(f"def {firma}: ...")
    funcion = arbol.body[0]
    if len(arbol.body) != 1 or not isinstance(funcion, ast.FunctionDef):
        raise SyntaxError("no es una firma")
    return funcion


def buscar_ciclo(dependencias: dict[str, list[str]]) -> list[str] | None:
    """Busca un ciclo en el grafo de dependencias entre módulos.

    Args:
        dependencias: Para cada módulo, los módulos que puede importar.

    Returns:
        El ciclo encontrado, con el primer módulo repetido al final, o None si no hay ciclos.
    """
    en_curso: list[str] = []
    terminados: set[str] = set()

    def visitar(modulo: str) -> list[str] | None:
        if modulo in en_curso:
            return [*en_curso[en_curso.index(modulo) :], modulo]
        if modulo in terminados:
            return None
        en_curso.append(modulo)
        for dependencia in dependencias.get(modulo, []):
            if ciclo := visitar(dependencia):
                return ciclo
        en_curso.pop()
        terminados.add(modulo)
        return None

    for modulo in sorted(dependencias):
        if ciclo := visitar(modulo):
            return ciclo
    return None
