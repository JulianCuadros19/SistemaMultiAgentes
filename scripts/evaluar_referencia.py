"""Evalúa implementaciones con las pruebas de aceptación de referencia (paso 15, ADR-0019).

Las mismas pruebas de `evaluacion/referencia/<caso>/` evalúan al sistema y a las dos líneas base de
un solo modelo. Corren en el entorno aislado, así que no tienen costo de modelos.

- `--oraculo` comprueba, antes de medir, que las pruebas de cada caso pasan con su implementación
  de control y que cada mutante falla al menos una.
- `--manifiesto ARCHIVO` evalúa las implementaciones de una lista JSON. Cada entrada trae
  `etiqueta`, `enfoque`, `caso`, `carpeta` (la raíz de la implementación, con `src/` y `tests/`) y
  `adaptador`.

  Por implementación se calculan:
  - las verificaciones de referencia;
  - sus pruebas propias;
  - los hallazgos de Ruff por severidad.

  El resultado queda en `<salida>/<etiqueta>.json`. Una implementación con resultado se salta, salvo
  con `--rehacer`.
- `--resumen` imprime la tabla de los resultados de la carpeta de salida.
- `--recolectar` reúne las implementaciones de los casos de referencia en
  `evaluacion/referencia/<caso>/implementaciones/<etiqueta>/`, versionadas con su origen, y escribe
  el manifiesto `evaluacion/referencia/implementaciones.json`. Reúne tres fuentes:
  - el sistema: la última versión de cada sesión de las corridas automáticas;
  - el modelo con diálogo: la entrega de cada corrida;
  - el modelo de un solo prompt: la entrega de cada corrida.

  Cada entrada espera su adaptador en `evaluacion/referencia/<caso>/adaptadores/<etiqueta>.py`. La
  evaluación salta las que todavía no lo tienen.

Requiere Docker y la imagen del entorno aislado (`docker compose build sandbox`), salvo
`--recolectar` y `--resumen`.

Uso:
    python scripts/evaluar_referencia.py --oraculo
    python scripts/evaluar_referencia.py --recolectar
    python scripts/evaluar_referencia.py --manifiesto evaluacion/referencia/implementaciones.json
    python scripts/evaluar_referencia.py --resumen
"""

import argparse
import json
import shutil
from pathlib import Path

from multiagente.evaluacion.referencia import (
    RAIZ_REFERENCIA,
    ErrorReferencia,
    ResultadoReferencia,
    cargar_caso_referencia,
    casos_de_referencia,
    evaluar_referencia,
    hallazgos_estaticos,
    leer_implementacion,
    pruebas_propias,
    validar_oraculo,
)
from multiagente.sandbox.ejecutor import EntornoAislado

RAIZ = Path(__file__).resolve().parents[1]
RESULTADOS = RAIZ / "evaluacion" / "resultados" / "paso-15"
SALIDA = RESULTADOS / "referencia"
MANIFIESTO = RAIZ_REFERENCIA / "implementaciones.json"
CORRIDAS_DEL_SISTEMA = ("corrida-ampliada", "sistema-2")
"""Carpetas de las corridas automáticas del sistema, en orden: la ampliada y la adicional."""
LINEAS_BASE = (
    ("modelo-unico", "modelo-unico", "modelo_unico"),
    ("llm-un-prompt", "un-prompt", "un_prompt"),
)
"""Por cada línea base: su carpeta de resultados, el prefijo de su etiqueta y su enfoque."""


