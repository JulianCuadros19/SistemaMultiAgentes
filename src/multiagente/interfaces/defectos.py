"""Corpus de defectos inyectados a propósito para evaluar al tester (paso 10).

Cada carpeta de `evaluacion/defectos/` trae:
- un caso de desarrollo (`evaluacion/casos/desarrollo-*.json`);
- una base limpia (`base/`): código que el tester debe aprobar;
- en `defectos.json`, las inyecciones sobre esa base, cada una con el veredicto y las reglas que
  el tester debe reportar.

Una inyección que no encuentra exactamente una vez el texto que reemplaza hace fallar la carga:
así el corpus no se desalinea en silencio de su base. No contiene datos de Realtix.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from pydantic import ConfigDict, Field, ValidationError, model_validator

from multiagente.core.esquemas.comunes import ModeloEstricto, TextoObligatorio
from multiagente.interfaces.casos import CasoDesarrollo, cargar_caso_desarrollo
from multiagente.interfaces.cliente_simulado import RAIZ_EVALUACION
from multiagente.orquestador.estado import Veredicto

RAIZ_DEFECTOS = RAIZ_EVALUACION / "defectos"
RAIZ_REPOSITORIO = RAIZ_EVALUACION.parent


class Cambio(ModeloEstricto):
    """Cambio sobre un archivo de la base: reemplazo, archivo nuevo o eliminación.

    El texto se conserva tal cual, con sus saltos de línea y su sangría.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    ruta: TextoObligatorio
    buscar: str | None = None
    reemplazar: str | None = None
    contenido: str | None = None
    eliminar: bool = False

    @model_validator(mode="after")
    def _un_solo_tipo(self) -> Self:
        tipos = [self.buscar is not None, self.contenido is not None, self.eliminar]
        if sum(tipos) != 1 or (self.buscar is not None) != (self.reemplazar is not None):
            raise ValueError(
                f"{self.ruta}: un cambio es buscar y reemplazar, un contenido nuevo o eliminar"
            )
        return self


class Esperado(ModeloEstricto):
    """Lo que el tester debe dictaminar sobre una variante.

    Attributes:
        veredicto: Veredicto esperado.
        reglas: Reglas que deben aparecer en los hallazgos.
        casos_juez: Casos que el juez de N14 debe marcar como incumplidos; cualquier otro caso
            que marque el juez es un rechazo falso.
    """

    veredicto: Veredicto
    reglas: list[TextoObligatorio] = Field(default_factory=list)
    casos_juez: list[TextoObligatorio] = Field(default_factory=list)


class DefectoInyectado(ModeloEstricto):
    """Defecto inyectado en la base, con lo que el tester debe reportar."""

    id: TextoObligatorio
    clase: TextoObligatorio
    descripcion: TextoObligatorio
    cambios: list[Cambio] = Field(min_length=1)
    esperado: Esperado
    solo_juez: bool = False


class DefinicionCorpus(ModeloEstricto):
    """Contenido de `defectos.json`."""

    caso: TextoObligatorio
    descripcion: TextoObligatorio
    control: Esperado
    defectos: list[DefectoInyectado]

    @model_validator(mode="after")
    def _identificadores_unicos(self) -> Self:
        ids = [defecto.id for defecto in self.defectos]
        if repetidos := sorted({i for i in ids if ids.count(i) > 1}):
            raise ValueError(f"Defectos con identificador repetido: {repetidos}")
        return self


class ErrorCorpus(ValueError):
    """El corpus de defectos no tiene la forma esperada o no se alinea con su base."""


@dataclass(frozen=True)
class Variante:
    """Código que se somete al tester: la base limpia o una inyección sobre ella."""

    id: str
    archivos: dict[str, str]
    esperado: Esperado
    defecto: DefectoInyectado | None

    @property
    def es_control(self) -> bool:
        """Indica si la variante es la base limpia."""
        return self.defecto is None


