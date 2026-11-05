from decimal import Decimal

import pytest

from credito_vivienda import (
    DatoInvalido,
    ReglasPendientes,
    Solicitud,
    calcular_cuota,
    calcular_resumen,
    generar_tabla,
    leer_solicitud,
)


@pytest.mark.parametrize("monto", ["10000000", "500000000"])
def test_limites_inclusivos_del_monto(monto):
    solicitud = leer_solicitud(monto, "120", "12")
    assert solicitud.monto == Decimal(monto)


@pytest.mark.parametrize("plazo", ["12", "240"])
def test_limites_inclusivos_del_plazo(plazo):
    solicitud = leer_solicitud("100000000", plazo, "12")
    assert solicitud.plazo == Decimal(plazo)


@pytest.mark.parametrize("tasa", ["1", "30", "1.00", "30.00"])
def test_limites_inclusivos_de_la_tasa(tasa):
    solicitud = leer_solicitud("100000000", "120", tasa)
    assert solicitud.tasa_anual == Decimal(tasa)


@pytest.mark.parametrize("monto", ["9999999.99", "500000000.01", "0", "-1"])
def test_monto_fuera_de_rango(monto):
    with pytest.raises(DatoInvalido, match="Monto: debe estar entre"):
        leer_solicitud(monto, "120", "12")


@pytest.mark.parametrize("plazo", ["11.99", "240.01", "0", "-1"])
def test_plazo_fuera_de_rango(plazo):
    with pytest.raises(DatoInvalido, match="Plazo: debe estar entre"):
        leer_solicitud("100000000", plazo, "12")


@pytest.mark.parametrize("tasa", ["0.99", "30.01", "0", "-1"])
def test_tasa_fuera_de_rango(tasa):
    with pytest.raises(DatoInvalido, match="Tasa efectiva anual: debe estar entre"):
        leer_solicitud("100000000", "120", tasa)


@pytest.mark.parametrize("tasa", ["12", "12.1", "12.25"])
def test_tasa_admite_hasta_dos_decimales(tasa):
    assert leer_solicitud("100000000", "120", tasa).tasa_anual == Decimal(tasa)


@pytest.mark.parametrize("tasa", ["12.001", "12.000"])
def test_tasa_rechaza_mas_de_dos_decimales(tasa):
    with pytest.raises(DatoInvalido, match="hasta dos decimales"):
        leer_solicitud("100000000", "120", tasa)


def test_plazo_fraccionario_no_se_rechaza_ni_se_trunca():
    solicitud = leer_solicitud("100000000", "120.5", "12")
    assert solicitud.plazo == Decimal("120.5")
    with pytest.raises(ReglasPendientes):
        generar_tabla(solicitud)


def test_monto_no_se_redondea_durante_la_lectura():
    solicitud = leer_solicitud("100000000.5", "120", "12")
    assert solicitud.monto == Decimal("100000000.5")


@pytest.mark.parametrize("campo", ["monto", "plazo", "tasa_anual"])
@pytest.mark.parametrize("texto", ["abc", "", "NaN", "Infinity", "12,5", "1e2", "1_000"])
def test_dato_no_numerico_o_formato_no_admitido(campo, texto):
    datos = {"monto": "100000000", "plazo": "120", "tasa_anual": "12"}
    datos[campo] = texto
    with pytest.raises(DatoInvalido, match="debe ser un número con punto decimal"):
        leer_solicitud(**datos)


def test_espacios_exteriores_y_signo_positivo():
    solicitud = leer_solicitud(" +100000000 ", " 120 ", " 12.25 ")
    assert solicitud == Solicitud(Decimal("100000000"), Decimal("120"), Decimal("12.25"))


@pytest.mark.parametrize("campo", ["monto", "plazo", "tasa_anual"])
@pytest.mark.parametrize("valor", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_api_rechaza_decimales_no_finitos(campo, valor):
    datos = {
        "monto": Decimal("100000000"),
        "plazo": Decimal("120"),
        "tasa_anual": Decimal("12"),
    }
    datos[campo] = valor
    with pytest.raises(DatoInvalido, match="decimal finito"):
        Solicitud(**datos)


def test_api_no_admite_flotantes_binarios():
    with pytest.raises(DatoInvalido, match="decimal finito"):
        Solicitud(100000000.0, Decimal("120"), Decimal("12"))


@pytest.mark.parametrize("operacion", [calcular_cuota, generar_tabla, calcular_resumen])
def test_operaciones_separadas_no_sustituyen_reglas_pendientes(operacion):
    solicitud = leer_solicitud("100000000", "120", "12")
    with pytest.raises(ReglasPendientes) as resultado:
        operacion(solicitud)
    mensaje = str(resultado.value)
    assert "redondeo de la tasa mensual" in mensaje
    assert "tratamiento de los medios pesos" in mensaje
    assert "No se ha autorizado una regla alternativa" in mensaje


def test_ejemplo_aprobado_permanece_pendiente_sin_cuota_inventada():
    solicitud = leer_solicitud("100000000", "120", "12")
    # La cuota esperada es 1399472; no hay autorización para una regla que la produzca.
    with pytest.raises(ReglasPendientes, match="Reglas de redondeo pendientes"):
        calcular_cuota(solicitud)


def test_no_se_acepta_el_ejemplo_fuera_del_rango_como_credito_valido():
    # Los 1200000 mencionados durante el diálogo son menores que el mínimo confirmado.
    with pytest.raises(DatoInvalido, match="Monto: debe estar entre"):
        leer_solicitud("1200000", "12", "12")
