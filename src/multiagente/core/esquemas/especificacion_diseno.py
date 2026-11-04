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
    """Interfaz pública de un módulo con su firma completa.

    Una interfaz de tipo `funcion` llamada `Clase.metodo` es un método de la clase `Clase`, que el
    mismo módulo declara como interfaz de tipo `clase`. Su firma es la del método, con `self` o
    `cls` como primer parámetro: `registrar(self, prestamo: Prestamo) -> None`.
    """

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
    `Predio(numero_predial: str, area_terreno: Decimal)`; la de un método `Clase.metodo`, la del
    método con `self`. Se admiten los prefijos `def` y `class`, el de la clase en un método y los
    dos puntos finales, que el modelo a veces agrega.

    Args:
        interfaz: Interfaz pública declarada en la especificación.

    Returns:
        La definición de función equivalente, con sus parámetros y su retorno.

    Raises:
        SyntaxError: Si la firma no es una firma de Python válida.
    """
    firma = interfaz.firma.strip().removeprefix("def ").removeprefix("class ").rstrip(":").strip()
    if clase := interfaz.nombre.rpartition(".")[0]:
        firma = firma.removeprefix(f"{clase}.")
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


def _agregados_y_retirados(
    antes: list[str], despues: list[str], que: str, donde: str = "", genero: str = "o"
) -> list[str]:
    sufijo = f" en {donde}" if donde else ""
    return [
        *(f"{que} agregad{genero}{sufijo}: {v}" for v in sorted(set(despues) - set(antes))),
        *(f"{que} retirad{genero}{sufijo}: {v}" for v in sorted(set(antes) - set(despues))),
    ]


def _firma_con_clase(interfaz: InterfazPublica) -> str:
    """La firma de la interfaz; la de un método, precedida de su clase."""
    clase = interfaz.nombre.rpartition(".")[0]
    firma = interfaz.firma.strip()
    if clase and not firma.startswith(f"{clase}."):
        return f"{clase}.{firma}"
    return firma


def _cambios_de_modulo(antes: Modulo, despues: Modulo) -> list[str]:
    nombre = despues.nombre
    cambios = [
        f"{campo.capitalize()} de {nombre}: {getattr(antes, campo)} → {getattr(despues, campo)}"
        for campo in ("ruta", "capa")
        if getattr(antes, campo) != getattr(despues, campo)
    ]
    previas = {i.nombre: i for i in antes.interfaces_publicas}
    nuevas = {i.nombre: i for i in despues.interfaces_publicas}
    cambios += [
        f"Interfaz nueva en {nombre}: `{_firma_con_clase(nuevas[i])}`"
        for i in nuevas
        if i not in previas
    ]
    cambios += [f"Interfaz retirada de {nombre}: {i}" for i in previas if i not in nuevas]
    for interfaz in (i for i in nuevas if i in previas):
        previa, nueva = previas[interfaz], nuevas[interfaz]
        if previa.firma != nueva.firma:
            cambios.append(
                f"Firma de {nombre}.{interfaz}: `{_firma_con_clase(previa)}` → "
                f"`{_firma_con_clase(nueva)}`"
            )
        if sorted(previa.excepciones) != sorted(nueva.excepciones):
            cambios.append(
                f"Excepciones de {nombre}.{interfaz}: {sorted(previa.excepciones)} → "
                f"{sorted(nueva.excepciones)}"
            )
    cambios += _agregados_y_retirados(
        antes.dependencias_permitidas, despues.dependencias_permitidas, "Dependencia", nombre, "a"
    )
    cambios += _agregados_y_retirados(
        antes.requerimientos, despues.requerimientos, "Requerimiento", nombre
    )
    return cambios


def _cambios_de_entidad(antes: Entidad, despues: Entidad) -> list[str]:
    previos = {c.nombre: c for c in antes.campos}
    nuevos = {c.nombre: c for c in despues.campos}
    cambios = [
        f"Campo nuevo en {despues.nombre}: {c} ({nuevos[c].tipo})"
        for c in nuevos
        if c not in previos
    ]
    cambios += [f"Campo retirado de {despues.nombre}: {c}" for c in previos if c not in nuevos]
    cambios += [
        f"Tipo de {despues.nombre}.{c}: {previos[c].tipo} → {nuevos[c].tipo}"
        for c in nuevos
        if c in previos and previos[c].tipo != nuevos[c].tipo
    ]
    return cambios


def diferencias(previa: EspecificacionDiseno, nueva: EspecificacionDiseno) -> list[str]:
    """Describe los cambios estructurales entre dos versiones de una especificación.

    Compara la arquitectura base, los módulos con sus interfaces, el modelo de datos, las
    dependencias externas y las reglas de dependencia. Las descripciones y las
    responsabilidades no cuentan: cambian de redacción sin cambiar el diseño.

    Args:
        previa: Versión anterior.
        nueva: Versión nueva.

    Returns:
        Un cambio por línea, en el orden de la especificación; vacía si no hay cambios.
    """
    cambios: list[str] = []
    if previa.arquitectura_base != nueva.arquitectura_base:
        cambios.append(f"Arquitectura base: {previa.arquitectura_base} → {nueva.arquitectura_base}")
    modulos = {m.nombre: m for m in previa.modulos}
    for modulo in nueva.modulos:
        if modulo.nombre in modulos:
            cambios += _cambios_de_modulo(modulos[modulo.nombre], modulo)
        else:
            interfaces = ", ".join(i.nombre for i in modulo.interfaces_publicas)
            cambios.append(f"Módulo nuevo {modulo.nombre}, con {interfaces}")
    vigentes = {m.nombre for m in nueva.modulos}
    cambios += [f"Módulo retirado: {m.nombre}" for m in previa.modulos if m.nombre not in vigentes]
    entidades = {e.nombre: e for e in previa.modelo_datos}
    for entidad in nueva.modelo_datos:
        if entidad.nombre in entidades:
            cambios += _cambios_de_entidad(entidades[entidad.nombre], entidad)
        else:
            cambios.append(f"Entidad nueva: {entidad.nombre}")
    actuales = {e.nombre for e in nueva.modelo_datos}
    cambios += [
        f"Entidad retirada: {e.nombre}" for e in previa.modelo_datos if e.nombre not in actuales
    ]
    cambios += _agregados_y_retirados(
        [d.paquete for d in previa.dependencias_externas],
        [d.paquete for d in nueva.dependencias_externas],
        "Dependencia externa",
        genero="a",
    )
    cambios += _agregados_y_retirados(
        previa.reglas_de_dependencia,
        nueva.reglas_de_dependencia,
        "Regla de dependencia",
        genero="a",
    )
    return cambios
