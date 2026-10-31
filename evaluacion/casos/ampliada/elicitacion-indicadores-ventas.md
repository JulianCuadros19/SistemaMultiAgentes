---
id: caso-ampliada-09
titulo: Indicadores comerciales mensuales desde Excel
cliente: Distribuidora Café de la Montaña (sintética)
proyecto: Indicadores comerciales mensuales
necesidad: Cada mes recibimos un archivo Excel con las ventas de todos los asesores y debemos producir otro Excel con los indicadores por región; es un proceso por lotes que hoy nos toma dos días.
version: 1.0
arquitecturas_esperadas: [ARQ-03]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la coordinadora comercial de una distribuidora de café. Conoces las ventas y las metas,
pero no tienes formación técnica.

## Lo que sabes

- Quien prepara los indicadores es la coordinadora comercial, una vez al mes.
- Lo necesitan para la reunión mensual de resultados con la gerencia.
- Archivo de entrada: un libro de Excel (.xlsx) con una hoja `ventas` y las columnas `fecha`,
  `asesor`, `region`, `producto`, `cantidad` y `valor_unitario`.
- Reglas:
  - el valor de una venta es la cantidad por el valor unitario, en pesos sin decimales;
  - las filas con cantidad cero o negativa, o con la región vacía, se excluyen y se cuentan
    como descartadas, con su motivo;
  - por cada región se calcula:
    - el total vendido y el número de ventas;
    - el ticket promedio, que es el total entre el número de ventas, redondeado al peso;
    - el asesor con mayor venta total;
    - el cumplimiento de la meta, que es de 50.000.000 pesos por región, en porcentaje con un
      decimal.
- Lo que debe entregar: un libro de Excel con una hoja `indicadores`, con una fila por región, y
  una hoja `descartadas`, con las filas excluidas y su motivo.
- Ejemplo que usan para verificar: la región Norte con dos ventas, 10 unidades a 2.000.000 y 5
  unidades a 4.000.000, tiene un total de 40.000.000, 2 ventas, un ticket promedio de
  20.000.000 y un cumplimiento del 80,0 %.
- Caso de error: si falta la hoja `ventas` o alguna de las columnas, el proceso se detiene
  indicando qué falta.
- Restricción importante: el proceso tiene etapas (lectura, validación, cálculo y escritura). Si
  falla la escritura, no quieren repetir las anteriores.
- Es de prioridad media.

## Lo que no sabes

No sabes cómo se liquidan las comisiones de los asesores ni cómo se fijan las metas: no son parte
de este proceso. No conoces detalles técnicos del sistema.