def aplicar(base: dict[str, str], defecto: DefectoInyectado) -> dict[str, str]:
    """Aplica los cambios de una inyección sobre una copia de la base.

    Args:
        base: Archivos de la base limpia por su ruta.
        defecto: Inyección a aplicar.

    Returns:
        Los archivos con el defecto inyectado.

    Raises:
        ErrorCorpus: Si un texto a reemplazar no aparece exactamente una vez, o si se elimina un
            archivo que no existe.
    """
    archivos = dict(base)
    for cambio in defecto.cambios:
        if cambio.eliminar:
            if cambio.ruta not in archivos:
                raise ErrorCorpus(f"{defecto.id}: no existe {cambio.ruta} para eliminarlo")
            del archivos[cambio.ruta]
        elif cambio.contenido is not None:
            archivos[cambio.ruta] = cambio.contenido
        else:
            texto = archivos.get(cambio.ruta, "")
            if (veces := texto.count(cambio.buscar)) != 1:
                raise ErrorCorpus(
                    f"{defecto.id}: {cambio.ruta} contiene {veces} veces el texto a reemplazar "
                    f"{cambio.buscar[:60]!r}; debe aparecer exactamente una vez"
                )
            archivos[cambio.ruta] = texto.replace(cambio.buscar, cambio.reemplazar)
    return archivos


@dataclass(frozen=True)
class CorpusDefectos:
    """Corpus de una carpeta de `evaluacion/defectos/`, con su base y su caso cargados."""

    nombre: str
    definicion: DefinicionCorpus
    caso: CasoDesarrollo
    base: dict[str, str]

    def variantes(self) -> list[Variante]:
        """La base limpia y cada inyección, en el orden del corpus.

        Returns:
            Las variantes listas para someterse al tester.

        Raises:
            ErrorCorpus: Si alguna inyección no se alinea con la base.
        """
        variantes = [
            Variante(
                id=f"{self.nombre}-control",
                archivos=dict(self.base),
                esperado=self.definicion.control,
                defecto=None,
            )
        ]
        variantes += [
            Variante(
                id=f"{self.nombre}-{defecto.id}",
                archivos=aplicar(self.base, defecto),
                esperado=defecto.esperado,
                defecto=defecto,
            )
            for defecto in self.definicion.defectos
        ]
        return variantes


def _leer_base(carpeta: Path) -> dict[str, str]:
    return {
        archivo.relative_to(carpeta).as_posix(): archivo.read_text(encoding="utf-8")
        for archivo in sorted(carpeta.rglob("*"))
        if archivo.is_file() and "__pycache__" not in archivo.parts
    }


def cargar_corpus_defectos(carpeta: Path) -> CorpusDefectos:
    """Lee un corpus de defectos con su base y su caso de desarrollo.

    Args:
        carpeta: Carpeta con `defectos.json` y `base/`.

    Returns:
        El corpus validado.

    Raises:
        ErrorCorpus: Si falta la base, si el JSON no cumple el esquema o si alguna inyección no
            se alinea con la base.
    """
    try:
        datos = json.loads((carpeta / "defectos.json").read_text(encoding="utf-8"))
        definicion = DefinicionCorpus.model_validate(datos)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ErrorCorpus(f"{carpeta.name}: {error}") from error
    base = _leer_base(carpeta / "base")
    if not base:
        raise ErrorCorpus(f"{carpeta.name}: no tiene archivos en base/")
    corpus = CorpusDefectos(
        nombre=carpeta.name,
        definicion=definicion,
        caso=cargar_caso_desarrollo(RAIZ_REPOSITORIO / definicion.caso),
        base=base,
    )
    corpus.variantes()
    return corpus


def cargar_corpus_de_defectos(raiz: Path = RAIZ_DEFECTOS) -> list[CorpusDefectos]:
    """Lee todos los corpus de `evaluacion/defectos/`.

    Args:
        raiz: Carpeta de los corpus.

    Returns:
        Los corpus en orden de nombre.
    """
    return [
        cargar_corpus_defectos(carpeta)
        for carpeta in sorted(raiz.iterdir())
        if (carpeta / "defectos.json").is_file()
    ]
