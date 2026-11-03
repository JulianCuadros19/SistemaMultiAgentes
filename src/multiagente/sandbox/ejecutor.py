"""Ejecución de código generado en un contenedor efímero sin red (RF-20, RNF-03).

Cada ejecución crea un contenedor con la imagen del entorno aislado y lo destruye al terminar:
- sin red, con el sistema de archivos de solo lectura y `/tmp` en memoria;
- sin root, sin capacidades y con límites de procesos, memoria y CPU;
- el código entra como un archivo tar por la entrada estándar, de modo que no se monta ninguna
  carpeta del anfitrión;
- si vence el tiempo límite, el contenedor se mata.

Ningún código generado se ejecuta en el anfitrión: este módulo solo invoca la CLI de Docker.
"""

import io
import json
import subprocess
import tarfile
import time
import uuid
from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from multiagente.core.configuracion import ConfiguracionSandbox

RAIZ_CODIGO = "/tmp/codigo"
"""Carpeta del contenedor, en memoria, donde se extrae el código."""

USUARIO = "10001:10001"
"""Usuario sin privilegios de la imagen (`docker/sandbox/Dockerfile`)."""

LIMITE_SALIDA = 100_000
"""Caracteres que se conservan de cada flujo de salida; el resto se trunca."""

CODIGO_ERROR_DOCKER = 125
"""Código de salida de `docker run` cuando el contenedor no llega a ejecutarse."""

MARCA_RESULTADO = "@@resultado-importacion@@"
"""Prefijo de la línea con el resultado de la importación, distinta de lo que imprima el código."""

SCRIPT_IMPORTACION = f"""
import importlib, json, sys, traceback
sys.path[:0] = ["{RAIZ_CODIGO}/src", "{RAIZ_CODIGO}"]
errores = {{}}
for nombre in sys.argv[1:]:
    try:
        importlib.import_module(nombre)
    except BaseException:
        errores[nombre] = traceback.format_exc(limit=5)
print("{MARCA_RESULTADO}" + json.dumps(errores))
"""
"""Importa cada módulo indicado y reporta los errores; corre dentro del contenedor."""

MARCA_PRUEBAS = "@@resultado-pruebas@@"
"""Prefijo de la línea con el resultado de las pruebas."""

MARCA_FALLA = "E   "
"""Prefijo con que pytest marca, en su reporte largo, las líneas que explican el error."""

SCRIPT_PRUEBAS = f"""
import contextlib, io, json
import pytest


class Recolector:
    def __init__(self):
        self.pruebas = {{}}
        self.recoleccion = []

    def pytest_runtest_logreport(self, report):
        prueba = self.pruebas.setdefault(
            report.nodeid, {{"resultado": None, "duracion": 0.0, "mensaje": ""}}
        )
        prueba["duracion"] += report.duration
        if report.failed:
            prueba["resultado"] = "fallo" if report.when == "call" else "error"
            prueba["mensaje"] = report.longreprtext[-3000:]
        elif report.skipped and prueba["resultado"] is None:
            prueba["resultado"] = "omitida"
            prueba["mensaje"] = report.longreprtext[-500:]
        elif report.passed and report.when == "call" and prueba["resultado"] is None:
            prueba["resultado"] = "paso"

    def pytest_collectreport(self, report):
        if report.failed:
            self.recoleccion.append(f"{{report.nodeid}}: {{report.longreprtext[-3000:]}}")


recolector = Recolector()
salida = io.StringIO()
with contextlib.redirect_stdout(salida):
    codigo = pytest.main(
        ["-q", "-p", "no:cacheprovider", "--continue-on-collection-errors",
         "--rootdir", "{RAIZ_CODIGO}", "-o", "pythonpath=src", "tests"],
        plugins=[recolector],
    )
print("{MARCA_PRUEBAS}" + json.dumps({{
    "codigo": int(codigo),
    "pruebas": recolector.pruebas,
    "recoleccion": recolector.recoleccion,
    "salida": salida.getvalue()[-5000:],
}}))
"""
"""Corre pytest sobre `tests/` y reporta cada prueba; corre dentro del contenedor.

La salida de pytest se guarda aparte para que la línea del resultado nunca quede truncada.
"""


class ErrorEntornoAislado(RuntimeError):
    """El contenedor no pudo ejecutarse: Docker no responde o falta la imagen."""


