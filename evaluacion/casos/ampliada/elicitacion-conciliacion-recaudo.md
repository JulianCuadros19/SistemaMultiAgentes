---
id: caso-ampliada-07
titulo: Conciliación diaria del recaudo de tres bancos
cliente: Empresa de Servicios Públicos del Norte (sintética)
proyecto: Conciliación de recaudo
necesidad: Cada día llegan archivos CSV con los pagos de tres bancos y debemos conciliarlos contra las facturas emitidas para saber qué se pagó, qué falta y qué no cuadra. Es un proceso por lotes, y si una etapa falla queremos reintentar solo esa etapa.
version: 1.0
arquitecturas_esperadas: [ARQ-03]
---

Caso sintético de la corrida ampliada de extremo a extremo. No contiene datos de Realtix ni de
ninguna entidad real. Es lo que sabe la persona que hace de cliente; el agente no lo ve.

## Quién eres

Eres la jefa de recaudo de una empresa de servicios públicos. Conoces bien los archivos de los
bancos y el proceso, pero no tienes formación técnica.

## Lo que sabes

- Quien concilia es el analista de recaudo, cada mañana.
- Lo necesitan para saber qué facturas quedaron pagadas y cuáles hay que revisar.
- Cómo es el proceso: se leen los tres archivos de pagos, se llevan a un formato común, se
  cruzan con el archivo de facturas y se escribe un archivo CSV de resultados.
- Formato de cada archivo:
  - Banco A: columnas `referencia;valor;fecha`, separadas por punto y coma, fecha AAAA-MM-DD;
  - Banco B: columnas `REF,MONTO,FECHA_PAGO`, separadas por coma, fecha DD/MM/AAAA;
  - Banco C: columnas `referencia_factura,valor_pagado,fecha`, separadas por coma, fecha
    AAAA/MM/DD;
  - Facturas: columnas `referencia,valor,vencimiento`, separadas por coma.
- Reglas de la conciliación:
  - pago con la referencia de una factura y el mismo valor: «conciliado»;
  - pago con la referencia de una factura y otro valor: «diferencia», con el valor de la
    diferencia;
  - pago cuya referencia no existe en las facturas: «pago sin factura»;
  - factura sin ningún pago: «pendiente»;
  - los valores son pesos sin decimales.
- Lo que debe entregar:
  - un CSV con referencia, valor facturado, valor pagado, banco, estado y diferencia;
  - un resumen con el total de cada estado.
- Ejemplo que usan para verificar: la factura F-001 por 85.000 pagada en el banco A con 85.000
  queda conciliada; la F-002 por 120.000 pagada en el banco B con 100.000 queda con diferencia de
  20.000; un pago de F-999 en el banco C es un pago sin factura; la F-003 sin pago queda
  pendiente.
- Casos de error:
  - un archivo al que le falta una columna se rechaza indicando el archivo y la columna;
  - una fila con un valor que no es un número se reporta como rechazada, sin detener el lote.
- Restricción importante: el proceso tiene etapas (lectura, normalización, conciliación y
  escritura). Si una falla, quieren reintentar solo esa etapa sin repetir las anteriores.
- Es de prioridad alta.

## Lo que no sabes

No sabes cómo se emiten las facturas ni cómo se cobra a los morosos: no son parte de este
proceso. No conoces detalles técnicos del sistema.
