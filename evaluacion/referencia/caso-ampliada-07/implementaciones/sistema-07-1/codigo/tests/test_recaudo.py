import csv
from datetime import date
from decimal import Decimal

import pytest

from contratos.esquemas import (
    DatosLeidos,
    DatosNormalizados,
    Factura,
    PagoEntrada,
    PagoNormalizado,
    RegistroResultado,
    Resumen,
)
from entrada_salida.archivos import (
    escribir_texto,
    generar_csv_banco_a,
    generar_csv_banco_b,
    generar_csv_banco_c,
    generar_csv_facturas,
    leer_csv_resultados,
)
from etapas.conciliacion import conciliar_lotes
from etapas.escritura import EscrituraError
from etapas.lectura import ColumnaFaltante, leer_archivos
from etapas.normalizacion import normalizar_datos
from orquestacion.pipeline import Orquestador


@pytest.fixture
def rutas(tmp_path):
    return tuple(str(tmp_path / nombre) for nombre in ("a.csv", "b.csv", "c.csv", "f.csv"))


def _preparar(rutas, pagos_a=None, pagos_b=None, pagos_c=None, facturas=None):
    generar_csv_banco_a(rutas[0], pagos_a or [])
    generar_csv_banco_b(rutas[1], pagos_b or [])
    generar_csv_banco_c(rutas[2], pagos_c or [])
    generar_csv_facturas(rutas[3], facturas or [])


def test_rf_01_esc_01_csv_y_resumen_de_los_cuatro_estados(rutas, tmp_path):
    _preparar(
        rutas,
        [("F1", "100", "2024-02-29")],
        [("F2", "90", "29/02/2024")],
        [("X", "0", "2024/02/29")],
        [
            ("F1", "100", "2024-03-01"),
            ("F2", "100", "2024-03-01"),
            ("F3", "200", "2024-03-01"),
        ],
    )
    destino = str(tmp_path / "resultado.csv")
    resumen = Orquestador().ejecutar(*rutas, destino)
    assert resumen == Resumen(1, 1, 1, 1)
    registros = leer_csv_resultados(destino)
    assert [registro.referencia for registro in registros] == ["F1", "F2", "X", "F3"]
    assert [registro.estado for registro in registros] == [
        "conciliado", "diferencia", "pago sin factura", "pendiente"
    ]
    assert [registro.banco for registro in registros] == ["A", "B", "C", None]
    assert registros[0].valor_facturado == registros[0].valor_pagado == Decimal("100")
    assert registros[1].diferencia == Decimal("-10")
    assert registros[2].valor_facturado is None
    assert registros[2].valor_pagado == Decimal(0)
    assert registros[2].diferencia == Decimal(0)
    assert registros[3].valor_pagado is None
    with open(destino, encoding="utf-8", newline="") as archivo:
        assert next(csv.reader(archivo)) == [
            "referencia", "valor facturado", "valor pagado", "banco", "estado", "diferencia"
        ]


@pytest.mark.parametrize("pagado,diferencia", [("90", "-10"), ("110", "10")])
def test_rf_01_esc_02_diferencia_firmada(rutas, pagado, diferencia):
    _preparar(
        rutas,
        pagos_a=[("F1", pagado, "2024-01-01")],
        facturas=[("F1", "100", "2024-01-31")],
    )
    datos = normalizar_datos(leer_archivos(*rutas))
    resultado = conciliar_lotes(datos)
    assert resultado.registros == [
        RegistroResultado("F1", Decimal("100"), Decimal(pagado), "A", "diferencia",
                          Decimal(diferencia))
    ]
    assert resultado.resumen == Resumen(0, 1, 0, 0)


@pytest.mark.parametrize(
    "indice,cabecera,columna",
    [
        (0, "referencia;fecha\n", "valor"),
        (1, "REF,FECHA_PAGO\n", "MONTO"),
        (2, "referencia_factura,fecha\n", "valor_pagado"),
        (3, "referencia,valor\n", "vencimiento"),
    ],
)
def test_rf_01_esc_03_columna_faltante(rutas, indice, cabecera, columna):
    _preparar(rutas)
    escribir_texto(rutas[indice], cabecera)
    with pytest.raises(ColumnaFaltante) as captura:
        leer_archivos(*rutas)
    assert captura.value.archivo == rutas[indice]
    assert captura.value.columna == columna
    assert rutas[indice] in str(captura.value)
    assert columna in str(captura.value)


@pytest.mark.parametrize("valor", ["abc", "", "1.5", "NaN", "Infinity", "1e3"])
def test_rf_01_esc_04_fila_invalida_no_detiene_lote(rutas, valor):
    escribir_texto(
        rutas[0],
        f"referencia;valor;fecha\nMALA;{valor};2024-01-01\nBUENA;50;2024-01-01\n",
    )
    escribir_texto(rutas[1], "REF,MONTO,FECHA_PAGO\n")
    escribir_texto(rutas[2], "referencia_factura,valor_pagado,fecha\n")
    generar_csv_facturas(
        rutas[3], [("MALA", "20", "2024-01-31"), ("BUENA", "50", "2024-01-31")]
    )
    resultado = conciliar_lotes(normalizar_datos(leer_archivos(*rutas)))
    assert resultado.resumen == Resumen(1, 0, 0, 1)
    assert [(fila.referencia, fila.estado) for fila in resultado.registros] == [
        ("BUENA", "conciliado"), ("MALA", "pendiente")
    ]
    assert resultado.registros[1].valor_pagado is None