class ResultadoEjecucion(BaseModel):
    """Resultado de una ejecución en el entorno aislado.

    Attributes:
        codigo_salida: Código de salida del comando; None si se mató por tiempo.
        salida: Salida estándar, truncada a `LIMITE_SALIDA` caracteres.
        errores: Salida de errores, truncada igual.
        vencido: Si se alcanzó el tiempo límite y el contenedor se mató.
        duracion_ms: Duración de la ejecución, creación del contenedor incluida.
    """

    model_config = ConfigDict(frozen=True)

    codigo_salida: int | None
    salida: str
    errores: str
    vencido: bool
    duracion_ms: int

    @property
    def exito(self) -> bool:
        """Indica si el comando terminó a tiempo y con código 0."""
        return not self.vencido and self.codigo_salida == 0


class ResultadoImportacion(BaseModel):
    """Resultado de importar los módulos de una versión en el entorno aislado.

    Attributes:
        errores: Traza del error de cada módulo que no se importó; vacía si todos se importan.
        ejecucion: Ejecución que produjo el resultado.
    """

    model_config = ConfigDict(frozen=True)

    errores: dict[str, str]
    ejecucion: ResultadoEjecucion

    @property
    def exito(self) -> bool:
        """Indica si todos los módulos se importaron sin error."""
        return not self.errores and self.ejecucion.exito


class PruebaReportada(BaseModel):
    """Resultado de una prueba de pytest en el entorno aislado.

    Attributes:
        archivo: Archivo de la prueba, p. ej. `tests/test_avaluo.py`.
        nombre: Nombre de la prueba dentro del archivo, con su clase y parámetros si los tiene.
        resultado: `paso`, `fallo`, `error` (en la preparación o el cierre) u `omitida`.
        duracion_ms: Duración de la prueba.
        mensaje: Detalle del fallo, del error o de la omisión, truncado.
    """

    model_config = ConfigDict(frozen=True)

    archivo: str
    nombre: str
    resultado: str
    duracion_ms: int
    mensaje: str = ""


class ResultadoPruebas(BaseModel):
    """Resultado de correr las pruebas de una versión en el entorno aislado.

    Attributes:
        pruebas: Cada prueba ejecutada, en orden de ejecución.
        errores_recoleccion: Archivos de prueba que pytest no pudo recolectar, con su error.
        codigo_pytest: Código de salida de pytest; None si no hubo resultado.
        salida_pytest: Final de la salida de pytest.
        ejecucion: Ejecución del contenedor que produjo el resultado.
    """

    model_config = ConfigDict(frozen=True)

    pruebas: tuple[PruebaReportada, ...]
    errores_recoleccion: tuple[str, ...]
    codigo_pytest: int | None
    salida_pytest: str
    ejecucion: ResultadoEjecucion

    @property
    def exito(self) -> bool:
        """Indica si hubo pruebas, se recolectaron todas y ninguna falló ni dio error."""
        return (
            self.ejecucion.exito
            and bool(self.pruebas)
            and not self.errores_recoleccion
            and all(prueba.resultado in ("paso", "omitida") for prueba in self.pruebas)
        )


def leer_resultado_pruebas(ejecucion: ResultadoEjecucion) -> ResultadoPruebas:
    """Lee la línea marcada que imprime el guion de pruebas.

    Args:
        ejecucion: Ejecución del guion de pruebas en el contenedor.

    Returns:
        El resultado por prueba; sin pruebas y con el motivo como error de recolección si la
        línea no está, por ejemplo porque venció el tiempo.
    """
    lineas = [
        linea.removeprefix(MARCA_PRUEBAS)
        for linea in ejecucion.salida.splitlines()
        if linea.startswith(MARCA_PRUEBAS)
    ]
    if not lineas:
        motivo = "tiempo vencido" if ejecucion.vencido else ejecucion.errores.strip()[-2000:]
        return ResultadoPruebas(
            pruebas=(),
            errores_recoleccion=(f"Sin resultado de las pruebas: {motivo}",),
            codigo_pytest=None,
            salida_pytest="",
            ejecucion=ejecucion,
        )
    datos = json.loads(lineas[-1])
    pruebas = []
    for nodo, prueba in datos["pruebas"].items():
        archivo, _, nombre = nodo.partition("::")
        pruebas.append(
            PruebaReportada(
                archivo=archivo,
                nombre=nombre,
                resultado=prueba["resultado"] or "error",
                duracion_ms=round(prueba["duracion"] * 1000),
                mensaje=prueba["mensaje"],
            )
        )
    return ResultadoPruebas(
        pruebas=tuple(pruebas),
        errores_recoleccion=tuple(datos["recoleccion"]),
        codigo_pytest=datos["codigo"],
        salida_pytest=datos["salida"],
        ejecucion=ejecucion,
    )


