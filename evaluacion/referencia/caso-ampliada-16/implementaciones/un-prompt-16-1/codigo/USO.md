# Crédito de vivienda

Herramienta de terminal para asesores. Calcula créditos con cuota fija, muestra su amortización completa y resume los pagos. No incluye aprobación del crédito, seguros, comisiones ni otros conceptos.

## Ejecución

Requiere Python 3.11. El código usa únicamente la biblioteca estándar y no necesita red. Desde la carpeta de la entrega, agregue `src/` a la ruta de importación:

```sh
export PYTHONPATH="$PWD/src"
python -m credito_vivienda cuota --monto 100000000 --plazo 120 --tasa 12
python -m credito_vivienda tabla --monto 100000000 --plazo 120 --tasa 12
python -m credito_vivienda tabla --monto 100000000 --plazo 120 --tasa 12 --csv tabla.csv
python -m credito_vivienda resumen --monto 100000000 --plazo 120 --tasa 12
python -m credito_vivienda --help
```

En PowerShell, configure la ruta con `$env:PYTHONPATH = "$PWD/src"`.

Cada invocación realiza una sola operación. Las tres requieren sus propios datos; no se guarda información entre ejecuciones.

## Entradas

- `--monto`: entre 10000000 y 500000000 pesos, inclusive.
- `--plazo`: entero entre 12 y 240 meses, inclusive.
- `--tasa`: tasa efectiva anual en porcentaje entre 1 y 30, inclusive, con hasta dos posiciones decimales. `12` significa 12 %, no 0,12 %.
- `--csv`: opcional y exclusivo de `tabla`; ruta del archivo de salida.

Escriba números sin separadores de miles ni símbolos monetarios. El separador decimal es el punto: `12.34`. Se rechazan números no finitos y textos que no sean números.

## Cálculo y decisiones sobre aspectos no definidos

Se usa `Decimal` con un contexto local de 60 dígitos de precisión, independiente del contexto decimal del programa que importe el paquete. No se convierte ningún dato a punto flotante binario. La raíz de la tasa se aproxima con aritmética decimal a esa precisión; no se redondea la tasa mensual al peso ni a un número reducido de decimales.

Con `a = tasa_anual / 100`, `r = (1 + a) ** (1/12) - 1` y `n = plazo`, la cuota es `monto * r / (1 - (1 + r) ** (-n))`.

Como no se especificó el criterio de desempate del redondeo, se utiliza **ROUND_HALF_UP**: medio peso se redondea hacia arriba. Como no se especificó si el monto admite fracciones de peso, se aceptan: primero se valida el monto original contra los límites y luego se redondea al peso para iniciar el crédito. La tasa conserva como máximo dos posiciones decimales escritas; por sencillez, `12.000` se rechaza aunque equivalga a `12`.

La cuota fija se redondea una vez al peso. Cada mes se redondea el interés del saldo inicial de ese mes al peso; el abono a capital es la cuota menos ese interés y el saldo es el saldo anterior menos el abono. Todos esos importes son enteros. En el último mes la cuota es el saldo pendiente más el interés del mes: así el saldo final queda exactamente en cero.

El resumen suma las cuotas e intereses de esta tabla, incluyendo el ajuste final; no multiplica simplemente la cuota fija por el plazo.

## Salidas

- `cuota`: `Cuota mensual: 1399472 pesos` para el ejemplo de 100000000 pesos, 120 meses y 12 % efectivo anual. Es la cuota fija, antes del ajuste del último mes.
- `tabla`: encabezado y una fila por mes, separados por tabulaciones. Columnas: `mes`, `cuota`, `interes`, `abono_capital`, `saldo`. Para el ejemplo, la primera fila contiene `1`, `1399472`, `948879`, `450593`, `99549407`.
- `resumen`: dos líneas con el total pagado y el total de intereses, en pesos.
- CSV: las mismas columnas y todas las filas, con encabezado, separador coma, codificación UTF-8 e importes enteros sin separadores de miles.

Si se pide CSV, también se muestra la tabla. El archivo existente se sobrescribe; no se crean carpetas padre. La exportación se intenta antes de imprimir la tabla, de modo que un error de escritura no se anuncia como éxito. La escritura no es transaccional: un fallo durante la escritura puede dejar un archivo parcial.

## Errores y códigos de salida

- `0`: operación completada, o ayuda solicitada.
- `2`: datos fuera de rango, tasa con demasiados decimales, datos mal formados, argumentos faltantes o inválidos, o error al escribir el CSV.

Los errores se muestran en la salida estándar de errores, identificando el dato o el problema de escritura, sin traceback. `argparse` genera la ayuda y los mensajes de argumentos obligatorios o sintaxis incorrecta.

## Uso desde Python

```python
from credito_vivienda import (
    calcular_cuota,
    calcular_resumen,
    crear_credito,
    generar_tabla,
    guardar_csv,
)

credito = crear_credito("100000000", 120, "12")
cuota = calcular_cuota(credito)  # int, pesos
filas = generar_tabla(credito)  # list[Fila]
resumen = calcular_resumen(credito)  # Resumen
 guardar = None
```

Para exportar, ejecute `guardar_csv(filas, "tabla.csv")`.

`crear_credito` admite monto y tasa como texto, entero o `Decimal`; utilice texto o `Decimal` para cantidades fraccionarias, no `float`. El plazo debe ser un `int`, no un booleano. Devuelve un `Credito` inmutable con campos `monto`, `plazo` y `tasa_anual`. También puede construir `Credito` directamente con `Decimal`; su constructor realiza la misma validación.

Cada `Fila` es inmutable y contiene `mes`, `cuota`, `interes`, `abono_capital` y `saldo`, todos enteros. `Resumen` contiene `total_pagado` y `total_intereses`, también enteros. Los datos inválidos lanzan `ValueError`; `guardar_csv` propaga `OSError` si no puede escribir. `credito_vivienda.cli.main(argv)` devuelve el código de salida de la operación; en errores de sintaxis de argumentos o al pedir ayuda, `argparse` lanza `SystemExit` con el código correspondiente.

## Pruebas

Con `src/` en la ruta de importación y pytest instalado:

```sh
python -m pytest tests
```

Las pruebas cubren las tres operaciones, los datos obligatorios, los límites inclusivos y sus errores, el ejemplo proporcionado, las fórmulas, el redondeo, las relaciones mensuales de amortización, la cancelación final, el resumen, la independencia del contexto decimal y la exportación CSV. Se ejecutan sin red y escriben únicamente en directorios temporales de pytest.
