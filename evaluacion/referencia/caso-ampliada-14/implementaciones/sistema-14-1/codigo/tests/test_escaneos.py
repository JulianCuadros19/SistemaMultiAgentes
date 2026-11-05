import runpy
import sys
from datetime import date

import pytest

from comandos.renombrar import ejecutar_renombrar
from comandos.reporte import ejecutar_reporte
from comandos.revisar import ejecutar_revisar
from comandos.validar import ejecutar_validar
from dominio.convencion import (
    AnioFueraDeRango,
    CambioNombre,
    CarpetaNoExiste,
    ConflictoRenombrado,
    EstructuraNombre,
    ExtensionInvalida,
    FormatoInvalido,
    TipoDesconocido,
    analizar_nombre,
    normalizar_nombre,
)
from entrada_salida.archivos import GestorArchivos
from servicios.renombrado import renombrar_archivos
from servicios.reporte import generar_reporte
from servicios.revision import CarpetaNoExiste as CarpetaRevisionNoExiste
from servicios.revision import revisar_carpeta
from servicios.validacion import validar_nombres


@pytest.fixture
def carpeta(tmp_path):
    gestor = GestorArchivos()
    ruta = str(tmp_path / "expedientes")
    gestor.crear_carpeta(ruta)
    return ruta, gestor


def _ejecutar_terminal(modulo, ruta, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [modulo, ruta])
    with pytest.raises(SystemExit) as terminacion:
        runpy.run_module(modulo, run_name="__main__")
    return terminacion.value.code, capsys.readouterr()


def test_rf_01_esc_01_revision_existente(carpeta, monkeypatch, capsys):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "ESC_2019_00042.pdf", None)
    assert revisar_carpeta(ruta, gestor) == ["ESC_2019_00042.pdf"]
    assert ejecutar_revisar(ruta) == ["ESC_2019_00042.pdf"]
    codigo, salida = _ejecutar_terminal("comandos.revisar", ruta, monkeypatch, capsys)
    assert codigo == 0
    assert salida.out.splitlines() == ["Revisión completada", "ESC_2019_00042.pdf"]
    assert salida.err == ""


def test_rf_01_esc_02_revision_programada_parcial(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "CER_2020_00001.pdf", None)
    # Solo se verifica la revisión invocable; no se demuestra el disparo nocturno.
    # No hay interfaz pública de planificador para preparar u observar ese disparo.
    assert revisar_carpeta(ruta, gestor) == ["CER_2020_00001.pdf"]
    assert ejecutar_revisar(ruta) == ["CER_2020_00001.pdf"]


def test_rf_01_esc_03_carpeta_inexistente(tmp_path, monkeypatch, capsys):
    ruta = str(tmp_path / "inexistente")
    with pytest.raises(CarpetaRevisionNoExiste, match="La carpeta no existe"):
        revisar_carpeta(ruta, GestorArchivos())
    with pytest.raises(CarpetaRevisionNoExiste, match="La carpeta no existe"):
        ejecutar_revisar(ruta)
    codigo, salida = _ejecutar_terminal("comandos.revisar", ruta, monkeypatch, capsys)
    assert codigo == 1
    assert salida.err.strip() == f"La carpeta no existe: {ruta}"
    assert salida.out == ""


def test_rf_02_esc_01_separadores_incorrectos(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "esc-2019-42.PDF", None)
    resultados, totales = validar_nombres(ruta, gestor)
    motivo = (
        "No cumple la convención TIPO_AAAA_NNNNN.pdf: "
        "los separadores deben ser guiones bajos"
    )
    assert len(resultados) == 1
    assert resultados[0].archivo == "esc-2019-42.PDF"
    assert resultados[0].motivo == motivo
    assert totales == {motivo: 1}
    assert ejecutar_validar(ruta) == (resultados, totales)
    with pytest.raises(FormatoInvalido, match="los separadores deben ser guiones bajos"):
        analizar_nombre("esc-2019-42.PDF", None)


def test_rf_02_esc_02_tipo_desconocido(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "XYZ_2019_00001.pdf", None)
    resultados, totales = validar_nombres(ruta, gestor)
    assert len(resultados) == 1
    assert resultados[0].archivo == "XYZ_2019_00001.pdf"
    assert "Tipo desconocido" in resultados[0].motivo
    assert totales == {resultados[0].motivo: 1}


def test_rf_02_esc_03_anio_fuera_de_rango(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "ESC_1949_00001.pdf", None)
    resultados, totales = validar_nombres(ruta, gestor)
    assert len(resultados) == 1
    assert resultados[0].archivo == "ESC_1949_00001.pdf"
    assert "Año fuera de rango" in resultados[0].motivo
    assert totales == {resultados[0].motivo: 1}


