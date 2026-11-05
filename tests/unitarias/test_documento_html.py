"""Conversión a HTML de la trazabilidad y de la traza, para la web."""

from langgraph.checkpoint.memory import InMemorySaver

from multiagente.core.configuracion import ConfiguracionOrquestador
from multiagente.interfaces.operacion import Operador
from multiagente.interfaces.web.documento_html import a_html
from multiagente.orquestador.estado import Decision
from multiagente.orquestador.grafo import construir_grafo
from multiagente.orquestador.simulacion import ServiciosSimulados, guion_completo
from multiagente.orquestador.traza import TrazaEnMemoria
from multiagente.persistencia.puntos_control import serializador


def test_titulos_listas_y_parrafos():
    html = a_html(
        "# Título\n\n- uno\n- **dos:** texto\n  - anidado\n\nUn párrafo\nque sigue.\n\n## Parte\n"
    )

    assert "<h1>Título</h1>" in html
    anidada = "<ul><li>anidado</li></ul>"
    assert f"<ul><li>uno</li><li><strong>dos:</strong> texto{anidada}</li></ul>" in html
    assert "<p>Un párrafo que sigue.</p>" in html
    assert "<h2>Parte</h2>" in html


def test_omite_el_titulo_que_la_pagina_ya_muestra():
    html = a_html("# Trazabilidad de la sesión x\n\n## Conversación\n", omitir_titulo=True)

    assert "Trazabilidad" not in html
    assert "<h2>Conversación</h2>" in html


def test_las_tablas_alinean_las_cifras_y_respetan_las_barras_escapadas():
    html = a_html(
        "| Nodo | Llamadas | Costo (USD) |\n"
        "|---|---|---|\n"
        "| N3 \\| diálogo | 8 | 0.1600 |\n"
        "| N4 | — | 0.0000 |\n"
    )

    assert '<th>Nodo</th><th class="num">Llamadas</th><th class="num">Costo (USD)</th>' in html
    assert '<td>N3 | diálogo</td><td class="num">8</td><td class="num">0.1600</td>' in html
    assert '<td class="num">—</td>' in html
    assert "---" not in html


def test_el_texto_se_escapa_antes_de_darle_formato():
    html = a_html("- **Cliente:** <script>alert('x')</script> & `<b>`\n")

    assert "<script>" not in html
    assert "&lt;script&gt;alert('x')&lt;/script&gt;" in html
    assert "&amp;" in html
    assert "<code>&lt;b&gt;</code>" in html


def test_convierte_la_trazabilidad_y_la_traza_reales_sin_dejar_marcas():
    traza = TrazaEnMemoria()
    app = construir_grafo(
        ServiciosSimulados(fallos_veredicto=0).como_servicios(),
        ConfiguracionOrquestador(_env_file=None),
        traza,
    ).compile(checkpointer=InMemorySaver(serde=serializador()))
    operador = Operador(app, traza=traza)
    guion = guion_completo()
    id_sesion = operador.iniciar("Oficina de catastro", "Gestión catastral", guion.necesidad)
    for respuesta in guion.respuestas_cliente[:7]:
        operador.responder(id_sesion, respuesta)
    for _ in range(3):
        operador.decidir(id_sesion, Decision.APROBADO, "Laura")

    trazabilidad = a_html(operador.trazabilidad(id_sesion), omitir_titulo=True)
    assert "<h2>Decisiones humanas</h2>" in trazabilidad
    assert "<table" in trazabilidad and "<strong>Cliente:</strong>" in trazabilidad
    documento = a_html(operador.traza(id_sesion), omitir_titulo=True)
    assert "<h2>Por nodo</h2>" in documento and '<td class="num">' in documento
    for html in (trazabilidad, documento):
        assert "**" not in html and "|---" not in html and "\n# " not in html
