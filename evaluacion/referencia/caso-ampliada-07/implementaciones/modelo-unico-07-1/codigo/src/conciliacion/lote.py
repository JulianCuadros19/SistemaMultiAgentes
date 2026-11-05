"""Lectura, normalización, conciliación y escritura con resultados conservados."""

import csv
import json
import os
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory

_ETAPAS = ("lectura", "normalizacion", "conciliacion", "escritura")
_ESTADOS = ("conciliada", "con_diferencia", "pendiente", "pago_sin_factura", "revision")
_ESQUEMAS = {
    "A": (";", "referencia", "valor", "fecha", "%Y-%m-%d"),
    "B": (",", "REF", "MONTO", "FECHA_PAGO", "%d/%m/%Y"),
    "C": (",", "referencia_factura", "valor_pagado", "fecha", "%Y/%m/%d"),
    "facturas": (",", "referencia", "valor", "vencimiento", ""),
}
_COLUMNAS = ("referencia", "valor_facturado", "valor_pagado", "banco", "estado", "diferencia")


@dataclass(frozen=True)
class Entrada:
    """Archivo CSV y origen: A, B, C o facturas."""

    origen: str
    ruta: str | Path


@dataclass(frozen=True)
class Incidencia:
    """Problema localizado; una fila nula indica un problema de archivo."""

    etapa: str
    archivo: str
    fila: int | None
    columna: str | None
    mensaje: str


@dataclass(frozen=True)
class Detalle:
    """Registro del reporte; los importes se representan como texto para el CSV."""

    referencia: str
    valor_facturado: str
    valor_pagado: str
    banco: str
    estado: str
    diferencia: str


class ErrorEtapa(RuntimeError):
    """Fallo de una etapa, con la causa original disponible en __cause__."""

    def __init__(self, etapa: str, causa: Exception) -> None:
        """Identificar la etapa que puede reintentarse."""
        self.etapa = etapa
        super().__init__(f"Falló la etapa {etapa}: {causa}")


@dataclass(frozen=True)
class _Fila:
    origen: str
    archivo: str
    fila: int
    referencia: str
    valor: str
    fecha: str


@dataclass(frozen=True)
class _Registro:
    fuente: _Fila
    importe: int | None
    revision: bool


def _leer_archivo(entrada: Entrada) -> tuple[list[_Fila], list[Incidencia]]:
    separador, referencia, valor, fecha, _ = _ESQUEMAS[entrada.origen]
    archivo = str(entrada.ruta)
    filas: list[_Fila] = []
    with Path(entrada.ruta).open(encoding="utf-8-sig", newline="") as manejador:
        lector = csv.DictReader(manejador, delimiter=separador, strict=True)
        columnas = lector.fieldnames or []
        faltantes = [nombre for nombre in (referencia, valor, fecha) if nombre not in columnas]
        if faltantes:
            problemas = [
                Incidencia(
                    "lectura", archivo, None, nombre,
                    f"Archivo rechazado: falta la columna {nombre}.",
                )
                for nombre in faltantes
            ]
            return [], problemas
        for datos in lector:
            if None in datos:
                raise ValueError(f"{archivo}, fila {lector.line_num}: hay columnas adicionales.")
            filas.append(
                _Fila(
                    entrada.origen, archivo, lector.line_num,
                    (datos[referencia] or "").strip(),
                    (datos[valor] or "").strip(),
                    (datos[fecha] or "").strip(),
                )
            )
    return filas, []


def _problema(fila: _Fila, columna: str, mensaje: str) -> Incidencia:
    return Incidencia("normalizacion", fila.archivo, fila.fila, columna, mensaje)


def _fecha_valida(texto: str, formato: str) -> bool:
    try:
        fecha = datetime.strptime(texto, formato)
    except ValueError:
        return False
    return fecha.strftime(formato) == texto


