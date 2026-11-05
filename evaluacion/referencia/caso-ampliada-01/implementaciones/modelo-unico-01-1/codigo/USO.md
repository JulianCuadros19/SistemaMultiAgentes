# Comisiones inmobiliarias

Módulo Python 3.11 para que la auxiliar de pagos calcule y explique la comisión de cada negocio cerrado. Funciona sin red y el código utiliza únicamente la biblioteca estándar.

## Uso

Con `src/` en la ruta de importación:

```python
from comisiones import calcular_comisiones

resultado = calcular_comisiones(
    tipo="venta",
    valor=300_000_000,
    numero_asesores=1,
    estado="cerrado",
)
print(resultado.comision_inmobiliaria)  # 9000000
print(resultado.comisiones_asesores)    # (3600000,)
```

Desde la raíz del proyecto, las pruebas se ejecutan con:

```sh
PYTHONPATH=src python -m pytest tests
```

## Entradas

Todos los argumentos se pasan por nombre y son obligatorios para el cálculo:

| Argumento | Valores aceptados |
| --- | --- |
| `tipo` | `"venta"` o `"arriendo"`, exactamente en minúsculas |
| `valor` | Entero Python positivo, en pesos colombianos, sin centavos. Precio total para venta; primer canon mensual para arriendo |
| `numero_asesores` | Entero Python `1` o `2` |
| `estado` | `"cerrado"` o `"abierto"` |

No se convierten cadenas ni números decimales a enteros. Tampoco se aceptan booleanos como importes o cantidades. No se definió un máximo para el valor: no se impone un tope de negocio y se usa aritmética entera exacta, sujeta a los recursos disponibles.

## Reglas y salida

- Venta: comisión bruta de la inmobiliaria = valor × 3 %.
- Arriendo: comisión bruta de la inmobiliaria = primer canon mensual completo.
- Parte calculada de cada asesor = comisión bruta × 40 % ÷ número de asesores.
- Cada asesor recibe al menos 300.000 pesos por negocio, incluso cuando la suma de los pagos supera el 40 % o la propia comisión de la inmobiliaria.
- Solo se calcula un negocio cerrado.

La función devuelve un `ResultadoComisiones` inmutable con:

- `comision_inmobiliaria`: entero en COP, comisión **bruta**, no el saldo tras pagar a los asesores.
- `comisiones_asesores`: tupla con uno o dos enteros en COP. Cada posición representa un asesor; no se reciben nombres ni identificadores. Los pagos son iguales.

Los resultados no tienen decimales. Para explicar el pago se pueden mostrar las fórmulas anteriores junto con las entradas y los importes finales; el módulo no genera un informe adicional.

### Ejemplos confirmados

| Negocio | Asesores | Comisión inmobiliaria | Pago por asesor |
| --- | --- | --- | --- |
| Venta de 300.000.000 | 1 | 9.000.000 | 3.600.000 |
| Arriendo de 1.000.000 | 2 | 1.000.000 | 300.000 |

En el segundo ejemplo, el reparto inicial da 200.000 por asesor, pero el mínimo eleva cada pago a 300.000.

## Decisiones sobre puntos no definidos por el cliente

Estas son decisiones de implementación, **no reglas confirmadas por el cliente**:

1. **Datos omitidos:** omitir un argumento o pasar `None` produce `ValueError` con `Falta el dato obligatorio: <nombre>`. Si faltan varios, se informa el primero en el orden `tipo`, `valor`, `numero_asesores`, `estado`.
2. **Empate de medio peso:** se redondea hacia arriba; por ejemplo, 300.001,50 se convierte en 300.002. En los demás casos se redondea al peso más cercano.
3. **Base para el asesor:** se usa la comisión de la inmobiliaria **antes de redondear**. Ambos resultados se redondean por separado, sin cálculos intermedios con coma flotante. Por ejemplo, una venta de 25.000.042 genera una comisión exacta de 750.001,26, que se muestra como 750.001; el asesor recibe 300.001 porque su parte exacta es 300.000,504.

También se eligieron mensajes simples para los demás datos inválidos, que no estaban especificados. El mínimo se aplica al pago individual; redondearlo y compararlo con el mínimo entero produce el mismo resultado que comparar primero el importe exacto. No se ajustan diferencias de redondeo entre asesores.

## Errores

Todos los rechazos usan `ValueError`:

| Situación | Mensaje |
| --- | --- |
| Dato omitido o `None` | `Falta el dato obligatorio: <nombre>` |
| Tipo no permitido | `El tipo de negocio debe ser venta o arriendo` |
| Valor cero, negativo o no entero | `El valor debe ser un entero mayor que cero, en pesos colombianos` |
| Número de asesores inválido | `El número de asesores debe ser 1 o 2` |
| Estado no permitido | `El estado debe ser cerrado o abierto` |
| Negocio abierto con datos válidos | `El negocio aún no está cerrado` |

Se comprueba primero que estén todos los datos; luego se validan tipo, valor, número de asesores y estado, en ese orden; finalmente se rechaza el negocio abierto. Esta prioridad para errores simultáneos es una decisión de implementación.

```python
try:
    calcular_comisiones(
        tipo="arriendo", valor=1_000_000, numero_asesores=2, estado="abierto"
    )
except ValueError as error:
    print(str(error))  # El negocio aún no está cerrado
```

## Fuera del alcance

No incluye lectura de planillas, interfaz gráfica, ejecución de pagos, almacenamiento, identificación de asesores ni acumulados mensuales. La integración debe invocar la función por cada negocio. No se añaden impuestos, descuentos ni otras condiciones de pago.
