"""Cálculo de tiempos hábiles para transiciones válidas a estados finales."""

from dataclasses import dataclass
from datetime import date, timedelta

from eventos.aviso import AvisoCambioEstado, RegistroFechasTramite, RegistroIndicadores


def _dias_habiles(inicio: date, fin: date) -> int:
    if fin < inicio:
        raise ValueError("La fecha final no puede preceder a la radicación.")
    dias = 0
    actual = inicio
    while actual < fin:
        actual += timedelta(days=1)
        if actual.weekday() < 5:
            dias += 1
    return dias


@dataclass
class IndicadorConsumidor:
    """Calcula tiempos de trámites terminados usando fechas registradas.

    Args:
        registro: Almacén de cálculos y promedios.
        fechas: Almacén de fechas de radicación.
    """

    registro: RegistroIndicadores
    fechas: RegistroFechasTramite

    def manejar(self, aviso: AvisoCambioEstado) -> None:
        """Registra días hábiles solo para transiciones válidas a estados finales.

        Args:
            aviso: Evento recibido del canal.

        Raises:
            ValueError: La fecha final precede a la radicación.
        """
        if not aviso.es_valida or aviso.estado_nuevo not in ("aprobado", "rechazado"):
            return
        inicio = self.fechas.obtener_fecha_radicado(aviso.numero_tramite)
        if inicio is None:
            return
        dias = _dias_habiles(inicio, aviso.fecha_hora.date())
        self.registro.registrar_dias(aviso.numero_tramite, aviso.tipo_tramite, dias)