def oraculo(entorno: EntornoAislado, salida: Path) -> bool:
    """Valida el oráculo de cada caso e informa el resultado.

    Args:
        entorno: Entorno aislado.
        salida: Carpeta donde se guarda la validación.

    Returns:
        Si los tres oráculos son válidos.
    """
    validos = True
    resultados = {}
    for id_caso in casos_de_referencia():
        validacion = validar_oraculo(entorno, cargar_caso_referencia(id_caso))
        resultados[id_caso] = validacion.model_dump(mode="json")
        control = validacion.control
        print(
            f"{id_caso}: control {control.cuenta('paso')} de {control.total} · "
            f"{'válido' if validacion.valido else 'NO VÁLIDO'}"
        )
        for nombre, resultado in validacion.mutantes.items():
            fallan = [v.nombre for v in resultado.verificaciones if v.resultado != "paso"]
            print(f"  mutante {nombre}: falla {len(fallan)} ({', '.join(fallan) or 'ninguna'})")
        for verificacion in control.verificaciones:
            if verificacion.resultado != "paso":
                print(f"  control: {verificacion.nombre} {verificacion.resultado}")
                print("    " + verificacion.detalle[-600:].replace("\n", "\n    "))
        validos = validos and validacion.valido
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "oraculo.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return validos


def evaluar_manifiesto(
    entorno: EntornoAislado, manifiesto: Path, salida: Path, rehacer: bool
) -> None:
    """Evalúa cada implementación del manifiesto y guarda su resultado.

    Args:
        entorno: Entorno aislado.
        manifiesto: Lista JSON de implementaciones.
        salida: Carpeta de los resultados.
        rehacer: Si se evalúan también las que ya tienen resultado.
    """
    salida.mkdir(parents=True, exist_ok=True)
    for entrada in json.loads(manifiesto.read_text(encoding="utf-8")):
        destino = salida / f"{entrada['etiqueta']}.json"
        if destino.exists() and not rehacer:
            print(f"{entrada['etiqueta']}: ya evaluada")
            continue
        if not (RAIZ / entrada["adaptador"]).exists():
            print(f"{entrada['etiqueta']}: sin adaptador todavía")
            continue
        caso = cargar_caso_referencia(entrada["caso"])
        implementacion = leer_implementacion(RAIZ / entrada["carpeta"])
        adaptador = (RAIZ / entrada["adaptador"]).read_text(encoding="utf-8")
        try:
            referencia = evaluar_referencia(entorno, caso, adaptador, implementacion)
        except ErrorReferencia as error:
            print(f"{entrada['etiqueta']}: {error}")
            continue
        propias = pruebas_propias(entorno, implementacion)
        resultado = {
            **entrada,
            "referencia": referencia.model_dump(mode="json"),
            "pasan": referencia.cuenta("paso"),
            "total": referencia.total,
            "ausentes": referencia.cuenta("ausente"),
            "tasa_errores": round(referencia.tasa_errores, 4),
            "pruebas_propias": propias.model_dump(mode="json"),
            "hallazgos": hallazgos_estaticos(implementacion),
        }
        destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"{entrada['etiqueta']}: {resultado['pasan']} de {resultado['total']} "
            f"({resultado['ausentes']} ausentes) · propias {propias.pasan} de {propias.total}"
        )


def resumen(salida: Path) -> None:
    """Imprime la tabla de resultados de la carpeta de salida.

    Args:
        salida: Carpeta de los resultados.
    """
    print("| Etiqueta | Enfoque | Caso | Pasan | Ausentes | Tasa de errores | Propias | Ruff |")
    print("|---|---|---|---|---|---|---|---|")
    for archivo in sorted(salida.glob("*.json")):
        if archivo.name == "oraculo.json":
            continue
        r = json.loads(archivo.read_text(encoding="utf-8"))
        referencia = ResultadoReferencia.model_validate(r["referencia"])
        propias = r["pruebas_propias"]
        hallazgos = ", ".join(f"{k} {v}" for k, v in sorted(r["hallazgos"].items())) or "—"
        pasan = f"{referencia.cuenta('paso')} de {referencia.total}"
        print(
            f"| {r['etiqueta']} | {r['enfoque']} | {r['caso']} | {pasan} | "
            f"{referencia.cuenta('ausente')} | {referencia.tasa_errores:.2f} | "
            f"{propias['pasan']} de {propias['total']} | {hallazgos} |"
        )


