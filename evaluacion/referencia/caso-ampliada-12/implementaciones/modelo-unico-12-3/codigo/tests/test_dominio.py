import pytest

from nit_service import calcular, validar


@pytest.mark.parametrize(
    ("nit", "esperado"),
    [("900123456", "8"), ("0", "0"), ("4", "1"), ("1", "8")],
)
def test_calculo_ejemplo_y_ramas_del_residuo(nit, esperado):
    assert calcular(nit) == esperado


@pytest.mark.parametrize(
    ("posicion", "esperado"),
    list(enumerate(["8", "4", "9", "5", "3", "1", "4", "7", "3", "1", "8", "2", "7", "1", "6"])),
)
def test_cada_peso_se_aplica_desde_la_derecha(posicion, esperado):
    assert calcular("1" + "0" * posicion) == esperado


def test_limite_de_quince_cifras():
    assert calcular("999999999999999") == "4"


@pytest.mark.parametrize("nit", ["900.123.456", "900-123-456", "900.123-456"])
def test_calculo_elimina_puntos_y_guiones(nit):
    assert calcular(nit) == "8"


@pytest.mark.parametrize(("recibido", "valido"), [("8", True), ("7", False)])
def test_ejemplos_validacion(recibido, valido):
    assert validar(f"900123456-{recibido}") == {
        "nit": "900123456",
        "digito_recibido": recibido,
        "digito_esperado": "8",
        "valido": valido,
    }


def test_validacion_normaliza_base():
    assert validar("900.123-456-8")["valido"] is True


def test_longitud_validacion_no_cuenta_digito_recibido():
    assert validar("999999999999999-4")["valido"] is True


def test_ceros_iniciales_se_conservan():
    resultado = validar("000900123456-8")
    assert resultado["nit"] == "000900123456"
    assert resultado["valido"] is True
    assert calcular("000900123456") == "8"


@pytest.mark.parametrize("operacion", [calcular, validar])
@pytest.mark.parametrize(
    ("base", "mensaje"),
    [
        ("ABC", "El NIT solo admite dígitos"),
        ("1234567890123456", "El NIT admite como máximo 15 dígitos"),
        ("", "El NIT debe contener al menos un dígito"),
        (".-", "El NIT debe contener al menos un dígito"),
        (" 123", "El NIT solo admite dígitos"),
        ("123 ", "El NIT solo admite dígitos"),
        ("1 23", "El NIT solo admite dígitos"),
        ("١٢٣", "El NIT solo admite dígitos"),
        ("12/3", "El NIT solo admite dígitos"),
    ],
)
def test_bases_mal_escritas(operacion, base, mensaje):
    entrada = base if operacion is calcular else f"{base}-8"
    with pytest.raises(ValueError) as error:
        operacion(entrada)
    assert str(error.value) == mensaje


@pytest.mark.parametrize("operacion", [calcular, validar])
@pytest.mark.parametrize("entrada", [None, 900123456, True, [], {}])
def test_nit_debe_ser_texto(operacion, entrada):
    with pytest.raises(ValueError, match="^El NIT debe enviarse como texto$"):
        operacion(entrada)


def test_validacion_necesita_separador():
    with pytest.raises(ValueError) as error:
        validar("9001234568")
    assert str(error.value) == "Para validar, envíe el NIT en formato NIT-dígito"


@pytest.mark.parametrize("recibido", ["", "88", "a", " ", "８", ".8"])
def test_digito_recibido_mal_escrito(recibido):
    with pytest.raises(ValueError) as error:
        validar(f"900123456-{recibido}")
    assert str(error.value) == "El dígito de verificación debe ser una sola cifra"
