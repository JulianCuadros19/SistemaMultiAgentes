"""Tareas en segundo plano de la web: cada avance largo corre aparte y la página lo consulta.

Generar un módulo tarda hasta 12 minutos: la petición no puede esperarlo. El ejecutor lanza cada
avance en un hilo, admite una sola tarea a la vez por sesión, contra envíos dobles, y guarda el
error de la última tarea para mostrarlo. El estado del grafo vive en los puntos de control, de
modo que la página lo consulta mientras tanto y, si el proceso se reinicia, la sesión aparece
detenida y se reanuda.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Tarea:
    """Avance de una sesión en curso o terminado.

    Attributes:
        descripcion: Qué se está haciendo, para mostrarlo a la persona.
        inicio: Momento de inicio, de `time.monotonic`.
        terminada: Si la tarea ya terminó.
        error: Error con que terminó, si falló.
    """

    descripcion: str
    inicio: float
    terminada: bool = False
    error: str | None = None

    @property
    def segundos(self) -> int:
        """Segundos transcurridos desde el inicio."""
        return int(time.monotonic() - self.inicio)


class EjecutorDeTareas:
    """Lanza los avances de cada sesión en segundo plano, uno a la vez por sesión."""

    def __init__(self, sincronico: bool = False) -> None:
        """Crea el ejecutor.

        Args:
            sincronico: Ejecuta cada tarea en el mismo hilo antes de volver; lo usan las pruebas.
        """
        self.sincronico = sincronico
        self._tareas: dict[str, Tarea] = {}
        self._candado = threading.Lock()

    def lanzar(self, id_sesion: str, descripcion: str, accion: Callable[[], object]) -> bool:
        """Lanza una tarea de la sesión si no hay otra en curso.

        Args:
            id_sesion: Identificador de la sesión.
            descripcion: Qué hace la tarea, para mostrarlo.
            accion: Trabajo de la tarea; su excepción queda como error de la tarea.

        Returns:
            True si se lanzó; False si la sesión ya tenía una tarea en curso.
        """
        with self._candado:
            previa = self._tareas.get(id_sesion)
            if previa is not None and not previa.terminada:
                return False
            tarea = Tarea(descripcion=descripcion, inicio=time.monotonic())
            self._tareas[id_sesion] = tarea

        def ejecutar() -> None:
            try:
                accion()
            except Exception as error:
                # El grafo guardó el último punto de control: la sesión se puede reanudar.
                tarea.error = f"{type(error).__name__}: {error}"
            finally:
                tarea.terminada = True

        if self.sincronico:
            ejecutar()
        else:
            threading.Thread(target=ejecutar, name=f"sesion-{id_sesion}", daemon=True).start()
        return True

    def en_curso(self, id_sesion: str) -> Tarea | None:
        """La tarea en curso de la sesión, si la hay."""
        tarea = self._tareas.get(id_sesion)
        return tarea if tarea is not None and not tarea.terminada else None

    def retirar_error(self, id_sesion: str) -> str | None:
        """Devuelve el error de la última tarea terminada de la sesión y lo olvida.

        Se muestra una sola vez: la siguiente carga de la página ya no lo repite.
        """
        with self._candado:
            tarea = self._tareas.get(id_sesion)
            if tarea is None or not tarea.terminada or tarea.error is None:
                return None
            error, tarea.error = tarea.error, None
            return error