def detalle_de_falla(texto: str, limite: int | None = None) -> str:
    """Resume en una línea por qué falló una prueba, a partir de su reporte o de una traza.

    pytest explica el error en las líneas que marca con `E` y tres espacios, como
    `E       assert 5 == 6`; la última línea del reporte, `archivo:línea: AssertionError`, no dice
    nada del fallo. Sin esas marcas, como en una traza de importación, se usa la última línea.

    Args:
        texto: Reporte de pytest o traza de Python.
        limite: Caracteres que se conservan; sin límite si se omite.

    Returns:
        Las líneas marcadas, sin la marca y unidas; si no hay, la última línea con texto, o «sin
        detalle».
    """
    marcadas = [
        " ".join(linea.removeprefix("E").split())
        for linea in texto.splitlines()
        if linea.startswith(MARCA_FALLA)
    ]
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    detalle = " ".join(filter(None, marcadas)) or (lineas[-1] if lineas else "sin detalle")
    return detalle if limite is None else detalle[:limite]


def es_ruta_segura(ruta: str) -> bool:
    """Indica si una ruta de archivo generado es relativa y no sale de su carpeta.

    Args:
        ruta: Ruta del archivo, con separadores `/`.

    Returns:
        True si es relativa, sin `..`, sin barras invertidas y sin partes vacías.
    """
    if not ruta or "\\" in ruta:
        return False
    return all(parte not in ("", ".", "..") for parte in ruta.split("/"))


def empaquetar(archivos: Mapping[str, str]) -> bytes:
    """Empaqueta los archivos en un tar en memoria, en orden y con fechas fijas.

    Args:
        archivos: Contenido de cada archivo por su ruta relativa.

    Returns:
        El archivo tar.

    Raises:
        ValueError: Si alguna ruta no es segura.
    """
    if inseguras := sorted(ruta for ruta in archivos if not es_ruta_segura(ruta)):
        raise ValueError(f"Rutas no admitidas en el entorno aislado: {inseguras}")
    memoria = io.BytesIO()
    with tarfile.open(fileobj=memoria, mode="w") as tar:
        for ruta in sorted(archivos):
            datos = archivos[ruta].encode("utf-8")
            info = tarfile.TarInfo(ruta)
            info.size = len(datos)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(datos))
    return memoria.getvalue()


def _texto(datos: bytes | str | None) -> str:
    if datos is None:
        return ""
    texto = datos.decode("utf-8", errors="replace") if isinstance(datos, bytes) else datos
    if len(texto) > LIMITE_SALIDA:
        return texto[:LIMITE_SALIDA] + f"\n[… salida truncada a {LIMITE_SALIDA} caracteres]"
    return texto


