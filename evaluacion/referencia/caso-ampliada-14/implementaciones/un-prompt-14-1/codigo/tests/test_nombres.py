"""Pruebas de cada regla de nombres y de los ejemplos del cliente."""

from datetime import date

import pytest

from escaneos import inspeccionar_nombre


@pytest.mark.parametrize("tipo", ["ESC", "CER", "PAZ"])
def test_tipos_validos(tipo: str) -> None:
    """Aceptar los tres tipos conocidos."""
    nombre = f"{tipo}_2019_00001.pdf"
    resultado = inspeccionar_nombre(nombre)
    assert resultado.valido
    assert resultado.destino == nombre
    assert resultado.motivos == ()


@pytest.mark.parametrize("anio", [1950, date.today().year])
def test_limites_del_anio(anio: int) -> None:
    """Aceptar ambos extremos del intervalo de años."""
    assert inspeccionar_nombre(f"ESC_{anio}_00001.pdf").valido


@pytest.mark.parametrize("anio", [1949, date.today().year + 1])
def test_anio_fuera_de_rango(anio: int) -> None:
    """No proponer corrección para años fuera del rango."""
    resultado = inspeccionar_nombre(f"ESC_{anio}_00001.pdf")
    assert resultado.destino is None
    assert any("Año fuera del rango" in motivo for motivo in resultado.motivos)


def test_ejemplo_de_correccion() -> None:
    """Corregir exactamente el ejemplo aportado por el cliente."""
    resultado = inspeccionar_nombre("esc-2019-42.PDF")
    assert not resultado.valido
    assert resultado.destino == "ESC_2019_00042.pdf"
    assert len(resultado.motivos) == 4


def test_ejemplo_tipo_desconocido() -> None:
    """Rechazar el ejemplo XYZ sin proponer destino."""
    resultado = inspeccionar_nombre("XYZ_2019_00001.pdf")
    assert resultado.destino is None
    assert resultado.motivos == ("Tipo desconocido",)


@pytest.mark.parametrize("tipo", ["esc", "cer", "paz", "eSc"])
def test_minusculas_del_tipo(tipo: str) -> None:
    """Pasar las letras del tipo a mayúsculas."""
    resultado = inspeccionar_nombre(f"{tipo}_2019_00001.pdf")
    assert resultado.destino == f"{tipo.upper()}_2019_00001.pdf"
    assert resultado.motivos == ("Tipo debe estar en mayúsculas",)


@pytest.mark.parametrize("separadores", [("-", "-"), (" ", " "), ("-", " "), ("_", "-")])
def test_separadores(separadores: tuple[str, str]) -> None:
    """Corregir guiones, espacios y combinaciones de separadores."""
    primero, segundo = separadores
    resultado = inspeccionar_nombre(f"ESC{primero}2019{segundo}00001.pdf")
    assert resultado.destino == "ESC_2019_00001.pdf"
    assert resultado.motivos == ("Separadores deben ser guiones bajos",)


@pytest.mark.parametrize("numero", ["1", "42", "123", "1234"])
def test_relleno_con_ceros(numero: str) -> None:
    """Completar cada longitud menor de cinco dígitos."""
    resultado = inspeccionar_nombre(f"ESC_2019_{numero}.pdf")
    assert resultado.destino == f"ESC_2019_{numero.zfill(5)}.pdf"
    assert resultado.motivos == ("Consecutivo debe tener cinco dígitos",)


@pytest.mark.parametrize("numero", ["00000", "00001", "99999"])
def test_consecutivos_de_cinco_digitos(numero: str) -> None:
    """No imponer un mínimo ni alterar consecutivos ya completos."""
    assert inspeccionar_nombre(f"ESC_2019_{numero}.pdf").valido


@pytest.mark.parametrize("extension", ["PDF", "Pdf", "pDf"])
def test_extension_pdf_mayusculas(extension: str) -> None:
    """Normalizar variantes de mayúsculas de la extensión pdf."""
    resultado = inspeccionar_nombre(f"ESC_2019_00001.{extension}")
    assert resultado.destino == "ESC_2019_00001.pdf"
    assert resultado.motivos == ("Extensión debe ser .pdf",)


@pytest.mark.parametrize("extension", ["txt", "jpg", "pdfx", ""])
def test_extension_distinta(extension: str) -> None:
    """No corregir extensiones que no representan pdf."""
    resultado = inspeccionar_nombre(f"ESC_2019_00001.{extension}")
    assert resultado.destino is None
    assert "Extensión distinta de pdf" in resultado.motivos


def test_sin_extension() -> None:
    """Rechazar archivos sin extensión."""
    resultado = inspeccionar_nombre("ESC_2019_00001")
    assert resultado.destino is None
    assert "Extensión distinta de pdf" in resultado.motivos


@pytest.mark.parametrize(
    "nombre",
    [
        "ESC_2019_.pdf",
        "ESC_2019_abc.pdf",
        "ESC_2019_１２３.pdf",
        "ESC_19_00001.pdf",
        "ESC__2019_00001.pdf",
        "ESC  2019  42.pdf",
        "ESC_2019_00001_extra.pdf",
        "documento.pdf",
        "ESC_2019_00001.pdf\n",
    ],
)
def test_formato_no_corregible(nombre: str) -> None:
    """No inventar correcciones para estructuras no definidas."""
    resultado = inspeccionar_nombre(nombre)
    assert not resultado.valido
    assert resultado.destino is None
    assert resultado.motivos


def test_consecutivo_demasiado_largo() -> None:
    """No truncar consecutivos de más de cinco dígitos."""
    resultado = inspeccionar_nombre("ESC_2019_123456.pdf")
    assert resultado.destino is None
    assert resultado.motivos == ("Consecutivo con más de cinco dígitos",)


def test_multiples_errores() -> None:
    """Reportar todas las causas semánticas encontradas."""
    resultado = inspeccionar_nombre("XYZ_1949_00001.txt")
    assert resultado.destino is None
    assert "Tipo desconocido" in resultado.motivos
    assert "Extensión distinta de pdf" in resultado.motivos
    assert any("Año fuera del rango" in motivo for motivo in resultado.motivos)
