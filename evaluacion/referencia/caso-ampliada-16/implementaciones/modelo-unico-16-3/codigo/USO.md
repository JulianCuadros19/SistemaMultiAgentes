# Crédito de vivienda

## Estado de la entrega

Esta entrega implementa la interfaz de terminal, las tres operaciones independientes y la validación de datos. **No emite cuotas, tablas, resúmenes ni CSV financieros:** el cliente confirmó que las reglas de redondeo siguen pendientes y rechazó conservar la precisión de la tasa mensual o redondear los medios pesos hacia arriba como solución alternativa.

Por tanto, no es todavía una calculadora operativa. Entregar cifras supondría aplicar una regla expresamente no autorizada. Las operaciones informan esta limitación, sin devolver cero, resultados aproximados ni el ejemplo esperado como una constante.

## Reglas confirmadas

- Monto entre 10000000 y 500000000 pesos, inclusive.
- Plazo entre 12 y 240 meses, inclusive. No se confirmó que deba ser entero.
- Tasa efectiva anual entre 1 y 30 por ciento, inclusive, con hasta dos decimales.
- Cuota, tabla y resumen son operaciones separadas.
- El CSV corresponde únicamente a la tabla y se solicita expresamente.
- Los datos fuera de rango deben rechazarse con mensaje claro y código de salida distinto de cero.
- No se incluyen seguros, comisiones ni otros cargos.

Las fórmulas indicadas por el cliente, todavía no ejecutables con un redondeo autorizado, son:

```text
a = porcentaje anual / 100
r = (1 + a) ** (1 / 12) - 1
cuota = monto * r / (1 - (1 + r) ** (-plazo))
interés del mes = saldo anterior * r
abono a capital = cuota del mes - interés del mes
saldo del mes = saldo anterior - abono a capital
```

Los importes deben redondearse al peso y la última cuota ajustarse para dejar saldo cero. También se pidió redondear la tasa mensual, pero no se definió cómo hacerlo sin anularla. No se ha definido el tratamiento de los medios pesos. El módulo no usa `float`, no redondea durante la lectura y no sustituye estas decisiones.

### Ejemplo de aceptación pendiente

Monto 100000000, plazo 120 meses, tasa efectiva anual 12 %, cuota esperada **1399472 pesos**. La entrada se valida correctamente, pero la operación termina con código 3. No se afirma haber verificado esa cuota: falta una regla autorizada que permita calcularla. Las pruebas verifican explícitamente que no se inventa un resultado para este caso.

El crédito de 1200000 pesos mencionado durante la aclaración del redondeo queda fuera del mínimo finalmente confirmado; no se trata como un segundo ejemplo válido de cálculo.

## Ejecución

Requiere Python 3.11. El código utiliza solamente la biblioteca estándar. Las pruebas requieren pytest. No se accede a la red.

Con `src/` en la ruta de importación:

```bash
export PYTHONPATH=src
python -m credito_vivienda --help
python -m credito_vivienda cuota --monto 100000000 --plazo 120 --tasa-anual 12
python -m credito_vivienda tabla --monto 100000000 --plazo 120 --tasa-anual 12
python -m credito_vivienda resumen --monto 100000000 --plazo 120 --tasa-anual 12
python -m credito_vivienda tabla --monto 100000000 --plazo 120 --tasa-anual 12 --csv tabla.csv
```

Cada comando con entradas válidas termina actualmente con código 3 y un mensaje de reglas pendientes en la salida de errores. No imprime resultados financieros. La solicitud de CSV no crea archivos ni modifica archivos existentes.

## Entradas y decisiones mínimas para aspectos no definidos

Estas son decisiones de implementación, no reglas financieras confirmadas:

