"""Reglas de nombres y procesamiento de una carpeta sin examinar los documentos."""

import os
import re
from collections import Counter
from contextlib import suppress
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

Modo = Literal["validar", "renombrar", "reportar"]
_PATRON = re.compile(r"([A-Za-z]+)[_-]([0-9]{4})[_-]([0-9]+)")
_TIPOS = {"ESC", "CER", "PAZ"}


class CarpetaError(Exception):
    """Indica que no se pudo obtener la lista de archivos de la carpeta."""


@dataclass(frozen=True)
class Evaluacion:
    """Describe un nombre, su posible corrección y los motivos de incumplimiento."""

    nombre: str
    destino: str | None
    motivos: tuple[str, ...]
    tipo: str | None
    anio: int | None

    @property
    def correcto(self) -> bool:
        """Indica si el nombre original cumple exactamente la convención."""
        return self.destino == self.nombre


@dataclass(frozen=True)
class Resultado:
    """Representa la línea de resultado de un archivo procesado."""

    nombre: str
    estado: str
    detalle: str
    destino: str | None = None


@dataclass(frozen=True)
class Informe:
    """Contiene los resultados y los conteos del modo de reporte."""

    resultados: tuple[Resultado, ...]
    por_anio: dict[int, int]
    por_tipo: dict[str, int]

    @property
    def totales(self) -> dict[str, int]:
        """Devuelve las cantidades por estado presente en el informe."""
        return dict(Counter(resultado.estado for resultado in self.resultados))

    @property
    def codigo_salida(self) -> int:
        """Devuelve uno ante incumplimientos, errores o conflictos; cero en otro caso."""
        estados_error = {"No cumple", "Error", "Conflicto"}
        return int(any(item.estado in estados_error for item in self.resultados))


def _motivos_correccion(
    nombre: str, cuerpo: str, extension: str, tipo: str, numero: str,
) -> tuple[str, ...]:
    motivos: list[str] = []
    if tipo != tipo.upper():
        motivos.append("El tipo debe estar en mayúsculas")
    if "-" in cuerpo:
        motivos.append("Los separadores deben ser guiones bajos")
    if len(numero) < 5:
        motivos.append("El consecutivo debe tener cinco dígitos")
    if extension != "pdf":
        motivos.append("La extensión debe ser .pdf en minúsculas")
    return tuple(motivos)


def evaluar_nombre(nombre: str, *, anio_actual: int | None = None) -> Evaluacion:
    """Evalúa un nombre usando el año local actual, o el año indicado para pruebas.

    Únicamente admite letras ASCII para el tipo y dígitos ASCII para año y
    consecutivo. Un destino nulo significa que el nombre no admite corrección.
    """
    limite = date.today().year if anio_actual is None else anio_actual
    cuerpo, separador, extension = nombre.rpartition(".")
    if not separador or extension.lower() != "pdf":
        return Evaluacion(nombre, None, ("La extensión debe ser pdf",), None, None)
    coincidencia = _PATRON.fullmatch(cuerpo)
    if coincidencia is None:
        motivo = "Formato inválido: se requiere TIPO_AAAA_NNNNN.pdf"
        return Evaluacion(nombre, None, (motivo,), None, None)
    tipo, anio_texto, numero = coincidencia.groups()
    anio = int(anio_texto)
    errores: list[str] = []
    if tipo.upper() not in _TIPOS:
        errores.append("Tipo desconocido: debe ser ESC, CER o PAZ")
    if not 1950 <= anio <= limite:
        errores.append(f"Año fuera de rango: debe estar entre 1950 y {limite}")
    if len(numero) > 5:
        errores.append("El consecutivo no puede tener más de cinco dígitos")
    if errores:
        return Evaluacion(nombre, None, tuple(errores), None, None)
    destino = f"{tipo.upper()}_{anio_texto}_{numero.zfill(5)}.pdf"
    motivos = _motivos_correccion(nombre, cuerpo, extension, tipo, numero)
    return Evaluacion(nombre, destino, motivos, tipo.upper(), anio)


