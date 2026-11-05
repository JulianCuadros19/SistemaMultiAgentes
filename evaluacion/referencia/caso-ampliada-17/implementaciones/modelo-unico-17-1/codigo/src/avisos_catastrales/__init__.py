"""Distribución asíncrona en memoria de avisos de trámites catastrales."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from queue import Queue
from threading import Lock, Thread

__all__ = [
    "Aviso", "Bitacora", "Canal", "Fallo", "Indicador", "Medicion", "Mensaje",
    "PreparadorMensajes", "Registro", "Sistema", "dias_habiles",
]

_TRANSICIONES = frozenset({
    ("radicado", "en revisión"),
    ("en revisión", "aprobado"),
    ("en revisión", "rechazado"),
})
_TEXTOS = {
    "en revisión": "Su trámite {numero} está en revisión",
    "aprobado": "Su trámite {numero} fue aprobado",
    "rechazado": "Su trámite {numero} fue rechazado; puede consultar el motivo en la oficina",
}


@dataclass(frozen=True)
class Aviso:
    """Datos inmutables de un aviso; los estados se conservan literalmente."""

    numero: str
    tipo: str
    estado_anterior: str | None
    estado_nuevo: str
    fecha_hora: datetime
    funcionario: str

    def __post_init__(self) -> None:
        """Rechazar datos estructuralmente incompletos, sin validar la transición."""
        for campo in ("numero", "tipo", "estado_nuevo", "funcionario"):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(f"{campo}: se requiere texto no vacío")
        if self.estado_anterior is not None and not isinstance(self.estado_anterior, str):
            raise ValueError("estado_anterior: se requiere texto o None")
        if not isinstance(self.fecha_hora, datetime):
            raise ValueError("fecha_hora: se requiere datetime")


@dataclass(frozen=True)
class Registro:
    """Aviso original y resultado de validar su transición."""

    aviso: Aviso
    valida: bool


@dataclass(frozen=True)
class Fallo:
    """Error de un consumidor, sin impedir la entrega a los demás."""

    consumidor: str
    registro: Registro
    tipo: str
    mensaje: str


class Canal:
    """Canal no persistente con una cola y un trabajador por consumidor."""

    def __init__(self) -> None:
        """Crear un canal abierto sin consumidores."""
        self._lock = Lock()
        self._colas: dict[str, Queue[Registro | None]] = {}
        self._hilos: list[Thread] = []
        self._fallos: list[Fallo] = []
        self._cerrado = False

    def suscribir(self, nombre: str, atender: Callable[[Registro], None]) -> None:
        """Conectar un consumidor para los avisos publicados desde este momento."""
        if not isinstance(nombre, str) or not nombre.strip():
            raise ValueError("nombre: se requiere texto no vacío")
        if not callable(atender):
            raise ValueError("atender: se requiere una función")
        with self._lock:
            if self._cerrado:
                raise RuntimeError("El canal está cerrado")
            if nombre in self._colas:
                raise ValueError(f"Consumidor ya suscrito: {nombre}")
            cola: Queue[Registro | None] = Queue()
            hilo = Thread(target=self._trabajar, args=(nombre, cola, atender), daemon=True)
            self._colas[nombre] = cola
            self._hilos.append(hilo)
            hilo.start()

    def publicar(self, aviso: Aviso) -> None:
        """Encolar un aviso sin esperar a que los consumidores lo atiendan."""
        if not isinstance(aviso, Aviso):
            raise ValueError("aviso: se requiere Aviso")
        registro = Registro(
            aviso, (aviso.estado_anterior, aviso.estado_nuevo) in _TRANSICIONES
        )
        with self._lock:
            if self._cerrado:
                raise RuntimeError("El canal está cerrado")
            for cola in self._colas.values():
                cola.put_nowait(registro)

    def _trabajar(
        self,
        nombre: str,
        cola: Queue[Registro | None],
        atender: Callable[[Registro], None],
    ) -> None:
        while True:
            registro = cola.get()
            try:
                if registro is None:
                    return
                try:
                    atender(registro)
                except Exception as error:  # noqa: BLE001 -- aislar y registrar fallos del consumidor
                    fallo = Fallo(nombre, registro, type(error).__name__, str(error))
                    with self._lock:
                        self._fallos.append(fallo)
            finally:
                cola.task_done()

    @property
    def fallos(self) -> tuple[Fallo, ...]:
        """Obtener una instantánea inmutable de los fallos registrados."""
        with self._lock:
            return tuple(self._fallos)

    def esperar(self) -> None:
        """Esperar al vaciado de las colas; usar fuera de los consumidores."""
        with self._lock:
            colas = tuple(self._colas.values())
        for cola in colas:
            cola.join()

    def cerrar(self) -> None:
        """Dejar de aceptar avisos y terminar tras atender los ya encolados."""
        with self._lock:
            if not self._cerrado:
                self._cerrado = True
                for cola in self._colas.values():
                    cola.put_nowait(None)
            hilos = tuple(self._hilos)
        for hilo in hilos:
            hilo.join()


class Bitacora:
    """Conservar todos los avisos recibidos, incluidos los inválidos."""

    def __init__(self) -> None:
        """Crear una bitácora vacía en memoria."""
        self._lock = Lock()
        self._registros: list[Registro] = []

    def atender(self, registro: Registro) -> None:
        """Guardar el aviso completo con su marca de validez."""
        with self._lock:
            self._registros.append(registro)

    @property
    def registros(self) -> tuple[Registro, ...]:
        """Obtener una instantánea de los registros en orden de recepción."""
        with self._lock:
            return tuple(self._registros)


def dias_habiles(inicio: date, fin: date) -> int:
    """Contar lunes a viernes en (inicio, fin], sin descontar festivos."""
    if type(inicio) is not date or type(fin) is not date:
        raise ValueError("Las fechas deben ser date, sin hora")
    if fin < inicio:
        raise ValueError("La fecha final es anterior a la radicación")
    semanas, resto = divmod((fin - inicio).days, 7)
    return semanas * 5 + sum(
        (inicio.weekday() + desplazamiento) % 7 < 5
        for desplazamiento in range(1, resto + 1)
    )


@dataclass(frozen=True)
class Medicion:
    """Resultado de un aviso terminal válido con fecha de radicación conocida."""

    aviso: Aviso
    fecha_radicacion: date
    dias: int


class Indicador:
    """Calcular tiempos y promedios por tipo sobre avisos terminales válidos."""

    def __init__(self) -> None:
        """Crear un indicador sin fechas ni mediciones."""
        self._lock = Lock()
        self._fechas: dict[str, date] = {}
        self._mediciones: list[Medicion] = []

    def guardar_fecha_radicacion(self, numero: str, fecha: date) -> None:
        """Guardar la fecha real de radicación suministrada por el integrador."""
        if not isinstance(numero, str) or not numero.strip():
            raise ValueError("numero: se requiere texto no vacío")
        if type(fecha) is not date:
            raise ValueError("fecha: se requiere date, sin hora")
        with self._lock:
            self._fechas[numero] = fecha

    def atender(self, registro: Registro) -> None:
        """Medir aprobaciones o rechazos válidos; fallar si falta su fecha."""
        aviso = registro.aviso
        if not registro.valida or aviso.estado_nuevo not in {"aprobado", "rechazado"}:
            return
        with self._lock:
            fecha = self._fechas.get(aviso.numero)
            if fecha is None:
                raise ValueError(f"No hay fecha de radicación para {aviso.numero}")
            dias = dias_habiles(fecha, aviso.fecha_hora.date())
            self._mediciones.append(Medicion(aviso, fecha, dias))

    @property
    def mediciones(self) -> tuple[Medicion, ...]:
        """Obtener una instantánea de las mediciones calculadas."""
        with self._lock:
            return tuple(self._mediciones)

    @property
    def promedios(self) -> dict[str, float]:
        """Obtener días hábiles promedio por tipo, sin redondeo adicional."""
        with self._lock:
            totales: dict[str, int] = {}
            cantidades: dict[str, int] = {}
            for medicion in self._mediciones:
                tipo = medicion.aviso.tipo
                totales[tipo] = totales.get(tipo, 0) + medicion.dias
                cantidades[tipo] = cantidades.get(tipo, 0) + 1
            return {tipo: total / cantidades[tipo] for tipo, total in totales.items()}


@dataclass(frozen=True)
class Mensaje:
    """Número de trámite y texto preparado, sin envío al ciudadano."""

    numero: str
    texto: str


class PreparadorMensajes:
    """Preparar los textos acordados por cada aviso válido."""

    def __init__(self) -> None:
        """Crear un preparador sin mensajes."""
        self._lock = Lock()
        self._mensajes: list[Mensaje] = []

    def atender(self, registro: Registro) -> None:
        """Preparar un mensaje únicamente si la transición es válida."""
        if not registro.valida:
            return
        aviso = registro.aviso
        texto = _TEXTOS[aviso.estado_nuevo].format(numero=aviso.numero)
        with self._lock:
            self._mensajes.append(Mensaje(aviso.numero, texto))

    @property
    def mensajes(self) -> tuple[Mensaje, ...]:
        """Obtener una instantánea de los mensajes preparados."""
        with self._lock:
            return tuple(self._mensajes)


class Sistema:
    """Conectar bitácora, indicador y mensajes como consumidores independientes."""

    def __init__(self) -> None:
        """Crear los tres consumidores y conectarlos al canal en memoria."""
        self.canal = Canal()
        self.bitacora = Bitacora()
        self.indicador = Indicador()
        self.mensajes = PreparadorMensajes()
        self.canal.suscribir("bitacora", self.bitacora.atender)
        self.canal.suscribir("indicador", self.indicador.atender)
        self.canal.suscribir("mensajes", self.mensajes.atender)

    def publicar(self, aviso: Aviso) -> None:
        """Publicar sin conocer ni esperar a los consumidores."""
        self.canal.publicar(aviso)

    def esperar(self) -> None:
        """Esperar al procesamiento para consultar resultados o hacer pruebas."""
        self.canal.esperar()

    def cerrar(self) -> None:
        """Procesar lo pendiente y liberar los trabajadores del canal."""
        self.canal.cerrar()
