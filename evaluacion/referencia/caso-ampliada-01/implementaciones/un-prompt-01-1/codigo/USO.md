# Comisiones por negocio cerrado

Módulo Python 3.11 para que la auxiliar de pagos liquide cada negocio durante el cierre mensual. Devuelve la comisión de la inmobiliaria y la de cada asesor. No necesita red ni dependencias externas para el cálculo.

## Uso

Con `src/` en la ruta de importación:

```python
from comisiones import calcular_comisiones

resultado = calcular_comisiones(
    tipo_negocio="venta",
    valor=300_000_000,
    numero_asesores=1,
    estado="cerrado",
)
print(resultado.comision_inmobiliaria)  # 9000000
print(resultado.comisiones_asesores)   # (3600000,)

resultado = calcular_comisiones(
    tipo_negocio="arriendo",
    valor=1_000_000,
    numero_asesores=2,
    estado="cerrado",
)
print(resultado.comision_inmobiliaria)  # 1000000
print(resultado.comisiones_asesores)   # (300000, 300000)
```

## Entradas

Los cuatro argumentos son obligatorios y se pasan por nombre:

| Argumento | Valores admitidos |
| --- | --- |
| `tipo_negocio` | `"venta"` o `"arriendo"` |
| `valor` | Precio de venta o primer canon mensual en pesos, finito y mayor que cero |
| `numero_asesores` | Entero `1` o `2`; no acepta booleanos ni `1.0` |
| `estado` | `"cerrado"` o `"abierto"`; abierto se rechaza |

`valor` admite `int`, `Decimal`, `float` o texto numérico decimal. Para conservar exactamente un importe con fracciones, se recomienda `Decimal` o texto, por ejemplo `Decimal("1000000.50")`. Los textos no deben contener separadores de miles ni símbolos monetarios: use `"1000000.50"`, no `"1.000.000,50"`. Los `float` se interpretan mediante su representación decimal `str(valor)`; el módulo no recupera precisión que se haya perdido antes de la llamada.

## Cálculo y explicación

1. Se exige un negocio cerrado: escritura firmada para venta o contrato firmado para arriendo.
2. Comisión inmobiliaria sin redondear:
   - Venta: `valor × 3 / 100`.
   - Arriendo: `valor` (100 % del primer canon mensual).
3. Participación conjunta de asesores: `comisión inmobiliaria × 40 / 100`.
4. Participación individual: dividir esa participación entre el número de asesores.
5. Aplicar a cada asesor el máximo entre su participación y 300.000 pesos.
6. Redondear la comisión inmobiliaria y cada comisión individual al peso más cercano.

En el arriendo del ejemplo, el 40 % es 400.000 y la división entre dos da 200.000. Por el mínimo individual, se pagan 300.000 a cada uno. El mínimo puede hacer que el total de los asesores supere el 40 %; no se reduce ni se impone un tope adicional.

## Salida

`ResultadoComisiones` es una clase de datos inmutable con:

- `comision_inmobiliaria: int`.
- `comisiones_asesores: tuple[int, ...]`: uno o dos importes iguales, uno por asesor.

Todos los importes finales son pesos colombianos enteros. La comisión inmobiliaria no se reduce por lo pagado a los asesores: es el importe del 3 % o del primer canon, no un saldo neto.

## Errores

Una entrada inválida genera `ValueError`:

| Situación | Mensaje |
| --- | --- |
| Negocio abierto | `El negocio aún no está cerrado` |
| Tipo inválido | `El tipo de negocio debe ser venta o arriendo` |
| Estado inválido | `El estado debe ser cerrado o abierto` |
| Valor inválido, cero, negativo o no finito | `El valor debe ser numérico, finito y mayor que cero` |
| Número de asesores distinto de los enteros 1 y 2 | `El número de asesores debe ser 1 o 2` |

Si falta un argumento obligatorio, Python genera `TypeError`. No se devuelve una liquidación parcial en caso de error.

## Decisiones para detalles no definidos

- Los empates de medio peso se redondean hacia arriba: 400.000,50 produce 400.001.
- No se redondea ningún resultado intermedio. Se usa aritmética racional exacta, independiente de la precisión global de `Decimal`.
- Se redondea cada asesor independientemente, sin ajustes posteriores para compensar diferencias en la suma.
- Los nombres de tipo y estado deben coincidir exactamente con los indicados, en minúsculas.
- Si hay varios datos inválidos, se informa el primero: tipo, estado, negocio abierto, número de asesores y valor, en ese orden.
- La auxiliar es responsable de marcar `cerrado` cuando se haya firmado el documento correspondiente; no se inspeccionan documentos.
- Se calcula un negocio por llamada. La tupla representa posiciones de asesores; no se requieren identificadores. El proceso mensual puede repetir las llamadas para sus negocios.

No se incluyen nómina, retenciones, impuestos, almacenamiento, interfaz gráfica, servicios web ni filtros de fechas.

## Pruebas

Con `src/` en la ruta de importación, ejecute:

```bash
python -m pytest tests/
```

Si su entorno aún no configura esa ruta, en una terminal POSIX puede ejecutar:

```bash
PYTHONPATH=src python -m pytest tests/
```

Las pruebas cubren los dos ejemplos, porcentajes, reparto, mínimos individuales, redondeos, obligatoriedad de cada entrada, negocios abiertos y datos inválidos. Solo requieren pytest y no usan red.