class EntornoAislado:
    """Ejecuta comandos sobre código generado en un contenedor efímero sin red."""

    def __init__(self, configuracion: ConfiguracionSandbox | None = None) -> None:
        """Prepara el entorno con la imagen y los límites configurados.

        Args:
            configuracion: Imagen y límites; si se omite, se lee de las variables SANDBOX_*.
        """
        self.configuracion = configuracion or ConfiguracionSandbox()

    def argumentos(self, nombre: str, comando: Sequence[str]) -> list[str]:
        """Arma la invocación de `docker run` para un contenedor efímero.

        El contenedor extrae el tar de la entrada estándar en `RAIZ_CODIGO` y ejecuta el
        comando desde allí. No monta volúmenes ni publica puertos.

        Args:
            nombre: Nombre del contenedor, para poder matarlo si vence el tiempo.
            comando: Comando a ejecutar dentro del contenedor, como lista de argumentos.

        Returns:
            Argumentos de la CLI de Docker, sin intérprete de comandos del anfitrión.
        """
        configuracion = self.configuracion
        preparar = (
            f"mkdir -p {RAIZ_CODIGO} && tar -x -f - -C {RAIZ_CODIGO} "
            f'&& cd {RAIZ_CODIGO} && exec "$@"'
        )
        return [
            "docker",
            "run",
            "--rm",
            "--interactive",
            "--pull=never",
            f"--name={nombre}",
            "--network=none",
            "--read-only",
            "--tmpfs=/tmp:rw,nosuid,nodev,size=64m",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            f"--user={USUARIO}",
            f"--pids-limit={configuracion.procesos}",
            f"--memory={configuracion.memoria}",
            f"--memory-swap={configuracion.memoria}",
            f"--cpus={configuracion.cpus}",
            "--env=PYTHONDONTWRITEBYTECODE=1",
            configuracion.imagen,
            "sh",
            "-c",
            preparar,
            "entorno-aislado",
            *comando,
        ]

    def ejecutar(
        self,
        archivos: Mapping[str, str],
        comando: Sequence[str],
        tiempo_limite_s: float | None = None,
    ) -> ResultadoEjecucion:
        """Ejecuta un comando sobre los archivos en un contenedor nuevo y lo destruye.

        Args:
            archivos: Contenido de cada archivo por su ruta relativa a `RAIZ_CODIGO`.
            comando: Comando a ejecutar, como lista de argumentos.
            tiempo_limite_s: Tiempo límite; si se omite, el configurado.

        Returns:
            Código de salida, salidas y si venció el tiempo.

        Raises:
            ValueError: Si alguna ruta no es segura.
            ErrorEntornoAislado: Si Docker no responde o la imagen no existe.
        """
        limite = tiempo_limite_s or self.configuracion.tiempo_limite_s
        nombre = f"multiagente-sandbox-{uuid.uuid4().hex[:12]}"
        entrada = empaquetar(archivos)
        inicio = time.perf_counter()
        try:
            proceso = subprocess.run(
                self.argumentos(nombre, comando),
                input=entrada,
                capture_output=True,
                timeout=limite,
                check=False,
            )
        except subprocess.TimeoutExpired as vencimiento:
            subprocess.run(["docker", "kill", nombre], capture_output=True, check=False)
            return ResultadoEjecucion(
                codigo_salida=None,
                salida=_texto(vencimiento.stdout),
                errores=_texto(vencimiento.stderr),
                vencido=True,
                duracion_ms=round((time.perf_counter() - inicio) * 1000),
            )
        except FileNotFoundError as error:
            raise ErrorEntornoAislado("La CLI de Docker no está disponible") from error
        duracion_ms = round((time.perf_counter() - inicio) * 1000)
        errores = _texto(proceso.stderr)
        if proceso.returncode == CODIGO_ERROR_DOCKER:
            raise ErrorEntornoAislado(
                "El contenedor no se pudo crear. ¿Docker está activo y la imagen construida "
                f"(docker compose --profile sandbox build sandbox)? {errores.strip()}"
            )
        return ResultadoEjecucion(
            codigo_salida=proceso.returncode,
            salida=_texto(proceso.stdout),
            errores=errores,
            vencido=False,
            duracion_ms=duracion_ms,
        )

    def importar(self, archivos: Mapping[str, str], modulos: Sequence[str]) -> ResultadoImportacion:
        """Importa cada módulo en el entorno aislado y reporta los que fallan.

        Los módulos se buscan en `src/` y en la raíz del código, como los declara la
        especificación de diseño (`dominio.predio` en `src/dominio/predio.py`).

        Args:
            archivos: Archivos de la versión del módulo.
            modulos: Nombres importables de los módulos, en notación de puntos.

        Returns:
            La traza de cada módulo que no se importó y la ejecución.

        Raises:
            ErrorEntornoAislado: Si Docker no responde o la imagen no existe.
        """
        ejecucion = self.ejecutar(archivos, ["python", "-I", "-c", SCRIPT_IMPORTACION, *modulos])
        lineas = [
            linea.removeprefix(MARCA_RESULTADO)
            for linea in ejecucion.salida.splitlines()
            if linea.startswith(MARCA_RESULTADO)
        ]
        if not lineas:
            motivo = "tiempo vencido" if ejecucion.vencido else ejecucion.errores.strip()[-2000:]
            errores = {modulo: f"Sin resultado de la importación: {motivo}" for modulo in modulos}
            return ResultadoImportacion(errores=errores, ejecucion=ejecucion)
        return ResultadoImportacion(errores=json.loads(lineas[-1]), ejecucion=ejecucion)

    def probar(
        self, archivos: Mapping[str, str], tiempo_limite_s: float | None = None
    ) -> ResultadoPruebas:
        """Corre las pruebas de `tests/` con pytest en el entorno aislado.

        `src/` entra en la ruta de importación, como la declara la especificación. La caché de
        pytest se desactiva, porque el sistema de archivos es de solo lectura fuera de `/tmp`.

        Args:
            archivos: Archivos de la versión del módulo, con sus pruebas.
            tiempo_limite_s: Tiempo límite; si se omite, el configurado.

        Returns:
            El resultado de cada prueba y los errores de recolección.

        Raises:
            ErrorEntornoAislado: Si Docker no responde o la imagen no existe.
        """
        ejecucion = self.ejecutar(archivos, ["python", "-I", "-c", SCRIPT_PRUEBAS], tiempo_limite_s)
        return leer_resultado_pruebas(ejecucion)
