import csv
from decimal import Decimal

import pytest

from comandos.cli import ErrorCLI, ejecutar_cuota, ejecutar_resumen, ejecutar_tabla
from dominio.credito import AmortizacionFila, Resumen, cuota_fija, redondear_peso, tasa_mensual
from entrada_salida.csv_salida import TablaCSV
from servicios.simulador import (
    ValidacionError,
    calcular_cuota,
    calcular_resumen,
    generar_tabla,
)


def test_rf_01_esc_01_cuota_valida():
    cuota = ejecutar_cuota(Decimal('12'), Decimal('100000000'), 120)
    assert cuota == Decimal('1399472')
    assert isinstance(cuota, Decimal)


def test_rf_01_esc_02_limites_inferiores():
    cuota = ejecutar_cuota(Decimal('1'), Decimal('10000000'), 12)
    assert cuota == Decimal('837833')
    assert cuota.as_tuple().exponent == 0


def test_rf_01_esc_03_falta_tasa():
    with pytest.raises(ErrorCLI, match="tasa efectiva anual") as captura:
        ejecutar_cuota(None, Decimal('100000000'), 120)
    assert captura.value.codigo_salida != 0
    assert captura.value.mensaje


def test_rf_02_esc_01_detalle_mensual():
    tabla = ejecutar_tabla(Decimal('12'), Decimal('100000000'), 120, None)
    assert len(tabla) == 120
    assert tabla[0].saldo_inicial == Decimal('100000000')
    for mes, fila in enumerate(tabla, start=1):
        assert isinstance(fila, AmortizacionFila)
        assert fila.mes == mes
        assert fila.interes >= 0
        assert fila.abono_capital >= 0
        assert fila.saldo_final >= 0
        assert fila.cuota == fila.interes + fila.abono_capital
        assert fila.saldo_final == fila.saldo_inicial - fila.abono_capital
        for valor in (
            fila.saldo_inicial, fila.interes, fila.abono_capital, fila.cuota, fila.saldo_final
        ):
            assert valor.as_tuple().exponent == 0
    assert all(
        anterior.saldo_final == siguiente.saldo_inicial
        for anterior, siguiente in zip(tabla, tabla[1:], strict=False)
    )


def test_rf_02_esc_02_exportar_csv(tmp_path):
    escritor = TablaCSV()
    ruta = str(tmp_path / 'tabla.csv')
    assert not escritor.existe(ruta)
    tabla = ejecutar_tabla(Decimal('12'), Decimal('100000000'), 120, ruta, escritor)
    assert escritor.existe(ruta)
    with open(ruta, encoding='utf-8', newline='') as archivo:
        filas = list(csv.DictReader(archivo))
    assert len(filas) == len(tabla)
    assert list(filas[0]) == [
        'mes', 'saldo_inicial', 'interes', 'abono_capital', 'cuota', 'saldo_final'
    ]
    for registro, fila in zip(filas, tabla, strict=True):
        assert int(registro['mes']) == fila.mes
        assert Decimal(registro['saldo_inicial']) == fila.saldo_inicial
        assert Decimal(registro['interes']) == fila.interes
        assert Decimal(registro['abono_capital']) == fila.abono_capital
        assert Decimal(registro['cuota']) == fila.cuota
        assert Decimal(registro['saldo_final']) == fila.saldo_final


def test_rf_02_esc_03_ajuste_final():
    tabla = ejecutar_tabla(Decimal('12'), Decimal('100000000'), 120, None)
    assert tabla[-1].saldo_final == Decimal(0)
    assert tabla[-1].abono_capital == tabla[-1].saldo_inicial
    assert tabla[-1].cuota == tabla[-1].saldo_inicial + tabla[-1].interes
    assert tabla[-1].cuota != tabla[0].cuota
    assert all(fila.cuota == tabla[0].cuota for fila in tabla[:-1])
    assert sum((fila.abono_capital for fila in tabla), Decimal(0)) == Decimal('100000000')


def test_rf_02_esc_04_falta_monto(tmp_path):
    escritor = TablaCSV()
    ruta = str(tmp_path / 'rechazado.csv')
    with pytest.raises(ErrorCLI, match='monto') as captura:
        ejecutar_tabla(Decimal('12'), None, 120, ruta, escritor)
    assert captura.value.codigo_salida != 0
    assert not escritor.existe(ruta)


def test_rf_03_esc_01_resumen_coherente():
    resumen = ejecutar_resumen(Decimal('12'), Decimal('100000000'), 120)
    tabla = ejecutar_tabla(Decimal('12'), Decimal('100000000'), 120, None)
    assert isinstance(resumen, Resumen)
    assert resumen.total_pagado == sum((fila.cuota for fila in tabla), Decimal(0))
    assert resumen.total_intereses == sum((fila.interes for fila in tabla), Decimal(0))
    assert resumen.total_pagado - resumen.total_intereses == Decimal('100000000')


