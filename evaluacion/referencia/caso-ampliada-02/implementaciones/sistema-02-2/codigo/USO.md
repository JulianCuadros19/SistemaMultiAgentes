# Reajuste anual del canon

Calcula el canon anual según el IPC anterior y el límite pactado, valida el periodo mínimo y devuelve el incremento efectivo tras redondear a centenas.

## Requisitos

- Python 3.11 o superior; el módulo se probó con Python 3.11.
- Sin dependencias externas: `requirements.txt` fija la versión de pytest.

## Instalación

Desde la carpeta del código, cree un entorno e instale las dependencias:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En Windows, el entorno se activa con `.venv\Scripts\activate`. `requirements.txt` acompaña al código: fija las versiones con que se probó e incluye pytest.

## Configuración

No requiere archivos, variables de entorno ni almacenamiento. Prepare importes y porcentajes como `Decimal` creados desde cadenas, y fechas como `datetime.date`. Para importar los módulos desde la raíz, use `PYTHONPATH=src`.

## Ejecución

No tiene punto de entrada de terminal. Invoque el caso de uso desde Python:

```python
from datetime import date
from decimal import Decimal

from aplicacion.calculo_reajuste import calcular_reajuste

resultado = calcular_reajuste(
    Decimal("1000000"),
    Decimal("5.20"),
    Decimal("7.00"),
    date(2024, 1, 15),
    date(2025, 1, 15),
)
print(resultado.canon_reajustado)  # Equivale a 1052000
```

## Pruebas

```sh
PYTHONPATH=src python -m pytest tests
```

En Windows, con PowerShell: `$env:PYTHONPATH = "src"; python -m pytest tests`.

## Interfaces

- `aplicacion.calculo_reajuste.calcular_reajuste`: caso de uso mostrado arriba. Devuelve un `ResultadoReajuste`; no modifica los datos recibidos.
- `dominio.reajuste.ResultadoReajuste`: objeto inmutable. Ejemplo: `ResultadoReajuste(Decimal("1052000"), Decimal("5.20"), Decimal("52000"))`.
- `dominio.reajuste.validar_periodo_doce_meses`: ejemplo: `validar_periodo_doce_meses(date(2024, 1, 15), date(2025, 1, 15))`. Devuelve `None` si el periodo es suficiente.
- `dominio.reajuste.calcular_porcentaje_aplicable`: ejemplo: `calcular_porcentaje_aplicable(Decimal("8.50"), Decimal("5.00"))` devuelve `Decimal("5.00")`. El rango y la precisión de sus argumentos numéricos se validan en el caso de uso.
- `dominio.reajuste.redondear_a_centena_mas_cercana`: ejemplo: `redondear_a_centena_mas_cercana(Decimal("1050"))` equivale a `1100`. Recibe un decimal finito.
- `dominio.reajuste.DatosObligatoriosFaltantes`: excepción sin argumentos. Ejemplo: capture `DatosObligatoriosFaltantes` al calcular con `canon_actual=None`.
- `dominio.reajuste.PeriodoInsuficienteDoceMeses`: excepción sin argumentos. Ejemplo: capture `PeriodoInsuficienteDoceMeses` al validar fechas separadas por menos de doce meses.
- `dominio.reajuste.ValorInvalido`: excepción sin argumentos. Ejemplo: capture `ValorInvalido` al calcular con un canon de `Decimal("0")`.

Las tres excepciones también están disponibles en `aplicacion.calculo_reajuste`.

## Supuestos

- Doce meses completos se cuentan por aniversario calendario, no mediante un número fijo de días. El aniversario del 29 de febrero es el 28 de febrero del año siguiente.
- Fechas ausentes o que no sean objetos `date` no permiten acreditar el periodo y producen `PeriodoInsuficienteDoceMeses`. Tampoco se puede acreditar un aniversario posterior al año 9999.
- Los porcentajes admiten ceros finales adicionales: `5.200` representa un valor con dos decimales significativos fraccionarios. No se redondean entradas con precisión superior; se rechazan.
- No se impone un límite adicional al IPC ni una precisión monetaria de entrada no especificada. Los valores numéricos del caso de uso deben ser `Decimal` finitos.
- Se sigue la secuencia de cálculo especificada: el canon calculado se redondea siempre a centenas, incluso si el porcentaje aplicado es cero. Por ello, un canon original que no sea múltiplo de cien puede cambiar únicamente por el redondeo. El incremento devuelto es siempre la diferencia efectiva respecto del canon original.
- Los resultados monetarios se mantienen como `Decimal`; no se aplica un formato textual de moneda ni se añaden dos decimales de presentación.
