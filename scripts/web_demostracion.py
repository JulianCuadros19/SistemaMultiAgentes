"""Levanta la web con servicios simulados y una sesión en cada estado, sin costo de modelos.

Sirve para revisar, rediseñar y capturar la interfaz web sin llamar a Azure OpenAI ni tocar
PostgreSQL. Los agentes son los simulados del paso 5 y todo vive en memoria: al detener el
servidor, las sesiones desaparecen. Las pruebas propias de N17 sí usan el entorno aislado de
Docker, con su imagen construida.

Abre nueve sesiones, una por estado que la interfaz debe mostrar:
- en el diálogo con el cliente;
- en la aprobación de los requerimientos (N6), de la especificación (N9) y final (N17);
- validada;
- en pausa por presupuesto;
- escalada;
- detenida por una falla;
- cerrada.

Uso:
    python scripts/web_demostracion.py                  # http://127.0.0.1:8010/
    python scripts/web_demostracion.py --puerto 8011
"""

import argparse
from decimal import Decimal

import uvicorn
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.operacion import Operador
from multiagente.interfaces.web.aplicacion import crear_aplicacion
from multiagente.orquestador.estado import Decision
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import ErrorSimulado, ServiciosSimulados, guion_completo
from multiagente.orquestador.traza import TrazaEnMemoria
from multiagente.persistencia.puntos_control import serializador

COSTO_POR_LLAMADA = Decimal("0.02")
"""Costo que anota cada nodo con modelo, para que el gasto de las sesiones se vea realista."""

RESPUESTAS = guion_completo().respuestas_cliente[:7]
"""Respuestas del cliente simulado hasta confirmar el resumen, que lleva la sesión a N6."""


class Demostracion:
    """Grafos simulados que comparten los puntos de control y la traza, como un solo sistema."""

    def __init__(self) -> None:
        """Prepara la memoria compartida de las sesiones y de su traza."""
        self.puntos_control = InMemorySaver(serde=serializador())
        self.traza = TrazaEnMemoria()

    def operador(
        self, simulacion: ServiciosSimulados, presupuesto: Decimal = Decimal("1.50")
    ) -> Operador:
        """Operador sobre un grafo con estos servicios simulados y este presupuesto.

        Args:
            simulacion: Servicios simulados, con sus fallos configurados.
            presupuesto: Presupuesto por módulo de las sesiones que abra este operador.

        Returns:
            El operador, que guarda sus sesiones en la memoria compartida.
        """
        configuracion = ConfiguracionOrquestador(
            _env_file=None, presupuesto_maximo_por_modulo_usd=presupuesto
        )
        app = construir_grafo(simulacion.como_servicios(), configuracion, self.traza).compile(
            checkpointer=self.puntos_control
        )
        return Operador(app, traza=self.traza)


def hasta_requerimientos(operador: Operador, cliente: str, proyecto: str, necesidad: str) -> str:
    """Abre una sesión y responde como el cliente hasta que espera la aprobación de N6."""
    id_sesion = operador.iniciar(cliente, proyecto, necesidad)
    for respuesta in RESPUESTAS:
        operador.responder(id_sesion, respuesta)
    return id_sesion


def hasta_final(operador: Operador, cliente: str, proyecto: str, necesidad: str) -> str:
    """Lleva una sesión hasta la aprobación final (N17), aprobando N6 y N9."""
    id_sesion = hasta_requerimientos(operador, cliente, proyecto, necesidad)
    operador.decidir(id_sesion, Decision.APROBADO, "Laura")
    operador.decidir(id_sesion, Decision.APROBADO, "Julián")
    return id_sesion


