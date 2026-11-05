"""Pruebas de escenarios y restricciones del simulador."""

import os
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal, localcontext
from pathlib import Path

import pytest

from comandos.simulador import main_cuota, main_resumen, main_tabla
from dominio.credito import DatosInvalidosError, ParametrosCredito, ResumenCredito
from entrada_salida.tabla_csv import EscritorTablaCSV
from servicios.simulacion import calcular_cuota, calcular_resumen, generar_tabla


def _ejecutar_proceso(codigo: str) -> subprocess.CompletedProcess[str]:
    raiz = Path(__file__).resolve().parents[1]
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(raiz / "src")
    # Se ejecuta Python directamente, con código fijo de pruebas y sin intérprete de comandos.
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", codigo],
        cwd=raiz,
        env=entorno,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def parametros():
    return ParametrosCredito(Decimal(100000000), 120, Decimal("0.12"))


def test_rf_01_esc_01_calcula_cuota(parametros):
    assert calcular_cuota(parametros) == 1399472


def test_rf_01_esc_02_redondea_al_peso():
    parametros = ParametrosCredito(Decimal(10000000), 12, Decimal("0.01"))
    cuota = calcular_cuota(parametros)
    assert type(cuota) is int
    assert cuota == 837833


def test_rf_01_esc_03_rechaza_tasa(parametros):
    parametros.tasa_efectiva_anual = Decimal(0)
    with pytest.raises(DatosInvalidosError, match="tasa"):
        calcular_cuota(parametros)
    proceso = _ejecutar_proceso(
        'from decimal import Decimal\n'
        'from dominio.credito import ParametrosCredito\n'
        'from servicios.simulacion import calcular_cuota\n'
        'p = ParametrosCredito(Decimal(100000000), 120, Decimal("0.12"))\n'
        'p.tasa_efectiva_anual = Decimal(0)\n'
        'calcular_cuota(p)\n'
    )
    assert proceso.returncode != 0
    assert "DatosInvalidosError: La tasa debe estar entre 0.01 y 0.30." in proceso.stderr


def test_rf_02_esc_01_guarda_csv(parametros, tmp_path):
    escritor = EscritorTablaCSV(str(tmp_path / "tabla.csv"))
    assert not escritor.existe()
    filas = generar_tabla(parametros, escritor)
    assert escritor.existe()
    lineas = escritor.leer()
    assert lineas[0] == "mes,cuota,interes,abono_capital,saldo"
    assert len(lineas) == 121
    assert len(filas) == 120
    assert filas[-1].saldo == 0
    assert lineas[-1].split(",") == [
        str(filas[-1].mes),
        str(filas[-1].cuota),
        str(filas[-1].interes),
        str(filas[-1].abono_capital),
        str(filas[-1].saldo),
    ]