def test_rf_01_esc_05_reanudar_conciliacion_sin_repetir_etapas(rutas, tmp_path):
    _preparar(
        rutas,
        pagos_a=[("F1", "10", "2024-01-01")],
        facturas=[("F1", "10", "2024-01-31")],
    )
    orquestador = Orquestador()
    orquestador.ejecutar_hasta("normalizacion", *rutas)
    assert orquestador.obtener_contadores() == {
        "lectura": 1, "normalizacion": 1, "conciliacion": 0, "escritura": 0
    }
    resumen = orquestador.reintentar_desde("conciliacion", str(tmp_path / "resultado.csv"))
    assert resumen == Resumen(1, 0, 0, 0)
    assert orquestador.obtener_contadores() == {
        "lectura": 1, "normalizacion": 1, "conciliacion": 1, "escritura": 1
    }


def test_rf_01_esc_05_reintentar_escritura_realmente_fallida(rutas, tmp_path):
    _preparar(rutas)
    orquestador = Orquestador()
    orquestador.ejecutar_hasta("conciliacion", *rutas)
    with pytest.raises(EscrituraError):
        orquestador.reintentar_desde("escritura", str(tmp_path))
    resumen = orquestador.reintentar_desde("escritura", str(tmp_path / "resultado.csv"))
    assert resumen == Resumen(0, 0, 0, 0)
    assert orquestador.obtener_contadores() == {
        "lectura": 1, "normalizacion": 1, "conciliacion": 1, "escritura": 2
    }


def test_lote_vacio_y_contadores_independientes(rutas, tmp_path):
    _preparar(rutas)
    primero = Orquestador()
    segundo = Orquestador()
    destino = str(tmp_path / "vacio.csv")
    assert primero.ejecutar(*rutas, destino) == Resumen(0, 0, 0, 0)
    assert leer_csv_resultados(destino) == []
    assert segundo.obtener_contadores() == {
        "lectura": 0, "normalizacion": 0, "conciliacion": 0, "escritura": 0
    }
    copia = primero.obtener_contadores()
    copia["lectura"] = 99
    assert primero.obtener_contadores()["lectura"] == 1


@pytest.mark.parametrize("etapa", ["normalizacion", "conciliacion", "escritura", "otra"])
def test_reintento_sin_estado_o_etapa_invalida(etapa, tmp_path):
    orquestador = Orquestador()
    with pytest.raises(ValueError):
        orquestador.reintentar_desde(etapa, str(tmp_path / "salida.csv"))
    assert all(contador == 0 for contador in orquestador.obtener_contadores().values())


def test_etapa_final_invalida_no_lee(rutas):
    orquestador = Orquestador()
    with pytest.raises(ValueError):
        orquestador.ejecutar_hasta("escritura", *rutas)
    assert orquestador.obtener_contadores()["lectura"] == 0


@pytest.mark.parametrize(
    "banco,fecha",
    [("A", "2023-02-29"), ("B", "2024-01-01"), ("C", "2024/1/01")],
)
def test_fecha_invalida(banco, fecha):
    datos = DatosLeidos([PagoEntrada("F", "0", fecha, banco)], [])
    with pytest.raises(ValueError):
        normalizar_datos(datos)


@pytest.mark.parametrize(
    "banco,fecha",
    [("A", "2024-02-29"), ("B", "29/02/2024"), ("C", "2024/02/29")],
)
def test_fecha_bisiesta_valida(banco, fecha):
    normalizados = normalizar_datos(DatosLeidos([PagoEntrada("F", "0", fecha, banco)], []))
    assert normalizados.pagos[0].fecha == date(2024, 2, 29)
    assert normalizados.pagos[0].valor_str == "0"
    assert normalizados.pagos[0].banco == banco


@pytest.mark.parametrize("referencia", ["", "   "])
def test_referencia_vacia_rechazada(referencia):
    with pytest.raises(ValueError):
        PagoEntrada(referencia, "0", "2024-01-01", "A")


@pytest.mark.parametrize("valor", [Decimal("0.1"), Decimal("NaN"), Decimal("Infinity")])
def test_factura_no_entera_rechazada(valor):
    with pytest.raises(ValueError):
        Factura("F", valor, date(2024, 1, 1))


@pytest.mark.parametrize("valor", ["0", "-1", "+1"])
def test_importes_enteros_limite(valor):
    pago = PagoNormalizado("F", valor, date(2024, 1, 1), "A")
    factura = Factura("F", Decimal(valor), date(2024, 1, 1))
    resultado = conciliar_lotes(DatosNormalizados([pago], [factura]))
    assert resultado.resumen == Resumen(1, 0, 0, 0)
    assert resultado.registros[0].valor_pagado == Decimal(valor)


def test_resumen_negativo_rechazado():
    with pytest.raises(ValueError):
        Resumen(-1, 0, 0, 0)


def test_banco_invalido_rechazado():
    with pytest.raises(ValueError):
        PagoEntrada("F", "1", "2024-01-01", "D")


def test_estado_invalido_rechazado():
    with pytest.raises(ValueError):
        RegistroResultado("F", None, Decimal(1), "A", "otro", Decimal(0))
