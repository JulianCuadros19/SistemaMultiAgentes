"""Modelo, consumidores y distribución asíncrona de avisos en memoria."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from queue import Queue
from threading import Lock, Thread

_LOG = logging.getLogger(__name__)


class TipoTramite(StrEnum):
    """Tipos de trámite admitidos por el dominio."""

    MUTACION = "mutación"
    RECTIFICACION = "rectificación"
    CERTIFICADO = "certificado"


class Estado(StrEnum):
    """Estados posibles de un trámite."""

    RADICADO = "radicado"
    EN_REVISION = "en revisión"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


_TRANSICIONES = frozenset(
    {
        (Estado.RADICADO, Estado.EN_REVISION),
        (Estado.EN_REVISION, Estado.APROBADO),
        (Estado.EN_REVISION, Estado.RECHAZADO),
    }
)


@dataclass(frozen=True)
class Aviso:
    """Datos completos e inmutables de un cambio de estado."""

    numero: str
    tipo: TipoTramite
    estado_anterior: Estado
    estado_nuevo: Estado
    fecha_hora: datetime
    funcionario: str

    @property
    def valido(self) -> bool:
        """Indicar si la transición pertenece a las tres permitidas."""
        return (self.estado_anterior, self.estado_nuevo) in _TRANSICIONES


@dataclass(frozen=True)
class RegistroBitacora:
    """Aviso original y marca de validez de su transición."""

    aviso: Aviso
    valido: bool


@dataclass(frozen=True)
class Medicion:
    """Duración de un aviso terminal, expresada en días hábiles."""

    numero: str
    tipo: TipoTramite
    dias: int


@dataclass(frozen=True)
class Mensaje:
    """Texto preparado para un ciudadano, sin envío externo."""

    numero: str
    texto: str


@dataclass(frozen=True)
class Fallo:
    """Error de un consumidor asociado al aviso que intentaba procesar."""

    consumidor: str
    aviso: Aviso
    descripcion: str


def dias_habiles(inicio: date, fin: date) -> int:
    """Contar lunes a viernes en el intervalo (inicio, fin], sin festivos.

    Raises:
        ValueError: Si el final es anterior al inicio.
    """
    diferencia = (fin - inicio).days
    if diferencia < 0:
        raise ValueError("La fecha final es anterior a la radicación")
    semanas, resto = divmod(diferencia, 7)
    return semanas * 5 + sum(
        (inicio + timedelta(days=desplazamiento)).weekday() < 5
        for desplazamiento in range(1, resto + 1)
    )


class Bitacora:
    """Guardar todos los avisos, incluidos los de transición inválida."""

    def __init__(self) -> None:
        """Crear una bitácora vacía y protegida frente a accesos concurrentes."""
        self._registros: list[RegistroBitacora] = []
        self._lock = Lock()

    def procesar(self, aviso: Aviso) -> None:
        """Registrar todos los datos originales y la validez de la transición."""
        with self._lock:
            self._registros.append(RegistroBitacora(aviso, aviso.valido))

    @property
    def registros(self) -> tuple[RegistroBitacora, ...]:
        """Obtener una instantánea inmutable en orden de recepción."""
        with self._lock:
            return tuple(self._registros)


class IndicadorTiempos:
    """Calcular duraciones terminales y su promedio por tipo de trámite."""

    def __init__(self) -> None:
        """Crear un indicador sin fechas de radicación ni mediciones."""
        self._radicaciones: dict[str, date] = {}
        self._mediciones: list[Medicion] = []
        self._lock = Lock()

    def registrar_radicacion(self, numero: str, fecha: date) -> None:
        """Cargar la fecha de origen conocida, sin ejecutar la radicación.

        Una carga posterior del mismo número reemplaza su fecha para futuros avisos.
        Las mediciones ya calculadas no se modifican.
        """
        with self._lock:
            self._radicaciones[numero] = fecha

    def procesar(self, aviso: Aviso) -> None:
        """Medir avisos válidos que llegan a aprobado o rechazado.

        Raises:
            ValueError: Si falta la fecha de radicación o el final la precede.
        """
        if not aviso.valido or aviso.estado_nuevo not in {Estado.APROBADO, Estado.RECHAZADO}:
            return
        with self._lock:
            inicio = self._radicaciones.get(aviso.numero)
            if inicio is None:
                raise ValueError(f"Falta la fecha de radicación de {aviso.numero}")
            dias = dias_habiles(inicio, aviso.fecha_hora.date())
            self._mediciones.append(Medicion(aviso.numero, aviso.tipo, dias))

    @property
    def mediciones(self) -> tuple[Medicion, ...]:
        """Obtener una instantánea de las duraciones calculadas."""
        with self._lock:
            return tuple(self._mediciones)

    @property
    def promedios(self) -> dict[TipoTramite, float]:
        """Obtener promedios de los tipos con al menos una medición."""
        with self._lock:
            totales: dict[TipoTramite, int] = {}
            cantidades: dict[TipoTramite, int] = {}
            for medicion in self._mediciones:
                totales[medicion.tipo] = totales.get(medicion.tipo, 0) + medicion.dias
                cantidades[medicion.tipo] = cantidades.get(medicion.tipo, 0) + 1
            return {tipo: total / cantidades[tipo] for tipo, total in totales.items()}


class MensajesCiudadano:
    """Preparar mensajes de cambios válidos sin enviarlos."""

    def __init__(self) -> None:
        """Crear una colección vacía de mensajes preparados."""
        self._mensajes: list[Mensaje] = []
        self._lock = Lock()

    def procesar(self, aviso: Aviso) -> None:
        """Preparar el texto correspondiente al estado nuevo del aviso válido."""
        if not aviso.valido:
            return
        textos = {
            Estado.APROBADO: f"Su trámite {aviso.numero} fue aprobado",
            Estado.RECHAZADO: (
                f"Su trámite {aviso.numero} fue rechazado; "
                "puede consultar el motivo en la oficina"
            ),
            Estado.EN_REVISION: f"Su trámite {aviso.numero} está en revisión",
        }
        with self._lock:
            self._mensajes.append(Mensaje(aviso.numero, textos[aviso.estado_nuevo]))

    @property
    def mensajes(self) -> tuple[Mensaje, ...]:
        """Obtener una instantánea de los mensajes, en orden de recepción."""
        with self._lock:
            return tuple(self._mensajes)


class _Consumidor:
    def __init__(
        self,
        nombre: str,
        procesar: Callable[[Aviso], None],
        incluir_invalidos: bool,
        registrar_fallo: Callable[[Fallo], None],
    ) -> None:
        self.nombre = nombre
        self.procesar = procesar
        self.incluir_invalidos = incluir_invalidos
        self.registrar_fallo = registrar_fallo
        self.cola: Queue[Aviso | None] = Queue()
        self.hilo = Thread(target=self._ejecutar, name=f"avisos-{nombre}", daemon=True)
        self.hilo.start()

    def _ejecutar(self) -> None:
        while True:
            aviso = self.cola.get()
            try:
                if aviso is None:
                    return
                try:
                    self.procesar(aviso)
                except Exception as error:
                    # Frontera de aislamiento: una excepción no detiene el consumidor.
                    _LOG.exception("Falló el consumidor %s", self.nombre)
                    self.registrar_fallo(
                        Fallo(self.nombre, aviso, f"{type(error).__name__}: {error}")
                    )
            finally:
                self.cola.task_done()


class CanalAvisos:
    """Distribuir avisos mediante una cola y un hilo por consumidor."""

    def __init__(self) -> None:
        """Crear un canal abierto sin suscriptores."""
        self._consumidores: dict[str, _Consumidor] = {}
        self._fallos: list[Fallo] = []
        self._lock = Lock()
        self._lock_fallos = Lock()
        self._cerrado = False

    def suscribir(
        self,
        nombre: str,
        procesar: Callable[[Aviso], None],
        *,
        incluir_invalidos: bool = False,
    ) -> None:
        """Añadir un consumidor independiente para las publicaciones futuras.

        Raises:
            ValueError: Si ya existe un consumidor con ese nombre.
            RuntimeError: Si el canal está cerrado.
        """
        with self._lock:
            if self._cerrado:
                raise RuntimeError("El canal está cerrado")
            if nombre in self._consumidores:
                raise ValueError(f"Consumidor duplicado: {nombre}")
            self._consumidores[nombre] = _Consumidor(
                nombre, procesar, incluir_invalidos, self._registrar_fallo
            )

    def publicar(self, aviso: Aviso) -> None:
        """Encolar el aviso sin esperar a que los consumidores lo procesen.

        Los inválidos solo llegan a suscriptores que los solicitan expresamente.

        Raises:
            RuntimeError: Si el canal está cerrado.
        """
        with self._lock:
            if self._cerrado:
                raise RuntimeError("El canal está cerrado")
            for consumidor in self._consumidores.values():
                if aviso.valido or consumidor.incluir_invalidos:
                    consumidor.cola.put_nowait(aviso)

    def esperar(self) -> None:
        """Esperar a vaciar las colas; usar con los productores detenidos."""
        with self._lock:
            consumidores = tuple(self._consumidores.values())
        for consumidor in consumidores:
            consumidor.cola.join()

    def cerrar(self) -> None:
        """Impedir nuevas publicaciones y esperar el trabajo pendiente.

        Es idempotente. Debe llamarse desde fuera de los consumidores.
        """
        with self._lock:
            self._cerrado = True
            consumidores = tuple(self._consumidores.values())
            for consumidor in consumidores:
                if consumidor.hilo.is_alive():
                    # Solo el primer cierre coloca el marcador de terminación.
                    if not getattr(consumidor, "_terminacion_encolada", False):
                        consumidor.cola.put_nowait(None)
                        consumidor._terminacion_encolada = True
        for consumidor in consumidores:
            consumidor.hilo.join()

    def _registrar_fallo(self, fallo: Fallo) -> None:
        with self._lock_fallos:
            self._fallos.append(fallo)

    @property
    def fallos(self) -> tuple[Fallo, ...]:
        """Obtener errores aislados; no se propagan al publicador."""
        with self._lock_fallos:
            return tuple(self._fallos)


class SistemaAvisos:
    """Componer los tres consumidores requeridos sobre un canal en memoria."""

    def __init__(self) -> None:
        """Crear bitácora, indicador, mensajes y sus respectivas suscripciones."""
        self.bitacora = Bitacora()
        self.indicador = IndicadorTiempos()
        self.mensajes = MensajesCiudadano()
        self.canal = CanalAvisos()
        self.canal.suscribir("bitácora", self.bitacora.procesar, incluir_invalidos=True)
        self.canal.suscribir("indicador", self.indicador.procesar)
        self.canal.suscribir("mensajes", self.mensajes.procesar)

    def cerrar(self) -> None:
        """Cerrar el canal y esperar la terminación de los tres consumidores."""
        self.canal.cerrar()
