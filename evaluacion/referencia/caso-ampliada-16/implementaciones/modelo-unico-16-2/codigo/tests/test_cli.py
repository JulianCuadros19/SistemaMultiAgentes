"""Pruebas de la atención interactiva y sus códigos de salida."""

import pytest

from vivienda import calcular
from vivienda.cli import main


def _entradas(monkeypatch, respuestas):
    iterador = iter(respuestas)
    monkeypatch.setattr("builtins.input", lambda mensaje: next(iterador))


def test_muestra_tabla_completa_y_resumen(monkeypatch, capsys):
    _entradas(monkeypatch, ["100000000", "120", "12", "n"])
    assert main() == 0
    salida = capsys.readouterr()
    resultado = calcular("100000000", "120", "12")
    assert "Cuota mensual fija (pesos): 1399472" in salida.out
    assert "Mes | Cuota | Interés | Abono a capital | Saldo (pesos)" in salida.out
    for fila in resultado.tabla:
        assert (
            f"{fila.mes} | {fila.cuota} | {fila.interes} | "
            f"{fila.abono_capital} | {fila.saldo}"
        ) in salida.out
    assert f"Total pagado (pesos): {resultado.total_pagado}" in salida.out
    assert f"Total intereses (pesos): {resultado.total_intereses}" in salida.out
    assert salida.err == ""


@pytest.mark.parametrize(
    ("respuestas", "mensaje"),
    [
        (["9999999", "120", "12"], "Monto fuera de rango"),
        (["500000001", "120", "12"], "Monto fuera de rango"),
        (["100000000", "11", "12"], "Plazo fuera de rango"),
        (["100000000", "241", "12"], "Plazo fuera de rango"),
        (["100000000", "120", "0.99"], "Tasa fuera de rango"),
        (["100000000", "120", "30.01"], "Tasa fuera de rango"),
        (["abc", "120", "12"], "Monto inválido"),
        (["100000000", "120", "12.123"], "Tasa inválida"),
    ],
)
def test_dato_invalido_sale_con_error(monkeypatch, capsys, respuestas, mensaje):
    _entradas(monkeypatch, respuestas)
    assert main() != 0
    salida = capsys.readouterr()
    assert mensaje in salida.err
    assert "Total pagado" not in salida.out


@pytest.mark.parametrize("respuesta", ["s", "si", "sí", "S"])
def test_exportacion_solicitada(monkeypatch, capsys, tmp_path, respuesta):
    ruta = tmp_path / "tabla.csv"
    _entradas(monkeypatch, ["100000000", "120", "12", respuesta, str(ruta)])
    assert main() == 0
    assert ruta.exists()
    assert "CSV guardado en:" in capsys.readouterr().out


@pytest.mark.parametrize("respuesta", ["", "n", "no"])
def test_csv_es_opcional(monkeypatch, capsys, respuesta):
    _entradas(monkeypatch, ["10000000", "12", "1", respuesta])
    assert main() == 0
    assert "CSV guardado en:" not in capsys.readouterr().out


@pytest.mark.parametrize("tipo_ruta", ["directorio", "padre_ausente", "vacia"])
def test_fallo_csv_conserva_tabla_y_sale_con_error(
    monkeypatch, capsys, tmp_path, tipo_ruta
):
    rutas = {
        "directorio": str(tmp_path),
        "padre_ausente": str(tmp_path / "ausente" / "tabla.csv"),
        "vacia": "",
    }
    _entradas(monkeypatch, ["100000000", "120", "12", "s", rutas[tipo_ruta]])
    assert main() != 0
    salida = capsys.readouterr()
    assert salida.err == "No se pudo guardar el CSV\n"
    assert "1 | 1399472 | 948879 | 450593 | 99549407" in salida.out
    assert "120 |" in salida.out
    assert "Total pagado" in salida.out


def test_respuesta_csv_invalida(monkeypatch, capsys):
    _entradas(monkeypatch, ["10000000", "12", "1", "quizás"])
    assert main() != 0
    assert "Respuesta inválida" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("excepcion", "mensaje"),
    [(EOFError, "Entrada incompleta"), (KeyboardInterrupt, "Operación cancelada")],
)
def test_interrupcion(monkeypatch, capsys, excepcion, mensaje):
    def interrumpir(mensaje_prompt):
        raise excepcion

    monkeypatch.setattr("builtins.input", interrumpir)
    assert main() != 0
    assert mensaje in capsys.readouterr().err