def preparar(demostracion: Demostracion) -> Operador:
    """Abre una sesión por estado y devuelve el operador que sirve la web.

    El orden importa: los servicios cuentan sus fallos iniciales entre todas las sesiones.
    """
    principal = demostracion.operador(
        ServiciosSimulados(fallos_veredicto=1, costo_por_llamada=COSTO_POR_LLAMADA)
    )
    necesidad = guion_completo().necesidad

    # La primera en llegar al tester gasta su fallo inicial: v1 rechazada y v2 aprobada.
    hasta_final(
        principal, "Oficina de catastro municipal (sintética)", "Gestión catastral", necesidad
    )
    validada = hasta_final(
        principal,
        "Secretaría de Hacienda de San Telmo (sintética)",
        "Servicio de tarifas prediales",
        "Consultar la tarifa del impuesto predial de un predio por su avalúo y destino",
    )
    principal.decidir(validada, Decision.APROBADO, "Julián")
    disenada = hasta_requerimientos(
        principal,
        "Inmobiliaria Horizonte Sur (sintética)",
        "Ciclo de vida de contratos",
        "Llevar el ciclo de vida de los contratos de arrendamiento, del borrador a la terminación",
    )
    principal.decidir(disenada, Decision.APROBADO, "Laura")
    hasta_requerimientos(
        principal,
        "Empresa de Servicios Públicos del Norte (sintética)",
        "Conciliación de recaudo",
        "Conciliar cada día el recaudo reportado por tres bancos contra las facturas emitidas",
    )
    en_dialogo = principal.iniciar(
        "Almacenes El Trébol (sintética)",
        "Crédito rotativo de clientes",
        "Necesitamos administrar el cupo de crédito de nuestros clientes con compras a crédito, "
        "abonos y bloqueos por mora, sin que nadie quede debiendo más de su cupo.",
    )
    for respuesta in RESPUESTAS[:2]:
        principal.responder(en_dialogo, respuesta)
    cerrada = principal.iniciar(
        "Centro Empresarial Torre Alameda (sintética)",
        "Reservas de parqueadero",
        "Reservar cupos de parqueadero por franja horaria para los visitantes del edificio",
    )
    principal.cerrar(cerrada, "Julián", "El cliente aplazó el proyecto para el próximo año.")

    # Las tres que necesitan otros servicios o presupuesto se abren con su propio operador.
    escalada = demostracion.operador(
        ServiciosSimulados(fallos_veredicto=99, costo_por_llamada=COSTO_POR_LLAMADA)
    )
    hasta_final(
        escalada,
        "Colegio Campestre Los Almendros (sintética)",
        "Aplicación de pagos de pensiones",
        "Aplicar los pagos de pensiones escolares que confirma o reversa la pasarela",
    )
    sin_presupuesto = demostracion.operador(
        ServiciosSimulados(fallos_veredicto=0, costo_por_llamada=COSTO_POR_LLAMADA),
        presupuesto=Decimal("0.12"),
    )
    agotada = sin_presupuesto.iniciar(
        "Cooperativa Lechera El Páramo (sintética)",
        "Monitoreo de cuartos fríos",
        "Alertar cuando la temperatura de un cuarto frío se sale de su rango",
    )
    for respuesta in RESPUESTAS:
        if sin_presupuesto.vista(agotada).pausa.punto != "dialogo":
            break  # Alcanzó el presupuesto: espera que alguien lo amplíe o cierre la sesión.
        sin_presupuesto.responder(agotada, respuesta)
    con_falla = demostracion.operador(
        ServiciosSimulados(
            fallos_veredicto=0, fallos_ejecucion=1, costo_por_llamada=COSTO_POR_LLAMADA
        )
    )
    try:
        hasta_final(
            con_falla,
            "Cámara de Comercio de Puerto Claro (sintética)",
            "Servicio de validación de NIT",
            "Validar el dígito de verificación del NIT de los comerciantes que se registran",
        )
    except ErrorSimulado:
        pass  # La sesión queda detenida en N11, que es el estado que se quiere mostrar.
    return principal


def main() -> None:
    """Prepara las sesiones de demostración y sirve la web hasta que se detenga con Ctrl+C."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--puerto", type=int, default=8010, help="Puerto local de la web.")
    argumentos = parser.parse_args()
    operador = preparar(Demostracion())
    print(f"Demostración en http://127.0.0.1:{argumentos.puerto}/ · Ctrl+C para detenerla.")
    uvicorn.run(
        crear_aplicacion(operador), host="127.0.0.1", port=argumentos.puerto, log_level="warning"
    )


if __name__ == "__main__":
    main()
