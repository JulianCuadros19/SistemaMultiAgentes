import csv
from datetime import date
from pathlib import Path

import pytest

import conciliacion as modulo
from conciliacion import (
    Archivos,
    ColumnaFaltanteError,
    Factura,
    Lote,
    Normalizados,
    Pago,
    conciliar,
    leer_archivos,
    normalizar,
)


@pytest.fixture
def entradas(tmp_path):
    contenidos = {
        "a.csv": "referencia;valor;fecha\nF-001;85.000;2026-11-01\n",
        "b.csv": "REF,MONTO,FECHA_PAGO\nF-002,100000,01/11/2026\n",
        "c.csv": "referencia_factura,valor_pagado,fecha\nF-999,30000,2026/11/01\n",
        "facturas.csv": (
            "referencia,valor,vencimiento\n"
            "F-001,85000,2026-10-31\n"
            "F-002,120.000,2026-10-31\n"
            "F-003,40000,2026-10-31\n"
        ),
    }
    for nombre, contenido in contenidos.items():
        (tmp_path / nombre).write_text(contenido, encoding="utf-8")
    return Archivos(
        tmp_path / "a.csv",
        tmp_path / "b.csv",
        tmp_path / "c.csv",
        tmp_path / "facturas.csv",
    )


@pytest.fixture
def informe(entradas):
    return conciliar(normalizar(leer_archivos(entradas)))


@pytest.mark.parametrize(
    ("indice", "banco", "referencia", "valor"),
    [(0, "A", "F-001", 85000), (1, "B", "F-002", 100000), (2, "C", "F-999", 30000)],
)
def test_formatos_bancarios(entradas, indice, banco, referencia, valor):
    pago = normalizar(leer_archivos(entradas)).pagos[indice]
    assert pago.banco == banco
    assert pago.referencia == referencia
    assert pago.valor == valor
    assert pago.fecha == date(2026, 11, 1)


def test_ejemplo_conciliado(informe):
    fila = informe.resultados[0]
    assert fila.referencia == "F-001"
    assert fila.valor_facturado == fila.valor_pagado == 85000
    assert fila.banco == "A"
    assert fila.estado == "conciliado"
    assert fila.diferencia == 0


def test_ejemplo_diferencia(informe):
    fila = informe.resultados[1]
    assert fila.referencia == "F-002"
    assert fila.valor_facturado == 120000
    assert fila.valor_pagado == 100000
    assert fila.banco == "B"
    assert fila.estado == "diferencia"
    assert fila.diferencia == 20000


def test_ejemplo_pago_sin_factura(informe):
    fila = informe.resultados[2]
    assert fila.referencia == "F-999"
    assert fila.valor_facturado is None
    assert fila.valor_pagado == 30000
    assert fila.banco == "C"
    assert fila.estado == "pago sin factura"
    assert fila.diferencia is None


def test_ejemplo_pendiente(informe):
    fila = informe.resultados[3]
    assert fila.referencia == "F-003"
    assert fila.valor_facturado == 40000
    assert fila.valor_pagado == 0
    assert fila.banco == ""
    assert fila.estado == "pendiente"
    assert fila.diferencia is None


def test_resumen_de_estados(informe):
    assert informe.resumen == {
        "conciliado": 1,
        "diferencia": 1,
        "pago sin factura": 1,
        "pendiente": 1,
    }


def test_csv_de_resultados(entradas, tmp_path):
    salida = tmp_path / "resultado.csv"
    informe = Lote(entradas, salida).ejecutar()
    with salida.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        filas = list(lector)
        assert lector.fieldnames == [
            "referencia", "valor_facturado", "valor_pagado", "banco", "estado", "diferencia"
        ]
    assert len(filas) == len(informe.resultados) == 4
    assert filas[0] == {
        "referencia": "F-001",
        "valor_facturado": "85000",
        "valor_pagado": "85000",
        "banco": "A",
        "estado": "conciliado",
        "diferencia": "0",
    }
    assert filas[1]["diferencia"] == "20000"
    assert filas[2]["valor_facturado"] == ""
    assert filas[2]["diferencia"] == ""
    assert filas[3]["banco"] == ""
    assert filas[3]["valor_pagado"] == "0"


@pytest.mark.parametrize(
    ("atributo", "separador", "columnas"),
    [
        ("banco_a", ";", ("referencia", "valor", "fecha")),
        ("banco_b", ",", ("REF", "MONTO", "FECHA_PAGO")),
        ("banco_c", ",", ("referencia_factura", "valor_pagado", "fecha")),
        ("facturas", ",", ("referencia", "valor", "vencimiento")),
    ],
)
@pytest.mark.parametrize("indice", [0, 1, 2])
def test_columna_faltante_rechaza_archivo(entradas, atributo, separador, columnas, indice):
    ruta = getattr(entradas, atributo)
    cabecera = separador.join(c for i, c in enumerate(columnas) if i != indice)
    ruta.write_text(cabecera + "\n", encoding="utf-8")
    with pytest.raises(ColumnaFaltanteError) as capturado:
        leer_archivos(entradas)
    assert capturado.value.archivo == str(ruta)
    assert capturado.value.columna == columnas[indice]
    assert str(ruta) in str(capturado.value)
    assert columnas[indice] in str(capturado.value)


