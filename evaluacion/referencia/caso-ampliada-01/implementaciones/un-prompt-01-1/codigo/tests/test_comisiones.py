"""Verifique reglas, ejemplos, validaciones y decisiones de redondeo."""

from decimal import Decimal, localcontext

import pytest

from comisiones import ResultadoComisiones, calcular_comisiones


def test_ejemplo_venta_300_millones() -> None:
    resultado = calcular_comisiones(
        tipo_negocio="venta", valor=300_000_000, numero_asesores=1, estado="cerrado"
    )
    assert resultado == ResultadoComisiones(9_000_000, (3_600_000,))


def test_ejemplo_arriendo_un_millon_dos_asesores() -> None:
    resultado = calcular_comisiones(
        tipo_negocio="arriendo", valor=1_000_000, numero_asesores=2, estado="cerrado"
    )
    assert resultado == ResultadoComisiones(1_000_000, (300_000, 300_000))


def test_venta_comision_inmobiliaria_tres_por_ciento() -> None:
    resultado = calcular_comisiones(
        tipo_negocio="venta", valor=100_000_000, numero_asesores=1, estado="cerrado"
    )
    assert resultado.comision_inmobiliaria == 3_000_000


def test_arriendo_comision_inmobiliaria_primer_canon_completo() -> None:
    resultado = calcular_comisiones(
        tipo_negocio="arriendo", valor=2_000_000, numero_asesores=1, estado="cerrado"
    )
    assert resultado.comision_inmobiliaria == 2_000_000


def test_un_asesor_recibe_cuarenta_por_ciento() -> None:
    resultado = calcular_comisiones(
        tipo_negocio="arriendo", valor=2_000_000, numero_asesores=1, estado="cerrado"
    )
    assert resultado.comisiones_asesores == (800_000,)


@pytest.mark.parametrize(
    ("tipo_negocio", "valor", "comision_individual"),
    [("venta", 300_000_000, 1_800_000), ("arriendo", 4_000_000, 800_000)],
)
def test_dos_asesores_reparten_cuarenta_por_ciento_en_partes_iguales(
    tipo_negocio: str, valor: int, comision_individual: int
) -> None:
    resultado = calcular_comisiones(
        tipo_negocio=tipo_negocio, valor=valor, numero_asesores=2, estado="cerrado"
    )
    assert resultado.comisiones_asesores == (comision_individual, comision_individual)


@pytest.mark.parametrize("tipo_negocio", ["venta", "arriendo"])
@pytest.mark.parametrize("numero_asesores", [1, 2])
def test_minimo_individual_en_cualquier_tipo_de_negocio(
    tipo_negocio: str, numero_asesores: int
) -> None:
    resultado = calcular_comisiones(
        tipo_negocio=tipo_negocio,
        valor=100_000,
        numero_asesores=numero_asesores,
        estado="cerrado",
    )
    assert resultado.comisiones_asesores == (300_000,) * numero_asesores


@pytest.mark.parametrize("numero_asesores", [1, 2])
def test_calculo_exactamente_en_el_minimo(numero_asesores: int) -> None:
    resultado = calcular_comisiones(
        tipo_negocio="arriendo",
        valor=750_000 * numero_asesores,
        numero_asesores=numero_asesores,
        estado="cerrado",
    )
    assert resultado.comisiones_asesores == (300_000,) * numero_asesores


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("1000000.49", 1_000_000), ("1000000.50", 1_000_001), ("1000000.51", 1_000_001)],
)
def test_redondeo_inmobiliaria_al_peso_mas_cercano(valor: str, esperado: int) -> None:
    resultado = calcular_comisiones(
        tipo_negocio="arriendo", valor=valor, numero_asesores=1, estado="cerrado"
    )
    assert resultado.comision_inmobiliaria == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("1000001", 400_000), ("1000001.25", 400_001), ("1000001.5", 400_001)],
)
def test_redondeo_asesor_al_peso_mas_cercano(valor: str, esperado: int) -> None:
    resultado = calcular_comisiones(
        tipo_negocio="arriendo", valor=valor, numero_asesores=1, estado="cerrado"
    )
    assert resultado.comisiones_asesores == (esperado,)


def test_redondeo_independiente_de_cada_asesor() -> None:
    resultado = calcular_comisiones(
        tipo_negocio="venta", valor=100_000_250, numero_asesores=2, estado="cerrado"
    )
    assert resultado.comisiones_asesores == (600_002, 600_002)


def test_no_se_redondea_la_base_del_calculo_del_asesor() -> None:
    resultado = calcular_comisiones(
        tipo_negocio="venta", valor="250000041.67", numero_asesores=1, estado="cerrado"
    )
    assert resultado == ResultadoComisiones(7_500_001, (3_000_001,))


