# Reajuste de arriendos

Módulo para que el analista de cartera calcule el reajuste de un contrato. Funciona con Python 3.11 y la biblioteca estándar, sin red. Las pruebas requieren pytest.

## Uso

Con `src/` en la ruta de importación:

```python
from reajuste_arriendo import ErrorReajuste, calcular_reajuste

try:
    resultado = calcular_reajuste(
        canon_actual="1200000",
        porcentaje_pactado="10",
        ipc_anterior="5.20",
        fecha_referencia="2024-06-15",
        fecha_reajuste="2025-06-15",
    )
except ErrorReajuste as error:
    print(str(error))
else:
    print(resultado.porcentaje_aplicado)  # 5.20
    print(format(resultado.nuevo_canon, "f"))  # 1262400
    print(format(resultado.incremento, "f"))  # 62400
```

Ejecutar las pruebas desde la raíz:

```sh
PYTHONPATH=src python -m pytest tests
```

## Entradas obligatorias

| Nombre | Contenido |
| --- | --- |
| `canon_actual` | Valor en pesos, mayor que cero. |
| `porcentaje_pactado` | Porcentaje entre 0 y 100 inclusive, con hasta dos decimales. |
| `ipc_anterior` | IPC del año calendario anterior, con hasta dos decimales. Puede ser cero o negativo; no se impone un máximo. |
| `fecha_referencia` | Fecha de inicio o del último reajuste, según corresponda. |
| `fecha_reajuste` | Fecha para la que se calcula el reajuste. |

Los números se reciben como `int`, `Decimal` o texto decimal sin separadores de miles, con punto decimal. Por ejemplo, `"1200000"` y `"5.20"`. Los porcentajes se expresan en unidades porcentuales: `5.20` significa 5,20 %, no 520 %. Se permiten espacios exteriores, notación científica y ceros decimales finales; `"5.2000"` equivale a `"5.20"`. Se rechazan `float`, booleanos, valores no finitos y otros tipos.

Las fechas se reciben como `datetime.date` o texto exactamente `AAAA-MM-DD`, entre los años 0001 y 9999. No se aceptan horas ni objetos `datetime.datetime`.

## Reglas y salida

1. Debe haber transcurrido al menos un año calendario desde la fecha de referencia. Se acepta el aniversario o una fecha posterior; no se exige que sea exactamente el día del aniversario.
2. Si el IPC es cero o negativo, o el porcentaje pactado es cero, el porcentaje aplicado y el incremento son cero y el canon se conserva **sin redondearlo**.
3. En otro caso, se aplica el menor de los dos porcentajes.
4. Se calcula `canon_actual × (1 + porcentaje_aplicado / 100)` y se redondea el nuevo canon a la centena más cercana.
5. El incremento es `nuevo_canon − canon_actual`.

Se devuelve un `ResultadoReajuste` inmutable con tres campos `Decimal`: `porcentaje_aplicado`, `nuevo_canon` e `incremento`. El porcentaje es el elegido antes del redondeo, no la variación efectiva del canon redondeado. Los importes no contienen símbolos de moneda ni separadores de miles. Para mostrarlos sin notación científica puede usarse `format(valor, "f")`.

Ejemplos acordados:

- Canon 1.200.000, pactado 10 %, IPC 5,20 %: porcentaje 5,20 %, canon 1.262.400, incremento 62.400.
- Canon 1.001, IPC 5,20 % y pactado al menos 5,20 %: canon 1.100 e incremento 99.

No se limita nuevamente el importe después del redondeo, aunque supere el aumento porcentual pactado. Tampoco se impide una disminución causada por el redondeo de un aumento pequeño: con canon 1.001 y ambos porcentajes de 0,01 %, el nuevo canon es 1.000 y el incremento es −1.

## Errores

Todos los rechazos de validación se comunican mediante `ErrorReajuste`, que hereda de `ValueError`.

| Situación | Mensaje |
| --- | --- |
| No han pasado doce meses, incluso si no habría aumento | `El contrato aún no cumple doce meses desde el último reajuste` |
| Dato omitido o `None` | `Falta el dato obligatorio: <nombre>` |
| Número o fecha inválidos, tipo no admitido o valor no finito | `Dato inválido: <nombre>` |
| Canon cero o negativo | `El canon actual debe ser mayor que cero` |
| Pactado fuera de rango | `El porcentaje pactado debe estar entre 0 y 100` |
| Porcentaje con más de dos decimales significativos después del punto | `El <nombre> debe tener como máximo dos decimales` |

`<nombre>` es el nombre del argumento. Si hay varios errores, se informa el primero: canon y su positividad, pactado y sus restricciones, IPC, fecha de referencia, fecha de reajuste y plazo, en ese orden.

## Decisiones sobre aspectos no definidos

Estas decisiones son de implementación, no reglas adicionales confirmadas por el cliente:

- Se ofrece una función para un contrato; no se añade un formato de archivos ni procesamiento por lotes.
- Se eligen los formatos y los mensajes descritos arriba. El único mensaje establecido por el cliente es el rechazo por plazo insuficiente.
- Se admite canon fraccionario porque solo se exigió que fuera positivo. En ese caso el incremento puede tener fracciones de peso. No hay un máximo monetario contractual; el cálculo usa precisión decimal ajustada a las entradas, sujeto a los recursos de Python.
- Un empate entre centenas se resuelve hacia arriba: 1.250 se convierte en 1.300.
- Para una referencia del 29 de febrero, el aniversario del año siguiente es el 28 de febrero. Una referencia del año 9999 nunca puede cumplir doce meses dentro del intervalo de fechas admitido y se rechaza con el mensaje de plazo.

## Fuera del alcance

No consulta ni verifica la procedencia del IPC: quien llama debe entregar el correspondiente al año calendario anterior a la fecha del reajuste. Tampoco selecciona entre inicio y último reajuste; quien llama proporciona la referencia correcta. No actualiza cobros ni contratos, almacena datos, genera documentos o acumula reajustes de años omitidos. Aunque hayan pasado varios años, cada llamada calcula un único reajuste con los datos suministrados.
