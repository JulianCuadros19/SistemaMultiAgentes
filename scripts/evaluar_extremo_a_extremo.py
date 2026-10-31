"""Corrida ampliada de extremo a extremo sobre muchos casos sintéticos, uno a la vez (paso 12).

Cada caso de `evaluacion/casos/ampliada/` recorre el flujo completo con los cuatro agentes reales,
como lo haría `scripts/producir_modulo.py --simulado`, con el bucle de la consola del sistema:
- un modelo hace de cliente con lo que sabe el caso;
- el analista simulado decide como en la prueba de extremo a extremo (ADR-0013):
  - en N6 rechaza una vez con los defectos escalados como observaciones y luego aprueba, si la
    aprobación no está bloqueada;
  - en N9 aprueba una especificación sin errores;
  - en N17 aprueba el módulo que aprobó el tester. Una sesión escalada queda en pausa en N17
    para que una persona la devuelva o la cierre.
- una sesión detenida por una falla se reanuda una vez.

Las sesiones quedan en PostgreSQL: se ven en `multiagente sesiones` y en la web. El resultado de
cada caso se escribe en `<salida>/<id del caso>.json`, con la arquitectura esperada (cabecera
`arquitecturas_esperadas`) y la elegida, el desenlace, las versiones, el tiempo y el costo por
nodo. El código y el reporte de cada versión van en `<salida>/<sesión>/v<n>/`. Un caso con
resultado se salta, así que la corrida se retoma donde quedó. Antes de cada caso se suma el costo
de la traza, cliente simulado incluido, y la corrida se detiene al llegar al presupuesto.

Cada llamada al modelo se agrega a docs/mediciones/paso-12-corrida-ampliada.jsonl con su sesión,
sin el contenido de los mensajes. Requiere `docker compose up -d --wait`, el corpus ingerido, la
imagen del entorno aislado y el archivo .env. Tiene costo.

Uso:
    python scripts/evaluar_extremo_a_extremo.py --solo caso-ampliada-16
    python scripts/evaluar_extremo_a_extremo.py --presupuesto 15
    python scripts/evaluar_extremo_a_extremo.py --resumen
"""

import argparse
import json
import logging
import statistics
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from multiagente.core.configuracion import (
    ConfiguracionAzureOpenAI,
    ConfiguracionInterfaces,
    ConfiguracionModelos,
)
from multiagente.interfaces.cliente_simulado import CasoElicitacion, ClienteSimulado, cargar_caso
from multiagente.interfaces.consola import (
    REVISORES,
    AtiendeDetenida,
    DecideRevisor,
    DecisionHumana,
    RespondeCliente,
    Tiempos,
    abrir_sesion,
    escribir_version,
    operar,
)
from multiagente.interfaces.operacion import Operador, VistaSesion, abrir_operador
from multiagente.llm.cliente import crear_cliente
from multiagente.llm.traza import RegistroPorSesion
from multiagente.orquestador.estado import Decision, Fase, Severidad

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_MEDICIONES = RAIZ / "docs" / "mediciones" / "paso-12-corrida-ampliada.jsonl"
CASOS = RAIZ / "evaluacion" / "casos" / "ampliada"
SALIDA = RAIZ / "evaluacion" / "resultados" / "corrida-ampliada"
REANUDACIONES = 1
"""Reanudaciones de una sesión detenida antes de dejarla así."""
NODO_DE_PAUSA = {"dialogo": "N4", "requerimientos": "N6", "especificacion": "N9", "final": "N17"}


@dataclass
class Bitacora:
    """Lo que hizo el analista simulado en una sesión."""

    id_sesion: str | None = None
    rechazos_n6: list[str] = field(default_factory=list)
    aprobados_con_defectos: list[str] = field(default_factory=list)
    capacidades_no_cubiertas: list[str] = field(default_factory=list)
    reanudaciones: int = 0
    motivo_pausa: str | None = None


def observaciones_del_analista(datos: dict[str, Any]) -> str:
    """Observaciones con que el analista devuelve al diálogo lo pendiente con el cliente."""
    preguntas = [p for historia in datos["historias"] for p in historia["preguntas_abiertas"]]
    return "Resolver con el cliente antes de aprobar: " + "; ".join(
        [*datos["defectos"], *preguntas]
    )