def test_rf_02_esc_04_extension_distinta(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "ESC_2019_00001.doc", None)
    resultados, totales = validar_nombres(ruta, gestor)
    assert len(resultados) == 1
    assert resultados[0].archivo == "ESC_2019_00001.doc"
    assert "Extensión distinta de pdf" in resultados[0].motivo
    assert totales == {resultados[0].motivo: 1}


def test_rf_03_esc_01_renombrado_efectivo(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "esc-2019-42.PDF", b"documento")
    cambios, conflictos, errores = renombrar_archivos(ruta, False, gestor)
    assert cambios == [CambioNombre("esc-2019-42.PDF", "ESC_2019_00042.pdf")]
    assert conflictos == []
    assert errores == []
    assert gestor.listar_archivos(ruta) == ["ESC_2019_00042.pdf"]
    assert ejecutar_renombrar(ruta, False) == ([], [], [])


def test_rf_03_esc_02_simulacion(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "esc-2019-42.PDF", None)
    cambios, conflictos, errores = renombrar_archivos(ruta, True, gestor)
    assert cambios == [CambioNombre("esc-2019-42.PDF", "ESC_2019_00042.pdf")]
    assert conflictos == []
    assert errores == []
    assert gestor.listar_archivos(ruta) == ["esc-2019-42.PDF"]


def test_rf_03_esc_03_conflicto(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "esc-2019-42.PDF", None)
    gestor.crear_archivo(ruta, "ESC_2019_00042.pdf", None)
    cambios, conflictos, errores = renombrar_archivos(ruta, False, gestor)
    assert cambios == []
    assert conflictos == [ConflictoRenombrado("esc-2019-42.PDF", "Conflicto")]
    assert errores == []
    assert gestor.listar_archivos(ruta) == ["ESC_2019_00042.pdf", "esc-2019-42.PDF"]


def test_rf_03_esc_04_tipo_no_corregible(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "XYZ_2019_00001.pdf", None)
    cambios, conflictos, errores = renombrar_archivos(ruta, False, gestor)
    assert cambios == []
    assert conflictos == []
    assert len(errores) == 1
    assert errores[0].archivo == "XYZ_2019_00001.pdf"
    assert "Tipo desconocido" in errores[0].motivo
    assert gestor.listar_archivos(ruta) == ["XYZ_2019_00001.pdf"]


def test_rf_04_esc_01_reporte_valido(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "ESC_2019_00042.pdf", None)
    gestor.crear_archivo(ruta, "CER_2020_00001.pdf", None)
    reporte = generar_reporte(ruta, gestor)
    assert reporte.conteos_por_anio_y_tipo == {2019: {"ESC": 1}, 2020: {"CER": 1}}
    assert reporte.total_archivos == 2
    assert len(reporte.lineas_por_archivo) == 2
    assert any("ESC_2019_00042.pdf" in linea for linea in reporte.lineas_por_archivo)
    assert any("CER_2020_00001.pdf" in linea for linea in reporte.lineas_por_archivo)
    assert ejecutar_reporte(ruta) == reporte


def test_rf_04_esc_02_mezcla_de_anios_y_tipos(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "ESC_2019_00042.pdf", None)
    gestor.crear_archivo(ruta, "CER_2019_00001.pdf", None)
    gestor.crear_archivo(ruta, "PAZ_2020_00001.pdf", None)
    reporte = generar_reporte(ruta, gestor)
    assert reporte.conteos_por_anio_y_tipo == {
        2019: {"CER": 1, "ESC": 1},
        2020: {"PAZ": 1},
    }
    assert reporte.total_archivos == 3
    assert len(reporte.lineas_por_archivo) == 3


def test_rf_04_esc_03_carpeta_inexistente(tmp_path, monkeypatch, capsys):
    ruta = str(tmp_path / "inexistente")
    with pytest.raises(CarpetaNoExiste, match="La carpeta no existe"):
        generar_reporte(ruta, GestorArchivos())
    with pytest.raises(CarpetaNoExiste, match="La carpeta no existe"):
        ejecutar_reporte(ruta)
    codigo, salida = _ejecutar_terminal("comandos.reporte", ruta, monkeypatch, capsys)
    assert codigo == 1
    assert salida.err.strip() == f"La carpeta no existe: {ruta}"
    assert salida.out == ""


@pytest.mark.parametrize("anio", [1950, date.today().year])
@pytest.mark.parametrize("consecutivo", [0, 99999])
def test_limites_validos(anio, consecutivo):
    nombre = f"ESC_{anio:04d}_{consecutivo:05d}.pdf"
    assert analizar_nombre(nombre, None) == EstructuraNombre("ESC", anio, consecutivo, "pdf")
    assert normalizar_nombre(nombre) == nombre