@pytest.mark.parametrize("atributo", ["banco_a", "banco_b", "banco_c", "facturas"])
def test_valor_no_numerico_se_reporta_sin_detener_lote(entradas, tmp_path, atributo):
    ruta = getattr(entradas, atributo)
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    separador = ";" if atributo == "banco_a" else ","
    campos = lineas[1].split(separador)
    campos[1] = "no es un número"
    lineas[1] = separador.join(campos)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    salida = tmp_path / "resultado.csv"
    informe = Lote(entradas, salida).ejecutar()
    assert salida.exists()
    assert len(informe.rechazadas) == 1
    rechazo = informe.rechazadas[0]
    assert rechazo.archivo == str(ruta)
    assert rechazo.fila == 2
    assert "no es un número" in rechazo.motivo
    assert informe.resultados
    if atributo == "banco_a":
        assert any(
            fila.referencia == "F-001" and fila.estado == "pendiente"
            for fila in informe.resultados
        )
    if atributo == "facturas":
        assert informe.resultados[0].estado == "pago sin factura"


@pytest.mark.parametrize("texto", ["85.50", "85000,00", "12.34.567", "", "1e3"])
def test_importes_no_enteros_rechazados(entradas, texto):
    entradas.banco_a.write_text(
        f"referencia;valor;fecha\nF-001;{texto};2026-11-01\n", encoding="utf-8"
    )
    datos = normalizar(leer_archivos(entradas))
    assert len(datos.rechazadas) == 1
    assert len(datos.pagos) == 2


@pytest.mark.parametrize("texto", ["85000", "85.000", " +85.000 "])
def test_pesos_enteros_y_separador_de_miles(entradas, texto):
    entradas.banco_a.write_text(
        f"referencia;valor;fecha\nF-001;{texto};2026-11-01\n", encoding="utf-8"
    )
    datos = normalizar(leer_archivos(entradas))
    assert datos.pagos[0].valor == 85000
    assert not datos.rechazadas


def test_fecha_invalida_rechaza_solo_la_fila(entradas):
    entradas.banco_a.write_text(
        "referencia;valor;fecha\nF-001;85000;2026-02-30\n", encoding="utf-8"
    )
    datos = normalizar(leer_archivos(entradas))
    assert len(datos.pagos) == 2
    assert len(datos.rechazadas) == 1
    assert datos.rechazadas[0].archivo == str(entradas.banco_a)


def test_sobrepago_diferencia_negativa():
    datos = Normalizados(
        (Pago("F", 110, date(2026, 1, 1), "A"),),
        (Factura("F", 100, "sin formato definido"),),
        (),
    )
    fila = conciliar(datos).resultados[0]
    assert fila.estado == "diferencia"
    assert fila.diferencia == -10


def test_duplicados_primera_factura_y_un_resultado_por_pago():
    datos = Normalizados(
        (
            Pago("F", 100, date(2026, 1, 1), "A"),
            Pago("F", 80, date(2026, 1, 2), "B"),
        ),
        (Factura("F", 100, ""), Factura("F", 200, "")),
        (),
    )
    informe = conciliar(datos)
    assert len(informe.resultados) == 2
    assert [fila.valor_facturado for fila in informe.resultados] == [100, 100]
    assert [fila.estado for fila in informe.resultados] == ["conciliado", "diferencia"]
    assert informe.resumen["pendiente"] == 0


def test_lote_vacio_conserva_cabecera_y_resumen(entradas, tmp_path):
    for ruta in (
        entradas.banco_a, entradas.banco_b, entradas.banco_c, entradas.facturas
    ):
        cabecera = ruta.read_text(encoding="utf-8").splitlines()[0]
        ruta.write_text(cabecera + "\n", encoding="utf-8")
    salida = tmp_path / "resultado.csv"
    informe = Lote(entradas, salida).ejecutar()
    assert informe.resultados == ()
    assert set(informe.resumen.values()) == {0}
    assert len(salida.read_text(encoding="utf-8").splitlines()) == 1