def cliente_simulado(simulado: ClienteSimulado, registro: RegistroPorSesion) -> RespondeCliente:
    """El cliente simulado responde la pregunta pendiente; su llamada queda con la sesión."""

    def responder(operador: Operador, vista: VistaSesion) -> str:
        conversacion = operador.estado(vista.id_sesion)["conversacion"]
        with registro.en_sesion(vista.id_sesion):
            respuesta = simulado.responder(conversacion, vista.pausa.datos["pregunta"])
        print(f"Cliente> {respuesta}")
        return respuesta

    return responder


def analista_simulado(bitacora: Bitacora, salida: Path) -> DecideRevisor:
    """Decide en los tres puntos de control como en la prueba de extremo a extremo."""

    def decidir(operador: Operador, vista: VistaSesion) -> DecisionHumana | None:
        punto, datos = vista.pausa.punto, vista.pausa.datos
        revisor = REVISORES[punto]
        if punto == "requerimientos":
            if datos["defectos"] and not bitacora.rechazos_n6:
                bitacora.rechazos_n6.append(observaciones_del_analista(datos))
                return DecisionHumana(Decision.RECHAZADO, revisor, bitacora.rechazos_n6[-1])
            if datos.get("bloqueo"):
                bitacora.motivo_pausa = f"N6 bloqueado: {datos['bloqueo']}"
                return None
            bitacora.aprobados_con_defectos.extend(datos["defectos"])
            return DecisionHumana(Decision.APROBADO, revisor)
        if punto == "especificacion":
            bitacora.capacidades_no_cubiertas = list(datos.get("capacidades_no_cubiertas") or [])
            if datos.get("errores") or datos.get("bloqueo"):
                bitacora.motivo_pausa = (
                    f"N9 con errores: {datos.get('errores') or datos['bloqueo']}"
                )
                return None
            return DecisionHumana(Decision.APROBADO, revisor)
        estado = operador.estado(vista.id_sesion)
        if (version := estado["codigo"].vigente) is not None:
            escribir_version(salida / vista.id_sesion, version, estado["validacion"].reporte)
        if datos.get("escalado") or datos.get("bloqueo") or datos.get("veredicto") != "aprobado":
            bitacora.motivo_pausa = f"N17: {datos.get('bloqueo') or 'el tester no aprobó'}"
            return None
        return DecisionHumana(Decision.APROBADO, revisor)

    return decidir


def reanudar_una_vez(bitacora: Bitacora) -> AtiendeDetenida:
    """Reanuda una sesión detenida hasta `REANUDACIONES` veces; después la deja así."""

    def atender(vista: VistaSesion) -> bool:
        if bitacora.reanudaciones >= REANUDACIONES:
            return False
        bitacora.reanudaciones += 1
        return True

    return atender


def leer_traza() -> list[dict[str, Any]]:
    """Llamadas de la corrida ampliada, de todos los procesos."""
    if not ARCHIVO_MEDICIONES.exists():
        return []
    return [json.loads(linea) for linea in ARCHIVO_MEDICIONES.read_text("utf-8").splitlines()]


def costo_acumulado() -> Decimal:
    """Costo de todas las llamadas de la corrida, con el cliente simulado."""
    return sum((Decimal(llamada["costo_usd"]) for llamada in leer_traza()), Decimal(0))


def desenlace(vista: VistaSesion | None) -> str:
    """Cómo terminó la sesión, para el resumen."""
    if vista is None:
        return "error"
    if vista.fase is Fase.VALIDADO:
        return "validado"
    if vista.pausa is not None:
        if vista.pausa.punto == "final" and vista.pausa.datos.get("escalado"):
            return "escalado"
        return f"en pausa en {NODO_DE_PAUSA[vista.pausa.punto]}"
    if vista.detenida:
        return "detenida"
    return str(vista.fase)


