from pathlib import Path

import pytest

from credito_vivienda.cli import main


def _argumentos(operacion="cuota", monto="100000000", plazo="120", tasa="12"):
    return [operacion, "--monto", monto, "--plazo", plazo, "--tasa-anual", tasa]


@pytest.mark.parametrize("operacion", ["cuota", "tabla", "resumen"])
def test_operaciones_independientes_informan_bloqueo(operacion, capsys):
    assert main(_argumentos(operacion)) == 3
    salida = capsys.readouterr()
    assert salida.out == ""
    assert "Reglas de redondeo pendientes de definir" in salida.err
    assert "archivos CSV" in salida.err


@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("monto", "9999999", "Monto: debe estar entre"),
        ("monto", "500000001", "Monto: debe estar entre"),
        ("plazo", "11", "Plazo: debe estar entre"),
        ("plazo", "241", "Plazo: debe estar entre"),
        ("tasa", "0.99", "Tasa efectiva anual: debe estar entre"),
        ("tasa", "30.01", "Tasa efectiva anual: debe estar entre"),
    ],
)
def test_fuera_de_rango_mensaje_claro_y_codigo_no_cero(campo, valor, mensaje, capsys):
    assert main(_argumentos(**{campo: valor})) == 2
    salida = capsys.readouterr()
    assert salida.out == ""
    assert mensaje in salida.err
    assert "inclusive" in salida.err


def test_tasa_con_exceso_de_decimales(capsys):
    assert main(_argumentos(tasa="12.123")) == 2
    assert "hasta dos decimales" in capsys.readouterr().err


@pytest.mark.parametrize("campo", ["monto", "plazo", "tasa"])
def test_no_numerico_se_rechaza_sin_traza(campo, capsys):
    assert main(_argumentos(**{campo: "texto"})) == 2
    salida = capsys.readouterr()
    assert "debe ser un número" in salida.err
    assert "Traceback" not in salida.err


def test_plazo_fraccionario_llega_al_bloqueo_sin_exigir_entero(capsys):
    assert main(_argumentos(plazo="120.5")) == 3
    assert "Reglas de redondeo pendientes" in capsys.readouterr().err


def test_tabla_no_genera_csv_por_defecto(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(_argumentos("tabla")) == 3
    assert list(tmp_path.iterdir()) == []


def test_csv_solicitado_no_se_crea_con_calculo_pendiente(tmp_path):
    destino = tmp_path / "amortizacion.csv"
    assert main([*_argumentos("tabla"), "--csv", str(destino)]) == 3
    assert not destino.exists()


def test_csv_existente_no_se_modifica_con_calculo_pendiente(tmp_path):
    destino = tmp_path / "amortizacion.csv"
    destino.write_text("contenido anterior\n", encoding="utf-8")
    assert main([*_argumentos("tabla"), "--csv", str(destino)]) == 3
    assert destino.read_text(encoding="utf-8") == "contenido anterior\n"


@pytest.mark.parametrize("operacion", ["cuota", "resumen"])
def test_csv_solo_se_solicita_con_tabla(operacion, tmp_path):
    destino: Path = tmp_path / "tabla.csv"
    with pytest.raises(SystemExit) as error:
        main([*_argumentos(operacion), "--csv", str(destino)])
    assert error.value.code == 2
    assert not destino.exists()


@pytest.mark.parametrize(
    "argumentos",
    [[], ["desconocida"], ["cuota"], ["tabla", "--csv"]],
)
def test_sintaxis_incompleta_o_invalida(argumentos):
    with pytest.raises(SystemExit) as error:
        main(argumentos)
    assert error.value.code == 2


def test_ayuda_explica_estado_pendiente(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
    salida = capsys.readouterr()
    assert "cálculo pendiente" in salida.out
    assert "cuota" in salida.out
    assert "tabla" in salida.out
    assert "resumen" in salida.out
