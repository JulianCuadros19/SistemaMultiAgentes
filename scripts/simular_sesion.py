"""Recorre una sesión completa del grafo con servicios simulados, persistida en PostgreSQL.

Muestra el esqueleto caminante del paso 5: los 17 nodos, los ciclos conversacional y de
corrección, y los retornos de los tres puntos de control humano. No llama a ningún modelo de
lenguaje. Requiere el contenedor levantado con `docker compose up -d --wait`.

Uso: python scripts/simular_sesion.py [--conservar]
"""

import argparse
from collections import Counter

from multiagente.orquestador.ejecucion import configuracion_hilo
from multiagente.orquestador.grafo import Nodo, construir_grafo
from multiagente.orquestador.simulacion import ServiciosSimulados, guion_completo, recorrer
from multiagente.persistencia.puntos_control import abrir_checkpointer


def main() -> None:
    """Ejecuta la sesión simulada e imprime el recorrido nodo por nodo."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--conservar",
        action="store_true",
        help="Conserva los puntos de control de la sesión en la base en lugar de borrarlos.",
    )
    argumentos = parser.parse_args()

    with abrir_checkpointer() as checkpointer:
        simulacion = ServiciosSimulados(fallos_veredicto=1)
        app = construir_grafo(simulacion.como_servicios()).compile(checkpointer=checkpointer)
        recorrido = recorrer(app, guion_completo(), cliente="Cliente simulado")

        for avance in recorrido.avances:
            nodos = " → ".join(nodo.split("_")[0].upper() for nodo in avance.nodos) or "inicio"
            pausa = f"pausa en «{avance.pausa.punto}»" if avance.pausa else "fin"
            print(f"{nodos}\n    {pausa} · fase {avance.fase}")

        visitas = Counter(recorrido.nodos)
        estado = app.get_state(configuracion_hilo(recorrido.id_sesion)).values
        print(f"\nSesión {recorrido.id_sesion}")
        print(f"Nodos distintos visitados: {len(visitas)} de {len(Nodo)}")
        print(f"Vueltas del ciclo conversacional (N3): {visitas[Nodo.N3]}")
        print(f"Vueltas del ciclo de corrección (N10): {visitas[Nodo.N10]}")
        for aprobacion in estado["sesion"].aprobaciones:
            detalle = f" · {aprobacion.observaciones}" if aprobacion.observaciones else ""
            print(f"  {aprobacion.punto:15} {aprobacion.decision:10}{detalle}")
        print(f"Fase final: {estado['sesion'].fase}")

        if argumentos.conservar:
            print("Puntos de control conservados en la base.")
        else:
            checkpointer.delete_thread(recorrido.id_sesion)
            print("Puntos de control de la sesión borrados.")


if __name__ == "__main__":
    main()
