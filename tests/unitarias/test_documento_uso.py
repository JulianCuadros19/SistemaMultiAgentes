"""Documento de uso del módulo generado: las secciones que escribe el sistema (RF-18)."""

from multiagente.agentes.desarrollador.uso import (
    PYTHON,
    SECCIONES_USO,
    componer_uso,
    secciones_faltantes,
)

REDACTADO = """# Cálculo del impuesto predial

Calcula el valor a pagar en la ventanilla.

## Requisitos

Python 3.11.

## Instalación

```sh
python3.11 -m venv .venv
pip install -r requirements.txt
pip install pytest
```

El sistema genera `requirements.txt` al exportar; no forma parte de los archivos entregados.

## Ejecución

```python
## esto es un comentario dentro del código, no una sección
calcular()
```

## Configuración

No requiere.

## Notas

Conforme a D1, se redondea al peso.

## Interfaces

- `calcular()`.

## Supuestos

- El impuesto llega en pesos enteros.
"""


def titulos(documento: str) -> list[str]:
    en_codigo = False
    lista = []
    for linea in documento.splitlines():
        if linea.startswith("```"):
            en_codigo = not en_codigo
        elif not en_codigo and linea.startswith("## "):
            lista.append(linea.removeprefix("## "))
    return lista


def test_las_secciones_del_sistema_reemplazan_las_que_redacto_el_modelo():
    uso = componer_uso(REDACTADO, ["openpyxl"])

    assert uso.startswith("# Cálculo del impuesto predial\n\nCalcula el valor a pagar")
    # El orden es el de RF-18; la sección que agregó el modelo queda al final.
    assert titulos(uso) == [*SECCIONES_USO, "Notas"]
    assert f"Python {PYTHON} o superior; el módulo se probó con Python {PYTHON}." in uso
    assert "Dependencias externas: `openpyxl`." in uso
    assert "pip install -r requirements.txt" in uso
    for copiado in ("python3.11 -m venv", "pip install pytest", "no forma parte"):
        assert copiado not in uso
    # Lo que redactó el modelo se conserva, incluido un «##» dentro de un bloque de código.
    assert "## esto es un comentario dentro del código" in uso
    assert "- El impuesto llega en pesos enteros.\n" in uso
    assert uso.endswith("\n") and not uso.endswith("\n\n")


def test_componer_dos_veces_da_lo_mismo_que_una():
    una = componer_uso(REDACTADO, [])
    assert componer_uso(una, []) == una
    assert "Sin dependencias externas: `requirements.txt` fija la versión de pytest." in una


def test_el_modelo_solo_redacta_lo_propio_del_modulo():
    propio = "# Uso\n\n" + "\n\n".join(
        f"## {seccion}\n\nTexto." for seccion in ("Configuración", "Ejecución", "Interfaces")
    )
    assert secciones_faltantes(propio) == [
        "Requisitos",
        "Instalación",
        "Pruebas",
        "Supuestos",
    ]
    assert secciones_faltantes(componer_uso(propio, [])) == ["Supuestos"]
