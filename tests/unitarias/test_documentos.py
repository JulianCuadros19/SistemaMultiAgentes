"""Documentos legibles de los artefactos (RF-33) y paquete de exportación del módulo (RF-35)."""

import json
import re
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.core.esquemas.especificacion_diseno import (
    DependenciaExterna,
    EspecificacionDiseno,
)
from multiagente.core.esquemas.requerimiento import (
    BacklogHistorias,
    HistoriaUsuario,
    RequerimientoFormal,
)
from multiagente.interfaces.documentos import (
    ErrorExportacion,
    especificacion_md,
    paquete_del_modulo,
    requerimientos_md,
    requirements_del_modulo,
    trazabilidad_md,
)
from multiagente.orquestador.ejecucion import (
    avanzar,
    configuracion_hilo,
    iniciar_sesion,
    validaciones,
)
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import ServiciosSimulados, guion_completo
from multiagente.persistencia.puntos_control import serializador
from multiagente.sandbox.requisitos import versiones_probadas

RAIZ = Path(__file__).resolve().parents[2]
ANEXOS = RAIZ / "tests" / "datos" / "anexos"


def rf27() -> RequerimientoFormal:
    datos = json.loads((ANEXOS / "anexo_a_rf27.json").read_text(encoding="utf-8"))
    datos.pop("_fuente")
    return RequerimientoFormal.model_validate(datos)


def backlog() -> list[HistoriaUsuario]:
    datos = json.loads((ANEXOS / "anexo_a_backlog.json").read_text(encoding="utf-8"))
    datos.pop("_fuente", None)
    return BacklogHistorias.model_validate(datos).historias


def especificacion_de_referencia() -> EspecificacionDiseno:
    plantilla = (
        RAIZ / "knowledge_base/arquitecturas_referencia/02-especificacion-de-diseno.md"
    ).read_text(encoding="utf-8")
    datos = json.loads(re.search(r"```json\n(.*?)\n```", plantilla, re.S).group(1))
    return EspecificacionDiseno.model_validate(datos)


def test_requerimientos_en_el_formato_del_anexo_a():
    historias = backlog()
    documento = requerimientos_md(historias, [rf27()], {"RF-27": ["eli-003 v1.1 · Plantilla"]})

    assert documento.startswith("# Requerimientos\n")
    assert f"| {historias[0].id} | Profesor |" in documento
    assert "## RF-27 · versión 1.0" in documento
    assert "| Título | Como analista del equipo técnico, quiero que el ciclo" in documento
    assert "| ESC-03 · Escalamiento por límite de iteraciones | DADO QUE" in documento
    assert "| Requerimiento relacionado | RF-19, RF-21, RF-24, RF-26 |" in documento
    assert "- eli-003 v1.1 · Plantilla" in documento


def test_especificacion_en_el_formato_del_anexo_b():
    especificacion = especificacion_de_referencia()
    documento = especificacion_md(especificacion)

    assert documento.startswith(f"# Especificación de diseño {especificacion.id_especificacion}")
    for modulo in especificacion.modulos:
        assert f"### {modulo.nombre}" in documento
        assert f"`{modulo.ruta}`" in documento
    assert "## Modelo de datos" in documento
    assert "## Reglas de dependencia" in documento


def sesion_validada():
    """Sesión simulada completa: rechazos en los tres puntos de control y módulo validado."""
    app = construir_grafo(
        ServiciosSimulados(fallos_veredicto=1).como_servicios(),
        ConfiguracionOrquestador(_env_file=None),
    ).compile(checkpointer=InMemorySaver(serde=serializador()))
    guion = guion_completo()
    id_sesion, avance = iniciar_sesion(app, "Oficina", guion.proyecto, guion.necesidad)
    while avance.pausa is not None:
        avance = avanzar(app, id_sesion, guion.responder(avance.pausa.punto))
    return app.get_state(configuracion_hilo(id_sesion)).values, validaciones(app, id_sesion)


def test_trazabilidad_de_la_sesion():
    estado, historial = sesion_validada()
    documento = trazabilidad_md(estado, historial)

    assert f"# Trazabilidad de la sesión {estado['sesion'].id_sesion}" in documento
    assert "fase: validado" in documento
    assert documento.count("| rechazado |") == 3
    assert documento.count("| aprobado |") == 3
    assert "- Versión 1 · 1 archivos · rechazado" in documento
    assert "  - Atiende: El radicado debe incluir el año" in documento


