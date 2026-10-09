"""Servidor de la interfaz web: `multiagente web`.

Abre el operador del sistema completo y sirve la aplicación con uvicorn, solo en la máquina local
(`INTERFAZ_HOST_WEB`, por defecto 127.0.0.1): no hay autenticación hasta el paso 14.
"""

import uvicorn

from multiagente.core.configuracion import ConfiguracionInterfaces
from multiagente.interfaces.operacion import abrir_operador
from multiagente.interfaces.web.aplicacion import crear_aplicacion


def servir(configuracion: ConfiguracionInterfaces, puerto: int | None = None) -> None:
    """Sirve la interfaz web hasta que la persona la detenga con Ctrl+C.

    Las sesiones viven en los puntos de control: si el servidor se detiene a mitad de un avance,
    la sesión aparece detenida al volver a levantarlo y se reanuda desde la página.

    Args:
        configuracion: Dirección, puerto y traza de la interfaz.
        puerto: Puerto; si se omite, el de la configuración.
    """
    puerto = puerto or configuracion.puerto_web
    with abrir_operador(configuracion) as operador:
        print(f"Interfaz web en http://{configuracion.host_web}:{puerto}/ · Ctrl+C para detenerla.")
        uvicorn.run(
            crear_aplicacion(operador),
            host=configuracion.host_web,
            port=puerto,
            log_level="warning",
        )