def _normalizar_fila(fila: _Fila) -> tuple[_Registro | None, list[Incidencia]]:
    _, columna_ref, columna_valor, columna_fecha, formato = _ESQUEMAS[fila.origen]
    try:
        numero = Decimal(fila.valor)
    except InvalidOperation:
        return None, [_problema(fila, columna_valor, "Fila rechazada: importe no numérico.")]
    if not numero.is_finite():
        return None, [_problema(fila, columna_valor, "Fila rechazada: importe no numérico.")]
    problemas: list[Incidencia] = []
    importe: int | None = None
    if re.fullmatch(r"[+-]?[0-9]+", fila.valor):
        importe = int(fila.valor)
        if importe <= 0:
            problemas.append(_problema(fila, columna_valor, "Importe cero o negativo: revisión."))
    else:
        problemas.append(
            _problema(fila, columna_valor, "Formato de importe no definido: revisión.")
        )
    if not fila.referencia:
        problemas.append(_problema(fila, columna_ref, "Referencia vacía: revisión."))
    if formato and not _fecha_valida(fila.fecha, formato):
        problemas.append(_problema(fila, columna_fecha, "Fecha inválida: revisión."))
    return _Registro(fila, importe, bool(problemas)), problemas


def _clave(registro: _Registro) -> tuple[str, str, int]:
    fila = registro.fuente
    if fila.referencia:
        return fila.referencia, "", 0
    return "", f"{fila.origen}:{fila.archivo}", fila.fila


def _valores_revision(registros: list[_Registro]) -> str:
    if not registros:
        return ""
    return json.dumps([registro.fuente.valor for registro in registros], ensure_ascii=False)


def _importe_unico(registros: list[_Registro]) -> str:
    if not registros:
        return ""
    return str(registros[0].importe)


def _problemas_grupo(registros: list[_Registro], mensaje: str) -> list[Incidencia]:
    return [
        Incidencia(
            "conciliacion", registro.fuente.archivo, registro.fuente.fila,
            _ESQUEMAS[registro.fuente.origen][1], mensaje,
        )
        for registro in registros
    ]


def _resolver_grupo(registros: list[_Registro]) -> tuple[Detalle, list[Incidencia]]:
    facturas = [registro for registro in registros if registro.fuente.origen == "facturas"]
    pagos = [registro for registro in registros if registro.fuente.origen != "facturas"]
    bancos = "|".join(sorted({registro.fuente.origen for registro in pagos}))
    problemas: list[Incidencia] = []
    if len(facturas) > 1:
        problemas.extend(_problemas_grupo(facturas, "Facturas repetidas: revisión."))
    if len(pagos) > 1:
        problemas.extend(_problemas_grupo(pagos, "Varios pagos para la referencia: revisión."))
    referencia = registros[0].fuente.referencia
    if problemas or any(registro.revision for registro in registros):
        return Detalle(
            referencia, _valores_revision(facturas), _valores_revision(pagos),
            bancos, "revision", "",
        ), problemas
    diferencia = ""
    if not facturas:
        estado = "pago_sin_factura"
    elif not pagos:
        estado = "pendiente"
    else:
        facturado = facturas[0].importe
        pagado = pagos[0].importe
        if facturado is None or pagado is None:
            raise ValueError("Un registro definitivo carece de importe normalizado.")
        estado = "conciliada" if pagado == facturado else "con_diferencia"
        if pagado == facturado:
            diferencia = "0"
        elif pagado < facturado:
            diferencia = f"faltan {facturado - pagado}"
        else:
            diferencia = f"sobran {pagado - facturado}"
    return Detalle(
        referencia, _importe_unico(facturas), _importe_unico(pagos),
        bancos, estado, diferencia,
    ), problemas