def test_paquete_del_modulo_validado():
    estado, historial = sesion_validada()
    paquete = paquete_del_modulo(estado, historial, versiones_probadas())

    version = estado["codigo"].vigente
    assert {ruta.removeprefix("codigo/") for ruta in paquete if ruta.startswith("codigo/")} == {
        *version.archivos,
        "requirements.txt",
    }
    requirements = paquete["codigo/requirements.txt"].splitlines()
    assert "pytest==9.1.1" in requirements and "pluggy==1.6.0" in requirements
    assert "## Cómo ponerlo en marcha" in paquete["LEEME.md"]
    assert "pip install -r requirements.txt" in paquete["LEEME.md"]
    assert "el módulo se probó con Python 3.11" in paquete["LEEME.md"]
    # Los artefactos estructurados se exportan validados contra su esquema.
    requerimientos = json.loads(paquete["requerimientos.json"])
    assert [
        RequerimientoFormal.model_validate(r) for r in requerimientos["requerimientos"]
    ] == list(estado["requerimientos"].requerimientos)
    especificacion = EspecificacionDiseno.model_validate_json(paquete["especificacion.json"])
    assert especificacion == estado["arquitectura"].especificacion
    for nombre in ("LEEME.md", "requerimientos.md", "especificacion.md", "trazabilidad.md"):
        assert paquete[nombre].endswith("\n")
    assert paquete["decision_arquitectura.md"].startswith(estado["arquitectura"].registro_decision)
    assert paquete["validacion.md"].startswith("# Reporte simulado de la versión 3")


def test_el_paquete_corrige_el_documento_de_uso_de_una_version_anterior():
    estado, historial = sesion_validada()
    codigo = estado["codigo"]
    anterior = codigo.vigente.model_copy(
        update={
            "archivos": {
                **codigo.vigente.archivos,
                "USO.md": "# Uso\n\n## Requisitos\n\nPython 3.11.\n\n## Instalación\n\n"
                "`python3.11 -m venv .venv` y `pip install pytest`.\n\n## Supuestos\n\nNinguno.\n",
            }
        }
    )
    estado = {**estado, "codigo": codigo.model_copy(update={"versiones": (anterior,)})}
    uso = paquete_del_modulo(estado, historial, versiones_probadas())["codigo/USO.md"]

    assert "python3.11" not in uso and "pip install pytest" not in uso
    assert "## Instalación\n\nDesde la carpeta del código" in uso
    assert uso.endswith("## Supuestos\n\nNinguno.\n")


def requirements(*paquetes: str) -> list[str]:
    especificacion = especificacion_de_referencia().model_copy(
        update={
            "dependencias_externas": [
                DependenciaExterna(paquete=paquete, proposito="prueba") for paquete in paquetes
            ]
        }
    )
    lineas = requirements_del_modulo(especificacion, versiones_probadas()).splitlines()
    return [linea for linea in lineas if not linea.startswith("#")]


def test_requirements_fija_las_versiones_del_entorno_aislado():
    # Primero las declaradas, luego las de ellas en orden alfabético y al final pytest con las
    # suyas, todas con la versión de la imagen. Una librería desconocida queda sin fijar.
    assert requirements("psycopg[binary]", "openpyxl", "desconocida") == [
        "psycopg[binary]==3.3.6",
        "openpyxl==3.1.5",
        "desconocida",
        "et_xmlfile==2.0.0",
        "psycopg-binary==3.3.6",
        "typing_extensions==4.16.0",
        "pytest==9.1.1",
        "iniconfig==2.3.1",
        "packaging==26.3",
        "pluggy==1.6.0",
        "Pygments==2.21.0",
    ]


def test_requirements_fija_las_transitivas_que_comparte_con_pytest_una_sola_vez():
    lineas = requirements("pandas", "typer")
    assert lineas[:2] == ["pandas==3.0.6", "typer==0.27.2"]
    for transitiva in ("numpy==2.4.6", "python-dateutil==2.9.0.post0", "six==1.17.0"):
        assert transitiva in lineas
    assert lineas.count("Pygments==2.21.0") == 1


def test_solo_se_exporta_un_modulo_validado():
    estado, historial = sesion_validada()
    sesion = estado["sesion"].model_copy(update={"fase": "aprobacion_final"})
    with pytest.raises(ErrorExportacion, match="validado"):
        paquete_del_modulo({**estado, "sesion": sesion}, historial)