def resultado_del_caso(
    operador: Operador,
    caso: CasoElicitacion,
    bitacora: Bitacora,
    vista: VistaSesion | None,
    tiempos: Tiempos,
    salida: Path,
) -> dict[str, Any]:
    """Reúne lo que se mide de una sesión: diseño, versiones, desenlace, tiempo y costo."""
    id_sesion = bitacora.id_sesion
    estado = operador.estado(id_sesion)
    historial = operador.historial(id_sesion)
    especificacion = estado["arquitectura"].especificacion
    elegida = especificacion.arquitectura_base if especificacion else None
    versiones = []
    for version, validacion in historial:
        escribir_version(salida / id_sesion, version, validacion.reporte)
        bloqueantes = Counter(
            h.regla for h in validacion.hallazgos if h.severidad is not Severidad.BAJA
        )
        versiones.append(
            {
                "numero": version.numero,
                "veredicto": validacion.veredicto.value if validacion.veredicto else None,
                "bloqueantes": dict(sorted(bloqueantes.items())),
                "bajas": sum(h.severidad is Severidad.BAJA for h in validacion.hallazgos),
            }
        )
    por_nodo: dict[str, Decimal] = defaultdict(Decimal)
    llamadas = [llamada for llamada in leer_traza() if llamada.get("sesion") == id_sesion]
    for llamada in llamadas:
        por_nodo[llamada["nodo"]] += Decimal(llamada["costo_usd"])
    sistema = sum((c for nodo, c in por_nodo.items() if nodo != "cliente_simulado"), Decimal(0))
    return {
        "caso": caso.id,
        "titulo": caso.titulo,
        "sesion": id_sesion,
        "esperadas": list(caso.arquitecturas_esperadas),
        "elegida": elegida,
        "coincide": elegida in caso.arquitecturas_esperadas,
        "desenlace": desenlace(vista),
        "motivo_pausa": bitacora.motivo_pausa,
        "modulos": len(especificacion.modulos) if especificacion else 0,
        "dependencias": (
            [d.paquete for d in especificacion.dependencias_externas] if especificacion else []
        ),
        "capacidades_no_cubiertas": bitacora.capacidades_no_cubiertas,
        "requerimientos": len(estado["requerimientos"].requerimientos),
        "casos_plan": len(estado["validacion"].plan_pruebas),
        "rechazos_n6": bitacora.rechazos_n6,
        "aprobados_con_defectos": bitacora.aprobados_con_defectos,
        "reanudaciones": bitacora.reanudaciones,
        "versiones": versiones,
        "iteracion": estado["control"].iteracion,
        "llamadas_n10": sum(llamada["nodo"] == "N10" for llamada in llamadas),
        "llamadas_con_error": sum(bool(llamada.get("error")) for llamada in llamadas),
        "tiempo_sistema_min": round(tiempos.sistema / 60, 2),
        "turno_maximo_s": round(max(tiempos.turnos), 1) if tiempos.turnos else None,
        "cierres_s": [round(segundos, 1) for segundos in tiempos.cierres],
        "costo_por_nodo": {nodo: str(costo) for nodo, costo in sorted(por_nodo.items())},
        "costo_sistema": str(sistema),
        "costo_cliente_simulado": str(por_nodo.get("cliente_simulado", Decimal(0))),
    }


def correr_caso(
    operador: Operador, caso: CasoElicitacion, salida: Path, bitacora: Bitacora
) -> dict[str, Any]:
    """Recorre el flujo completo de un caso con el cliente y el analista simulados."""
    simulado = ClienteSimulado(
        crear_cliente(ConfiguracionAzureOpenAI()),
        ConfiguracionModelos().despliegue_cliente_simulado,
        caso,
        operador.registro,
    )
    tiempos = Tiempos()
    bitacora.id_sesion = abrir_sesion(
        operador, caso.cliente, caso.proyecto, caso.necesidad, tiempos
    )
    print(f"Sesión {bitacora.id_sesion}")
    vista = operar(
        operador,
        bitacora.id_sesion,
        cliente_simulado(simulado, operador.registro),
        analista_simulado(bitacora, salida),
        reanudar_una_vez(bitacora),
        tiempos,
    )
    return resultado_del_caso(operador, caso, bitacora, vista, tiempos, salida)


def correr(casos: list[CasoElicitacion], salida: Path, presupuesto: Decimal) -> None:
    """Corre los casos sin resultado, uno a la vez, mientras alcance el presupuesto."""
    configuracion = ConfiguracionInterfaces(
        traza_llamadas=ARCHIVO_MEDICIONES, carpeta_trabajo=salida
    )
    with abrir_operador(configuracion) as operador:
        for caso in casos:
            archivo = salida / f"{caso.id}.json"
            if archivo.exists():
                print(f"{caso.id}: ya tiene resultado; se salta.")
                continue
            if (gastado := costo_acumulado()) >= presupuesto:
                print(f"Presupuesto alcanzado: USD {gastado:.4f} de {presupuesto}. Se detiene.")
                return
            print(f"\n=== {caso.id} · {caso.titulo} · gastado USD {gastado:.4f} ===")
            bitacora = Bitacora()
            try:
                resultado = correr_caso(operador, caso, salida, bitacora)
            except Exception as error:  # noqa: BLE001 - la corrida sigue con el siguiente caso
                resultado = {
                    "caso": caso.id,
                    "titulo": caso.titulo,
                    "sesion": bitacora.id_sesion,
                    "esperadas": list(caso.arquitecturas_esperadas),
                    "desenlace": "error",
                    "error": f"{type(error).__name__}: {error}",
                    "traza": traceback.format_exc(),
                }
            archivo.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n")
            print(
                f"--- {caso.id}: {resultado['desenlace']} · {resultado.get('elegida')} · USD "
                f"{resultado.get('costo_sistema', '?')} · {resultado.get('tiempo_sistema_min')} min"
            )