def _listar(carpeta: Path) -> list[Path]:
    try:
        with os.scandir(carpeta) as entradas:
            archivos = [
                carpeta / entrada.name
                for entrada in entradas
                if entrada.is_file(follow_symlinks=False)
            ]
        return sorted(archivos, key=lambda archivo: archivo.name)
    except FileNotFoundError as error:
        raise CarpetaError(f"La carpeta no existe: {carpeta}") from error
    except NotADirectoryError as error:
        raise CarpetaError(f"La ruta no es una carpeta: {carpeta}") from error
    except OSError as error:
        raise CarpetaError(f"No se puede leer la carpeta {carpeta}: {error}") from error


def _mover_sin_sobrescribir(origen: Path, destino: Path) -> None:
    # La creación del enlace es exclusiva: nunca reemplaza un destino existente.
    os.link(origen, destino, follow_symlinks=False)
    try:
        origen.unlink()
    except OSError:
        with suppress(OSError):
            destino.unlink()
        raise


def _resultado_lectura(evaluacion: Evaluacion) -> Resultado:
    if evaluacion.correcto:
        return Resultado(evaluacion.nombre, "Correcto", "Cumple la convención")
    estado = "Error" if evaluacion.destino is None else "No cumple"
    return Resultado(
        evaluacion.nombre, estado, "; ".join(evaluacion.motivos), evaluacion.destino,
    )


def _resultado_renombrado(
    carpeta: Path,
    evaluacion: Evaluacion,
    destinos: Counter[str],
    simular: bool,
) -> Resultado:
    if evaluacion.correcto or evaluacion.destino is None:
        return _resultado_lectura(evaluacion)
    nombre = evaluacion.nombre
    destino = carpeta / evaluacion.destino
    if destinos[evaluacion.destino] > 1 or os.path.lexists(destino):
        return Resultado(nombre, "Conflicto", "Conflicto", evaluacion.destino)
    if simular:
        return Resultado(nombre, "Cambio", "Simulación: no se modificó", evaluacion.destino)
    try:
        _mover_sin_sobrescribir(carpeta / nombre, destino)
    except FileExistsError:
        return Resultado(nombre, "Conflicto", "Conflicto", evaluacion.destino)
    except OSError as error:
        return Resultado(nombre, "Error", f"No se pudo renombrar: {error}", evaluacion.destino)
    return Resultado(nombre, "Renombrado", "Cambio aplicado", evaluacion.destino)


def procesar_carpeta(
    carpeta: str | Path,
    modo: Modo = "validar",
    *,
    simular: bool = False,
    anio_actual: int | None = None,
) -> Informe:
    """Procesa archivos directos y devuelve resultados sin imprimirlos.

    El reporte cuenta únicamente nombres ya correctos. Los conflictos se
    comprueban para todos los destinos antes de realizar cualquier cambio.

    Raises:
        CarpetaError: Si no se puede listar la carpeta.
        ValueError: Si el modo no existe o la simulación no es de renombrado.
    """
    if modo not in {"validar", "renombrar", "reportar"}:
        raise ValueError("Modo desconocido")
    if simular and modo != "renombrar":
        raise ValueError("La simulación solo se admite en el modo renombrar")
    ruta = Path(carpeta)
    evaluaciones = [
        evaluar_nombre(archivo.name, anio_actual=anio_actual) for archivo in _listar(ruta)
    ]
    destinos = Counter(item.destino for item in evaluaciones if item.destino is not None)
    resultados: list[Resultado] = []
    por_anio: Counter[int] = Counter()
    por_tipo: Counter[str] = Counter()
    for item in evaluaciones:
        if modo == "renombrar":
            resultado = _resultado_renombrado(ruta, item, destinos, simular)
        else:
            resultado = _resultado_lectura(item)
        resultados.append(resultado)
        if modo == "reportar" and item.correcto:
            if item.anio is not None and item.tipo is not None:
                por_anio[item.anio] += 1
                por_tipo[item.tipo] += 1
    return Informe(tuple(resultados), dict(sorted(por_anio.items())), dict(sorted(por_tipo.items())))
