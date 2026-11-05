"""Oráculo común del paso 15: carga, adaptadores y clasificación, sin Docker (ADR-0019)."""

import pytest

from multiagente.evaluacion.referencia import (
    ADAPTADOR,
    COMUN,
    PRUEBAS,
    ErrorReferencia,
    aplicar_cambios,
    archivos_para_referencia,
    cargar_caso_referencia,
    casos_de_referencia,
    clasificar,
    evaluar_referencia,
    leer_implementacion,
    problemas_del_adaptador,
)
from multiagente.sandbox.ejecutor import PruebaReportada, ResultadoEjecucion, ResultadoPruebas


def corrida(pruebas, recoleccion=()):
    ejecucion = ResultadoEjecucion(
        codigo_salida=0, salida="", errores="", vencido=False, duracion_ms=1
    )
    return ResultadoPruebas(
        pruebas=tuple(pruebas),
        errores_recoleccion=tuple(recoleccion),
        codigo_pytest=0,
        salida_pytest="",
        ejecucion=ejecucion,
    )


def reportada(nombre, resultado, mensaje=""):
    return PruebaReportada(
        archivo=PRUEBAS, nombre=nombre, resultado=resultado, duracion_ms=1, mensaje=mensaje
    )


def test_los_tres_casos_cargan_con_sus_verificaciones_y_mutantes():
    assert casos_de_referencia() == ["caso-ampliada-02", "caso-ampliada-12", "caso-ampliada-16"]
    conteos = {
        id_caso: (len(caso.verificaciones), len(caso.mutantes))
        for id_caso in casos_de_referencia()
        for caso in [cargar_caso_referencia(id_caso)]
    }
    assert conteos == {
        "caso-ampliada-02": (9, 3),
        "caso-ampliada-12": (10, 3),
        "caso-ampliada-16": (10, 3),
    }
    caso = cargar_caso_referencia("caso-ampliada-12")
    assert all(mutante.codigo != caso.control for mutante in caso.mutantes)


def test_un_cambio_de_mutante_debe_aparecer_una_sola_vez():
    assert aplicar_cambios("a = 1", [{"buscar": "1", "reemplazar": "2"}]) == "a = 2"
    with pytest.raises(ErrorReferencia, match="aparece 2 veces"):
        aplicar_cambios("1 + 1", [{"buscar": "1", "reemplazar": "2"}])
    with pytest.raises(ErrorReferencia, match="aparece 0 veces"):
        aplicar_cambios("a = 1", [{"buscar": "b", "reemplazar": "c"}])


def test_el_adaptador_no_puede_calcular():
    calcula = (
        "import math\n"
        "from decimal import Decimal\n"
        "def cuota(monto, plazo, tasa):\n"
        "    total = 0\n"
        "    total += monto\n"
        "    return round(monto * tasa) + sum([plazo])\n"
        "x = Decimal(1).quantize(Decimal(1))\n"
    )
    problemas = problemas_del_adaptador(calcula)
    assert "línea 1: importa math" in problemas
    assert "línea 5: operación aritmética" in problemas
    assert "línea 6: llama a round()" in problemas
    assert "línea 6: llama a sum()" in problemas
    assert "línea 7: llama a .quantize()" in problemas
    assert problemas_del_adaptador("def f(:\n")[0].startswith("El adaptador no compila")


def test_el_adaptador_que_solo_traduce_se_admite():
    traduce = (
        "from decimal import Decimal\n"
        "from credito.calculo import calcular_cuota\n"
        "from referencia_comun import Ausente\n"
        "def cuota(monto: int, plazo: int, tasa: Decimal) -> int:\n"
        "    resultado = calcular_cuota(Decimal(monto), plazo, tasa)\n"
        "    if resultado.get('error') is not None:\n"
        "        raise ValueError(f\"{resultado['error']}\")\n"
        "    return int(resultado['cuota'])\n"
        "def tabla(monto, plazo, tasa):\n"
        "    raise Ausente('sin tabla')\n"
    )
    assert problemas_del_adaptador(traduce) == []


