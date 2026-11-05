"""Conciliación de pagos bancarios por etapas reintentables."""

import csv
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

_ESTADOS = ("conciliado", "diferencia", "pago sin factura", "pendiente")
_COLUMNAS_SALIDA = (
    "referencia",
    "valor_facturado",
    "valor_pagado",
    "banco",
    "estado",
    "diferencia",
)
_FORMATOS_FECHA = {"A": "%Y-%m-%d", "B": "%d/%m/%Y", "C": "%Y/%m/%d"}
_COLUMNAS_PAGO = {
    "A": ("referencia", "valor", "fecha"),
    "B": ("REF", "MONTO", "FECHA_PAGO"),
    "C": ("referencia_factura", "valor_pagado", "fecha"),
}


class ColumnaFaltanteError(ValueError):
    """Indica el archivo y la columna obligatoria ausente."""

    def __init__(self, archivo: str, columna: str) -> None:
        """Construye el error conservando sus datos para consulta programática."""
        self.archivo = archivo
        self.columna = columna
        super().__init__(f"Archivo {archivo}: falta la columna {columna!r}")


@dataclass(frozen=True)
class Archivos:
    """Rutas de los tres archivos bancarios y del archivo de facturas."""

    banco_a: Path
    banco_b: Path
    banco_c: Path
    facturas: Path


@dataclass(frozen=True)
class FilaCruda:
    """Fila leída, con archivo y número de línea para informar rechazos."""

    archivo: str
    fila: int
    banco: str | None
    datos: dict[str, str]


@dataclass(frozen=True)
class Lectura:
    """Instantánea de las filas originales de un lote."""

    pagos: tuple[FilaCruda, ...]
    facturas: tuple[FilaCruda, ...]


@dataclass(frozen=True)
class Rechazo:
    """Fila excluida de la conciliación y motivo de su rechazo."""

    archivo: str
    fila: int
    motivo: str


@dataclass(frozen=True)
class Pago:
    """Pago normalizado, expresado en pesos enteros."""

    referencia: str
    valor: int
    fecha: date
    banco: str


@dataclass(frozen=True)
class Factura:
    """Factura normalizada; el vencimiento se conserva sin interpretarlo."""

    referencia: str
    valor: int
    vencimiento: str


@dataclass(frozen=True)
class Normalizados:
    """Pagos y facturas válidos, junto con las filas rechazadas."""

    pagos: tuple[Pago, ...]
    facturas: tuple[Factura, ...]
    rechazadas: tuple[Rechazo, ...]


@dataclass(frozen=True)
class Resultado:
    """Una fila de conciliación; None representa un importe no aplicable."""

    referencia: str
    valor_facturado: int | None
    valor_pagado: int
    banco: str
    estado: str
    diferencia: int | None


@dataclass(frozen=True)
class Informe:
    """Resultados, conteo de cada estado y detalle de filas rechazadas."""

    resultados: tuple[Resultado, ...]
    resumen: dict[str, int]
    rechazadas: tuple[Rechazo, ...]


def _leer_csv(
    ruta: Path,
    separador: str,
    columnas: tuple[str, ...],
    banco: str | None,
) -> tuple[FilaCruda, ...]:
    filas: list[FilaCruda] = []
    with ruta.open(encoding="utf-8-sig", newline="") as entrada:
        lector = csv.DictReader(entrada, delimiter=separador)
        for columna in columnas:
            if columna not in (lector.fieldnames or []):
                raise ColumnaFaltanteError(str(ruta), columna)
        for fila in lector:
            datos = {columna: fila.get(columna) or "" for columna in columnas}
            filas.append(FilaCruda(str(ruta), lector.line_num, banco, datos))
    return tuple(filas)


