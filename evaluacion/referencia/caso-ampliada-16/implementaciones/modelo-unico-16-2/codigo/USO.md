# Crédito de vivienda

Herramienta interactiva para asesores: calcula una cuota mensual fija, muestra toda la amortización y resume el total pagado y los intereses. Permite guardar la tabla en CSV. No incluye seguros, comisiones ni otros cobros. Funciona sin red, con Python 3.11 y biblioteca estándar; las pruebas requieren pytest.

## Ejecutar

Desde la carpeta que contiene `src/`:

```sh
PYTHONPATH=src python -m vivienda
PYTHONPATH=src python -m pytest tests
```

En PowerShell, establecer primero `$env:PYTHONPATH = 'src'` y ejecutar los comandos sin el prefijo `PYTHONPATH=src`.

La herramienta pregunta:

1. Monto en pesos enteros, sin puntos ni comas: `100000000`.
2. Plazo en meses enteros: `120`.
3. Tasa efectiva anual como porcentaje sin `%`: `12` o `12.50`.
4. Después de mostrar el resultado, si se quiere guardar CSV: `s` o `n`.
5. Si se pide guardar, nombre o ruta del archivo: `tabla.csv`.

## Entradas y límites

Los extremos se incluyen:

| Entrada | Límite | Formato |
| --- | --- | --- |
| Monto | 10000000 a 500000000 pesos | Dígitos, sin separadores ni decimales |
| Plazo | 12 a 240 meses | Dígitos, sin decimales |
| Tasa | 1 a 30 por ciento | Dígitos, con punto y hasta dos decimales |

Se ignoran espacios exteriores. No se admiten signos, notación científica, coma decimal ni `%`. Como decisión simple de formato, se admiten hasta 9 caracteres para el monto, 3 para el plazo y 5 para la tasa; no se admite rellenar con ceros hasta exceder esas longitudes.

## Cálculo y redondeo pendiente de aprobación

Con `a = tasa_anual / 100`, `r = (1 + a) ** (1 / 12) - 1`, capital `P` y plazo `n`, la cuota antes de redondear es:

```text
P * r / (1 - (1 + r) ** (-n))
```

**El cliente no definió ni aprobó un criterio preciso de redondeo.** Para entregar un módulo ejecutable se aplica provisionalmente la opción estándar de Decimal: al peso más cercano, con los empates exactos al entero par (`ROUND_HALF_EVEN`). Esta es una decisión de implementación pendiente de validación de negocio, no un acuerdo con el cliente ni una afirmación de que sea su política financiera. La terminal también advierte esta situación.

Se utilizan 50 cifras significativas para tasas y fórmula, sin aritmética binaria de coma flotante. La raíz mensual se aproxima a esa precisión; no se presenta como una raíz matemáticamente exacta.

Se redondea la cuota fija una vez y el interés sobre el saldo de cada mes. Después, con enteros:

- Abono a capital = cuota − interés.
- Saldo nuevo = saldo anterior − abono a capital.
- En el último mes, cuota = saldo anterior + interés; así el saldo queda exactamente en cero.

Este uso del redondeo mes a mes también es provisional. Garantiza que las filas y los totales cuadren en pesos enteros. Los totales son las sumas de las filas, no la cuota fija multiplicada por el plazo.

El ejemplo aportado queda reproducido: para `100000000`, `120`, `12`, la cuota fija es `1399472`; el primer interés es `948879`, el abono `450593` y el saldo `99549407`. El cliente no aportó totales finales de referencia; las pruebas verifican su consistencia, sin atribuirle cifras finales no suministradas.

## Salidas y CSV

La pantalla muestra cuota fija, advertencia de ajuste final, todas las filas y los dos totales. Columnas acordadas: mes, cuota, interés, abono a capital y saldo. Todos los importes se muestran como enteros sin separadores de miles.

Decisiones simples para la exportación y su solicitud:

- Se pregunta después de mostrar la tabla; `s`, `si` o `sí` aceptan, sin distinguir mayúsculas. `n`, `no` o Enter omiten la exportación.
- CSV UTF-8, separado por comas, con encabezado `mes,cuota,interes,abono_capital,saldo`.
- Una fila por mes, sin filas adicionales de resumen.
- Se solicita una ruta; las rutas relativas parten del directorio actual.
- El archivo existente se reemplaza y no se crean directorios. Conviene elegir un nombre nuevo para conservar otros archivos.
- El guardado no es atómico: si ocurre un fallo durante la escritura podría quedar un archivo parcial.

## Errores

Éxito: código de salida `0`. Error: código `1`, con mensaje en la salida de errores.

- Fuera de rango: `Monto fuera de rango: debe estar entre 10000000 y 500000000 pesos.`, o el mensaje equivalente para plazo y tasa.
- Formato incorrecto: mensaje específico indicando cómo ingresar el dato.
- Fallo del CSV, incluida ruta vacía: exactamente `No se pudo guardar el CSV`. La tabla y el resumen ya mostrados permanecen en pantalla; termina con error y no vuelve a intentar, conforme a lo acordado.
- Respuesta inválida a la solicitud de CSV: mensaje indicando usar `s` o `n`, y termina con error.
- Fin prematuro de la entrada: `Entrada incompleta: no se recibieron todos los datos.`
- Interrupción por teclado: `Operación cancelada.`

Como decisión simple de interacción, los datos se solicitan una vez y se validan al recibir los tres; no se repregunta ante errores.

## Uso desde Python

Con `src/` en la ruta de importación:

```python
from vivienda import calcular, guardar_csv

resultado = calcular('100000000', '120', '12')
print(resultado.cuota_mensual)
print(resultado.tabla[0])
print(resultado.total_pagado, resultado.total_intereses)
guardar_csv(resultado, 'tabla.csv')
```

`calcular` recibe tres cadenas, valida las entradas y devuelve un `Resultado` inmutable. `tasa_mensual` es un Decimal expresado como fracción, no porcentaje. `tabla` es una tupla de `Cuota`, con atributos `mes`, `cuota`, `interes`, `abono_capital` y `saldo`. Entradas inválidas producen `ValueError`.

`guardar_csv` acepta una cadena o `pathlib.Path`. Propaga los errores de escritura; la terminal los convierte en el mensaje acordado. No se incluyen fechas de pago, pagos extraordinarios, tasas variables ni otros cobros.
