"""Línea base de un modelo único sobre los casos de referencia (paso 15, ADR-0019).

En cada corrida, un solo despliegue de Azure OpenAI hace todo el trabajo. Es el de N10, con el
prompt único de `evaluacion/modelo_unico.md`:
- conversa con el mismo cliente simulado que la evaluación del sistema;
- entrega en una respuesta el código, las pruebas y `USO.md`.

No usa recuperación, puntos de control ni tester.

**Resultados.** Cada corrida queda en `<salida>/<caso>/corrida-<n>/`:
- `resultado.json`, con la transcripción, los tiempos, el costo y el error si lo hubo;
- los archivos de la entrega, en `archivos/`.

Una corrida con resultado se salta, así que la evaluación se retoma donde quedó.

**Costo.** Cada llamada, también las del cliente simulado, se agrega a la traza con su corrida, sin
el contenido de los mensajes: por defecto `docs/mediciones/paso-15-modelo-unico.jsonl`. Antes de
cada corrida se suma lo gastado en la traza. Si con una corrida más se pasaría del presupuesto, se
detiene. Cuesta unos 0,5 USD por corrida.

Requiere el archivo .env.

Uso:
    python scripts/evaluar_modelo_unico.py --presupuesto 4.5
    python scripts/evaluar_modelo_unico.py --solo caso-ampliada-12 --corridas 1 --presupuesto 1
    python scripts/evaluar_modelo_unico.py --resumen
"""

import argparse
import json
import logging
from decimal import Decimal
from pathlib import Path

from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionModelos,
    ConfiguracionOrquestador,
    ConfiguracionRazonamiento,
)
from multiagente.evaluacion.modelo_unico import crear_modelo_unico
from multiagente.evaluacion.referencia import casos_de_referencia
from multiagente.evaluacion.traza import gastado_en_traza
from multiagente.interfaces.cliente_simulado import (
    RAIZ_EVALUACION,
    CasoElicitacion,
    ClienteSimulado,
    cargar_caso,
)
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroJsonl

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ_EVALUACION / "resultados" / "paso-15" / "modelo-unico"
TRAZA = RAIZ / "docs" / "mediciones" / "paso-15-modelo-unico.jsonl"
CASOS = RAIZ_EVALUACION / "casos" / "ampliada"
COSTO_ESTIMADO_POR_CORRIDA = Decimal("0.6")
"""Margen que se reserva antes de empezar una corrida, para no pasar del presupuesto."""


def casos(solo: list[str] | None) -> list[CasoElicitacion]:
    """Fichas de los casos de referencia, o de los indicados."""
    ids = solo or casos_de_referencia()
    fichas = {caso.id: caso for caso in map(cargar_caso, sorted(CASOS.glob("*.md")))}
    if desconocidos := sorted(set(ids) - set(fichas)):
        raise SystemExit(f"Casos desconocidos: {desconocidos}")
    return [fichas[id_caso] for id_caso in ids]


def correr(
    seleccion: list[CasoElicitacion],
    corridas: int,
    salida: Path,
    traza: Path,
    presupuesto: Decimal,
) -> None:
    """Corre las corridas sin resultado, mientras alcance el presupuesto."""
    azure = crear_cliente(ConfiguracionAzureOpenAI())
    modelos = ConfiguracionModelos()
    razonamiento = ConfiguracionRazonamiento()
    limite = ConfiguracionOrquestador().max_turnos_elicitacion
    for numero in range(1, corridas + 1):
        for caso in seleccion:
            carpeta = salida / caso.id / f"corrida-{numero}"
            if (carpeta / "resultado.json").exists():
                continue
            if (total := gastado_en_traza(traza)) + COSTO_ESTIMADO_POR_CORRIDA > presupuesto:
                print(
                    f"Presupuesto: USD {total:.4f} de {presupuesto}. Se detiene antes de {carpeta}."
                )
                return
            corrida = f"modelo-unico-{caso.id}-{numero}"
            registro = RegistroJsonl(traza, sesion=corrida)
            cliente = ClienteSimulado(azure, modelos.despliegue_cliente_simulado, caso, registro)
            modelo = crear_modelo_unico(azure, registro, modelos, razonamiento, limite)
            resultado = modelo.resolver(caso, cliente, registro, corrida)
            for ruta, contenido in resultado.archivos.items():
                destino = carpeta / "archivos" / ruta
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(contenido, encoding="utf-8")
            carpeta.mkdir(parents=True, exist_ok=True)
            (carpeta / "resultado.json").write_text(
                resultado.model_dump_json(indent=2, exclude={"archivos"}), encoding="utf-8"
            )
            print(
                f"{caso.id} corrida {numero}: {len(resultado.archivos)} archivos, "
                f"{resultado.turnos_cliente} turnos del cliente, {resultado.tiempo_total_s:.0f} s, "
                f"USD {resultado.costo_modelo_usd:.4f}"
                + (f" · {resultado.error}" if resultado.error else "")
            )


def resumir(salida: Path, traza: Path) -> None:
    """Imprime la tabla de las corridas y lo gastado."""
    print(
        "| Caso | Corrida | Archivos | Turnos del cliente | Límite | Tiempo (s) "
        "| Sin el cliente (s) | Costo (USD) | Error |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for archivo in sorted(salida.glob("*/corrida-*/resultado.json")):
        r = json.loads(archivo.read_text(encoding="utf-8"))
        archivos = sum(1 for p in (archivo.parent / "archivos").rglob("*") if p.is_file())
        sin_cliente = r["tiempo_total_s"] - r["tiempo_cliente_s"]
        print(
            f"| {r['caso']} | {archivo.parent.name} | {archivos} | {r['turnos_cliente']} | "
            f"{'sí' if r['llego_al_limite'] else 'no'} | {r['tiempo_total_s']:.0f} | "
            f"{sin_cliente:.0f} | {Decimal(r['costo_modelo_usd']):.4f} | {r['error'] or '—'} |"
        )
    print(f"\nGastado en la traza, con el cliente simulado: USD {gastado_en_traza(traza):.4f}")


def main() -> None:
    """Punto de entrada del guion."""
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--solo", nargs="+", metavar="ID", help="corre solo estos casos")
    argumentos.add_argument("--corridas", type=int, default=3, help="corridas por caso")
    argumentos.add_argument("--presupuesto", type=Decimal, help="tope en USD de la traza")
    argumentos.add_argument("--salida", type=Path, default=SALIDA, help="carpeta de resultados")
    argumentos.add_argument("--traza", type=Path, default=TRAZA, help="traza de las llamadas")
    argumentos.add_argument("--resumen", action="store_true", help="solo imprime el resumen")
    opciones = argumentos.parse_args()
    if opciones.resumen:
        resumir(opciones.salida, opciones.traza)
        return
    if opciones.presupuesto is None:
        argumentos.error("--presupuesto es obligatorio: la corrida tiene costo")
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")
    correr(
        casos(opciones.solo),
        opciones.corridas,
        opciones.salida,
        opciones.traza,
        opciones.presupuesto,
    )
    resumir(opciones.salida, opciones.traza)


if __name__ == "__main__":
    main()