def _relativa(ruta: Path) -> str:
    return ruta.relative_to(RAIZ).as_posix()


def _ultima_version(sesion: Path) -> Path | None:
    """Carpeta de la última versión de una sesión, `v<n>`, o None si no hay versiones."""
    versiones = [p for p in sesion.glob("v*") if p.is_dir() and p.name[1:].isdigit()]
    return max(versiones, key=lambda p: int(p.name[1:])) if versiones else None


def _entrada(etiqueta: str, enfoque: str, caso: str, codigo: Path, origen: Path) -> dict[str, str]:
    """Copia una implementación y su origen a la carpeta versionada del caso."""
    destino = RAIZ_REFERENCIA / caso / "implementaciones" / etiqueta
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(
        codigo, destino / "codigo", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    shutil.copy(origen, destino / f"origen{origen.suffix}")
    return {
        "etiqueta": etiqueta,
        "enfoque": enfoque,
        "caso": caso,
        "carpeta": _relativa(destino / "codigo"),
        "origen": _relativa(destino / f"origen{origen.suffix}"),
        "adaptador": _relativa(RAIZ_REFERENCIA / caso / "adaptadores" / f"{etiqueta}.py"),
    }


def recolectar() -> list[dict[str, str]]:
    """Reúne las implementaciones de los casos de referencia y escribe el manifiesto."""
    entradas = []
    for caso in casos_de_referencia():
        numero = caso.rsplit("-", 1)[-1]
        for orden, nombre in enumerate(CORRIDAS_DEL_SISTEMA, start=1):
            resultado = RESULTADOS / nombre / f"{caso}.json"
            if not resultado.exists():
                continue
            sesion = json.loads(resultado.read_text(encoding="utf-8"))["sesion"]
            if (version := _ultima_version(RESULTADOS / nombre / sesion)) is not None:
                etiqueta = f"sistema-{numero}-{orden}"
                entradas.append(_entrada(etiqueta, "sistema", caso, version, resultado))
        for carpeta, prefijo, enfoque in LINEAS_BASE:
            for resultado in sorted((RESULTADOS / carpeta / caso).glob("corrida-*/resultado.json")):
                corrida = resultado.parent.name.removeprefix("corrida-")
                archivos = resultado.parent / "archivos"
                if archivos.is_dir():
                    etiqueta = f"{prefijo}-{numero}-{corrida}"
                    entradas.append(_entrada(etiqueta, enfoque, caso, archivos, resultado))
    MANIFIESTO.write_text(
        json.dumps(entradas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for entrada in entradas:
        tiene = "con adaptador" if (RAIZ / entrada["adaptador"]).exists() else "sin adaptador"
        print(f"{entrada['etiqueta']}: {entrada['carpeta']} ({tiene})")
    return entradas


def main() -> None:
    """Punto de entrada del guion."""
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    accion = argumentos.add_mutually_exclusive_group(required=True)
    accion.add_argument("--oraculo", action="store_true", help="valida el oráculo de cada caso")
    accion.add_argument("--manifiesto", type=Path, help="lista JSON de implementaciones")
    accion.add_argument("--resumen", action="store_true", help="tabla de los resultados")
    accion.add_argument("--recolectar", action="store_true", help="reúne las implementaciones")
    argumentos.add_argument("--salida", type=Path, default=SALIDA, help="carpeta de resultados")
    argumentos.add_argument("--rehacer", action="store_true", help="evalúa también las evaluadas")
    opciones = argumentos.parse_args()
    if opciones.oraculo:
        raise SystemExit(0 if oraculo(EntornoAislado(), opciones.salida) else 1)
    if opciones.recolectar:
        recolectar()
        return
    if opciones.manifiesto:
        evaluar_manifiesto(EntornoAislado(), opciones.manifiesto, opciones.salida, opciones.rehacer)
    else:
        resumen(opciones.salida)


if __name__ == "__main__":
    main()
