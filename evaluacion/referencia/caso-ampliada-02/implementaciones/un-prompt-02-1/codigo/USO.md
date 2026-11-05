# Reajuste del canon de arriendo

Módulo local para el analista de cartera. Valida el plazo y calcula el nuevo canon, el porcentaje aplicado y el incremento. No almacena contratos, consulta IPC, cobra cánones ni envía notificaciones. No requiere red ni servicios externos.

## Uso

Python 3.11, con `src/` en la ruta de importación:

```python
from datetime import date
from decimal import Decimal

from reajuste_arriendo import calcular_reajuste

resultado = calcular_reajuste(
    canon_actual=Decimal("1200000"),
    porcentaje_pactado=Decimal("10"),
    ipc_anterior=Decimal("5.20"),
    fecha_base=date(2023, 6, 1),
    fecha_reajuste=date(2024, 6, 1),
)

print(resultado.nuevo_canon)          # 1262400
print(resultado.porcentaje_aplicado)  # 5.20
print(resultado.incremento)           # 62400
```

Para el segundo ejemplo, canon `950000`, pactado `3` e IPC `5.20`, devuelve canon `978500`, porcentaje `3` e incremento `28500`.

## Entradas

Todos los argumentos son obligatorios:

| Argumento | Contenido |
| --- | --- |
| `canon_actual` | Importe vigente en pesos, finito y mayor que cero. |
| `porcentaje_pactado` | Porcentaje finito entre 0 y 100 inclusive, hasta dos decimales. |
| `ipc_anterior` | IPC finito del año calendario anterior al reajuste, hasta dos decimales; admite cero y negativos. |
| `fecha_base` | `datetime.date`: inicio del contrato o último reajuste, según corresponda. |
| `fecha_reajuste` | `datetime.date`: fecha efectiva propuesta para el reajuste. |

Los números pueden ser `Decimal`, `int`, `float` o texto numérico reconocido por `Decimal`, usando punto decimal y sin separadores de miles. Se recomienda `Decimal` o texto para importes exactos. Los `float` se convierten mediante su representación textual. No se aceptan booleanos, valores no finitos ni `None`. Las fechas no admiten texto ni `datetime.datetime`; pueden construirse con `date.fromisoformat(...)` antes de llamar.

El analista debe proporcionar el IPC del año correcto y la fecha base pertinente: el módulo no tiene un historial con el que comprobarlos. Para preparar una notificación anticipada, debe utilizar la fecha efectiva del reajuste, no la fecha en que redacta la notificación.

## Reglas y decisiones de los casos no definidos

1. Se exige al menos un aniversario completo desde la fecha base; se usan doce meses calendario, no 365 días. Para un inicio o reajuste el 29 de febrero, el aniversario siguiente es el 28 de febrero si ese año no es bisiesto. Una fecha anterior a la base también se rechaza.
2. Con IPC cero o negativo, se conserva exactamente el canon recibido, sin redondearlo; porcentaje e incremento son cero. El plazo y los demás datos igualmente deben ser válidos.
3. Con IPC positivo, se aplica `min(porcentaje_pactado, ipc_anterior)` y se calcula `canon_actual × (1 + porcentaje / 100)`.
4. Se redondea ese importe a la centena más cercana. Los empates se redondean hacia arriba: `1234550` pasa a `1234600`; `1234567` pasa a `1234600`.
5. El incremento es el nuevo canon ya redondeado menos el canon actual. El redondeo puede hacer que esta diferencia no coincida exactamente con el aumento porcentual sin redondear; no se añade un ajuste posterior ni se modifica el porcentaje aplicado.

No se impone que el canon de entrada sea entero, porque no se especificó esa restricción. Los ceros decimales finales de los porcentajes no cuentan como precisión adicional: `5.2000` se admite, `5.201` no. Si el pactado es cero y el IPC es positivo, se sigue la fórmula y el redondeo general; la excepción de conservar el importe sin redondeo solo corresponde al IPC no positivo.

## Salida y errores

Devuelve un `ResultadoReajuste` inmutable con tres campos `Decimal`: `nuevo_canon`, `porcentaje_aplicado` e `incremento`. Los importes están en pesos y el porcentaje en unidades porcentuales, no en fracción decimal. No cambia las entradas ni registra un reajuste.

- `ValueError`: datos inválidos, ausentes mediante `None`, o plazo insuficiente.
- Para plazo insuficiente, el mensaje exacto es: **El contrato aún no cumple doce meses desde el último reajuste**.
- `TypeError`: se omitió un argumento obligatorio en la llamada.

Si hay varios errores, se informa el primero encontrado: canon, porcentaje pactado, IPC, fechas y plazo, en ese orden.

## Pruebas

El código usa únicamente la biblioteca estándar. Las pruebas requieren el pytest del entorno:

```sh
PYTHONPATH=src python -m pytest tests/
```

Cubren ambos ejemplos, selección del porcentaje, redondeo y empates, IPC no positivo, aniversario y año bisiesto, obligatoriedad, rangos, precisión decimal, entradas inválidas y mensaje de plazo.