class Lote:
    """Procesar entradas conservando en memoria cada etapa completada.

    No ejecuta etapas anteriores al reintentar ni recupera ejecuciones cerradas.
    Una misma instancia no debe utilizarse concurrentemente.
    """

    def __init__(self, entradas: Iterable[Entrada], destino: str | Path) -> None:
        """Configurar los archivos y el directorio de los tres reportes."""
        self._entradas = tuple(entradas)
        for entrada in self._entradas:
            if entrada.origen not in _ESQUEMAS:
                raise ValueError(f"Origen desconocido: {entrada.origen}.")
        self._destino = Path(destino)
        self._completadas: list[str] = []
        self._fallida: str | None = None
        self._filas: tuple[_Fila, ...] = ()
        self._registros: tuple[_Registro, ...] = ()
        self._detalle: tuple[Detalle, ...] = ()
        self._incidencias: dict[str, tuple[Incidencia, ...]] = {}

    @property
    def completadas(self) -> tuple[str, ...]:
        """Obtener las etapas terminadas, en orden."""
        return tuple(self._completadas)

    @property
    def etapa_fallida(self) -> str | None:
        """Obtener la última etapa fallida hasta que termine su reintento."""
        return self._fallida

    @property
    def incidencias(self) -> tuple[Incidencia, ...]:
        """Obtener los problemas de las etapas que finalizaron."""
        return tuple(
            problema
            for etapa in _ETAPAS
            for problema in self._incidencias.get(etapa, ())
        )

    @property
    def detalle(self) -> tuple[Detalle, ...]:
        """Obtener el reporte después de completar la conciliación."""
        if "conciliacion" not in self._completadas:
            raise ValueError("La conciliación todavía no está completada.")
        return self._detalle

    @property
    def resumen(self) -> dict[str, int]:
        """Contar registros del detalle por estado, incluyendo estados con cero."""
        resultado = dict.fromkeys(_ESTADOS, 0)
        for registro in self.detalle:
            resultado[registro.estado] += 1
        return resultado

    def ejecutar_etapa(self, etapa: str) -> None:
        """Ejecutar o reintentar una etapa; una ya completada no se vuelve a ejecutar.

        Raises:
            ValueError: Si el nombre es desconocido o faltan etapas anteriores.
            ErrorEtapa: Si falla el procesamiento; conserva las etapas anteriores.
        """
        if etapa not in _ETAPAS:
            raise ValueError(f"Etapa desconocida: {etapa}.")
        if etapa in self._completadas:
            return
        siguiente = _ETAPAS[len(self._completadas)]
        if etapa != siguiente:
            raise ValueError(f"Debe completarse primero la etapa {siguiente}.")
        operaciones = {
            "lectura": self._hacer_lectura,
            "normalizacion": self._hacer_normalizacion,
            "conciliacion": self._hacer_conciliacion,
            "escritura": self._hacer_escritura,
        }
        try:
            operaciones[etapa]()
        except (OSError, UnicodeError, csv.Error, ValueError) as causa:
            self._fallida = etapa
            raise ErrorEtapa(etapa, causa) from causa
        self._completadas.append(etapa)
        self._fallida = None

    def ejecutar(self) -> None:
        """Continuar el lote desde su primera etapa pendiente hasta la escritura."""
        for etapa in _ETAPAS:
            self.ejecutar_etapa(etapa)

    def _hacer_lectura(self) -> None:
        filas: list[_Fila] = []
        problemas: list[Incidencia] = []
        for entrada in self._entradas:
            nuevas, incidencias = _leer_archivo(entrada)
            filas.extend(nuevas)
            problemas.extend(incidencias)
        self._filas = tuple(filas)
        self._incidencias["lectura"] = tuple(problemas)

    def _hacer_normalizacion(self) -> None:
        registros: list[_Registro] = []
        problemas: list[Incidencia] = []
        for fila in self._filas:
            registro, incidencias = _normalizar_fila(fila)
            problemas.extend(incidencias)
            if registro is not None:
                registros.append(registro)
        self._registros = tuple(registros)
        self._incidencias["normalizacion"] = tuple(problemas)

    def _hacer_conciliacion(self) -> None:
        grupos: dict[tuple[str, str, int], list[_Registro]] = defaultdict(list)
        for registro in self._registros:
            grupos[_clave(registro)].append(registro)
        detalle: list[Detalle] = []
        problemas: list[Incidencia] = []
        for registros in grupos.values():
            resultado, incidencias = _resolver_grupo(registros)
            detalle.append(resultado)
            problemas.extend(incidencias)
        self._detalle = tuple(detalle)
        self._incidencias["conciliacion"] = tuple(problemas)

    def _hacer_escritura(self) -> None:
        self._destino.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="conciliacion-", dir=self._destino) as temporal:
            carpeta = Path(temporal)
            with (carpeta / "detalle.csv").open("w", encoding="utf-8", newline="") as archivo:
                escritor = csv.DictWriter(archivo, fieldnames=_COLUMNAS)
                escritor.writeheader()
                escritor.writerows(asdict(registro) for registro in self.detalle)
            documentos = {
                "resumen.json": self.resumen,
                "incidencias.json": [asdict(problema) for problema in self.incidencias],
            }
            for nombre, documento in documentos.items():
                (carpeta / nombre).write_text(
                    json.dumps(documento, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            for nombre in ("detalle.csv", "resumen.json", "incidencias.json"):
                os.replace(carpeta / nombre, self._destino / nombre)
