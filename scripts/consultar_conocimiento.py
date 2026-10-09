"""Consulta la base de conocimiento como lo haría un agente, solo en sus colecciones autorizadas.

Muestra los fragmentos recuperados con su similitud y sus rangos semántico y léxico, y los
descartados por irrelevantes (RF-32). Requiere haber ejecutado scripts/ingestar_conocimiento.py.

Uso: python scripts/consultar_conocimiento.py --agente tester "dinero con punto flotante"
"""

import argparse

import psycopg

from multiagente.core.configuracion import ConfiguracionBaseDatos
from multiagente.rag.colecciones import Agente
from multiagente.rag.embeddings import VectorizadorTEI
from multiagente.rag.recuperacion import Recuperador


def main() -> None:
    """Ejecuta una consulta e imprime el resultado."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("consulta", help="Texto de la consulta.")
    parser.add_argument("--agente", type=Agente, choices=list(Agente), required=True)
    parser.add_argument("-k", type=int, default=None, help="Número máximo de fragmentos.")
    argumentos = parser.parse_args()

    with psycopg.connect(ConfiguracionBaseDatos().cadena_conexion()) as conexion:
        recuperador = Recuperador(conexion, VectorizadorTEI(), argumentos.agente)
        resultado = recuperador.recuperar(argumentos.consulta, k=argumentos.k)

    print(f"Agente: {resultado.agente} · colecciones: {', '.join(resultado.colecciones)}")
    if resultado.sin_contexto:
        print("Sin contexto relevante en la base de conocimiento.")
    for posicion, fragmento in enumerate(resultado.fragmentos, 1):
        print(
            f"{posicion}. [{fragmento.coleccion}] {fragmento.titulo}\n"
            f"   similitud {fragmento.similitud:.3f} · rango semántico "
            f"{fragmento.rango_semantico or '-'} · léxico {fragmento.rango_lexico or '-'}"
        )
    if resultado.descartados:
        print(f"Descartados por irrelevantes: {len(resultado.descartados)}")


if __name__ == "__main__":
    main()
