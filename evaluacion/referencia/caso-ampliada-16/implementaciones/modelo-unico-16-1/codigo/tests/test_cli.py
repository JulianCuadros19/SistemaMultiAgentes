"""Pruebas de las opciones de terminal, exportación y códigos de error."""

import csv
from pathlib import Path

import pytest

from vivienda import amortizacion, crear_credito, resumen
from vivienda.cli import main

_DATOS = ["--monto", "100000000", "--plazo", "120", "--tasa", "12"]


def test_consulta_solo_cuota(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["cuota", *_DATOS]) == 0
    captura = capsys.readouterr()
    assert captura.out == "Cuota mensual: 1399472 pesos\n"
    assert captura.err == ""


def test_consulta_solo_tabla(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["tabla", *_DATOS]) == 0
    captura = capsys.readouterr()
    lineas = captura.out.splitlines()
    assert lineas[0] == "mes\tcuota\tinteres\tcapital\tsaldo"
    assert len(lineas) == 121
    assert lineas[1] == "1\t1399472\t948879\t450593\t99549407"
    assert lineas[-1].split("\t")[0] == "120"
    assert lineas[-1].split("\t")[-1] == "0"
    assert captura.err == ""


def test_resumen_terminal(capsys: pytest.CaptureFixture[str]) -> None:
    totales = resumen(crear_credito(100_000_000, 120, "12"))
    assert main(["resumen", *_DATOS]) == 0
    assert capsys.readouterr().out == (
        f"Total pagado: {totales.total_pagado} pesos\n"
        f"Total de intereses: {totales.total_intereses} pesos\n"
    )


def test_csv_completo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ruta = tmp_path / "amortización.csv"
    assert main(["tabla", *_DATOS, "--csv", str(ruta)]) == 0
    with ruta.open(encoding="utf-8", newline="") as archivo:
        filas_csv = list(csv.reader(archivo))
    assert filas_csv[0] == ["mes", "cuota", "interes", "capital", "saldo"]
    filas = amortizacion(crear_credito(100_000_000, 120, "12"))
    assert filas_csv[1:] == [
        [str(valor) for valor in (fila.mes, fila.cuota, fila.interes, fila.capital, fila.saldo)]
        for fila in filas
    ]
    assert len(capsys.readouterr().out.splitlines()) == 121


@pytest.mark.parametrize(
    ("opcion", "valor", "mensaje"),
    [
        ("--monto", "0", "Monto:"),
        ("--monto", "-1", "Monto:"),
        ("--monto", "500000001", "Monto:"),
        ("--monto", "100000000.50", "Monto:"),
        ("--plazo", "120.5", "Plazo:"),
        ("--plazo", "11", "Plazo:"),
        ("--plazo", "241", "Plazo:"),
        ("--tasa", "0", "Tasa efectiva anual:"),
        ("--tasa", "-1", "Tasa efectiva anual:"),
        ("--tasa", "30.01", "Tasa efectiva anual:"),
        ("--tasa", "12.001", "Tasa efectiva anual:"),
        ("--tasa", "abc", "Tasa efectiva anual:"),
    ],
)
@pytest.mark.parametrize("comando", ["cuota", "tabla", "resumen"])
def test_dato_invalido_sale_con_error(
    opcion: str,
    valor: str,
    mensaje: str,
    comando: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    datos = _DATOS.copy()
    datos[datos.index(opcion) + 1] = valor
    assert main([comando, *datos]) == 1
    captura = capsys.readouterr()
    assert captura.out == ""
    assert "Error:" in captura.err
    assert mensaje in captura.err


def test_error_guardando_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ruta = tmp_path / "carpeta_inexistente" / "tabla.csv"
    assert main(["tabla", *_DATOS, "--csv", str(ruta)]) == 1
    captura = capsys.readouterr()
    assert captura.out == ""
    assert "Error al mostrar o guardar el resultado:" in captura.err
    assert not ruta.exists()


def test_csv_sobrescribe_archivo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ruta = tmp_path / "tabla.csv"
    ruta.write_text("contenido anterior", encoding="utf-8")
    assert main(["tabla", *_DATOS, "--csv", str(ruta)]) == 0
    assert "contenido anterior" not in ruta.read_text(encoding="utf-8")
    capsys.readouterr()


@pytest.mark.parametrize(
    "argumentos",
    [[], ["otro"], ["cuota"], ["cuota", *_DATOS, "--csv", "tabla.csv"]],
)
def test_sintaxis_invalida(
    argumentos: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as error:
        main(argumentos)
    assert error.value.code == 2
    assert capsys.readouterr().err


def test_ayuda(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
    salida = capsys.readouterr().out
    assert all(comando in salida for comando in ("cuota", "tabla", "resumen"))