def leer_archivos(archivos: Archivos) -> Lectura:
    """Lee los cuatro CSV y comprueba todas sus columnas obligatorias.

    Args:
        archivos: Rutas de los archivos de entrada.

    Returns:
        Instantánea de las filas sin convertir valores ni fechas.

    Raises:
        ColumnaFaltanteError: Falta una columna obligatoria.
        OSError: No se puede leer un archivo.
        UnicodeError: Un archivo no está codificado en UTF-8.
        csv.Error: El lector CSV no puede procesar un archivo.
    """
    pagos: list[FilaCruda] = []
    for banco, ruta, separador in (
        ("A", archivos.banco_a, ";"),
        ("B", archivos.banco_b, ","),
        ("C", archivos.banco_c, ","),
    ):
        pagos.extend(_leer_csv(ruta, separador, _COLUMNAS_PAGO[banco], banco))
    facturas = _leer_csv(
        archivos.facturas, ",", ("referencia", "valor", "vencimiento"), None
    )
    return Lectura(tuple(pagos), facturas)


def _valor(texto: str) -> int:
    limpio = texto.strip()
    if re.fullmatch(r"[+-]?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)", limpio) is None:
        raise ValueError(f"valor no válido en pesos enteros: {texto!r}")
    return int(limpio.replace(".", ""))


def _normalizar_pago(fila: FilaCruda) -> Pago:
    if fila.banco not in _COLUMNAS_PAGO:
        raise ValueError(f"banco no válido: {fila.banco!r}")
    referencia, valor, fecha = _COLUMNAS_PAGO[fila.banco]
    importe = _valor(fila.datos[valor])
    fecha_pago = datetime.strptime(
        fila.datos[fecha].strip(), _FORMATOS_FECHA[fila.banco]
    ).date()
    return Pago(fila.datos[referencia].strip(), importe, fecha_pago, fila.banco)


def _normalizar_factura(fila: FilaCruda) -> Factura:
    return Factura(
        fila.datos["referencia"].strip(),
        _valor(fila.datos["valor"]),
        fila.datos["vencimiento"].strip(),
    )


def normalizar(lectura: Lectura) -> Normalizados:
    """Convierte importes y fechas, rechazando filas inválidas sin detener el lote.

    Args:
        lectura: Instantánea obtenida con leer_archivos.

    Returns:
        Filas válidas y rechazos con archivo, línea y motivo. Un valor inválido
        en pagos o facturas, o una fecha de pago inválida, rechaza solo esa fila.
    """
    pagos: list[Pago] = []
    facturas: list[Factura] = []
    rechazos: list[Rechazo] = []
    for fila in lectura.pagos:
        try:
            pagos.append(_normalizar_pago(fila))
        except ValueError as error:
            rechazos.append(Rechazo(fila.archivo, fila.fila, str(error)))
    for fila in lectura.facturas:
        try:
            facturas.append(_normalizar_factura(fila))
        except ValueError as error:
            rechazos.append(Rechazo(fila.archivo, fila.fila, str(error)))
    return Normalizados(tuple(pagos), tuple(facturas), tuple(rechazos))


def _cruzar_pago(pago: Pago, factura: Factura | None) -> Resultado:
    if factura is None:
        return Resultado(
            pago.referencia, None, pago.valor, pago.banco, "pago sin factura", None
        )
    diferencia = factura.valor - pago.valor
    estado = "conciliado" if diferencia == 0 else "diferencia"
    return Resultado(
        pago.referencia, factura.valor, pago.valor, pago.banco, estado, diferencia
    )