def test_la_implementacion_entra_sin_sus_pruebas_y_con_el_oraculo():
    caso = cargar_caso_referencia("caso-ampliada-12")
    implementacion = {
        "src/nit/digito.py": "x = 1\n",
        "tests/test_nit.py": "def test(): pass\n",
        ADAPTADOR: "impostor\n",
        "USO.md": "# Uso\n",
    }
    archivos = archivos_para_referencia(caso, "adaptador\n", implementacion)
    assert set(archivos) == {"src/nit/digito.py", "USO.md", ADAPTADOR, COMUN, PRUEBAS}
    assert archivos[ADAPTADOR] == "adaptador\n"
    assert archivos[PRUEBAS] == caso.pruebas


def test_clasifica_pasa_falla_ausente_y_no_ejecutada():
    caso = cargar_caso_referencia("caso-ampliada-12")
    primera, segunda, tercera, *resto = caso.verificaciones
    resultado = clasificar(
        caso,
        corrida(
            [
                reportada(primera, "paso"),
                reportada(segunda, "fallo", "AssertionError: assert 7 == 6"),
                reportada(tercera, "fallo", "E   referencia_comun.Ausente: no valida"),
            ]
            + [reportada(nombre, "paso") for nombre in resto[:-1]]
        ),
    )
    estados = [verificacion.resultado for verificacion in resultado.verificaciones]
    assert estados[:3] == ["paso", "fallo", "ausente"]
    assert estados[-1] == "error"
    assert (resultado.cuenta("paso"), resultado.total) == (len(resto), 10)
    assert resultado.tasa_errores == pytest.approx(0.3)


def test_un_fallo_que_cita_la_docstring_de_rechaza_no_cuenta_como_ausente():
    caso = cargar_caso_referencia("caso-ampliada-02")
    primera, *resto = caso.verificaciones
    traza = (
        "Raises:\n    Ausente: Si la implementación no ofrece el comportamiento.\n"
        "E   AssertionError: Se rechazó con otro mensaje"
    )
    resultado = clasificar(
        caso,
        corrida([reportada(primera, "fallo", traza), *(reportada(n, "paso") for n in resto)]),
    )
    assert resultado.verificaciones[0].resultado == "fallo"
    assert resultado.cuenta("ausente") == 0


def test_si_el_adaptador_no_importa_todo_cuenta_como_error():
    caso = cargar_caso_referencia("caso-ampliada-02")
    resultado = clasificar(
        caso, corrida([], ["tests/test_referencia.py: ModuleNotFoundError: No module named 'x'"])
    )
    assert {verificacion.resultado for verificacion in resultado.verificaciones} == {"error"}
    assert "ModuleNotFoundError" in resultado.verificaciones[0].detalle
    assert resultado.tasa_errores == 1.0


def test_un_adaptador_que_calcula_no_llega_al_entorno_aislado():
    class EntornoQueNoSeUsa:
        def probar(self, archivos):
            raise AssertionError("no debía ejecutarse")

    caso = cargar_caso_referencia("caso-ampliada-16")
    with pytest.raises(ErrorReferencia, match="operación aritmética"):
        evaluar_referencia(
            EntornoQueNoSeUsa(), caso, "def cuota(m, p, t):\n    return m * t\n", {"src/x.py": ""}
        )


def test_lee_los_archivos_de_texto_de_una_implementacion(tmp_path):
    (tmp_path / "src" / "paquete" / "__pycache__").mkdir(parents=True)
    (tmp_path / "src" / "paquete" / "modulo.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src" / "paquete" / "__pycache__" / "modulo.cpython-311.pyc").write_bytes(b"\0")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_modulo.py").write_text("def test(): pass\n", encoding="utf-8")
    (tmp_path / "USO.md").write_text("# Uso\n", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG")
    assert set(leer_implementacion(tmp_path)) == {
        "src/paquete/modulo.py",
        "tests/test_modulo.py",
        "USO.md",
    }