@pytest.mark.parametrize("anio", [1949, date.today().year + 1])
def test_anios_invalidos(anio):
    nombre = f"ESC_{anio}_00001.pdf"
    with pytest.raises(AnioFueraDeRango):
        analizar_nombre(nombre, None)
    with pytest.raises(AnioFueraDeRango):
        normalizar_nombre(nombre)


@pytest.mark.parametrize("consecutivo", ["", "-1", "100000", "000001"])
def test_consecutivos_invalidos(consecutivo):
    nombre = f"ESC_2019_{consecutivo}.pdf"
    with pytest.raises(FormatoInvalido):
        analizar_nombre(nombre, None)
    with pytest.raises(FormatoInvalido):
        normalizar_nombre(nombre)


@pytest.mark.parametrize("tipo", ["ESC", "CER", "PAZ"])
def test_tipos_validos(tipo):
    assert analizar_nombre(f"{tipo}_2019_00001.pdf", None).tipo == tipo
    assert normalizar_nombre(f"{tipo.lower()}-2019-1.PDF") == f"{tipo}_2019_00001.pdf"


def test_errores_especificos_del_dominio():
    with pytest.raises(TipoDesconocido):
        analizar_nombre("XYZ_2019_00001.pdf", None)
    with pytest.raises(ExtensionInvalida):
        normalizar_nombre("ESC_2019_00001.doc")
    with pytest.raises(FormatoInvalido):
        analizar_nombre("ESC_2019_1.pdf", None)
    with pytest.raises(FormatoInvalido):
        normalizar_nombre("sin_estructura.pdf")
    with pytest.raises(AnioFueraDeRango):
        analizar_nombre("ESC_2020_00001.pdf", 2019)


@pytest.mark.parametrize("ruta", ["", " "])
def test_ruta_vacia(ruta):
    with pytest.raises(CarpetaRevisionNoExiste):
        revisar_carpeta(ruta, GestorArchivos())


def test_validacion_y_renombrado_sin_carpeta(tmp_path):
    ruta = str(tmp_path / "inexistente")
    gestor = GestorArchivos()
    with pytest.raises(CarpetaNoExiste):
        validar_nombres(ruta, gestor)
    with pytest.raises(CarpetaNoExiste):
        renombrar_archivos(ruta, True, gestor)
    with pytest.raises(FileNotFoundError):
        gestor.listar_archivos(ruta)
    with pytest.raises(FileNotFoundError):
        gestor.renombrar(ruta, "original.pdf", "nuevo.pdf")


def test_modo_de_simulacion_invalido(carpeta):
    ruta, gestor = carpeta
    with pytest.raises(TypeError, match="booleano"):
        renombrar_archivos(ruta, "true", gestor)


def test_colision_entre_propuestas(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "esc-2019-42.PDF", None)
    gestor.crear_archivo(ruta, "esc_2019_42.pdf", None)
    cambios, conflictos, errores = renombrar_archivos(ruta, True, gestor)
    assert len(cambios) == 1
    assert len(conflictos) == 1
    assert conflictos[0].motivo == "Conflicto"
    assert errores == []
    assert gestor.listar_archivos(ruta) == ["esc-2019-42.PDF", "esc_2019_42.pdf"]


def test_reporte_con_invalido_y_carpeta_vacia(carpeta):
    ruta, gestor = carpeta
    vacio = generar_reporte(ruta, gestor)
    assert vacio.lineas_por_archivo == []
    assert vacio.conteos_por_anio_y_tipo == {}
    assert vacio.total_archivos == 0
    gestor.crear_archivo(ruta, "incorrecto.txt", None)
    reporte = generar_reporte(ruta, gestor)
    assert len(reporte.lineas_por_archivo) == 1
    assert "incorrecto.txt: Error:" in reporte.lineas_por_archivo[0]
    assert reporte.total_archivos == 0


def test_gestor_no_sobrescribe_y_rechaza_rutas(carpeta):
    ruta, gestor = carpeta
    gestor.crear_archivo(ruta, "original.pdf", None)
    gestor.crear_archivo(ruta, "destino.pdf", None)
    with pytest.raises(FileExistsError, match="Conflicto"):
        gestor.renombrar(ruta, "original.pdf", "destino.pdf")
    with pytest.raises(ValueError):
        gestor.crear_archivo(ruta, "../fuera.pdf", None)
    assert gestor.listar_archivos(ruta) == ["destino.pdf", "original.pdf"]