def test_rf_03_esc_02_limites_superiores():
    resumen = ejecutar_resumen(Decimal('30'), Decimal('500000000'), 240)
    assert resumen.total_pagado > Decimal('500000000')
    assert resumen.total_intereses > 0
    assert resumen.total_pagado.as_tuple().exponent == 0
    assert resumen.total_intereses.as_tuple().exponent == 0
    assert resumen.total_pagado - resumen.total_intereses == Decimal('500000000')


def test_rf_03_esc_03_plazo_invalido():
    with pytest.raises(ErrorCLI, match='plazo') as captura:
        ejecutar_resumen(Decimal('12'), Decimal('100000000'), 10)
    assert captura.value.codigo_salida != 0
    assert captura.value.mensaje


@pytest.mark.parametrize(
    ('tea', 'monto', 'plazo'),
    [
        (Decimal('0.99'), Decimal('100000000'), 120),
        (Decimal('30.01'), Decimal('100000000'), 120),
        (Decimal('12.001'), Decimal('100000000'), 120),
        (Decimal('NaN'), Decimal('100000000'), 120),
        (Decimal('Infinity'), Decimal('100000000'), 120),
        (Decimal('12'), Decimal('9999999.99'), 120),
        (Decimal('12'), Decimal('500000000.01'), 120),
        (Decimal('12'), Decimal('NaN'), 120),
        (Decimal('12'), Decimal('Infinity'), 120),
        (Decimal('12'), Decimal('100000000'), 11),
        (Decimal('12'), Decimal('100000000'), 241),
        (Decimal('12'), Decimal('100000000'), Decimal('120')),
        (Decimal('12'), Decimal('100000000'), True),
        ('12', Decimal('100000000'), 120),
        (Decimal('12'), '100000000', 120),
        (None, Decimal('100000000'), 120),
        (Decimal('12'), None, 120),
        (Decimal('12'), Decimal('100000000'), None),
    ],
)
@pytest.mark.parametrize('servicio', [calcular_cuota, generar_tabla, calcular_resumen])
def test_servicios_rechazan_datos_invalidos(servicio, tea, monto, plazo):
    with pytest.raises(ValidacionError):
        servicio(tea, monto, plazo)


@pytest.mark.parametrize('campo', ['tea', 'monto', 'plazo'])
@pytest.mark.parametrize('comando', [ejecutar_cuota, ejecutar_resumen])
def test_comandos_rechazan_ausencias(comando, campo):
    argumentos = {'tea': Decimal('12'), 'monto': Decimal('100000000'), 'plazo': 120}
    argumentos[campo] = None
    with pytest.raises(ErrorCLI) as captura:
        comando(**argumentos)
    assert captura.value.codigo_salida != 0


def test_dominio_calculos_y_redondeo():
    tasa = tasa_mensual(Decimal('0.12'))
    assert Decimal('0.009488') < tasa < Decimal('0.009489')
    assert redondear_peso(cuota_fija(Decimal('100000000'), 120, tasa)) == Decimal('1399472')
    assert redondear_peso(Decimal('1.49')) == Decimal(1)
    assert redondear_peso(Decimal('1.50')) == Decimal(2)
    assert redondear_peso(Decimal('-1.50')) == Decimal(-2)


def test_monto_fraccionario_y_tasa_con_ceros_finales():
    tabla = generar_tabla(Decimal('12.000'), Decimal('10000000.50'), 12)
    resumen = calcular_resumen(Decimal('12.000'), Decimal('10000000.50'), 12)
    assert tabla[0].saldo_inicial == Decimal('10000001')
    assert tabla[-1].saldo_final == 0
    assert resumen.total_pagado - resumen.total_intereses == Decimal('10000001')


def test_exportacion_por_defecto_y_delimitador(tmp_path):
    ruta = str(tmp_path / 'predeterminado.csv')
    tabla = ejecutar_tabla(Decimal('1'), Decimal('10000000'), 12, ruta)
    assert TablaCSV().existe(ruta)
    alternativa = str(tmp_path / 'alternativa.csv')
    escritor = TablaCSV(';')
    escritor.guardar(tabla, alternativa)
    assert escritor.existe(alternativa)
    with open(alternativa, encoding='utf-8', newline='') as archivo:
        registros = list(csv.reader(archivo, delimiter=';'))
    assert len(registros) == 13
    assert len(registros[0]) == 6