def test_rf_02_esc_02_no_guarda_csv(parametros, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    filas = generar_tabla(parametros, None)
    assert len(filas) == 120
    assert filas[0].mes == 1
    assert filas[0].cuota == 1399472
    assert filas[-1].saldo == 0
    assert list(tmp_path.iterdir()) == []
    saldo_anterior = 100000000
    for fila in filas:
        assert fila.cuota == fila.interes + fila.abono_capital
        assert fila.saldo == saldo_anterior - fila.abono_capital
        assert all(
            type(valor) is int
            for valor in (fila.cuota, fila.interes, fila.abono_capital, fila.saldo)
        )
        saldo_anterior = fila.saldo


def test_rf_02_esc_03_rechaza_plazo(parametros, tmp_path):
    parametros.plazo_en_meses = 6
    escritor = EscritorTablaCSV(str(tmp_path / "tabla.csv"))
    with pytest.raises(DatosInvalidosError, match="plazo"):
        generar_tabla(parametros, escritor)
    assert not escritor.existe()
    proceso = _ejecutar_proceso(
        'from decimal import Decimal\n'
        'from dominio.credito import ParametrosCredito\n'
        'from servicios.simulacion import generar_tabla\n'
        'p = ParametrosCredito(Decimal(100000000), 120, Decimal("0.12"))\n'
        'p.plazo_en_meses = 6\n'
        'generar_tabla(p, None)\n'
    )
    assert proceso.returncode != 0
    assert (
        "DatosInvalidosError: El plazo en meses debe ser un entero entre 12 y 240."
        in proceso.stderr
    )


def test_rf_03_esc_01_muestra_resumen(parametros):
    # Oráculo numérico independiente para los datos concretos del escenario.
    # Los intereses se redondean mensualmente y el último pago liquida el saldo.
    # No se invocan cuota ni tabla para obtener los totales esperados.
    with localcontext() as contexto:
        contexto.prec = 40
        tasa_esperada = Decimal("1.12") ** (Decimal(1) / Decimal(12)) - Decimal(1)
        saldo_esperado = Decimal(100000000)
        cuota_esperada = Decimal(1399472)
        intereses_esperados = Decimal(0)
        for _ in range(119):
            interes_esperado = (saldo_esperado * tasa_esperada).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
            intereses_esperados += interes_esperado
            saldo_esperado -= cuota_esperada - interes_esperado
        ultimo_interes_esperado = (saldo_esperado * tasa_esperada).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
        intereses_esperados += ultimo_interes_esperado
        pagado_esperado = Decimal(119) * cuota_esperada + saldo_esperado
        pagado_esperado += ultimo_interes_esperado

    resumen = calcular_resumen(parametros)
    assert isinstance(resumen, ResumenCredito)
    assert type(resumen.total_pagado) is int
    assert type(resumen.total_intereses) is int
    assert resumen.total_pagado == int(pagado_esperado)
    assert resumen.total_intereses == int(intereses_esperados)
    assert resumen.total_pagado > 100000000
    assert resumen.total_intereses == resumen.total_pagado - 100000000


def test_rf_03_esc_02_resumen_separado(parametros, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resumen = calcular_resumen(parametros)
    assert isinstance(resumen, ResumenCredito)
    assert resumen.total_intereses > 0
    assert list(tmp_path.iterdir()) == []


def test_rf_03_esc_03_rechaza_monto(parametros):
    parametros.monto = Decimal(9000000)
    with pytest.raises(DatosInvalidosError, match="monto"):
        calcular_resumen(parametros)
    proceso = _ejecutar_proceso(
        'from decimal import Decimal\n'
        'from dominio.credito import ParametrosCredito\n'
        'from servicios.simulacion import calcular_resumen\n'
        'p = ParametrosCredito(Decimal(100000000), 120, Decimal("0.12"))\n'
        'p.monto = Decimal(9000000)\n'
        'calcular_resumen(p)\n'
    )
    assert proceso.returncode != 0
    assert (
        "DatosInvalidosError: El monto debe estar entre 10.000.000 y 500.000.000."
        in proceso.stderr
    )


@pytest.mark.parametrize(
    ("monto", "plazo", "tasa", "mensaje"),
    [
        (None, 120, Decimal("0.12"), "monto"),
        ("", 120, Decimal("0.12"), "monto"),
        (100000000, 120, Decimal("0.12"), "monto"),
        (Decimal("NaN"), 120, Decimal("0.12"), "monto"),
        (Decimal("Infinity"), 120, Decimal("0.12"), "monto"),
        (Decimal(9999999), 120, Decimal("0.12"), "monto"),
        (Decimal(500000001), 120, Decimal("0.12"), "monto"),
        (Decimal("10000000.5"), 120, Decimal("0.12"), "monto"),
        (Decimal(100000000), None, Decimal("0.12"), "plazo"),
        (Decimal(100000000), True, Decimal("0.12"), "plazo"),
        (Decimal(100000000), Decimal(120), Decimal("0.12"), "plazo"),
        (Decimal(100000000), 11, Decimal("0.12"), "plazo"),
        (Decimal(100000000), 241, Decimal("0.12"), "plazo"),
        (Decimal(100000000), 120, None, "tasa"),
        (Decimal(100000000), 120, "", "tasa"),
        (Decimal(100000000), 120, Decimal("NaN"), "tasa"),
        (Decimal(100000000), 120, Decimal("Infinity"), "tasa"),
        (Decimal(100000000), 120, Decimal("0.009"), "tasa"),
        (Decimal(100000000), 120, Decimal("0.31"), "tasa"),
        (Decimal(100000000), 120, Decimal("0.125"), "tasa"),
    ],
)
def test_constructor_rechaza_datos_invalidos(monto, plazo, tasa, mensaje):
    with pytest.raises(DatosInvalidosError, match=mensaje):
        ParametrosCredito(monto, plazo, tasa)


@pytest.mark.parametrize("monto", [Decimal(10000000), Decimal(500000000)])
@pytest.mark.parametrize("plazo", [12, 240])
@pytest.mark.parametrize("tasa", [Decimal("0.01"), Decimal("0.30")])
def test_limites_inclusivos(monto, plazo, tasa):
    parametros = ParametrosCredito(monto, plazo, tasa)
    parametros.validar()
    assert calcular_cuota(parametros) > 0
    assert generar_tabla(parametros, None)[-1].saldo == 0
    resumen = calcular_resumen(parametros)
    assert Decimal(resumen.total_pagado - resumen.total_intereses) == monto


def test_tasa_mensual_y_ceros_finales():
    parametros = ParametrosCredito(Decimal(10000000), 12, Decimal("0.1200"))
    tasa = parametros.tasa_mensual()
    assert isinstance(tasa, Decimal)
    assert abs((Decimal(1) + tasa) ** 12 - Decimal("1.12")) < Decimal("1e-25")


def test_resumen_coincide_con_movimientos(parametros):
    resumen = calcular_resumen(parametros)
    filas = generar_tabla(parametros, None)
    assert resumen.total_pagado == sum(fila.cuota for fila in filas)
    assert resumen.total_intereses == sum(fila.interes for fila in filas)


def test_adaptadores_delegan(parametros):
    assert main_cuota(parametros) == calcular_cuota(parametros)
    assert main_tabla(parametros, None) == generar_tabla(parametros, None)
    assert main_resumen(parametros) == calcular_resumen(parametros)


def test_escritor_devuelve_ruta(parametros, tmp_path):
    ruta = str(tmp_path / "tabla.csv")
    escritor = EscritorTablaCSV(ruta)
    assert escritor.escribir(generar_tabla(parametros, None)) == ruta
    assert escritor.existe()


def test_validar_revisa_modificaciones(parametros):
    parametros.plazo_en_meses = 0
    with pytest.raises(DatosInvalidosError, match="plazo"):
        parametros.validar()


@pytest.mark.parametrize("operacion", [calcular_cuota, calcular_resumen])
def test_servicios_rechazan_parametros_vacios(operacion):
    with pytest.raises(DatosInvalidosError, match="parámetros"):
        operacion(None)


def test_tabla_rechaza_parametros_vacios():
    with pytest.raises(DatosInvalidosError, match="parámetros"):
        generar_tabla(None, None)