def conciliar(datos: Normalizados) -> Informe:
    """Cruza cada pago con su factura y agrega las facturas sin pagos.

    Args:
        datos: Pagos y facturas normalizados.

    Returns:
        Informe con una fila por pago y una por referencia pendiente. El resumen
        contiene el conteo de filas de los cuatro estados, incluidos los ceros.
    """
    facturas: dict[str, Factura] = {}
    for factura in datos.facturas:
        facturas.setdefault(factura.referencia, factura)
    resultados: list[Resultado] = []
    pagadas: set[str] = set()
    for pago in datos.pagos:
        resultados.append(_cruzar_pago(pago, facturas.get(pago.referencia)))
        pagadas.add(pago.referencia)
    for referencia, factura in facturas.items():
        if referencia not in pagadas:
            resultados.append(
                Resultado(referencia, factura.valor, 0, "", "pendiente", None)
            )
    resumen = dict.fromkeys(_ESTADOS, 0)
    for resultado in resultados:
        resumen[resultado.estado] += 1
    return Informe(tuple(resultados), resumen, datos.rechazadas)


def escribir_csv(informe: Informe, salida: Path) -> None:
    """Escribe el CSV de resultados mediante sustitución atómica.

    Args:
        informe: Resultados que se escribirán.
        salida: Archivo destino; su directorio debe existir.

    Raises:
        OSError: No se puede crear, escribir o reemplazar el archivo destino.
    """
    temporal: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=salida.parent,
            prefix=f".{salida.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            escritor = csv.writer(archivo)
            escritor.writerow(_COLUMNAS_SALIDA)
            for resultado in informe.resultados:
                escritor.writerow(
                    (
                        resultado.referencia,
                        resultado.valor_facturado,
                        resultado.valor_pagado,
                        resultado.banco,
                        resultado.estado,
                        resultado.diferencia,
                    )
                )
        os.replace(temporal, salida)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


class Lote:
    """Ejecuta y conserva en memoria las etapas completadas de un lote.

    Si una etapa falla, su resultado no se guarda. Reintentar ejecutar continúa
    desde esa etapa, sin volver a procesar las anteriores.
    """

    def __init__(self, archivos: Archivos, salida: Path) -> None:
        """Configura el lote sin leer entradas ni escribir archivos."""
        self._archivos = archivos
        self._salida = salida
        self._lectura: Lectura | None = None
        self._normalizados: Normalizados | None = None
        self._informe: Informe | None = None
        self._escrito = False

    @property
    def etapa_pendiente(self) -> str | None:
        """Devuelve la primera etapa no completada, o None si terminó el lote."""
        if self._lectura is None:
            return "lectura"
        if self._normalizados is None:
            return "normalización"
        if self._informe is None:
            return "conciliación"
        if not self._escrito:
            return "escritura"
        return None

    def leer(self) -> Lectura:
        """Ejecuta la lectura una vez; devuelve la instantánea si ya se completó."""
        if self._lectura is None:
            self._lectura = leer_archivos(self._archivos)
        return self._lectura

    def normalizar(self) -> Normalizados:
        """Normaliza una vez; exige lectura previa o lanza RuntimeError."""
        if self._lectura is None:
            raise RuntimeError("Debe completar la lectura antes de normalizar")
        if self._normalizados is None:
            self._normalizados = normalizar(self._lectura)
        return self._normalizados

    def conciliar(self) -> Informe:
        """Concilia una vez; exige normalización previa o lanza RuntimeError."""
        if self._normalizados is None:
            raise RuntimeError("Debe completar la normalización antes de conciliar")
        if self._informe is None:
            self._informe = conciliar(self._normalizados)
        return self._informe

    def escribir(self) -> Informe:
        """Escribe una vez; exige conciliación previa o lanza RuntimeError."""
        if self._informe is None:
            raise RuntimeError("Debe completar la conciliación antes de escribir")
        if not self._escrito:
            escribir_csv(self._informe, self._salida)
            self._escrito = True
        return self._informe

    def ejecutar(self) -> Informe:
        """Completa las etapas pendientes y devuelve el informe tras escribir.

        Las excepciones se propagan al llamador. Después de corregir su causa,
        invocar este método en la misma instancia reintenta la etapa fallida y
        continúa con las posteriores, sin repetir las completadas.
        """
        self.leer()
        self.normalizar()
        self.conciliar()
        return self.escribir()