def resumir(salida: Path) -> None:
    """Imprime en Markdown la tabla por caso, la cobertura por arquitectura y los totales."""
    resultados = [
        json.loads(archivo.read_text("utf-8")) for archivo in sorted(salida.glob("*.json"))
    ]
    if not resultados:
        print(f"Sin resultados en {salida}.")
        return
    print("| Caso | Esperada | Elegida | Desenlace | Versiones | Bloqueantes | Min | USD |")
    print("|---|---|---|---|---|---|---|---|")
    for r in resultados:
        bloqueantes = " → ".join(",".join(v["bloqueantes"]) or "—" for v in r.get("versiones", []))
        print(
            f"| {r['caso']} | {', '.join(r['esperadas'])} | {r.get('elegida') or '—'} | "
            f"{r['desenlace']} | {len(r.get('versiones', []))} | {bloqueantes or '—'} | "
            f"{r.get('tiempo_sistema_min', '—')} | {r.get('costo_sistema', '—')} |"
        )
    print("\n**Cobertura por arquitectura** (esperada → casos, elegida, coincide):")
    esperadas = Counter(a for r in resultados for a in r["esperadas"][:1])
    elegidas = Counter(r.get("elegida") for r in resultados if r.get("elegida"))
    coinciden = Counter(r["esperadas"][0] for r in resultados if r.get("coincide"))
    for arquitectura in sorted(set(esperadas) | set(elegidas)):
        print(
            f"- {arquitectura}: esperada en {esperadas[arquitectura]}, elegida en "
            f"{elegidas[arquitectura]}, coincide en {coinciden[arquitectura]}"
        )
    print(f"\n**Desenlaces:** {dict(Counter(r['desenlace'] for r in resultados))}")
    sistema = sum((Decimal(r.get("costo_sistema", "0")) for r in resultados), Decimal(0))
    cliente = sum((Decimal(r.get("costo_cliente_simulado", "0")) for r in resultados), Decimal(0))
    minutos = [r["tiempo_sistema_min"] for r in resultados if "tiempo_sistema_min" in r]
    print(
        f"**Costo:** sistema USD {sistema:.4f}, cliente simulado USD {cliente:.4f}; traza completa "
        f"USD {costo_acumulado():.4f}"
    )
    if minutos:
        print(
            f"**Tiempo del sistema:** media {statistics.mean(minutos):.1f} min, máximo "
            f"{max(minutos):.1f} min (RNF-01: 20 min por módulo)"
        )


def main() -> None:
    """Corre los casos de la corrida ampliada o imprime su resumen."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--casos", type=Path, default=CASOS, help="Carpeta de los casos.")
    parser.add_argument("--solo", nargs="+", metavar="ID", help="Corre solo estos casos.")
    parser.add_argument(
        "--presupuesto", type=Decimal, default=Decimal(15), help="Tope en USD de la traza."
    )
    parser.add_argument("--salida", type=Path, default=SALIDA, help="Carpeta de resultados.")
    parser.add_argument("--resumen", action="store_true", help="Solo imprime el resumen.")
    argumentos = parser.parse_args()
    argumentos.salida.mkdir(parents=True, exist_ok=True)
    if argumentos.resumen:
        resumir(argumentos.salida)
        return
    logging.basicConfig(level=logging.WARNING, format="(aviso) %(message)s")
    casos = [cargar_caso(archivo) for archivo in sorted(argumentos.casos.glob("*.md"))]
    if argumentos.solo:
        if desconocidos := sorted(set(argumentos.solo) - {caso.id for caso in casos}):
            parser.error(f"Casos desconocidos: {desconocidos}")
        casos = [caso for caso in casos if caso.id in argumentos.solo]
    correr(casos, argumentos.salida, argumentos.presupuesto)
    resumir(argumentos.salida)


if __name__ == "__main__":
    main()
