"""Convención de nombres y resultados de las operaciones sobre escaneos."""

import re
from dataclasses import dataclass
from datetime import date


class CarpetaNoExiste(FileNotFoundError):
    """Indica que la carpeta solicitada no existe.

    Args:
        mensaje: Descripción del problema de acceso a la carpeta.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción con el mensaje indicado.

        Args:
            mensaje: Descripción del problema de acceso a la carpeta.
        """
        super().__init__(mensaje)


class FormatoInvalido(ValueError):
    """Indica que el nombre no cumple la estructura requerida.

    Args:
        mensaje: Descripción del incumplimiento.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción con el mensaje indicado."""
        super().__init__(mensaje)


class TipoDesconocido(ValueError):
    """Indica que el tipo no corresponde a ESC, CER o PAZ.

    Args:
        mensaje: Descripción del incumplimiento.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción con el mensaje indicado."""
        super().__init__(mensaje)


class AnioFueraDeRango(ValueError):
    """Indica que el año no pertenece al intervalo admitido.

    Args:
        mensaje: Descripción del incumplimiento.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción con el mensaje indicado."""
        super().__init__(mensaje)


class ExtensionInvalida(ValueError):
    """Indica que la extensión no es pdf.

    Args:
        mensaje: Descripción del incumplimiento.
    """

    def __init__(self, mensaje: str) -> None:
        """Inicializa la excepción con el mensaje indicado."""
        super().__init__(mensaje)


@dataclass(frozen=True)
class EstructuraNombre:
    """Representa los componentes de un nombre válido.

    Args:
        tipo: ESC, CER o PAZ.
        anio: Año entre 1950 y el año actual.
        consecutivo: Entero entre 0 y 99999.
        extension: Extensión pdf.
    """

    tipo: str
    anio: int
    consecutivo: int
    extension: str

    def __post_init__(self) -> None:
        """Valida los componentes recibidos.

        Raises:
            TipoDesconocido: El tipo no es conocido.
            AnioFueraDeRango: El año no pertenece al intervalo admitido.
            FormatoInvalido: El consecutivo no es un entero de hasta cinco dígitos.
            ExtensionInvalida: La extensión no es pdf.
        """
        _validar_componentes(self.tipo, self.anio, self.consecutivo, self.extension, None)


@dataclass(frozen=True)
class ResultadoValidacion:
    """Describe el incumplimiento de un archivo.

    Args:
        archivo: Nombre del archivo.
        motivo: Descripción del incumplimiento.
    """

    archivo: str
    motivo: str


@dataclass(frozen=True)
class CambioNombre:
    """Representa un cambio propuesto o aplicado.

    Args:
        anterior: Nombre original.
        nuevo: Nombre que cumple la convención.
    """

    anterior: str
    nuevo: str

    def __post_init__(self) -> None:
        """Comprueba que el destino cumple la convención.

        Raises:
            FormatoInvalido: La estructura del destino es inválida.
            TipoDesconocido: El tipo del destino es desconocido.
            AnioFueraDeRango: El año del destino está fuera de rango.
            ExtensionInvalida: La extensión del destino no es pdf.
        """
        analizar_nombre(self.nuevo, None)


@dataclass(frozen=True)
class ConflictoRenombrado:
    """Describe un destino ocupado.

    Args:
        archivo: Nombre original.
        motivo: Motivo Conflicto.
    """

    archivo: str
    motivo: str


@dataclass(frozen=True)
class ErrorRenombrado:
    """Describe un nombre que no puede corregirse.

    Args:
        archivo: Nombre original.
        motivo: Descripción del error de dominio.
    """

    archivo: str
    motivo: str


@dataclass(frozen=True)
class Reporte:
    """Contiene las líneas de detalle y los totales del reporte.

    Args:
        lineas_por_archivo: Una línea por archivo encontrado.
        conteos_por_anio_y_tipo: Conteos de nombres válidos por año y tipo.
        total_archivos: Suma de los conteos.
    """

    lineas_por_archivo: list[str]
    conteos_por_anio_y_tipo: dict[int, dict[str, int]]
    total_archivos: int