def test_resultados_son_pesos_enteros() -> None:
    resultado = calcular_comisiones(
        tipo_negocio="arriendo", valor="2000000.75", numero_asesores=2, estado="cerrado"
    )
    assert type(resultado.comision_inmobiliaria) is int
    assert all(type(importe) is int for importe in resultado.comisiones_asesores)


@pytest.mark.parametrize("tipo_negocio", ["venta", "arriendo"])
def test_negocio_abierto_se_rechaza_con_mensaje_exacto(tipo_negocio: str) -> None:
    with pytest.raises(ValueError) as error:
        calcular_comisiones(
            tipo_negocio=tipo_negocio, valor=300_000_000, numero_asesores=1, estado="abierto"
        )
    assert str(error.value) == "El negocio aún no está cerrado"


@pytest.mark.parametrize("valor", [0, -1, "0", Decimal("-0.01")])
def test_valor_cero_o_negativo_se_rechaza(valor: int | str | Decimal) -> None:
    with pytest.raises(ValueError, match="mayor que cero"):
        calcular_comisiones(
            tipo_negocio="venta", valor=valor, numero_asesores=1, estado="cerrado"
        )


@pytest.mark.parametrize("numero_asesores", [3, 4, 100])
def test_mas_de_dos_asesores_se_rechaza(numero_asesores: int) -> None:
    with pytest.raises(ValueError, match="El número de asesores debe ser 1 o 2"):
        calcular_comisiones(
            tipo_negocio="venta",
            valor=300_000_000,
            numero_asesores=numero_asesores,
            estado="cerrado",
        )


@pytest.mark.parametrize("numero_asesores", [0, -1, 1.0, True, "2", None])
def test_numero_asesores_debe_ser_entero_uno_o_dos(numero_asesores: object) -> None:
    with pytest.raises(ValueError, match="El número de asesores debe ser 1 o 2"):
        calcular_comisiones(
            tipo_negocio="venta",
            valor=300_000_000,
            numero_asesores=numero_asesores,
            estado="cerrado",
        )


@pytest.mark.parametrize("tipo_negocio", ["", "Venta", "otro", None])
def test_tipo_negocio_invalido(tipo_negocio: object) -> None:
    with pytest.raises(ValueError, match="El tipo de negocio debe ser venta o arriendo"):
        calcular_comisiones(
            tipo_negocio=tipo_negocio, valor=1_000_000, numero_asesores=1, estado="cerrado"
        )


@pytest.mark.parametrize("estado", ["", "Cerrado", "firmado", None])
def test_estado_invalido(estado: object) -> None:
    with pytest.raises(ValueError, match="El estado debe ser cerrado o abierto"):
        calcular_comisiones(
            tipo_negocio="arriendo", valor=1_000_000, numero_asesores=1, estado=estado
        )


@pytest.mark.parametrize(
    "valor",
    [None, True, "", "no numérico", "1.000.000", "NaN", "Infinity", float("inf"),
     float("nan"), Decimal("sNaN"), []],
)
def test_valor_no_numerico_o_no_finito_se_rechaza(valor: object) -> None:
    with pytest.raises(ValueError, match="numérico, finito y mayor que cero"):
        calcular_comisiones(
            tipo_negocio="arriendo", valor=valor, numero_asesores=1, estado="cerrado"
        )


@pytest.mark.parametrize("valor", [2_000_000, 2_000_000.0, "2000000", Decimal("2000000")])
def test_representaciones_numericas_admitidas(valor: int | float | str | Decimal) -> None:
    resultado = calcular_comisiones(
        tipo_negocio="arriendo", valor=valor, numero_asesores=1, estado="cerrado"
    )
    assert resultado == ResultadoComisiones(2_000_000, (800_000,))


@pytest.mark.parametrize("campo", ["tipo_negocio", "valor", "numero_asesores", "estado"])
def test_todos_los_datos_son_obligatorios(campo: str) -> None:
    datos = {
        "tipo_negocio": "venta",
        "valor": 300_000_000,
        "numero_asesores": 1,
        "estado": "cerrado",
    }
    datos.pop(campo)
    with pytest.raises(TypeError):
        calcular_comisiones(**datos)


def test_calculo_no_depende_de_precision_decimal_global() -> None:
    with localcontext() as contexto:
        contexto.prec = 2
        resultado = calcular_comisiones(
            tipo_negocio="venta",
            valor=Decimal("250000041.67"),
            numero_asesores=1,
            estado="cerrado",
        )
    assert resultado == ResultadoComisiones(7_500_001, (3_000_001,))