@pytest.mark.parametrize(
    ("funcion_fallida", "etapa"),
    [
        ("leer_archivos", "lectura"),
        ("normalizar", "normalización"),
        ("conciliar", "conciliación"),
        ("escribir_csv", "escritura"),
    ],
)
def test_reintento_solo_repite_etapa_fallida(
    entradas, tmp_path, monkeypatch, funcion_fallida, etapa
):
    funciones = ("leer_archivos", "normalizar", "conciliar", "escribir_csv")
    llamadas = dict.fromkeys(funciones, 0)

    def envolver(nombre, original):
        def instrumentada(*args, **kwargs):
            llamadas[nombre] += 1
            if nombre == funcion_fallida and llamadas[nombre] == 1:
                raise OSError("fallo temporal")
            return original(*args, **kwargs)

        return instrumentada

    for nombre in funciones:
        monkeypatch.setattr(modulo, nombre, envolver(nombre, getattr(modulo, nombre)))
    lote = Lote(entradas, tmp_path / "resultado.csv")
    with pytest.raises(OSError, match="fallo temporal"):
        lote.ejecutar()
    assert lote.etapa_pendiente == etapa
    posicion = funciones.index(funcion_fallida)
    assert all(llamadas[nombre] == 1 for nombre in funciones[:posicion])
    assert all(llamadas[nombre] == 0 for nombre in funciones[posicion + 1:])
    informe = lote.ejecutar()
    assert lote.etapa_pendiente is None
    assert informe.resumen["conciliado"] == 1
    assert llamadas == {
        nombre: 2 if nombre == funcion_fallida else 1 for nombre in funciones
    }
    assert lote.ejecutar() is informe
    assert llamadas == {
        nombre: 2 if nombre == funcion_fallida else 1 for nombre in funciones
    }


def test_reintentar_lectura_despues_de_corregir_columna(entradas, tmp_path):
    original = entradas.banco_b.read_text(encoding="utf-8")
    entradas.banco_b.write_text("REF,MONTO\nF-002,100000\n", encoding="utf-8")
    lote = Lote(entradas, tmp_path / "resultado.csv")
    with pytest.raises(ColumnaFaltanteError):
        lote.ejecutar()
    assert lote.etapa_pendiente == "lectura"
    entradas.banco_b.write_text(original, encoding="utf-8")
    assert lote.ejecutar().resumen["diferencia"] == 1


def test_reintento_de_escritura_con_error_real(entradas, tmp_path):
    salida = tmp_path / "no_existe" / "resultado.csv"
    lote = Lote(entradas, salida)
    with pytest.raises(FileNotFoundError):
        lote.ejecutar()
    assert lote.etapa_pendiente == "escritura"
    for ruta in (
        entradas.banco_a, entradas.banco_b, entradas.banco_c, entradas.facturas
    ):
        ruta.unlink()
    salida.parent.mkdir()
    informe = lote.escribir()
    assert salida.exists()
    assert informe.resumen["pendiente"] == 1
    assert lote.etapa_pendiente is None


def test_escritura_fallida_no_destruye_destino(informe, tmp_path, monkeypatch):
    salida = tmp_path / "resultado.csv"
    salida.write_text("resultado anterior\n", encoding="utf-8")

    def fallar_reemplazo(origen: Path, destino: Path) -> None:
        raise PermissionError("destino bloqueado")

    monkeypatch.setattr(modulo.os, "replace", fallar_reemplazo)
    with pytest.raises(PermissionError, match="destino bloqueado"):
        modulo.escribir_csv(informe, salida)
    assert salida.read_text(encoding="utf-8") == "resultado anterior\n"
    assert list(tmp_path.iterdir()) == [salida]


@pytest.mark.parametrize("metodo", ["normalizar", "conciliar", "escribir"])
def test_etapa_individual_exige_predecesora(entradas, tmp_path, metodo):
    lote = Lote(entradas, tmp_path / "resultado.csv")
    with pytest.raises(RuntimeError, match="Debe completar"):
        getattr(lote, metodo)()
    assert lote.etapa_pendiente == "lectura"


def test_etapas_individuales_y_cache_de_lectura(entradas, tmp_path):
    lote = Lote(entradas, tmp_path / "resultado.csv")
    lectura = lote.leer()
    assert lote.etapa_pendiente == "normalización"
    entradas.banco_a.unlink()
    assert lote.leer() is lectura
    datos = lote.normalizar()
    assert lote.normalizar() is datos
    assert lote.etapa_pendiente == "conciliación"
    informe = lote.conciliar()
    assert lote.conciliar() is informe
    assert lote.etapa_pendiente == "escritura"
    assert lote.escribir() is informe
    assert lote.etapa_pendiente is None


def test_archivo_inexistente_se_propaga(entradas):
    entradas.banco_c.unlink()
    with pytest.raises(FileNotFoundError):
        leer_archivos(entradas)


def test_bom_columnas_extra_y_vencimiento_sin_interpretar(entradas):
    entradas.facturas.write_text(
        "\ufeffreferencia,valor,vencimiento,extra\n F-001 ,85000,cualquier texto,ignorado\n",
        encoding="utf-8",
    )
    datos = normalizar(leer_archivos(entradas))
    assert datos.facturas == (Factura("F-001", 85000, "cualquier texto"),)
    assert not datos.rechazadas