def _extraer(nombre: str) -> tuple[str, int, int, str]:
    if not isinstance(nombre, str):
        raise FormatoInvalido("El nombre debe ser texto")
    coincidencia = re.fullmatch(r"([A-Za-z]+)[_ -]([0-9]{4})[_ -]([0-9]+)\.([A-Za-z0-9]+)", nombre)
    if coincidencia is None:
        raise FormatoInvalido("No cumple la convención TIPO_AAAA_NNNNN.pdf")
    tipo, anio, consecutivo, extension = coincidencia.groups()
    if len(consecutivo) > 5:
        raise FormatoInvalido("El consecutivo debe tener entre uno y cinco dígitos")
    return tipo, int(anio), int(consecutivo), extension


def _validar_componentes(
    tipo: str, anio: int, consecutivo: int, extension: str, anio_actual: int | None
) -> None:
    limite = date.today().year if anio_actual is None else anio_actual
    if tipo not in ("ESC", "CER", "PAZ"):
        raise TipoDesconocido("Tipo desconocido: debe ser ESC, CER o PAZ")
    if type(limite) is not int or limite < 1950:
        raise AnioFueraDeRango("El año actual debe ser un entero mayor o igual a 1950")
    if type(anio) is not int or not 1950 <= anio <= limite:
        raise AnioFueraDeRango(f"Año fuera de rango: debe estar entre 1950 y {limite}")
    if type(consecutivo) is not int or not 0 <= consecutivo <= 99999:
        raise FormatoInvalido("El consecutivo debe estar entre 0 y 99999")
    if extension != "pdf":
        raise ExtensionInvalida("Extensión distinta de pdf")


def analizar_nombre(nombre: str, anio_actual: int | None) -> EstructuraNombre:
    """Analiza un nombre que debe cumplir exactamente la convención.

    Args:
        nombre: Nombre del archivo, sin ruta.
        anio_actual: Límite superior del año; None utiliza el año del calendario local.

    Returns:
        Componentes del nombre válido.

    Raises:
        FormatoInvalido: La estructura, las mayúsculas o el consecutivo son incorrectos.
        TipoDesconocido: El tipo es desconocido.
        AnioFueraDeRango: El año está fuera del intervalo admitido.
        ExtensionInvalida: La extensión no es exactamente pdf.
    """
    tipo, anio, consecutivo, extension = _extraer(nombre)
    if "-" in nombre or " " in nombre:
        raise FormatoInvalido(
            "No cumple la convención TIPO_AAAA_NNNNN.pdf: "
            "los separadores deben ser guiones bajos"
        )
    _validar_componentes(tipo.upper(), anio, consecutivo, extension, anio_actual)
    esperado = f"{tipo.upper()}_{anio:04d}_{consecutivo:05d}.pdf"
    if nombre != esperado:
        raise FormatoInvalido("No cumple la convención TIPO_AAAA_NNNNN.pdf")
    # El constructor usa el calendario real; aquí el límite explícito ya fue verificado.
    if anio > date.today().year:
        raise AnioFueraDeRango("Año fuera de rango: supera el año actual del calendario")
    return EstructuraNombre(tipo, anio, consecutivo, extension)


def normalizar_nombre(nombre: str) -> str:
    """Corrige únicamente los aspectos normalizables del nombre.

    Args:
        nombre: Nombre original del archivo, sin ruta.

    Returns:
        Nombre con tipo en mayúsculas, separadores bajos y consecutivo de cinco dígitos.

    Raises:
        FormatoInvalido: La estructura no es corregible.
        TipoDesconocido: El tipo es desconocido.
        AnioFueraDeRango: El año está fuera del intervalo admitido.
        ExtensionInvalida: La extensión no es pdf ni PDF.
    """
    tipo, anio, consecutivo, extension = _extraer(nombre)
    extension = "pdf" if extension == "PDF" else extension
    _validar_componentes(tipo.upper(), anio, consecutivo, extension, None)
    return f"{tipo.upper()}_{anio:04d}_{consecutivo:05d}.pdf"
