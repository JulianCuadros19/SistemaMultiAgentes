"""Pruebas de las operaciones de terminal y sus errores."""

import pytest

from credito_vivienda import calcular_resumen, crear_credito
from credito_vivienda.cli import main

_DATOS = ["--monto", "100000000", "--plazo", "120", "--tasa", "12"]


def test_operacion_cuota(capsys):
    assert main(["cuota", *_DATOS]) == 0
    salida = capsys.readouterr()
    assert salida.out == "Cuota mensual: 1399472 pesos\n"
    assert salida.err == ""


def test_operacion_tabla_completa_sin_archivo(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["tabla", *_DATOS]) == 0
    salida = capsys.readouterr()
    lineas = salida.out.splitlines()
    assert lineas[0] == "mes\tcuota\tinteres\tabono_capital\tsaldo"
    assert lineas[1] == "1\t1399472\t948879\t450593\t99549407"
    assert len(lineas) == 121
    assert lineas[-1].split("\t")[0] == "120"
    assert lineas[-1].split("\t")[-1] == "0"
    assert list(tmp_path.iterdir()) == []
    assert salida.err == ""


def test_operacion_tabla_muestra_y_exporta(capsys, tmp_path):
    ruta = tmp_path / "tabla.csv"
    assert main(["tabla", *_DATOS, "--csv", str(ruta)]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 121
    assert len(ruta.read_text(encoding="utf-8").splitlines()) == 121


def test_operacion_resumen(capsys):
    resumen = calcular_resumen(crear_credito(100_000_000, 120, "12"))
    assert main(["resumen", *_DATOS]) == 0
    salida = capsys.readouterr()
    assert salida.out == (
        f"Total pagado: {resumen.total_pagado} pesos\n"
        f"Total de intereses: {resumen.total_intereses} pesos\n"
    )
    assert salida.err == ""


@pytest.mark.parametrize("operacion", ["cuota", "tabla", "resumen"])
@pytest.mark.parametrize(
    ("opcion", "valor", "mensaje"),
    [
        ("--monto", "9999999", "Monto"),
        ("--monto", "500000001", "Monto"),
        ("--plazo", "11", "Plazo"),
        ("--plazo", "241", "Plazo"),
        ("--tasa", "0.99", "Tasa efectiva anual"),
        ("--tasa", "30.01", "Tasa efectiva anual"),
        ("--tasa", "12.345", "dos decimales"),
        ("--monto", "abc", "Monto"),
        ("--tasa", "NaN", "finito"),
    ],
)
def test_error_datos_devuelve_codigo_no_cero(operacion, opcion, valor, mensaje, capsys):
    argumentos = _DATOS.copy()
    argumentos[argumentos.index(opcion) + 1] = valor
    assert main([operacion, *argumentos]) == 2
    salida = capsys.readouterr()
    assert salida.out == ""
    assert "Error:" in salida.err
    assert mensaje in salida.err
    assert "Traceback" not in salida.err


@pytest.mark.parametrize("operacion", ["cuota", "tabla", "resumen"])
@pytest.mark.parametrize("opcion", ["--monto", "--plazo", "--tasa"])
def test_cada_dato_es_obligatorio(operacion, opcion, capsys):
    argumentos = _DATOS.copy()
    indice = argumentos.index(opcion)
    del argumentos[indice:indice + 2]
    with pytest.raises(SystemExit) as error:
        main([operacion, *argumentos])
    assert error.value.code == 2
    assert opcion in capsys.readouterr().err


def test_plazo_no_entero_rechazado(capsys):
    with pytest.raises(SystemExit) as error:
        main(["cuota", "--monto", "100000000", "--plazo", "12.5", "--tasa", "12"])
    assert error.value.code == 2
    assert "--plazo" in capsys.readouterr().err


def test_operacion_obligatoria(capsys):
    with pytest.raises(SystemExit) as error:
        main([])
    assert error.value.code == 2
    assert capsys.readouterr().err


@pytest.mark.parametrize("operacion", ["cuota", "resumen"])
def test_csv_solo_disponible_para_tabla(operacion, capsys):
    with pytest.raises(SystemExit) as error:
        main([operacion, *_DATOS, "--csv", "tabla.csv"])
    assert error.value.code == 2
    assert "--csv" in capsys.readouterr().err


def test_error_csv_mensaje_claro_sin_traza(capsys, tmp_path):
    ruta = tmp_path / "inexistente" / "tabla.csv"
    assert main(["tabla", *_DATOS, "--csv", str(ruta)]) == 2
    salida = capsys.readouterr()
    assert salida.out == ""
    assert "Error:" in salida.err
    assert "tabla.csv" in salida.err
    assert "Traceback" not in salida.err


def test_ayuda(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
    assert "cuota" in capsys.readouterr().out
