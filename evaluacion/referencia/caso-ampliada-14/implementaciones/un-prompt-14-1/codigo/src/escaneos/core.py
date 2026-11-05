"""Reglas de nombres y operaciones sobre una carpeta de escaneos."""

import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

Operacion = Literal["validar", "renombrar", "reporte"]
Estado = Literal[
    "Válido", "Inválido", "Sin cambios", "Renombrado", "Simulado", "Conflicto", "Error"
]

_TIPOS = frozenset({"ESC", "CER", "PAZ"})
_PATRON = re.compile(r"([^_ -]+)([_ -])([0-9]{4})([_ -])([0-9]+)")


@dataclass(frozen=True)
class InspeccionNombre:
    """Descripción de un nombre y, si es corregible, su destino canónico."""

    nombre: str
    destino: str | None
    motivos: tuple[str, ...]

    @property
    def valido(self) -> bool:
        """Indicar si el nombre ya cumple exactamente la convención."""
        return self.destino == self.nombre


@dataclass(frozen=True)
class ResultadoArchivo:
    """Resultado individual de una operación sobre un archivo."""

    nombre: str
    estado: Estado
    motivo: str
    destino: str | None = None


@dataclass(frozen=True)
class Informe:
    """Resultados por archivo y conteos del reporte."""

    operacion: Operacion
    archivos: tuple[ResultadoArchivo, ...]
    por_anio: dict[int, int]
    por_tipo: dict[str, int]

    @property
    def total(self) -> int:
        """Obtener el número de archivos examinados."""
        return len(self.archivos)

    @property
    def totales(self) -> dict[str, int]:
        """Contar los resultados de cada estado presente."""
        return dict(sorted(Counter(archivo.estado for archivo in self.archivos).items()))

    @property
    def codigo_salida(self) -> int:
        """Obtener 0 para éxito, 1 para incidencias o 2 para errores de E/S."""
        estados = self.totales
        if "Error" in estados:
            return 2
        if "Inválido" in estados or "Conflicto" in estados:
            return 1
        return 0


def inspeccionar_nombre(nombre: str) -> InspeccionNombre:
    """Validar un nombre sin acceder al disco y calcular una corrección segura.

    El año máximo se obtiene de la fecha local actual. Un destino nulo indica
    que no es posible corregir el nombre mediante las reglas permitidas.
    """
    base, punto, extension = nombre.rpartition(".")
    errores: list[str] = []
    if not punto or extension.lower() != "pdf":
        errores.append("Extensión distinta de pdf")
    coincidencia = _PATRON.fullmatch(base)
    if coincidencia is None:
        errores.append("Formato inválido: se espera TIPO_AAAA_NNNNN.pdf")
        return InspeccionNombre(nombre, None, tuple(errores))

    tipo, separador1, anio, separador2, consecutivo = coincidencia.groups()
    if tipo.upper() not in _TIPOS:
        errores.append("Tipo desconocido")
    if not 1950 <= int(anio) <= date.today().year:
        errores.append(f"Año fuera del rango 1950–{date.today().year}")
    if len(consecutivo) > 5:
        errores.append("Consecutivo con más de cinco dígitos")
    if errores:
        return InspeccionNombre(nombre, None, tuple(errores))

    motivos = tuple(
        mensaje
        for condicion, mensaje in (
            (tipo != tipo.upper(), "Tipo debe estar en mayúsculas"),
            (
                separador1 != "_" or separador2 != "_",
                "Separadores deben ser guiones bajos",
            ),
            (len(consecutivo) < 5, "Consecutivo debe tener cinco dígitos"),
            (extension != "pdf", "Extensión debe ser .pdf"),
        )
        if condicion
    )
    destino = f"{tipo.upper()}_{anio}_{consecutivo.zfill(5)}.pdf"
    return InspeccionNombre(nombre, destino, motivos)


def _validar(inspeccion: InspeccionNombre) -> ResultadoArchivo:
    """Crear el resultado de validación de un nombre."""
    if inspeccion.valido:
        return ResultadoArchivo(inspeccion.nombre, "Válido", "Nombre conforme")
    return ResultadoArchivo(inspeccion.nombre, "Inválido", "; ".join(inspeccion.motivos))


