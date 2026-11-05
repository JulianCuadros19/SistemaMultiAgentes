# Calculadora de crédito de vivienda

Herramienta para que un asesor consulte desde su terminal la cuota mensual, la amortización completa o un resumen con total pagado y total de intereses. Permite exportar la tabla a CSV. No incluye seguros, comisiones ni abonos adicionales.

## Entorno y ejecución

Requiere Python 3.11. El módulo usa exclusivamente la biblioteca estándar; las pruebas requieren pytest. No necesita red, base de datos ni servicios externos.

Desde la carpeta de la entrega, en una terminal POSIX:

```sh
export PYTHONPATH=src
python -m vivienda cuota --monto 100000000 --plazo 120 --tasa 12
python -m vivienda tabla --monto 100000000 --plazo 120 --tasa 12
python -m vivienda tabla --monto 100000000 --plazo 120 --tasa 12 --csv tabla.csv
python -m vivienda resumen --monto 100000000 --plazo 120 --tasa 12
python -m vivienda --help
python -m pytest tests
```

En PowerShell, sustituya `export PYTHONPATH=src` por `$env:PYTHONPATH = "src"`.

Los datos se ingresan como argumentos, no mediante preguntas interactivas. Cada comando consulta una opción por separado. `--csv` solo está disponible con `tabla`; al exportar también se muestra la tabla en pantalla.

## Entradas

| Argumento | Formato | Límites inclusivos |
| --- | --- | --- |
| `--monto` | Pesos enteros, sin centavos ni separadores de miles | 10000000 a 500000000 |
| `--plazo` | Meses enteros | 12 a 240 |
| `--tasa` | Porcentaje efectivo anual, con hasta dos decimales | 1 a 30 |
| `--csv` | Ruta del archivo, solo para `tabla` | Opcional |

Ejemplos válidos de tasa: `12`, `12.5`, `12.50`. Se utiliza punto decimal, no coma, y no se escribe el símbolo `%`. La tasa `12` significa 12 %, no una tasa fraccionaria de 12. Los enteros no aceptan punto decimal, incluso si sus decimales son cero. Se rechazan notación científica, valores no finitos y separadores de miles. Se permiten espacios exteriores en los valores.

## Cálculos

Con `P` como monto, `n` como plazo y `a` como tasa anual porcentual:

```text
r = (1 + a / 100)^(1 / 12) - 1
cuota = P * r / (1 - (1 + r)^(-n))
interés del mes = saldo anterior * r
capital del mes = cuota del mes - interés del mes
saldo del mes = saldo anterior - capital del mes
```

La última cuota es el saldo pendiente más el interés de ese mes; el saldo final es cero. Los cálculos utilizan `Decimal`, nunca `float`, con 60 dígitos de precisión interna. La tasa mensual, que en general es irracional, se aproxima con esa precisión; no se afirma que sea una representación matemática exacta.

### Decisiones sobre aspectos no definidos

El cliente confirmó que estos detalles seguían sin definir. Las siguientes son decisiones de implementación, **no acuerdos adicionales con el cliente**:

- Los medios pesos se redondean hacia arriba (`ROUND_HALF_UP` para importes positivos).
- Se redondea primero la cuota fija al peso. Cada mes se redondea el interés al peso y se calculan capital y saldo con esos enteros. No se conservan centavos ocultos en los saldos.
- El resumen suma las cuotas de la tabla, incluida la última ajustada, y suma los intereses de los mismos meses. Por tanto, total pagado = monto + total de intereses.
- La tabla en pantalla tiene columnas separadas por tabuladores, en este orden: `mes`, `cuota`, `interes`, `capital`, `saldo`. No se agrega una columna de saldo inicial: el monto ingresado es el saldo anterior al mes 1.
- El CSV usa las mismas columnas, encabezado, coma como separador y codificación UTF-8. Los importes son enteros sin símbolos monetarios ni separadores de miles.
- La exportación sobrescribe el archivo de destino si existe. No crea carpetas faltantes. Es una escritura directa, no una operación atómica; un fallo durante la escritura puede dejar un archivo parcial.
- La interfaz usa comandos y argumentos, sin un menú interactivo.

## Salidas y ejemplo de verificación

Para 100000000 pesos, 120 meses y 12 % efectivo anual:

```text
Cuota mensual: 1399472 pesos
```

La primera fila de la amortización es:

| mes | cuota | interes | capital | saldo |
| --- | --- | --- | --- | --- |
| 1 | 1399472 | 948879 | 450593 | 99549407 |

La tabla contiene exactamente 120 filas de datos y termina con saldo cero. La cuota de la última fila puede diferir de la cuota fija. El resumen imprime dos líneas etiquetadas: `Total pagado` y `Total de intereses`, en pesos enteros.

## Uso desde Python

Con `src/` en la ruta de importación:

```python
from vivienda import amortizacion, crear_credito, cuota_mensual, resumen

credito = crear_credito("100000000", "120", "12")
cuota = cuota_mensual(credito)     # int: 1399472
filas = amortizacion(credito)     # tuple de FilaAmortizacion
primera = filas[0]                # mes, cuota, interes, capital, saldo
final = filas[-1].saldo           # int: 0
totales = resumen(credito)        # Resumen: total_pagado, total_intereses
```

`crear_credito` acepta monto y plazo como cadenas o enteros; la tasa puede ser cadena, entero o `Decimal`. No acepta `float` ni booleanos. También se valida la construcción directa de `Credito`. Los objetos de crédito, filas y resumen son dataclasses inmutables. `tasa_mensual(credito)` devuelve una tasa fraccionaria `Decimal`.

## Errores

- Datos inválidos: mensaje claro en stderr y código de salida **1**. Ejemplo: `Error: Monto: ingrese un entero entre 10000000 y 500000000, sin decimales ni separadores de miles.`
- Plazo inválido: mensaje que indica entero entre 12 y 240.
- Tasa inválida: mensaje que indica porcentaje entre 1 y 30, hasta dos decimales y punto decimal.
- Fallos al guardar el CSV o mostrar el resultado: mensaje `Error al mostrar o guardar el resultado: ...` y código **1**. El detalle final proviene del sistema operativo.
- Fallos de aritmética decimal: mensaje `Error en el cálculo decimal: ...` y código **1**.
- Argumentos faltantes, comando desconocido u opción no admitida: ayuda de uso y diagnóstico en stderr, código **2**.
- Consulta correcta o ayuda: código **0**.

La validación ocurre antes de calcular, mostrar o abrir el CSV. Desde Python, los errores de entrada se notifican mediante `EntradaInvalida`, una subclase de `ValueError`.

## Pruebas incluidas

Cubren el ejemplo proporcionado, conversión de tasa, fórmula de cuota, reglas mensuales, tabla completa, ajuste final, resumen, extremos inclusivos de los rangos, tasa con dos decimales, importes sin centavos, decisiones de redondeo, independencia de la precisión externa, datos inválidos, opciones separadas, formato y contenido del CSV, sobrescritura, errores de archivo, ayuda y códigos de salida. Se ejecutan sin red.