- Se usan subcomandos `cuota`, `tabla` y `resumen`, con opciones obligatorias `--monto`, `--plazo` y `--tasa-anual`.
- Los números se escriben sin separadores de miles y con punto decimal opcional: `100000000`, `120.5`, `12.25`. Se permiten signo inicial y espacios exteriores. No se admiten coma decimal, notación científica, guiones bajos, símbolos monetarios ni el símbolo `%`.
- La tasa se ingresa como porcentaje: `12` significa 12 %, no 0.12 %.
- Se cuentan los decimales escritos de la tasa; `12.00` se admite y `12.000` se rechaza. No se redondean tasas con más de dos decimales.
- Las fracciones de monto y plazo se conservan en la validación, porque no se especificó su rechazo. Esto no autoriza amortizar fracciones de mes: antes de habilitar la tabla deberá aclararse ese caso.
- Las entradas no numéricas se rechazan con mensaje claro y código 2, sin preguntar de nuevo. El asesor puede volver a ejecutar el comando con el dato corregido.
- `--csv RUTA` solo existe en `tabla`; el asesor elige el nombre. No se define un nombre automático.
- Se adopta el bloqueo con código 3 como comportamiento conservador de esta entrega mientras faltan reglas. El cliente no confirmó ese comportamiento como regla de negocio; es una limitación explícita, no una autorización obtenida.

No se fijan columnas ni formatos de una tabla ficticia: todavía no hay resultados exportables. Las columnas y los formatos del CSV y de las salidas financieras siguen pendientes.

## Salidas y errores

| Situación | Salida | Código |
| --- | --- | --- |
| Ayuda | Uso del comando en salida estándar | 0 |
| Argumentos ausentes o desconocidos | Mensaje de argparse en salida de errores | 2 |
| Dato no numérico o formato no admitido | Mensaje que identifica el campo | 2 |
| Valor fuera de rango | Campo, límites y unidad | 2 |
| Tasa con más de dos decimales | Mensaje de precisión admitida | 2 |
| Datos válidos, reglas pendientes | Mensaje de redondeo pendiente, sin resultados ni CSV | 3 |

Ejemplo de error de rango:

```text
Error: Monto: debe estar entre 10000000 y 500000000 pesos, inclusive.
```

Ejemplo de bloqueo:

```text
Error: Reglas de redondeo pendientes de definir: redondeo de la tasa mensual y tratamiento de los medios pesos. No se ha autorizado una regla alternativa; no se emiten resultados financieros ni archivos CSV.
```

## Uso desde Python

```python
from credito_vivienda import ReglasPendientes, calcular_cuota, leer_solicitud

solicitud = leer_solicitud("100000000", "120", "12")
try:
    calcular_cuota(solicitud)
except ReglasPendientes as error:
    print(error)
```

`leer_solicitud` devuelve una `Solicitud` inmutable con campos `Decimal`: `monto`, `plazo` y `tasa_anual`. También puede construirse directamente con valores `Decimal`; no se aceptan flotantes binarios.

`DatoInvalido` representa errores de entrada. `calcular_cuota`, `generar_tabla` y `calcular_resumen` son operaciones independientes y actualmente siempre lanzan `ReglasPendientes` para solicitudes válidas. Su retorno se anota como `Never` para hacer explícito que no hay resultados financieros disponibles en esta versión.

## Pruebas y limitaciones de verificación

```bash
PYTHONPATH=src python -m pytest tests
```

Las pruebas cubren límites inclusivos, rechazo de cada rango, precisión de la tasa, entradas no numéricas, conservación decimal, plazo no entero, operaciones separadas, ejemplo aprobado bloqueado, códigos de salida, ayuda y ausencia de creación o modificación de CSV.

No se pueden verificar cuotas numéricas, amortización mensual, ajuste final a cero ni totales sin elegir un redondeo no autorizado. Esos criterios permanecen pendientes, al igual que la salida real del CSV. No se presentan pruebas de bloqueo como pruebas de corrección financiera.

Para habilitar los cálculos se necesita definir el redondeo de la tasa mensual y de los medios pesos, confirmar el ejemplo con esas reglas y resolver cómo se tratarían plazos fraccionarios al generar la tabla. No se ofrecen opciones para que el asesor elija reglas financieras por atención, pues esa posibilidad tampoco fue autorizada.