def _mover_sin_sobrescribir(origen: Path, destino: Path) -> None:
    """Mover usando un enlace exclusivo y eliminar después el nombre original."""
    os.link(origen, destino, follow_symlinks=False)
    try:
        origen.unlink()
    except OSError:
        # El original sigue disponible; intentar deshacer el enlace recién creado.
        destino.unlink()
        raise


def _renombrar(
    carpeta: Path,
    inspeccion: InspeccionNombre,
    ocupados: set[str],
    simular: bool,
) -> ResultadoArchivo:
    """Corregir un archivo o reservar su destino durante una simulación."""
    nombre = inspeccion.nombre
    destino = inspeccion.destino
    if destino is None:
        return _validar(inspeccion)
    if inspeccion.valido:
        return ResultadoArchivo(nombre, "Sin cambios", "Nombre conforme")
    if destino in ocupados:
        return ResultadoArchivo(nombre, "Conflicto", "El destino ya existe", destino)
    if not simular:
        try:
            _mover_sin_sobrescribir(carpeta / nombre, carpeta / destino)
        except FileExistsError:
            return ResultadoArchivo(nombre, "Conflicto", "El destino ya existe", destino)
        except OSError as error:
            return ResultadoArchivo(nombre, "Error", str(error), destino)
    ocupados.discard(nombre)
    ocupados.add(destino)
    estado: Estado = "Simulado" if simular else "Renombrado"
    return ResultadoArchivo(nombre, estado, "; ".join(inspeccion.motivos), destino)


def _reportar(inspeccion: InspeccionNombre) -> ResultadoArchivo:
    """Indicar los datos contables de un nombre válido."""
    if not inspeccion.valido:
        return _validar(inspeccion)
    tipo, anio, _ = inspeccion.nombre.split("_")
    return ResultadoArchivo(inspeccion.nombre, "Válido", f"Año: {anio}; Tipo: {tipo}")


def _conteos(
    resultados: list[ResultadoArchivo],
) -> tuple[dict[int, int], dict[str, int]]:
    """Contar únicamente nombres válidos por año y por tipo."""
    anios: Counter[int] = Counter()
    tipos: Counter[str] = Counter()
    for resultado in resultados:
        if resultado.estado == "Válido":
            tipo, anio, _ = resultado.nombre.split("_")
            anios[int(anio)] += 1
            tipos[tipo] += 1
    return dict(sorted(anios.items())), dict(sorted(tipos.items()))


def _entradas(carpeta: Path) -> tuple[Path, ...]:
    """Comprobar la carpeta y obtener una instantánea ordenada de sus entradas."""
    if not carpeta.exists():
        raise FileNotFoundError(f"La carpeta no existe: {carpeta}")
    if not carpeta.is_dir():
        raise NotADirectoryError(f"La ruta no es una carpeta: {carpeta}")
    return tuple(sorted(carpeta.iterdir(), key=lambda entrada: entrada.name))


def procesar(
    carpeta: str | Path,
    operacion: Operacion,
    *,
    simular: bool = False,
) -> Informe:
    """Ejecutar una operación sobre los archivos directos de una carpeta.

    No recorre subcarpetas ni sigue enlaces simbólicos. Las operaciones validar
    y reporte son de solo lectura. Los errores de carpeta se propagan como
    OSError; los errores individuales de renombrado quedan en el informe.

    Raises:
        ValueError: Si la operación no existe o la simulación no es de renombrado.
        OSError: Si no se puede acceder a la carpeta.
    """
    if operacion not in {"validar", "renombrar", "reporte"}:
        raise ValueError(f"Operación desconocida: {operacion}")
    if simular and operacion != "renombrar":
        raise ValueError("La simulación solo está disponible para renombrar")
    ruta = Path(carpeta)
    entradas = _entradas(ruta)
    ocupados = {entrada.name for entrada in entradas}
    resultados: list[ResultadoArchivo] = []
    for entrada in entradas:
        if entrada.is_symlink() or not entrada.is_file():
            continue
        inspeccion = inspeccionar_nombre(entrada.name)
        if operacion == "renombrar":
            resultado = _renombrar(ruta, inspeccion, ocupados, simular)
        elif operacion == "validar":
            resultado = _validar(inspeccion)
        else:
            resultado = _reportar(inspeccion)
        resultados.append(resultado)
    anios, tipos = _conteos(resultados) if operacion == "reporte" else ({}, {})
    return Informe(operacion, tuple(resultados), anios, tipos)
